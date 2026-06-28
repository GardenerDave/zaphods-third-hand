"""Run a model-free consultation probe against a validated LARQL runtime rule.

This helper checks whether a user input should consult the runtime rule and
records a bounded result. It does not call a model, write durable memory,
train LoRA, mutate model weights, or promote the candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_runtime_consultation_probe.v0"
PROBE_STATUS = "completed"
CONSULTATION_VERDICT = "runtime_rule_consulted"
NOT_CONSULTED_VERDICT = "runtime_rule_not_consulted"
ALLOWED_NEXT_STEP = "draft_larql_model_context_packet"
REPAIR_NEXT_STEP = "repair_or_reverify_larql_runtime_consultation_inputs"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"

OUTPUT_FILES = ("larql_runtime_consultation_probe.json", "larql_runtime_consultation_probe.md")


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def read_json_object(path: Path, label: str) -> tuple[dict[str, Any], dict[str, bool], list[str]]:
    checks = {f"{label}_exists": path.exists(), f"{label}_parses": False}
    notes: list[str] = []
    if not checks[f"{label}_exists"]:
        notes.append(f"{label} missing: {path}")
        return {}, checks, notes
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        notes.append(f"{label} JSON parse failed: {exc.msg}")
        return {}, checks, notes
    if not isinstance(payload, dict):
        notes.append(f"{label} is not a JSON object.")
        return {}, checks, notes
    checks[f"{label}_parses"] = True
    return payload, checks, notes


def runtime_rule_ready(runtime_rule: dict[str, Any], validation: dict[str, Any]) -> bool:
    return all(
        [
            runtime_rule.get("report_type") == "affordance_larql_rule.v0",
            runtime_rule.get("runtime_installation_status") == "installed_for_runtime_consultation",
            runtime_rule.get("runtime_scope") == "consultation_only",
            runtime_rule.get("durable_memory_status") == "not_written",
            runtime_rule.get("candidate_promotion_status") == "not_promoted",
            validation.get("report_type") == "affordance_larql_runtime_install_validation.v0",
            validation.get("validation_verdict") == "larql_runtime_install_validated",
            validation.get("allowed_next_step") == "run_larql_runtime_consultation_probe",
            validation.get("runtime_rule_validated_for_consultation") is True,
            validation.get("durable_memory_written") is False,
            validation.get("candidate_promoted") is False,
            validation.get("lora_training_started") is False,
            validation.get("model_weights_mutated") is False,
            runtime_rule.get("candidate_id") == validation.get("candidate_id"),
            runtime_rule.get("source_failure_id") == validation.get("source_failure_id"),
            runtime_rule.get("rule_id") == validation.get("rule_id"),
            runtime_rule.get("candidate_digest") == validation.get("candidate_digest"),
        ]
    )


def has_cuda_nvidia_trigger(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("cuda", "nvidia"))


def runtime_rule_requires_reverify(runtime_rule: dict[str, Any]) -> bool:
    items = [str(item).lower() for item in (runtime_rule.get("requires_reverify_when") or [])]
    return all(
        [
            any("active host is unknown" in item or "unknown host" in item for item in items),
            any("local host and remote host differ" in item for item in items),
            any("hardware, gpu, driver, endpoint, or host profile may have changed" in item for item in items),
            any("candidate digest or source digests do not match" in item for item in items),
        ]
    )



def build_checks(
    runtime_rule: dict[str, Any],
    validation: dict[str, Any],
    active_host: str,
    host_constraint: str,
    user_input: str,
    rule_checks: dict[str, bool],
    validation_checks: dict[str, bool],
) -> dict[str, bool]:
    checks = {}
    checks.update(rule_checks)
    checks.update(validation_checks)
    checks.update(
        {
            "runtime_rule_report_type_ok": runtime_rule.get("report_type") == "affordance_larql_rule.v0",
            "runtime_rule_status_ok": runtime_rule.get("runtime_installation_status")
            == "installed_for_runtime_consultation",
            "runtime_scope_ok": runtime_rule.get("runtime_scope") == "consultation_only",
            "runtime_rule_durable_memory_status_ok": runtime_rule.get("durable_memory_status") == "not_written",
            "runtime_rule_candidate_promotion_status_ok": runtime_rule.get("candidate_promotion_status")
            == "not_promoted",
            "validation_report_type_ok": validation.get("report_type")
            == "affordance_larql_runtime_install_validation.v0",
            "validation_verdict_ok": validation.get("validation_verdict")
            == "larql_runtime_install_validated",
            "validation_next_step_ok": validation.get("allowed_next_step")
            == "run_larql_runtime_consultation_probe",
            "validation_runtime_rule_validated_for_consultation_true": validation.get(
                "runtime_rule_validated_for_consultation"
            )
            is True,
            "validation_durable_memory_written_false": validation.get("durable_memory_written") is False,
            "validation_candidate_promoted_false": validation.get("candidate_promoted") is False,
            "validation_lora_training_started_false": validation.get("lora_training_started") is False,
            "validation_model_weights_mutated_false": validation.get("model_weights_mutated") is False,
            "candidate_id_matches": runtime_rule.get("candidate_id") == validation.get("candidate_id"),
            "source_failure_id_matches": runtime_rule.get("source_failure_id")
            == validation.get("source_failure_id"),
            "rule_id_matches": runtime_rule.get("rule_id") == validation.get("rule_id"),
            "candidate_digest_matches": runtime_rule.get("candidate_digest")
            == validation.get("candidate_digest"),
            "active_host_matches": active_host == "navigator_desktop",
            "host_constraint_matches": host_constraint == "no_cuda",
            "input_has_cuda_nvidia_trigger": has_cuda_nvidia_trigger(user_input),
            "rule_blocks_cuda_nvidia": any(
                "cuda" in str(item).lower() and "nvidia" in str(item).lower()
                for item in (runtime_rule.get("blocks_or_warns_on") or [])
            ),
            "rule_recommends_lm_studio": any(
                "lm studio" in str(item).lower()
                and "openai-compatible endpoint" in str(item).lower()
                for item in (runtime_rule.get("recommends") or [])
            ),
            "rule_requires_reverify": runtime_rule_requires_reverify(runtime_rule),
        }
    )
    return checks


def consultation_verdict(checks: dict[str, bool]) -> str:
    required = [
        "runtime_rule_exists",
        "runtime_rule_parses",
        "validation_exists",
        "validation_parses",
        "runtime_rule_report_type_ok",
        "runtime_rule_status_ok",
        "runtime_scope_ok",
        "runtime_rule_durable_memory_status_ok",
        "runtime_rule_candidate_promotion_status_ok",
        "validation_report_type_ok",
        "validation_verdict_ok",
        "validation_next_step_ok",
        "validation_runtime_rule_validated_for_consultation_true",
        "validation_durable_memory_written_false",
        "validation_candidate_promoted_false",
        "validation_lora_training_started_false",
        "validation_model_weights_mutated_false",
        "candidate_id_matches",
        "source_failure_id_matches",
        "rule_id_matches",
        "candidate_digest_matches",
        "active_host_matches",
        "host_constraint_matches",
        "input_has_cuda_nvidia_trigger",
        "rule_blocks_cuda_nvidia",
        "rule_recommends_lm_studio",
        "rule_requires_reverify",
    ]
    if all(checks.get(name, False) for name in required):
        return CONSULTATION_VERDICT
    return NOT_CONSULTED_VERDICT


def disallowed_actions() -> list[str]:
    return [
        "call_model",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_runtime_rule",
        "modify_validation_report",
        "commit_or_push",
    ]


def build_report(runtime_rule: dict[str, Any], validation: dict[str, Any], active_host: str, host_constraint: str, user_input: str, checks: dict[str, bool]) -> dict[str, Any]:
    verdict = consultation_verdict(checks)
    matched = verdict == CONSULTATION_VERDICT
    return {
        "report_type": REPORT_TYPE,
        "probe_status": PROBE_STATUS,
        "consultation_verdict": verdict,
        "allowed_next_step": ALLOWED_NEXT_STEP if matched else REPAIR_NEXT_STEP,
        "rule_id": runtime_rule.get("rule_id"),
        "candidate_id": runtime_rule.get("candidate_id"),
        "source_failure_id": runtime_rule.get("source_failure_id"),
        "candidate_digest": runtime_rule.get("candidate_digest"),
        "matched_runtime_rule": matched,
        "blocked_path": "CUDA/NVIDIA troubleshooting path on RX580/no_cuda host" if matched else "",
        "recommended_path": "LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow" if matched else "",
        "requires_reverify": not matched,
        "model_called": False,
        "durable_memory_written": False,
        "candidate_promoted": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
        "notes": [
            "Consultation probe only; no model is called.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Runtime Consultation Probe v0",
            "",
            f"Candidate id: `{report.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{report.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{report.get('rule_id') or 'unknown'}`",
            f"Consultation verdict: `{report['consultation_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            "",
            "This is consultation probe evidence only.",
            "No model is called.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
        ]
    )


def write_reports(runtime_rule_path: Path, validation_path: Path, active_host: str, host_constraint: str, user_input: str, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime_rule, rule_checks, rule_notes = read_json_object(runtime_rule_path, "runtime_rule")
    validation, validation_checks, validation_notes = read_json_object(validation_path, "validation")
    checks = build_checks(runtime_rule, validation, active_host, host_constraint, user_input, rule_checks, validation_checks)
    report = build_report(runtime_rule, validation, active_host, host_constraint, user_input, checks)
    report["notes"] = [*rule_notes, *validation_notes, *report["notes"]]
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(report) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-rule", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--active-host", required=True)
    parser.add_argument("--host-constraint", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.runtime_rule, args.validation, args.active_host, args.host_constraint, args.input, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
