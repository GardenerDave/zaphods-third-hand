#!/usr/bin/env python3
"""Review the unsupported-certainty runtime-rule packet without calling a model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REPORT_TYPE = "affordance_larql_runtime_rule_packet_review.v0"
REVIEW_STATUS = "runtime_rule_packet_review_only"
APPROVED_VERDICT = "approved_unsupported_certainty_scope_claim_runtime_rule_packet_for_install_approval_boundary"
REJECTED_VERDICT = "rejected_unsupported_certainty_scope_claim_runtime_rule_packet"
APPROVED_NEXT_STEP = "hold_for_explicit_unsupported_certainty_runtime_rule_install_approval"
REJECTED_NEXT_STEP = "repair_unsupported_certainty_scope_claim_runtime_rule_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = (
    "unsupported_certainty_scope_claim_runtime_rule_packet_review.json",
    "unsupported_certainty_scope_claim_runtime_rule_packet_review.md",
)


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


def draft_ready(draft: dict[str, Any]) -> dict[str, bool]:
    applies_when = draft.get("applies_when") if isinstance(draft.get("applies_when"), list) else []
    blocks = draft.get("blocks") if isinstance(draft.get("blocks"), list) else []
    response = draft.get("required_response_behavior") if isinstance(draft.get("required_response_behavior"), list) else []
    contract = draft.get("json_contract") if isinstance(draft.get("json_contract"), dict) else {}
    return {
        "draft_present": bool(draft),
        "draft_rule_id_ok": draft.get("rule_id") == "unsupported_certainty_scope_claim_v0",
        "draft_candidate_id_ok": draft.get("candidate_id") == "unsupported_certainty_scope_claim",
        "draft_source_failure_id_ok": draft.get("source_failure_id") == "unsupported_certainty_scope_claim.real",
        "draft_rule_status_ok": draft.get("rule_status") == "draft_not_installed",
        "draft_status_ok": draft.get("status") == "draft_not_installed",
        "draft_summary_mentions_bounded_claim": "bounded claim" in str(draft.get("summary", "")).lower(),
        "draft_summary_mentions_global_certainty": "global certainty" in str(draft.get("summary", "")).lower(),
        "draft_applies_when_checked_scope_only": "checked scope only" in applies_when,
        "draft_applies_when_validation_command_part_repo": "a validation command checked only part of the repo" in applies_when,
        "draft_applies_when_test_suite_subset": "a test suite checked only a specific subset" in applies_when,
        "draft_applies_when_file_inspection_named_files": "a file inspection covered only named files" in applies_when,
        "draft_applies_when_search_results_limited_scope": "search results covered only a limited scope" in applies_when,
        "draft_applies_when_complete_success_temptation": "a model response is tempted to summarize partial evidence as complete success"
        in applies_when,
        "draft_blocks_all_issues_fixed": "all issues are fixed" in blocks,
        "draft_blocks_no_problems_remain": "no problems remain" in blocks,
        "draft_blocks_whole_repo_clean": "whole repo is clean" in blocks,
        "draft_blocks_safe_to_merge": "safe to merge" in blocks,
        "draft_blocks_task_complete": "task complete" in blocks,
        "draft_blocks_guaranteed": "guaranteed" in blocks,
        "draft_blocks_always": "always" in blocks,
        "draft_blocks_never": "never" in blocks,
        "draft_blocks_global_claim_unsup": "any global certainty claim unsupported by the checked scope" in blocks,
        "draft_response_state_checked_scope": "state the checked scope" in response,
        "draft_response_state_only_passed": "state only the checked scope passed" in response,
        "draft_response_global_claim_not_authorized": "global claim is not authorized" in response,
        "draft_response_set_global_claim_authorized_false": "set global_claim_authorized to false" in response,
        "draft_response_hold_global_completion_claims": "hold global completion merge cleanliness claims" in response,
        "draft_response_require_broader_validation": "require broader validation or review before global claims" in response,
        "draft_response_preserve_evidence": "preserve checked scope, validation output, and unreviewed scope" in response,
        "contract_present": bool(contract),
        "contract_evidence_boundary_ok": contract.get("evidence_boundary") == "checked scope only",
        "contract_allowed_claim_ok": contract.get("allowed_claim") == "the checked scope passed",
        "contract_global_claim_authorized_false": contract.get("global_claim_authorized") is False,
        "contract_held_claims_ok": contract.get("held_claims")
        == [
            "all issues are fixed",
            "no problems remain",
            "whole repo is clean",
            "safe to merge",
            "task complete",
        ],
        "contract_required_next_step_ok": contract.get("required_next_step") == "broader validation or review",
        "contract_evidence_to_preserve_ok": contract.get("evidence_to_preserve")
        == ["checked scope", "validation output", "unreviewed scope"],
    }


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "packet_report_type_ok",
        "packet_status_ok",
        "packet_verdict_ok",
        "packet_next_step_ok",
        "source_failure_id_present",
        "candidate_id_present",
        "rule_id_present",
        "candidate_review_verdict_ok",
        "runtime_rule_status_ok",
        "runtime_rule_install_authorized_false",
        "runtime_rule_modification_authorized_false",
        "model_call_performed_false",
        "training_data_written_false",
        "dataset_artifact_written_false",
        "durable_memory_written_false",
        "candidate_promotion_authorized_false",
        "model_weights_mutated_false",
        "automatic_failure_to_curriculum_capture_authorized_false",
        "draft_present",
    ]
    return all(checks.get(name, False) for name in required) and all(
        checks.get(name, False) for name in checks if name.startswith("draft_") or name.startswith("contract_")
    )


def build_review(packet: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    ready = packet_ready(checks)
    return {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": APPROVED_VERDICT if ready else REJECTED_VERDICT,
        "allowed_next_step": APPROVED_NEXT_STEP if ready else REJECTED_NEXT_STEP,
        "source_failure_id": packet.get("source_failure_id"),
        "candidate_id": packet.get("candidate_id"),
        "rule_id": packet.get("rule_id"),
        "runtime_rule_install_authorized": False,
        "runtime_rule_modification_authorized": False,
        "model_call_performed_in_review": False,
        "training_data_written": False,
        "dataset_artifact_written": False,
        "durable_memory_written": False,
        "candidate_promotion_authorized": False,
        "model_weights_mutated": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "promotion_verdict": PROMOTION_VERDICT,
        "checks": checks,
        "disallowed_actions": [
            "call_model",
            "write_training_data",
            "write_dataset_artifact",
            "write_durable_memory",
            "promote_candidate",
            "train_lora_adapter",
            "mutate_model_weights",
            "modify_runtime_rule",
            "install_runtime_rule",
            "commit_or_push",
        ],
    }


def render_markdown(review: dict[str, Any], packet: dict[str, Any]) -> str:
    draft = packet.get("draft_runtime_rule") if isinstance(packet.get("draft_runtime_rule"), dict) else {}
    return "\n".join(
        [
            "# Unsupported Certainty / Scope-Claim Runtime Rule Packet Review",
            "",
            f"Review verdict: `{review['review_verdict']}`",
            f"Allowed next step: `{review['allowed_next_step']}`",
            "",
            "## Draft reviewed",
            "",
            json.dumps(draft, indent=2, sort_keys=True),
            "",
            "## Checks",
            "",
        ]
    )


def write_reports(packet_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    draft = packet.get("draft_runtime_rule") if isinstance(packet.get("draft_runtime_rule"), dict) else {}
    checks = {
        **packet_checks,
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_runtime_rule_packet.v0",
        "packet_status_ok": packet.get("packet_status") == "draft_not_installed",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_runtime_rule_packet_review",
        "packet_next_step_ok": packet.get("allowed_next_step") == "review_unsupported_certainty_scope_claim_runtime_rule_packet",
        "source_failure_id_present": bool(packet.get("source_failure_id")),
        "candidate_id_present": bool(packet.get("candidate_id")),
        "rule_id_present": bool(packet.get("rule_id")),
        "candidate_review_verdict_ok": packet.get("candidate_review_verdict")
        == "approved_unsupported_certainty_scope_claim_candidate_for_runtime_rule_draft",
        "runtime_rule_status_ok": packet.get("runtime_rule_status") == "draft_not_installed",
        "runtime_rule_install_authorized_false": packet.get("runtime_rule_install_authorized") is False,
        "runtime_rule_modification_authorized_false": packet.get("runtime_rule_modification_authorized") is False,
        "model_call_performed_false": packet.get("model_call_performed") is False,
        "training_data_written_false": packet.get("training_data_written") is False,
        "dataset_artifact_written_false": packet.get("dataset_artifact_written") is False,
        "durable_memory_written_false": packet.get("durable_memory_written") is False,
        "candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized") is False,
        "model_weights_mutated_false": packet.get("model_weights_mutated") is False,
        "automatic_failure_to_curriculum_capture_authorized_false": packet.get(
            "automatic_failure_to_curriculum_capture_authorized"
        )
        is False,
        **draft_ready(draft),
    }
    review = build_review(packet, checks)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(review, packet), encoding="utf-8")
    review["notes"] = [*packet_notes, "Review only; no runtime rule is installed."]
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.packet, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
