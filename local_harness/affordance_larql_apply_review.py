"""Record review of an inert LARQL apply packet.

This helper reads a LARQL apply packet and operator decision, then records
whether actual LARQL application is authorized. It does not apply LARQL, create
or modify a real rule file, mutate durable memory, train LoRA, or promote the
candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_apply_review.v0"
REVIEW_STATUS = "review_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
READY_PACKET_VERDICT = "ready_for_larql_apply_review"
READY_PACKET_NEXT_STEP = "review_larql_apply_packet"

APPROVE = "approve_larql_application"
REJECT = "reject_larql_application"

APPROVED_VERDICT = "approved_for_larql_application_only"
REJECTED_VERDICT = "rejected_larql_application"

OUTPUT_FILES = ("larql_apply_review.json", "larql_apply_review.md")


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


def build_checks(apply_packet: dict[str, Any], packet_checks: dict[str, bool]) -> dict[str, bool]:
    checks = dict(packet_checks)
    proposed = apply_packet.get("proposed_larql_rule")
    if not isinstance(proposed, dict):
        proposed = {}
    criteria = apply_packet.get("apply_review_criteria")
    if not isinstance(criteria, list):
        criteria = []
    checks.update(
        {
            "report_type_ok": apply_packet.get("report_type") == "affordance_larql_apply_packet.v0",
            "packet_status_ok": apply_packet.get("packet_status") == "packet_only",
            "packet_verdict_ok": apply_packet.get("packet_verdict")
            == READY_PACKET_VERDICT,
            "allowed_next_step_ok": apply_packet.get("allowed_next_step")
            == READY_PACKET_NEXT_STEP,
            "promotion_held_ok": apply_packet.get("promotion_verdict") == PROMOTION_VERDICT,
            "input_dry_run_packet_verdict_ok": apply_packet.get(
                "input_dry_run_packet_verdict"
            )
            == "ready_for_larql_dry_run_review",
            "input_dry_run_review_verdict_ok": apply_packet.get(
                "input_dry_run_review_verdict"
            )
            == "approved_for_larql_apply_packet_drafting_only",
            "larql_application_authorized_false": apply_packet.get(
                "larql_application_authorized"
            )
            is False,
            "candidate_promotion_authorized_false": apply_packet.get(
                "candidate_promotion_authorized"
            )
            is False,
            "durable_memory_authorized_false": apply_packet.get("durable_memory_authorized") is False,
            "lora_training_authorized_false": apply_packet.get("lora_training_authorized") is False,
            "proposed_rule_status_ok": proposed.get("status") == "proposed_not_applied",
            "candidate_id_present": bool(apply_packet.get("candidate_id")),
            "source_failure_id_present": bool(apply_packet.get("source_failure_id")),
            "rule_id_present": bool(apply_packet.get("rule_id")),
            "candidate_digest_present": bool(apply_packet.get("candidate_digest")),
            "apply_review_criteria_present": bool(criteria),
        }
    )
    return checks


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "report_type_ok",
        "packet_status_ok",
        "packet_verdict_ok",
        "allowed_next_step_ok",
        "promotion_held_ok",
        "input_dry_run_packet_verdict_ok",
        "input_dry_run_review_verdict_ok",
        "larql_application_authorized_false",
        "candidate_promotion_authorized_false",
        "durable_memory_authorized_false",
        "lora_training_authorized_false",
        "proposed_rule_status_ok",
        "candidate_id_present",
        "source_failure_id_present",
        "rule_id_present",
        "candidate_digest_present",
        "apply_review_criteria_present",
    ]
    return all(checks.get(name, False) for name in required)


def review_verdict(checks: dict[str, bool], decision: str) -> str:
    if not packet_ready(checks):
        return "invalid_input"
    if decision == APPROVE:
        return APPROVED_VERDICT
    if decision == REJECT:
        return REJECTED_VERDICT
    return "invalid_input"


def allowed_next_step(verdict: str) -> str:
    if verdict == APPROVED_VERDICT:
        return "apply_larql_rule_from_reviewed_packet"
    if verdict == REJECTED_VERDICT:
        return "revise_larql_apply_packet"
    return "repair_or_replace_larql_apply_review_inputs"


def disallowed_actions() -> list[str]:
    return [
        "apply_larql_patch",
        "modify_larql_rule_file",
        "mutate_durable_memory",
        "train_lora_adapter",
        "promote_candidate",
        "modify_apply_packet",
        "commit_or_push",
    ]


def build_review(apply_packet_path: Path, decision: str, operator_summary: str) -> dict[str, Any]:
    apply_packet, packet_checks, packet_notes = read_json_object(apply_packet_path, "packet")
    checks = build_checks(apply_packet, packet_checks)
    verdict = review_verdict(checks, decision)
    notes = [
        *packet_notes,
        "Review only; no LARQL patch is applied by this review.",
        "No durable memory is written.",
        "No LoRA training is authorized.",
        "No candidate promotion is granted.",
        "Approval only authorizes a later apply step.",
    ]
    if not packet_ready(checks):
        notes.append("Apply packet failed one or more required readiness checks.")
    return {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": verdict,
        "allowed_next_step": allowed_next_step(verdict),
        "candidate_id": apply_packet.get("candidate_id"),
        "source_failure_id": apply_packet.get("source_failure_id"),
        "rule_id": apply_packet.get("rule_id"),
        "candidate_digest": apply_packet.get("candidate_digest"),
        "promotion_verdict": PROMOTION_VERDICT,
        "larql_application_authorized": verdict == APPROVED_VERDICT,
        "candidate_promotion_authorized": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "operator_decision": decision,
        "operator_summary": operator_summary,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
        "notes": notes,
    }


def render_markdown(review: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Apply Review v0",
            "",
            f"Candidate id: `{review.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{review.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{review.get('rule_id') or 'unknown'}`",
            f"Review verdict: `{review['review_verdict']}`",
            f"Allowed next step: `{review['allowed_next_step']}`",
            f"Promotion verdict: `{review['promotion_verdict']}`",
            "",
            "This is review only.",
            "No LARQL patch is applied by this review.",
            "No durable memory is written.",
            "No LoRA training is authorized.",
            "No candidate promotion is granted.",
            "Approval only authorizes a later apply step.",
        ]
    )


def write_reports(apply_packet_path: Path, decision: str, operator_summary: str, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    review = build_review(apply_packet_path, decision, operator_summary)
    (out_dir / OUTPUT_FILES[0]).write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(review) + "\n", encoding="utf-8")
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-packet", required=True, type=Path)
    parser.add_argument("--decision", required=True, choices=[APPROVE, REJECT])
    parser.add_argument("--operator-summary", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.apply_packet, args.decision, args.operator_summary, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
