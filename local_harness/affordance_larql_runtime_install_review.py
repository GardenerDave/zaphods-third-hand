"""Record review of an inert LARQL runtime install packet.

This helper reads a runtime-install packet and operator decision, then records
whether runtime installation is authorized. It does not install the rule,
write durable memory, train LoRA, mutate model weights, or promote the
candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_runtime_install_review.v0"
REVIEW_STATUS = "review_only"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
READY_PACKET_VERDICT = "ready_for_runtime_install_review"
READY_PACKET_NEXT_STEP = "review_larql_runtime_install_packet"

APPROVE = "approve_runtime_install"
REJECT = "reject_runtime_install"

APPROVED_VERDICT = "approved_for_runtime_installation_only"
REJECTED_VERDICT = "rejected_runtime_installation"

OUTPUT_FILES = ("larql_runtime_install_review.json", "larql_runtime_install_review.md")


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
    rule_payload = packet.get("rule_payload")
    if not isinstance(rule_payload, dict):
        rule_payload = {}
    checks.update(
        {
            "report_type_ok": packet.get("report_type") == "affordance_larql_runtime_install_packet.v0",
            "packet_status_ok": packet.get("packet_status") == "packet_only",
            "packet_verdict_ok": packet.get("packet_verdict") == READY_PACKET_VERDICT,
            "allowed_next_step_ok": packet.get("allowed_next_step") == READY_PACKET_NEXT_STEP,
            "proposed_runtime_action_ok": packet.get("proposed_runtime_action")
            == "install_rule_for_runtime_consultation_only",
            "packet_runtime_installation_authorized_false": packet.get("runtime_installation_authorized")
            is False,
            "packet_durable_memory_authorized_false": packet.get("durable_memory_authorized") is False,
            "packet_candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized")
            is False,
            "packet_lora_training_authorized_false": packet.get("lora_training_authorized") is False,
            "rule_payload_present": bool(rule_payload),
            "rule_payload_runtime_installation_status_ok": rule_payload.get("runtime_installation_status")
            == "not_installed",
            "rule_payload_rule_status_ok": rule_payload.get("rule_status") == "applied_as_bounded_artifact",
            "rule_payload_durable_memory_status_ok": rule_payload.get("durable_memory_status")
            == "not_written",
            "rule_payload_candidate_promotion_status_ok": rule_payload.get("candidate_promotion_status")
            == "not_promoted",
            "candidate_id_matches": packet.get("candidate_id") == rule_payload.get("candidate_id"),
            "source_failure_id_matches": packet.get("source_failure_id")
            == rule_payload.get("source_failure_id"),
            "rule_id_matches": packet.get("rule_id") == rule_payload.get("rule_id"),
            "candidate_digest_matches": packet.get("candidate_digest")
            == rule_payload.get("candidate_digest"),
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
        "proposed_runtime_action_ok",
        "packet_runtime_installation_authorized_false",
        "packet_durable_memory_authorized_false",
        "packet_candidate_promotion_authorized_false",
        "packet_lora_training_authorized_false",
        "rule_payload_present",
        "rule_payload_runtime_installation_status_ok",
        "rule_payload_rule_status_ok",
        "rule_payload_durable_memory_status_ok",
        "rule_payload_candidate_promotion_status_ok",
        "candidate_id_matches",
        "source_failure_id_matches",
        "rule_id_matches",
        "candidate_digest_matches",
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
        return "install_larql_runtime_rule_from_reviewed_packet"
    if verdict == REJECTED_VERDICT:
        return "revise_larql_runtime_install_packet"
    return "repair_or_replace_larql_runtime_install_review_inputs"


def disallowed_actions() -> list[str]:
    return [
        "install_runtime_rule",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_runtime_install_packet",
        "commit_or_push",
    ]


def build_review(packet: dict[str, Any], decision: str, operator_summary: str) -> dict[str, Any]:
    checks = build_checks(packet, {})
    verdict = review_verdict(checks, decision)
    return {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": verdict,
        "allowed_next_step": allowed_next_step(verdict),
        "rule_id": packet.get("rule_id"),
        "candidate_id": packet.get("candidate_id"),
        "source_failure_id": packet.get("source_failure_id"),
        "candidate_digest": packet.get("candidate_digest"),
        "promotion_verdict": PROMOTION_VERDICT,
        "runtime_installation_authorized": verdict == APPROVED_VERDICT,
        "durable_memory_authorized": False,
        "candidate_promotion_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "operator_decision": decision,
        "operator_summary": operator_summary,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
        "notes": [
            "Review only; no runtime rule is installed.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "Approval only authorizes a later install step.",
        ],
    }


def render_markdown(review: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Runtime Install Review v0",
            "",
            f"Candidate id: `{review.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{review.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{review.get('rule_id') or 'unknown'}`",
            f"Review verdict: `{review['review_verdict']}`",
            f"Allowed next step: `{review['allowed_next_step']}`",
            "",
            "This is review only.",
            "No runtime rule is installed.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "Approval only authorizes a later install step.",
        ]
    )


def write_reports(packet_path: Path, decision: str, operator_summary: str, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    checks = build_checks(packet, packet_checks)
    verdict = review_verdict(checks, decision)
    review = {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": verdict,
        "allowed_next_step": allowed_next_step(verdict),
        "rule_id": packet.get("rule_id"),
        "candidate_id": packet.get("candidate_id"),
        "source_failure_id": packet.get("source_failure_id"),
        "candidate_digest": packet.get("candidate_digest"),
        "promotion_verdict": PROMOTION_VERDICT,
        "runtime_installation_authorized": verdict == APPROVED_VERDICT,
        "durable_memory_authorized": False,
        "candidate_promotion_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "operator_decision": decision,
        "operator_summary": operator_summary,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
        "notes": [
            *packet_notes,
            "Review only; no runtime rule is installed.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "Approval only authorizes a later install step.",
        ],
    }
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(review) + "\n", encoding="utf-8")
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--decision", required=True, choices=[APPROVE, REJECT])
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
