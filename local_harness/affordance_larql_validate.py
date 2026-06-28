"""Validate an applied bounded LARQL rule artifact.

This helper consumes the applied rule artifact plus its application report and
records whether the artifact remains bounded and internally consistent. It does
not install the rule into durable memory, train LoRA, mutate model weights, or
promote the candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_rule_validation.v0"
VALIDATION_STATUS = "completed"
VALIDATION_VERDICT = "larql_rule_artifact_validated"
INVALID_VERDICT = "invalid_input"
ALLOWED_NEXT_STEP = "draft_larql_runtime_install_packet"
REPAIR_NEXT_STEP = "repair_larql_rule_artifact"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"

OUTPUT_FILES = ("larql_rule_validation_report.json", "larql_rule_validation_report.md")


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


def _non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def build_checks(rule: dict[str, Any], apply_report: dict[str, Any], rule_checks: dict[str, bool], report_checks: dict[str, bool]) -> dict[str, bool]:
    checks = {}
    checks.update(rule_checks)
    checks.update(report_checks)
    applies_when = rule.get("applies_when")
    blocks_or_warns_on = rule.get("blocks_or_warns_on")
    recommends = rule.get("recommends")
    requires_reverify_when = rule.get("requires_reverify_when")
    checks.update(
        {
            "rule_report_type_ok": rule.get("report_type") == "affordance_larql_rule.v0",
            "rule_status_ok": rule.get("rule_status") == "applied_as_bounded_artifact",
            "rule_runtime_installation_status_ok": rule.get("runtime_installation_status")
            == "not_installed",
            "rule_durable_memory_status_ok": rule.get("durable_memory_status") == "not_written",
            "rule_candidate_promotion_status_ok": rule.get("candidate_promotion_status")
            == "not_promoted",
            "rule_applies_when_non_empty": _non_empty_list(applies_when),
            "rule_blocks_or_warns_on_non_empty": _non_empty_list(blocks_or_warns_on),
            "rule_recommends_non_empty": _non_empty_list(recommends),
            "rule_requires_reverify_when_non_empty": _non_empty_list(requires_reverify_when),
            "rule_blocks_cuda_nvidia_troubleshooting": any(
                "cuda" in str(item).lower() and "nvidia" in str(item).lower()
                for item in (blocks_or_warns_on or [])
            ),
            "rule_recommends_lm_studio": any(
                "lm studio" in str(item).lower()
                and "openai-compatible endpoint" in str(item).lower()
                for item in (recommends or [])
            ),
            "rule_requires_reverify_conditions": (
                any("unknown" in str(item).lower() for item in (requires_reverify_when or []))
                and any(
                    "remote host differ" in str(item).lower()
                    or "local host and remote host differ" in str(item).lower()
                    for item in (requires_reverify_when or [])
                )
                and any(
                    any(
                        token in str(item).lower()
                        for token in ("stale", "hardware", "gpu", "driver", "endpoint", "host profile")
                    )
                    for item in (requires_reverify_when or [])
                )
                and any("digest" in str(item).lower() for item in (requires_reverify_when or []))
            ),
            "apply_report_report_type_ok": apply_report.get("report_type")
            == "affordance_larql_apply_report.v0",
            "apply_report_verdict_ok": apply_report.get("apply_verdict")
            == "larql_rule_artifact_written",
            "apply_report_next_step_ok": apply_report.get("allowed_next_step")
            == "validate_larql_rule_artifact",
            "apply_report_runtime_behavior_modified_false": apply_report.get(
                "runtime_behavior_modified"
            )
            is False,
            "apply_report_durable_memory_written_false": apply_report.get("durable_memory_written")
            is False,
            "apply_report_candidate_promoted_false": apply_report.get("candidate_promoted") is False,
            "apply_report_lora_training_started_false": apply_report.get("lora_training_started")
            is False,
            "apply_report_model_weights_mutated_false": apply_report.get("model_weights_mutated")
            is False,
            "candidate_id_matches": rule.get("candidate_id") == apply_report.get("candidate_id"),
            "source_failure_id_matches": rule.get("source_failure_id")
            == apply_report.get("source_failure_id"),
            "rule_id_matches": rule.get("rule_id") == apply_report.get("rule_id"),
            "candidate_digest_matches": rule.get("candidate_digest")
            == apply_report.get("candidate_digest"),
        }
    )
    return checks


def validation_ready(checks: dict[str, bool]) -> bool:
    required = [
        "rule_exists",
        "rule_parses",
        "apply_report_exists",
        "apply_report_parses",
        "rule_report_type_ok",
        "rule_status_ok",
        "rule_runtime_installation_status_ok",
        "rule_durable_memory_status_ok",
        "rule_candidate_promotion_status_ok",
        "rule_applies_when_non_empty",
        "rule_blocks_or_warns_on_non_empty",
        "rule_recommends_non_empty",
        "rule_requires_reverify_when_non_empty",
        "rule_blocks_cuda_nvidia_troubleshooting",
        "rule_recommends_lm_studio",
        "rule_requires_reverify_conditions",
        "apply_report_report_type_ok",
        "apply_report_verdict_ok",
        "apply_report_next_step_ok",
        "apply_report_runtime_behavior_modified_false",
        "apply_report_durable_memory_written_false",
        "apply_report_candidate_promoted_false",
        "apply_report_lora_training_started_false",
        "apply_report_model_weights_mutated_false",
        "candidate_id_matches",
        "source_failure_id_matches",
        "rule_id_matches",
        "candidate_digest_matches",
    ]
    return all(checks.get(name, False) for name in required)


def validation_verdict(checks: dict[str, bool]) -> str:
    return VALIDATION_VERDICT if validation_ready(checks) else INVALID_VERDICT


def disallowed_actions() -> list[str]:
    return [
        "install_runtime_rule",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_rule_artifact",
        "modify_apply_report",
        "commit_or_push",
    ]


def build_report(rule: dict[str, Any], apply_report: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    verdict = validation_verdict(checks)
    return {
        "report_type": REPORT_TYPE,
        "validation_status": VALIDATION_STATUS,
        "validation_verdict": verdict,
        "allowed_next_step": ALLOWED_NEXT_STEP if verdict == VALIDATION_VERDICT else REPAIR_NEXT_STEP,
        "rule_id": rule.get("rule_id"),
        "candidate_id": rule.get("candidate_id"),
        "source_failure_id": rule.get("source_failure_id"),
        "candidate_digest": rule.get("candidate_digest"),
        "runtime_installation_authorized": False,
        "durable_memory_authorized": False,
        "candidate_promotion_authorized": False,
        "lora_training_authorized": False,
        "promotion_verdict": PROMOTION_VERDICT,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
    }


def render_markdown(rule: dict[str, Any], report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Rule Validation v0",
            "",
            f"Candidate id: `{rule.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{rule.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{rule.get('rule_id') or 'unknown'}`",
            f"Validation verdict: `{report['validation_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            "",
            "This is validation only.",
            "The rule artifact remains bounded.",
            "Runtime installation is not performed.",
            "Durable memory is not written.",
            "The candidate is not promoted.",
            "LoRA is not trained.",
        ]
    )


def write_reports(rule_path: Path, apply_report_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rule, rule_checks, rule_notes = read_json_object(rule_path, "rule")
    apply_report, report_checks, report_notes = read_json_object(apply_report_path, "apply_report")
    checks = build_checks(rule, apply_report, rule_checks, report_checks)
    report = build_report(rule, apply_report, checks)
    report["notes"] = [
        *rule_notes,
        *report_notes,
        "Validation only; runtime installation is not performed.",
        "No durable memory, LoRA training, or candidate promotion is authorized.",
    ]
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(rule, report) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rule", required=True, type=Path)
    parser.add_argument("--apply-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.rule, args.apply_report, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
