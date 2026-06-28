"""Record review of an inert LARQL dry-run packet.

This helper reads a dry-run packet and operator decision, then records whether
the draft is ready for later LARQL apply-packet drafting. It does not apply
LARQL, create an apply packet, mutate durable memory, train LoRA, or promote
the candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_dry_run_review.v0"
REVIEW_STATUS = "review_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
READY_PACKET_VERDICT = "ready_for_larql_dry_run_review"
READY_PACKET_NEXT_STEP = "review_larql_dry_run_packet"

APPROVED = "approve_for_larql_apply_packet_drafting"
REJECTED = "reject_larql_dry_run_packet"

APPROVED_VERDICT = "approved_for_larql_apply_packet_drafting_only"
REJECTED_VERDICT = "rejected_larql_dry_run_packet"

OUTPUT_FILES = ("larql_dry_run_review.json", "larql_dry_run_review.md")


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


def build_checks(packet: dict[str, Any], packet_checks: dict[str, bool]) -> dict[str, bool]:
    checks = dict(packet_checks)
    larql_rule = packet.get("larql_rule_draft")
    if not isinstance(larql_rule, dict):
        larql_rule = {}
    checks.update(
        {
            "report_type_ok": packet.get("report_type") == "affordance_larql_dry_run_packet.v0",
            "packet_verdict_ok": packet.get("packet_verdict") == READY_PACKET_VERDICT,
            "allowed_next_step_ok": packet.get("allowed_next_step") == READY_PACKET_NEXT_STEP,
            "baseline_result_verdict_ok": packet.get("baseline_result_verdict") == "baseline_pass",
            "baseline_audit_verdict_ok": packet.get("baseline_audit_verdict") == "audit_pass",
            "candidate_digest_verified_ok": packet.get("candidate_digest_verified") is True,
            "promotion_held_ok": packet.get("promotion_verdict") == PROMOTION_VERDICT,
            "larql_application_authorized_false": packet.get("larql_application_authorized") is False,
            "candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized")
            is False,
            "durable_memory_authorized_false": packet.get("durable_memory_authorized") is False,
            "lora_training_authorized_false": packet.get("lora_training_authorized") is False,
            "larql_rule_draft_status_ok": larql_rule.get("status") == "draft_not_applied",
        }
    )
    return checks


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "report_type_ok",
        "packet_verdict_ok",
        "allowed_next_step_ok",
        "baseline_result_verdict_ok",
        "baseline_audit_verdict_ok",
        "candidate_digest_verified_ok",
        "promotion_held_ok",
        "larql_application_authorized_false",
        "candidate_promotion_authorized_false",
        "durable_memory_authorized_false",
        "lora_training_authorized_false",
        "larql_rule_draft_status_ok",
    ]
    return all(checks.get(name, False) for name in required)


def review_verdict(checks: dict[str, bool], decision: str) -> str:
    if not packet_ready(checks):
        return "invalid_input"
    if decision == APPROVED:
        return APPROVED_VERDICT
    if decision == REJECTED:
        return REJECTED_VERDICT
    return "invalid_input"


def allowed_next_step(verdict: str) -> str:
    if verdict == APPROVED_VERDICT:
        return "draft_larql_apply_packet"
    if verdict == REJECTED_VERDICT:
        return "revise_larql_dry_run_packet"
    return "repair_or_replace_larql_dry_run_review_inputs"


def disallowed_actions() -> list[str]:
    return [
        "apply_larql_patch",
        "create_apply_packet",
        "mutate_durable_memory",
        "train_lora_adapter",
        "promote_candidate",
        "modify_dry_run_packet",
        "commit_or_push",
    ]


def build_review(packet_path: Path, decision: str, operator_summary: str) -> dict[str, Any]:
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    checks = build_checks(packet, packet_checks)
    verdict = review_verdict(checks, decision)
    notes = [
        *packet_notes,
        "Review only; no LARQL patch is applied.",
        "No durable memory is written.",
        "No LoRA training is authorized.",
        "No candidate promotion is granted.",
        "Approval only permits drafting a later apply packet.",
    ]
    if not packet_ready(checks):
        notes.append("Packet failed one or more required readiness checks.")
    return {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": verdict,
        "allowed_next_step": allowed_next_step(verdict),
        "candidate_id": packet.get("candidate_id"),
        "source_failure_id": packet.get("source_failure_id"),
        "rule_id": (packet.get("larql_rule_draft") or {}).get("rule_id"),
        "promotion_verdict": PROMOTION_VERDICT,
        "larql_application_authorized": False,
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
            "# LARQL Dry-Run Review v0",
            "",
            f"Candidate id: `{review.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{review.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{review.get('rule_id') or 'unknown'}`",
            f"Review verdict: `{review['review_verdict']}`",
            f"Allowed next step: `{review['allowed_next_step']}`",
            f"Promotion verdict: `{review['promotion_verdict']}`",
            "",
            "This is review only.",
            "No LARQL patch is applied.",
            "No durable memory is written.",
            "No LoRA training is authorized.",
            "No candidate promotion is granted.",
            "Approval only permits drafting a later apply packet.",
        ]
    )


def write_reports(packet_path: Path, decision: str, operator_summary: str, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    review = build_review(packet_path, decision, operator_summary)
    (out_dir / OUTPUT_FILES[0]).write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(review) + "\n", encoding="utf-8")
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--decision", required=True, choices=[APPROVED, REJECTED])
    parser.add_argument("--operator-summary", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.packet, args.decision, args.operator_summary, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
