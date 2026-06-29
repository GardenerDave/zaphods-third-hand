#!/usr/bin/env python3
"""Draft a runtime-rule packet for the unsupported-certainty / scope-claim candidate.

This is packet-only. It does not install a runtime rule, call a model, write
durable memory, write training data, write dataset artifacts, promote a
candidate, train LoRA, mutate model weights, or perform automatic
failure-to-curriculum capture.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REPORT_TYPE = "affordance_larql_runtime_rule_packet.v0"
PACKET_STATUS = "draft_not_installed"
PACKET_VERDICT = "ready_for_runtime_rule_packet_review"
ALLOWED_NEXT_STEP = "review_unsupported_certainty_scope_claim_runtime_rule_packet"
OUTPUT_FILE = "unsupported_certainty_scope_claim_runtime_rule_packet.json"

SOURCE_FAILURE_ID = "unsupported_certainty_scope_claim.real"
CANDIDATE_ID = "unsupported_certainty_scope_claim"
RULE_ID = "unsupported_certainty_scope_claim_v0"

JSON_CONTRACT = {
    "evidence_boundary": "checked scope only",
    "allowed_claim": "the checked scope passed",
    "global_claim_authorized": False,
    "held_claims": [
        "all issues are fixed",
        "no problems remain",
        "whole repo is clean",
        "safe to merge",
        "task complete",
    ],
    "required_next_step": "broader validation or review",
    "evidence_to_preserve": ["checked scope", "validation output", "unreviewed scope"],
}


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


def draft_is_safe(draft: dict[str, Any]) -> bool:
    applies_when = "\n".join(map(str, draft.get("applies_when") or [])).lower()
    blocks = "\n".join(map(str, draft.get("blocks") or [])).lower()
    response = "\n".join(map(str, draft.get("required_response_behavior") or [])).lower()
    contract = draft.get("json_contract") or {}
    return all(
        [
            "checked scope only" in applies_when,
            "checked scope passed" in response,
            "global claim is not authorized" in response,
            "broader validation or review" in response,
            "all issues are fixed" in blocks,
            "no problems remain" in blocks,
            "whole repo is clean" in blocks,
            "safe to merge" in blocks,
            "task complete" in blocks,
            "guaranteed" in blocks,
            "always" in blocks,
            "never" in blocks,
            contract.get("evidence_boundary") == JSON_CONTRACT["evidence_boundary"],
            contract.get("allowed_claim") == JSON_CONTRACT["allowed_claim"],
            contract.get("global_claim_authorized") is False,
            contract.get("held_claims") == JSON_CONTRACT["held_claims"],
            contract.get("required_next_step") == JSON_CONTRACT["required_next_step"],
            contract.get("evidence_to_preserve") == JSON_CONTRACT["evidence_to_preserve"],
        ]
    )


def build_runtime_rule_draft() -> dict[str, Any]:
    return {
        "rule_id": RULE_ID,
        "candidate_id": CANDIDATE_ID,
        "source_failure_id": SOURCE_FAILURE_ID,
        "status": "draft_not_installed",
        "rule_status": "draft_not_installed",
        "summary": "A bounded check may support a bounded claim, but it does not authorize global certainty, universal claims, or broad completion claims.",
        "applies_when": [
            "checked scope only",
            "a validation command checked only part of the repo",
            "a test suite checked only a specific subset",
            "a file inspection covered only named files",
            "search results covered only a limited scope",
            "a model response is tempted to summarize partial evidence as complete success",
        ],
        "blocks": [
            "all issues are fixed",
            "no problems remain",
            "whole repo is clean",
            "safe to merge",
            "task complete",
            "guaranteed",
            "always",
            "never",
            "any global certainty claim unsupported by the checked scope",
        ],
        "required_response_behavior": [
            "state the checked scope",
            "state only the checked scope passed",
            "global claim is not authorized",
            "set global_claim_authorized to false",
            "hold global completion merge cleanliness claims",
            "require broader validation or review before global claims",
            "preserve checked scope, validation output, and unreviewed scope",
        ],
        "json_contract": JSON_CONTRACT,
    }


def build_packet(candidate: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    draft = build_runtime_rule_draft()
    checks = {
        "candidate_report_type_ok": candidate.get("report_type") == "affordance_larql_candidate.v0",
        "candidate_status_ok": candidate.get("candidate_status") == "draft_not_installed",
        "candidate_verdict_ok": candidate.get("candidate_verdict") == "ready_for_supervised_review",
        "candidate_source_failure_id_ok": candidate.get("source_failure_id") == SOURCE_FAILURE_ID,
        "candidate_candidate_id_ok": candidate.get("candidate_id") == CANDIDATE_ID,
        "candidate_rule_id_ok": candidate.get("rule_id") == RULE_ID,
        "candidate_json_contract_drafted_true": candidate.get("json_contract_drafted") is True,
        "candidate_allowed_next_step_ok": candidate.get("allowed_next_step")
        == "review_unsupported_certainty_scope_claim_candidate",
        "candidate_model_call_performed_false": candidate.get("model_call_performed") is False,
        "candidate_training_data_written_false": candidate.get("training_data_written") is False,
        "candidate_dataset_artifact_written_false": candidate.get("dataset_artifact_written") is False,
        "candidate_durable_memory_written_false": candidate.get("durable_memory_written") is False,
        "candidate_candidate_promotion_authorized_false": candidate.get("candidate_promotion_authorized") is False,
        "candidate_runtime_rule_modification_authorized_false": candidate.get("runtime_rule_modification_authorized")
        is False,
        "candidate_model_weights_mutated_false": candidate.get("model_weights_mutated") is False,
        "candidate_automatic_failure_to_curriculum_capture_authorized_false": candidate.get(
            "automatic_failure_to_curriculum_capture_authorized"
        )
        is False,
        "review_report_type_ok": review.get("report_type") == "affordance_larql_candidate_review.v0",
        "review_status_ok": review.get("review_status") == "candidate_review_only",
        "review_verdict_ok": review.get("review_verdict")
        == "approved_unsupported_certainty_scope_claim_candidate_for_runtime_rule_draft",
        "review_next_step_ok": review.get("allowed_next_step")
        == "draft_unsupported_certainty_scope_claim_runtime_rule_packet",
        "review_candidate_id_ok": review.get("candidate_id") == CANDIDATE_ID,
        "review_source_failure_id_ok": review.get("source_failure_id") == SOURCE_FAILURE_ID,
        "review_rule_id_ok": review.get("rule_id") == RULE_ID,
        "review_model_call_performed_in_review_false": review.get("model_call_performed_in_review") is False,
        "review_training_data_written_false": review.get("training_data_written") is False,
        "review_dataset_artifact_written_false": review.get("dataset_artifact_written") is False,
        "review_durable_memory_written_false": review.get("durable_memory_written") is False,
        "review_candidate_promotion_authorized_false": review.get("candidate_promotion_authorized") is False,
        "review_runtime_rule_modification_authorized_false": review.get("runtime_rule_modification_authorized")
        is False,
        "review_model_weights_mutated_false": review.get("model_weights_mutated") is False,
        "review_automatic_failure_to_curriculum_capture_authorized_false": review.get(
            "automatic_failure_to_curriculum_capture_authorized"
        )
        is False,
        "draft_safe": draft_is_safe(draft),
    }
    ready = all(checks.values())
    return {
        "report_type": REPORT_TYPE,
        "packet_status": PACKET_STATUS,
        "packet_verdict": "ready_for_runtime_rule_packet_review" if ready else "runtime_rule_packet_rejected",
        "allowed_next_step": ALLOWED_NEXT_STEP if ready else "repair_unsupported_certainty_scope_claim_inputs",
        "source_failure_id": SOURCE_FAILURE_ID,
        "candidate_id": CANDIDATE_ID,
        "rule_id": RULE_ID,
        "candidate_review_verdict": review.get("review_verdict"),
        "runtime_rule_status": "draft_not_installed",
        "runtime_rule_install_authorized": False,
        "runtime_rule_modification_authorized": False,
        "model_call_performed": False,
        "training_data_written": False,
        "dataset_artifact_written": False,
        "durable_memory_written": False,
        "candidate_promotion_authorized": False,
        "model_weights_mutated": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "json_contract": JSON_CONTRACT,
        "draft_runtime_rule": draft,
        "checks": checks,
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
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


def render_markdown(packet: dict[str, Any]) -> str:
    draft = packet.get("draft_runtime_rule") or {}
    return "\n".join(
        [
            "# Unsupported Certainty / Scope-Claim Runtime Rule Packet",
            "",
            f"Packet verdict: `{packet['packet_verdict']}`",
            f"Allowed next step: `{packet['allowed_next_step']}`",
            "",
            "## Draft runtime rule",
            "",
            f"- Rule id: `{draft.get('rule_id')}`",
            f"- Status: `{draft.get('rule_status')}`",
            f"- Summary: {draft.get('summary')}",
            "- Applies when: checked scope only; partial validation, partial file inspection, or limited search results.",
            "- Blocks: global completion claims from partial evidence.",
            "- Required response behavior: state the checked scope, keep global claims held, and require broader validation or review.",
        ]
    )


def write_reports(candidate_path: Path, review_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    candidate, candidate_checks, candidate_notes = read_json_object(candidate_path, "candidate")
    review, review_checks, review_notes = read_json_object(review_path, "review")
    packet = build_packet(candidate, review)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_FILE).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "unsupported_certainty_scope_claim_runtime_rule_packet.md").write_text(
        render_markdown(packet) + "\n", encoding="utf-8"
    )
    packet["notes"] = [*candidate_notes, *review_notes, "Draft only; no runtime rule is installed."]
    packet["input_checks"] = {**candidate_checks, **review_checks}
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--candidate-review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.candidate, args.candidate_review, args.out)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
