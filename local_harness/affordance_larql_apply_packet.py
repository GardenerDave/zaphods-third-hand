"""Draft a model-free LARQL apply packet.

This helper consumes an inert LARQL dry-run packet and approved dry-run review
then writes a bounded apply-packet draft. It does not apply LARQL, mutate
durable memory, train LoRA, or promote the candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_apply_packet.v0"
PACKET_STATUS = "packet_only"
PACKET_VERDICT = "ready_for_larql_apply_review"
ALLOWED_NEXT_STEP = "review_larql_apply_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"

OUTPUT_FILES = ("larql_apply_packet.json", "larql_apply_packet.md")


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


def build_checks(
    dry_run_packet: dict[str, Any],
    dry_run_review: dict[str, Any],
    packet_checks: dict[str, bool],
    review_checks: dict[str, bool],
) -> dict[str, bool]:
    checks = {}
    checks.update(packet_checks)
    checks.update(review_checks)
    larql_rule = dry_run_packet.get("larql_rule_draft")
    if not isinstance(larql_rule, dict):
        larql_rule = {}
    checks.update(
        {
            "dry_run_packet_report_type_ok": dry_run_packet.get("report_type")
            == "affordance_larql_dry_run_packet.v0",
            "dry_run_packet_verdict_ok": dry_run_packet.get("packet_verdict")
            == "ready_for_larql_dry_run_review",
            "dry_run_packet_next_step_ok": dry_run_packet.get("allowed_next_step")
            == "review_larql_dry_run_packet",
            "dry_run_packet_baseline_verdict_ok": dry_run_packet.get("baseline_result_verdict")
            == "baseline_pass",
            "dry_run_packet_audit_verdict_ok": dry_run_packet.get("baseline_audit_verdict")
            == "audit_pass",
            "dry_run_packet_candidate_digest_verified_ok": dry_run_packet.get(
                "candidate_digest_verified"
            )
            is True,
            "dry_run_packet_promotion_held_ok": dry_run_packet.get("promotion_verdict")
            == PROMOTION_VERDICT,
            "dry_run_packet_larql_application_authorized_false": dry_run_packet.get(
                "larql_application_authorized"
            )
            is False,
            "dry_run_packet_candidate_promotion_authorized_false": dry_run_packet.get(
                "candidate_promotion_authorized"
            )
            is False,
            "dry_run_packet_durable_memory_authorized_false": dry_run_packet.get(
                "durable_memory_authorized"
            )
            is False,
            "dry_run_packet_lora_training_authorized_false": dry_run_packet.get(
                "lora_training_authorized"
            )
            is False,
            "dry_run_packet_rule_status_ok": larql_rule.get("status") == "draft_not_applied",
            "dry_run_review_report_type_ok": dry_run_review.get("report_type")
            == "affordance_larql_dry_run_review.v0",
            "dry_run_review_verdict_ok": dry_run_review.get("review_verdict")
            == "approved_for_larql_apply_packet_drafting_only",
            "dry_run_review_next_step_ok": dry_run_review.get("allowed_next_step")
            == "draft_larql_apply_packet",
            "dry_run_review_promotion_held_ok": dry_run_review.get("promotion_verdict")
            == PROMOTION_VERDICT,
            "dry_run_review_larql_application_authorized_false": dry_run_review.get(
                "larql_application_authorized"
            )
            is False,
            "dry_run_review_candidate_promotion_authorized_false": dry_run_review.get(
                "candidate_promotion_authorized"
            )
            is False,
            "dry_run_review_durable_memory_authorized_false": dry_run_review.get(
                "durable_memory_authorized"
            )
            is False,
            "dry_run_review_lora_training_authorized_false": dry_run_review.get(
                "lora_training_authorized"
            )
            is False,
            "candidate_id_matches": dry_run_review.get("candidate_id")
            == dry_run_packet.get("candidate_id"),
            "source_failure_id_matches": dry_run_review.get("source_failure_id")
            == dry_run_packet.get("source_failure_id"),
            "rule_id_matches": dry_run_review.get("rule_id")
            == (dry_run_packet.get("larql_rule_draft") or {}).get("rule_id"),
        }
    )
    return checks


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "dry_run_packet_report_type_ok",
        "dry_run_packet_verdict_ok",
        "dry_run_packet_next_step_ok",
        "dry_run_packet_baseline_verdict_ok",
        "dry_run_packet_audit_verdict_ok",
        "dry_run_packet_candidate_digest_verified_ok",
        "dry_run_packet_promotion_held_ok",
        "dry_run_packet_larql_application_authorized_false",
        "dry_run_packet_candidate_promotion_authorized_false",
        "dry_run_packet_durable_memory_authorized_false",
        "dry_run_packet_lora_training_authorized_false",
        "dry_run_packet_rule_status_ok",
        "review_exists",
        "review_parses",
        "dry_run_review_report_type_ok",
        "dry_run_review_verdict_ok",
        "dry_run_review_next_step_ok",
        "dry_run_review_promotion_held_ok",
        "dry_run_review_larql_application_authorized_false",
        "dry_run_review_candidate_promotion_authorized_false",
        "dry_run_review_durable_memory_authorized_false",
        "dry_run_review_lora_training_authorized_false",
        "candidate_id_matches",
        "source_failure_id_matches",
        "rule_id_matches",
    ]
    return all(checks.get(name, False) for name in required)


def larql_rule_draft(dry_run_packet: dict[str, Any]) -> dict[str, Any]:
    draft = dry_run_packet.get("larql_rule_draft")
    if not isinstance(draft, dict):
        draft = {}
    return {
        "rule_id": draft.get("rule_id"),
        "status": "proposed_not_applied",
        "applies_when": list(draft.get("applies_when") or []),
        "blocks_or_warns_on": list(draft.get("blocks_or_warns_on") or []),
        "recommends": list(draft.get("recommends") or []),
        "requires_reverify_when": list(draft.get("requires_reverify_when") or []),
    }


def apply_review_criteria(dry_run_packet: dict[str, Any]) -> list[str]:
    rule = larql_rule_draft(dry_run_packet)
    return [
        "Rule remains scoped to navigator_desktop or matching host evidence/profile constraints.",
        "Rule blocks or warns on CUDA/NVIDIA troubleshooting for RX580/no_cuda hosts.",
        "Rule recommends the LM Studio OpenAI-compatible endpoint path only under matching evidence.",
        "Rule requires reverify when active host is unknown, split, stale, or digest evidence mismatches.",
        "Rule does not promote the candidate or write durable memory.",
    ]


def review_verdict(checks: dict[str, bool]) -> str:
    return "invalid_input" if not packet_ready(checks) else PACKET_VERDICT


def disallowed_actions() -> list[str]:
    return [
        "apply_larql_patch",
        "mutate_durable_memory",
        "train_lora_adapter",
        "promote_candidate",
        "modify_dry_run_packet",
        "modify_dry_run_review",
        "commit_or_push",
    ]


def build_packet(
    dry_run_packet_path: Path,
    dry_run_review_path: Path,
) -> dict[str, Any]:
    dry_run_packet, packet_checks, packet_notes = read_json_object(dry_run_packet_path, "packet")
    dry_run_review, review_checks, review_notes = read_json_object(dry_run_review_path, "review")
    checks = build_checks(dry_run_packet, dry_run_review, packet_checks, review_checks)
    verdict = review_verdict(checks)
    notes = [
        *packet_notes,
        *review_notes,
        "Apply-packet draft only; no LARQL patch is applied.",
        "No durable memory, LoRA training, or candidate promotion is authorized.",
    ]
    return {
        "report_type": REPORT_TYPE,
        "packet_status": PACKET_STATUS,
        "packet_verdict": verdict,
        "allowed_next_step": ALLOWED_NEXT_STEP if verdict == PACKET_VERDICT else "repair_inputs_before_larql_apply_packet",
        "candidate_id": dry_run_packet.get("candidate_id"),
        "source_failure_id": dry_run_packet.get("source_failure_id"),
        "rule_id": (dry_run_packet.get("larql_rule_draft") or {}).get("rule_id"),
        "candidate_digest": dry_run_packet.get("candidate_digest"),
        "promotion_verdict": PROMOTION_VERDICT,
        "larql_application_authorized": False,
        "candidate_promotion_authorized": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "input_dry_run_packet_verdict": dry_run_packet.get("packet_verdict"),
        "input_dry_run_review_verdict": dry_run_review.get("review_verdict"),
        "proposed_larql_rule": larql_rule_draft(dry_run_packet),
        "apply_review_criteria": apply_review_criteria(dry_run_packet),
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
        "notes": notes,
    }


def render_markdown(packet: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Apply Packet v0",
            "",
            f"Candidate id: `{packet.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{packet.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{packet.get('rule_id') or 'unknown'}`",
            f"Packet verdict: `{packet['packet_verdict']}`",
            f"Allowed next step: `{packet['allowed_next_step']}`",
            f"Promotion verdict: `{packet['promotion_verdict']}`",
            "",
            "This is packet only.",
            "It is not an applied LARQL patch.",
            "It is not durable memory.",
            "It is not LoRA training.",
            "It is not candidate promotion.",
            "This packet only permits later review of whether LARQL application should be authorized.",
            "",
            "## Proposed Rule",
            "",
            f"- Rule id: `{packet['proposed_larql_rule']['rule_id']}`",
            f"- Status: `{packet['proposed_larql_rule']['status']}`",
            "",
            "## Apply Review Criteria",
            "",
            *[f"- {item}" for item in packet["apply_review_criteria"]],
            "",
            "## Boundary",
            "",
            "No LARQL patch is applied by this packet.",
        ]
    )


def write_reports(
    dry_run_packet_path: Path,
    dry_run_review_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet = build_packet(dry_run_packet_path, dry_run_review_path)
    (out_dir / OUTPUT_FILES[0]).write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(packet) + "\n", encoding="utf-8")
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run-packet", required=True, type=Path)
    parser.add_argument("--dry-run-review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.dry_run_packet, args.dry_run_review, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
