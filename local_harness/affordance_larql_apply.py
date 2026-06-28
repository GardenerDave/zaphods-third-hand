"""Apply a bounded LARQL rule artifact from approved packet/review evidence.

This helper writes an inert rule artifact plus an application report. It does
not install the rule into durable memory, train LoRA, mutate model weights,
promote the candidate, or modify runtime behavior.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_apply_report.v0"
RULE_REPORT_TYPE = "affordance_larql_rule.v0"
APPLY_STATUS = "completed"
RULE_STATUS = "applied_as_bounded_artifact"
RUNTIME_INSTALLATION_STATUS = "not_installed"
DURABLE_MEMORY_STATUS = "not_written"
CANDIDATE_PROMOTION_STATUS = "not_promoted"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"

APPROVED_PACKET_VERDICT = "ready_for_larql_apply_review"
APPROVED_REVIEW_VERDICT = "approved_for_larql_application_only"
APPROVED_REVIEW_NEXT_STEP = "apply_larql_rule_from_reviewed_packet"

OUTPUT_FILES = ("larql_rule.json", "larql_rule.md", "larql_apply_report.json", "larql_apply_report.md")


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


def build_checks(apply_packet: dict[str, Any], apply_review: dict[str, Any], packet_checks: dict[str, bool], review_checks: dict[str, bool]) -> dict[str, bool]:
    checks = {}
    checks.update(packet_checks)
    checks.update(review_checks)
    proposed = apply_packet.get("proposed_larql_rule")
    if not isinstance(proposed, dict):
        proposed = {}
    required_rule_fields = [
        proposed.get("rule_id"),
        proposed.get("applies_when"),
        proposed.get("blocks_or_warns_on"),
        proposed.get("recommends"),
        proposed.get("requires_reverify_when"),
    ]
    checks.update(
        {
            "apply_packet_report_type_ok": apply_packet.get("report_type") == "affordance_larql_apply_packet.v0",
            "apply_packet_status_ok": apply_packet.get("packet_status") == "packet_only",
            "apply_packet_verdict_ok": apply_packet.get("packet_verdict") == APPROVED_PACKET_VERDICT,
            "apply_packet_next_step_ok": apply_packet.get("allowed_next_step")
            == "review_larql_apply_packet",
            "apply_packet_promotion_held_ok": apply_packet.get("promotion_verdict") == PROMOTION_VERDICT,
            "apply_packet_larql_application_authorized_false": apply_packet.get(
                "larql_application_authorized"
            )
            is False,
            "apply_packet_candidate_promotion_authorized_false": apply_packet.get(
                "candidate_promotion_authorized"
            )
            is False,
            "apply_packet_durable_memory_authorized_false": apply_packet.get("durable_memory_authorized")
            is False,
            "apply_packet_lora_training_authorized_false": apply_packet.get("lora_training_authorized")
            is False,
            "apply_packet_rule_status_ok": proposed.get("status") == "proposed_not_applied",
            "apply_packet_proposed_rule_fields_present": all(required_rule_fields),
            "apply_packet_candidate_id_present": bool(apply_packet.get("candidate_id")),
            "apply_packet_source_failure_id_present": bool(apply_packet.get("source_failure_id")),
            "apply_packet_rule_id_present": bool(apply_packet.get("rule_id")),
            "apply_packet_candidate_digest_present": bool(apply_packet.get("candidate_digest")),
            "apply_packet_apply_review_criteria_present": bool(apply_packet.get("apply_review_criteria")),
            "apply_review_report_type_ok": apply_review.get("report_type") == "affordance_larql_apply_review.v0",
            "apply_review_status_ok": apply_review.get("review_status") == "review_only",
            "apply_review_verdict_ok": apply_review.get("review_verdict") == APPROVED_REVIEW_VERDICT,
            "apply_review_next_step_ok": apply_review.get("allowed_next_step") == APPROVED_REVIEW_NEXT_STEP,
            "apply_review_promotion_held_ok": apply_review.get("promotion_verdict") == PROMOTION_VERDICT,
            "apply_review_larql_application_authorized_true": apply_review.get("larql_application_authorized") is True,
            "apply_review_candidate_promotion_authorized_false": apply_review.get(
                "candidate_promotion_authorized"
            )
            is False,
            "apply_review_durable_memory_authorized_false": apply_review.get("durable_memory_authorized")
            is False,
            "apply_review_lora_training_authorized_false": apply_review.get("lora_training_authorized")
            is False,
            "candidate_id_matches": apply_review.get("candidate_id") == apply_packet.get("candidate_id"),
            "source_failure_id_matches": apply_review.get("source_failure_id") == apply_packet.get("source_failure_id"),
            "rule_id_matches": apply_review.get("rule_id") == apply_packet.get("rule_id"),
            "candidate_digest_matches": apply_review.get("candidate_digest") == apply_packet.get("candidate_digest"),
        }
    )
    return checks


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "apply_packet_exists",
        "apply_packet_parses",
        "apply_packet_report_type_ok",
        "apply_packet_status_ok",
        "apply_packet_verdict_ok",
        "apply_packet_next_step_ok",
        "apply_packet_promotion_held_ok",
        "apply_packet_larql_application_authorized_false",
        "apply_packet_candidate_promotion_authorized_false",
        "apply_packet_durable_memory_authorized_false",
        "apply_packet_lora_training_authorized_false",
        "apply_packet_rule_status_ok",
        "apply_packet_proposed_rule_fields_present",
        "apply_packet_candidate_id_present",
        "apply_packet_source_failure_id_present",
        "apply_packet_rule_id_present",
        "apply_packet_candidate_digest_present",
        "apply_packet_apply_review_criteria_present",
        "apply_review_exists",
        "apply_review_parses",
        "apply_review_report_type_ok",
        "apply_review_status_ok",
        "apply_review_verdict_ok",
        "apply_review_next_step_ok",
        "apply_review_promotion_held_ok",
        "apply_review_larql_application_authorized_true",
        "apply_review_candidate_promotion_authorized_false",
        "apply_review_durable_memory_authorized_false",
        "apply_review_lora_training_authorized_false",
        "candidate_id_matches",
        "source_failure_id_matches",
        "rule_id_matches",
        "candidate_digest_matches",
    ]
    return all(checks.get(name, False) for name in required)


def proposed_rule(apply_packet: dict[str, Any]) -> dict[str, Any]:
    draft = apply_packet.get("proposed_larql_rule")
    if not isinstance(draft, dict):
        draft = {}
    return {
        "report_type": RULE_REPORT_TYPE,
        "rule_status": RULE_STATUS,
        "runtime_installation_status": RUNTIME_INSTALLATION_STATUS,
        "durable_memory_status": DURABLE_MEMORY_STATUS,
        "candidate_promotion_status": CANDIDATE_PROMOTION_STATUS,
        "rule_id": draft.get("rule_id"),
        "candidate_id": apply_packet.get("candidate_id"),
        "source_failure_id": apply_packet.get("source_failure_id"),
        "candidate_digest": apply_packet.get("candidate_digest"),
        "applies_when": list(draft.get("applies_when") or []),
        "blocks_or_warns_on": list(draft.get("blocks_or_warns_on") or []),
        "recommends": list(draft.get("recommends") or []),
        "requires_reverify_when": list(draft.get("requires_reverify_when") or []),
    }


def apply_report(apply_packet: dict[str, Any], apply_review: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "apply_status": APPLY_STATUS if packet_ready(checks) else "invalid_input",
        "apply_verdict": "larql_rule_artifact_written" if packet_ready(checks) else "invalid_input",
        "allowed_next_step": "validate_larql_rule_artifact" if packet_ready(checks) else "repair_inputs_before_larql_apply",
        "rule_id": apply_packet.get("rule_id"),
        "candidate_id": apply_packet.get("candidate_id"),
        "source_failure_id": apply_packet.get("source_failure_id"),
        "candidate_digest": apply_packet.get("candidate_digest"),
        "promotion_verdict": PROMOTION_VERDICT,
        "larql_rule_artifact_written": bool(packet_ready(checks)),
        "runtime_behavior_modified": False,
        "candidate_promotion_authorized": False,
        "durable_memory_written": False,
        "durable_memory_authorized": False,
        "larql_application_authorized": False,
        "candidate_promoted": False,
        "lora_training_authorized": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "checks": checks,
        "disallowed_actions": [
            "install_runtime_rule",
            "write_durable_memory",
            "train_lora_adapter",
            "mutate_model_weights",
            "promote_candidate",
            "modify_candidate",
            "modify_apply_packet",
            "modify_apply_review",
            "commit_or_push",
        ],
        "notes": [
            "Rule artifact written; runtime installation not performed.",
            "Durable memory not written.",
            "LoRA not trained.",
            "Candidate not promoted.",
        ],
    }


def render_markdown(rule: dict[str, Any], report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Apply Artifact v0",
            "",
            f"Candidate id: `{rule.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{rule.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{rule.get('rule_id') or 'unknown'}`",
            f"Apply verdict: `{report['apply_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            f"Promotion verdict: `{report['promotion_verdict']}`",
            "",
            "This is packet only.",
            "It is not an applied LARQL patch.",
            "It is not durable memory.",
            "It is not LoRA training.",
            "It is not candidate promotion.",
            "The rule artifact is written for later validation; runtime installation is not performed.",
        ]
    )


def write_reports(apply_packet_path: Path, apply_review_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    apply_packet, packet_checks, packet_notes = read_json_object(apply_packet_path, "apply_packet")
    apply_review, review_checks, review_notes = read_json_object(apply_review_path, "apply_review")
    checks = build_checks(apply_packet, apply_review, packet_checks, review_checks)
    rule = proposed_rule(apply_packet)
    report = apply_report(apply_packet, apply_review, checks)
    report["notes"] = [
        *packet_notes,
        *review_notes,
        "Apply artifact only; no runtime installation is performed.",
        "No durable memory, LoRA training, or candidate promotion is authorized.",
    ]
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(rule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(rule, report) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[2]).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / OUTPUT_FILES[3]).write_text(render_markdown(rule, report) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-packet", required=True, type=Path)
    parser.add_argument("--apply-review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.apply_packet, args.apply_review, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
