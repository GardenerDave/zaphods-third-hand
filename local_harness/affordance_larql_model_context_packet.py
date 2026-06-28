"""Draft a bounded LARQL model-context packet from consultation evidence.

This helper is model-free. It packages the already-consulted runtime rule,
the consultation result, and user input into an inert packet for later probe
review. It does not call a model, write durable memory, train LoRA, mutate
model weights, or promote the candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_model_context_packet.v0"
PACKET_STATUS = "packet_only"
PACKET_VERDICT = "ready_for_larql_model_response_probe"
ALLOWED_NEXT_STEP = "run_larql_model_response_probe"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = ("larql_model_context_packet.json", "larql_model_context_packet.md")


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


def consultation_ready(consultation: dict[str, Any], runtime_rule: dict[str, Any]) -> bool:
    return all(
        [
            consultation.get("report_type") == "affordance_larql_runtime_consultation_probe.v0",
            consultation.get("consultation_verdict") == "runtime_rule_consulted",
            consultation.get("allowed_next_step") == "draft_larql_model_context_packet",
            consultation.get("matched_runtime_rule") is True,
            consultation.get("model_called") is False,
            consultation.get("durable_memory_written") is False,
            consultation.get("candidate_promoted") is False,
            consultation.get("lora_training_started") is False,
            consultation.get("model_weights_mutated") is False,
            runtime_rule.get("report_type") == "affordance_larql_rule.v0",
            runtime_rule.get("runtime_installation_status") == "installed_for_runtime_consultation",
            runtime_rule.get("runtime_scope") == "consultation_only",
            runtime_rule.get("durable_memory_status") == "not_written",
            runtime_rule.get("candidate_promotion_status") == "not_promoted",
            consultation.get("candidate_id") == runtime_rule.get("candidate_id"),
            consultation.get("source_failure_id") == runtime_rule.get("source_failure_id"),
            consultation.get("candidate_digest") == runtime_rule.get("candidate_digest"),
            consultation.get("rule_id") == runtime_rule.get("rule_id"),
            consultation.get("blocked_path"),
            consultation.get("recommended_path"),
        ]
    )


def contains_trigger(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("cuda", "nvidia"))


def build_runtime_rule_context(runtime_rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": runtime_rule.get("rule_id"),
        "runtime_scope": runtime_rule.get("runtime_scope"),
        "runtime_installation_status": runtime_rule.get("runtime_installation_status"),
        "durable_memory_status": runtime_rule.get("durable_memory_status"),
        "candidate_promotion_status": runtime_rule.get("candidate_promotion_status"),
        "applies_when": runtime_rule.get("applies_when") or [],
        "blocks_or_warns_on": runtime_rule.get("blocks_or_warns_on") or [],
        "recommends": runtime_rule.get("recommends") or [],
        "requires_reverify_when": runtime_rule.get("requires_reverify_when") or [],
    }


def build_model_instruction(runtime_rule: dict[str, Any]) -> str:
    return "\n".join(
        [
            "You are preparing a bounded LARQL model-context packet for later review.",
            "Active host is navigator_desktop.",
            "Host constraint is no_cuda.",
            "CUDA/NVIDIA troubleshooting is blocked on this host.",
            "Recommend the LM Studio OpenAI-compatible endpoint path for the small-model GPU-backed workflow.",
            "Require reverify if host, profile, driver, GPU, endpoint, or digest evidence changes.",
            "Do not claim CUDA is available.",
            "Do not recommend installing NVIDIA CUDA on an RX580/no_cuda host.",
            "Do not apply any rule here.",
            f"Rule id: {runtime_rule.get('rule_id') or 'unknown'}.",
        ]
    )


def disallowed_actions() -> list[str]:
    return [
        "call_model",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_runtime_rule",
        "modify_consultation_probe",
        "commit_or_push",
    ]


def build_report(
    consultation: dict[str, Any],
    runtime_rule: dict[str, Any],
    user_input: str,
    checks: dict[str, bool],
) -> dict[str, Any]:
    consulted = consultation_ready(consultation, runtime_rule)
    return {
        "report_type": REPORT_TYPE,
        "packet_status": PACKET_STATUS,
        "packet_verdict": PACKET_VERDICT if consulted else "invalid_input",
        "allowed_next_step": ALLOWED_NEXT_STEP if consulted else "repair_or_reverify_larql_runtime_consultation_inputs",
        "candidate_id": runtime_rule.get("candidate_id"),
        "source_failure_id": runtime_rule.get("source_failure_id"),
        "rule_id": runtime_rule.get("rule_id"),
        "candidate_digest": runtime_rule.get("candidate_digest"),
        "model_call_authorized": False,
        "durable_memory_authorized": False,
        "candidate_promotion_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "runtime_rule_context": build_runtime_rule_context(runtime_rule) if consulted else {},
        "user_input": user_input,
        "model_instruction": build_model_instruction(runtime_rule) if consulted else "",
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
        "notes": [
            "Packet only; no model is called.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Model Context Packet v0",
            "",
            f"Candidate id: `{report.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{report.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{report.get('rule_id') or 'unknown'}`",
            f"Packet verdict: `{report['packet_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            "",
            "This is packet evidence only.",
            "The packet is not an applied rule.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
            "The model instruction is bounded to navigator_desktop and no_cuda.",
        ]
    )


def write_reports(
    consultation_path: Path,
    runtime_rule_path: Path,
    user_input: str,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    consultation, consultation_checks, consultation_notes = read_json_object(consultation_path, "consultation")
    runtime_rule, rule_checks, rule_notes = read_json_object(runtime_rule_path, "runtime_rule")
    checks = {
        **consultation_checks,
        **rule_checks,
        "consultation_report_type_ok": consultation.get("report_type") == "affordance_larql_runtime_consultation_probe.v0",
        "consultation_verdict_ok": consultation.get("consultation_verdict") == "runtime_rule_consulted",
        "consultation_next_step_ok": consultation.get("allowed_next_step")
        == "draft_larql_model_context_packet",
        "consultation_matched_runtime_rule_true": consultation.get("matched_runtime_rule") is True,
        "consultation_model_called_false": consultation.get("model_called") is False,
        "consultation_durable_memory_written_false": consultation.get("durable_memory_written") is False,
        "consultation_candidate_promoted_false": consultation.get("candidate_promoted") is False,
        "consultation_lora_training_started_false": consultation.get("lora_training_started") is False,
        "consultation_model_weights_mutated_false": consultation.get("model_weights_mutated") is False,
        "runtime_rule_report_type_ok": runtime_rule.get("report_type") == "affordance_larql_rule.v0",
        "runtime_rule_status_ok": runtime_rule.get("runtime_installation_status")
        == "installed_for_runtime_consultation",
        "runtime_rule_scope_ok": runtime_rule.get("runtime_scope") == "consultation_only",
        "runtime_rule_durable_memory_status_ok": runtime_rule.get("durable_memory_status") == "not_written",
        "runtime_rule_candidate_promotion_status_ok": runtime_rule.get("candidate_promotion_status")
        == "not_promoted",
        "candidate_id_matches": consultation.get("candidate_id") == runtime_rule.get("candidate_id"),
        "source_failure_id_matches": consultation.get("source_failure_id")
        == runtime_rule.get("source_failure_id"),
        "rule_id_matches": consultation.get("rule_id") == runtime_rule.get("rule_id"),
        "candidate_digest_matches": consultation.get("candidate_digest") == runtime_rule.get("candidate_digest"),
        "blocked_path_present": bool(consultation.get("blocked_path")),
        "recommended_path_present": bool(consultation.get("recommended_path")),
        "active_host_is_navigator_desktop": "navigator_desktop" in user_input.lower()
        or "navigator_desktop" in build_model_instruction(runtime_rule).lower(),
        "host_constraint_no_cuda": "no_cuda" in build_model_instruction(runtime_rule).lower(),
        "input_has_cuda_nvidia_trigger": contains_trigger(user_input),
    }
    report = build_report(consultation, runtime_rule, user_input, checks)
    if report["packet_verdict"] == "ready_for_larql_model_response_probe":
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(report) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consultation", required=True, type=Path)
    parser.add_argument("--runtime-rule", required=True, type=Path)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.consultation, args.runtime_rule, args.input, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
