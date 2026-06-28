"""Validate a LARQL runtime-install artifact and install report.

This helper consumes a runtime rule artifact and install report, then records
whether the runtime rule is internally consistent for consultation only. It
does not call a model, write durable memory, train LoRA, mutate weights, or
promote the candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_runtime_install_validation.v0"
VALIDATION_STATUS = "completed"
VALIDATION_VERDICT = "larql_runtime_install_validated"
INVALID_VERDICT = "invalid_input"
ALLOWED_NEXT_STEP = "run_larql_runtime_consultation_probe"
REPAIR_NEXT_STEP = "repair_larql_runtime_install"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"

OUTPUT_FILES = ("larql_runtime_install_validation_report.json", "larql_runtime_install_validation_report.md")


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


def build_checks(runtime_rule: dict[str, Any], install_report: dict[str, Any], rule_checks: dict[str, bool], report_checks: dict[str, bool]) -> dict[str, bool]:
    checks = {}
    checks.update(rule_checks)
    checks.update(report_checks)
    checks.update(
        {
            "runtime_rule_report_type_ok": runtime_rule.get("report_type") == "affordance_larql_rule.v0",
            "runtime_rule_status_ok": runtime_rule.get("runtime_installation_status")
            == "installed_for_runtime_consultation",
            "runtime_rule_scope_ok": runtime_rule.get("runtime_scope") == "consultation_only",
            "runtime_rule_installed_from_review_ok": runtime_rule.get("installed_from_review")
            == "approved_for_runtime_installation_only",
            "runtime_rule_durable_memory_status_ok": runtime_rule.get("durable_memory_status")
            == "not_written",
            "runtime_rule_candidate_promotion_status_ok": runtime_rule.get("candidate_promotion_status")
            == "not_promoted",
            "runtime_rule_blocks_cuda_nvidia": any(
                "cuda" in str(item).lower() and "nvidia" in str(item).lower()
                for item in (runtime_rule.get("blocks_or_warns_on") or [])
            ),
            "runtime_rule_recommends_lm_studio": any(
                "lm studio" in str(item).lower()
                and "openai-compatible endpoint" in str(item).lower()
                for item in (runtime_rule.get("recommends") or [])
            ),
            "runtime_rule_requires_reverify": (
                any(
                    "unknown host" in str(item).lower() or "active host is unknown" in str(item).lower()
                    for item in (runtime_rule.get("requires_reverify_when") or [])
                )
                and any(
                    "local host and remote host differ" in str(item).lower()
                    or "split" in str(item).lower()
                    for item in (runtime_rule.get("requires_reverify_when") or [])
                )
                and any(
                    any(
                        token in str(item).lower()
                        for token in ("hardware", "gpu", "driver", "endpoint", "host profile")
                    )
                    for item in (runtime_rule.get("requires_reverify_when") or [])
                )
                and any("digest" in str(item).lower() for item in (runtime_rule.get("requires_reverify_when") or []))
            ),
            "install_report_report_type_ok": install_report.get("report_type")
            == "affordance_larql_runtime_install_report.v0",
            "install_report_verdict_ok": install_report.get("install_verdict")
            == "runtime_rule_installed_for_consultation",
            "install_report_next_step_ok": install_report.get("allowed_next_step")
            == "validate_larql_runtime_install",
            "install_report_runtime_rule_written_true": install_report.get("runtime_rule_written")
            is True,
            "install_report_durable_memory_written_false": install_report.get("durable_memory_written")
            is False,
            "install_report_candidate_promoted_false": install_report.get("candidate_promoted") is False,
            "install_report_lora_training_started_false": install_report.get("lora_training_started") is False,
            "install_report_model_weights_mutated_false": install_report.get("model_weights_mutated")
            is False,
            "rule_id_matches": runtime_rule.get("rule_id") == install_report.get("rule_id"),
            "candidate_id_matches": runtime_rule.get("candidate_id") == install_report.get("candidate_id"),
            "source_failure_id_matches": runtime_rule.get("source_failure_id")
            == install_report.get("source_failure_id"),
            "candidate_digest_matches": runtime_rule.get("candidate_digest")
            == install_report.get("candidate_digest"),
        }
    )
    return checks


def validation_ready(checks: dict[str, bool]) -> bool:
    required = [
        "runtime_rule_exists",
        "runtime_rule_parses",
        "install_report_exists",
        "install_report_parses",
        "runtime_rule_report_type_ok",
        "runtime_rule_status_ok",
        "runtime_rule_scope_ok",
        "runtime_rule_installed_from_review_ok",
        "runtime_rule_durable_memory_status_ok",
        "runtime_rule_candidate_promotion_status_ok",
        "runtime_rule_blocks_cuda_nvidia",
        "runtime_rule_recommends_lm_studio",
        "runtime_rule_requires_reverify",
        "install_report_report_type_ok",
        "install_report_verdict_ok",
        "install_report_next_step_ok",
        "install_report_runtime_rule_written_true",
        "install_report_durable_memory_written_false",
        "install_report_candidate_promoted_false",
        "install_report_lora_training_started_false",
        "install_report_model_weights_mutated_false",
        "rule_id_matches",
        "candidate_id_matches",
        "source_failure_id_matches",
        "candidate_digest_matches",
    ]
    return all(checks.get(name, False) for name in required)


def disallowed_actions() -> list[str]:
    return [
        "call_model",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_runtime_rule",
        "modify_install_report",
        "commit_or_push",
    ]


def build_report(runtime_rule: dict[str, Any], install_report: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    verdict = VALIDATION_VERDICT if validation_ready(checks) else INVALID_VERDICT
    return {
        "report_type": REPORT_TYPE,
        "validation_status": VALIDATION_STATUS,
        "validation_verdict": verdict,
        "allowed_next_step": ALLOWED_NEXT_STEP if verdict == VALIDATION_VERDICT else REPAIR_NEXT_STEP,
        "rule_id": runtime_rule.get("rule_id"),
        "candidate_id": runtime_rule.get("candidate_id"),
        "source_failure_id": runtime_rule.get("source_failure_id"),
        "candidate_digest": runtime_rule.get("candidate_digest"),
        "runtime_rule_validated_for_consultation": verdict == VALIDATION_VERDICT,
        "durable_memory_written": False,
        "candidate_promoted": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "promotion_verdict": PROMOTION_VERDICT,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
    }


def render_markdown(runtime_rule: dict[str, Any], report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Runtime Install Validation v0",
            "",
            f"Candidate id: `{runtime_rule.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{runtime_rule.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{runtime_rule.get('rule_id') or 'unknown'}`",
            f"Validation verdict: `{report['validation_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            "",
            "This is validation only.",
            "The runtime rule remains consultation-only.",
            "No model is called.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
        ]
    )


def write_reports(runtime_rule_path: Path, install_report_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime_rule, rule_checks, rule_notes = read_json_object(runtime_rule_path, "runtime_rule")
    install_report, report_checks, report_notes = read_json_object(install_report_path, "install_report")
    checks = build_checks(runtime_rule, install_report, rule_checks, report_checks)
    report = build_report(runtime_rule, install_report, checks)
    report["notes"] = [
        *rule_notes,
        *report_notes,
        "Validation only; no model is called.",
        "No durable memory, LoRA training, or candidate promotion is authorized.",
    ]
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(runtime_rule, report) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-rule", required=True, type=Path)
    parser.add_argument("--install-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.runtime_rule, args.install_report, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
