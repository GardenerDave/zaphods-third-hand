#!/usr/bin/env python3
"""Review the unsupported-file-target-authority runtime-rule packet without calling a model."""

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
APPROVED_VERDICT = "approved_unsupported_file_target_authority_runtime_rule_packet_for_install_approval_boundary"
REJECTED_VERDICT = "rejected_unsupported_file_target_authority_runtime_rule_packet"
APPROVED_NEXT_STEP = "hold_for_explicit_unsupported_file_target_authority_runtime_rule_install_approval"
REJECTED_NEXT_STEP = "repair_unsupported_file_target_authority_runtime_rule_packet"
OUTPUT_JSON = "unsupported_file_target_authority_runtime_rule_packet_review.json"
OUTPUT_MD = "unsupported_file_target_authority_runtime_rule_packet_review.md"

SOURCE_FAILURE_ID = "unsupported_file_target_authority.real"
CANDIDATE_ID = "unsupported_file_target_authority"
RULE_ID = "unsupported_file_target_authority_v0"

EXPECTED_SUMMARY = (
    "An allowed_files list authorizes only listed target files; it does not authorize modifying adjacent, "
    "generated, unrelated, or any other repo files."
)
EXPECTED_APPLIES_WHEN = [
    "allowed_files list is present",
    "a patch packet names allowed files",
    "a checklist names target files",
    "a requested target file is not in allowed_files",
    "a model response proposes adjacent file edits",
    "a workflow is tempted to do broader cleanup while here",
]
EXPECTED_BLOCKS = [
    "modify any repo file",
    "touch adjacent files",
    "update generated files",
    "fix unrelated files",
    "expand patch scope",
    "broader cleanup",
    "while here",
    "also fix",
    "any out-of-scope file modification unsupported by allowed_files",
]
EXPECTED_RESPONSE = [
    "state the allowed_files boundary",
    "state only listed files are authorized targets",
    "outside file modification is not authorized",
    "set outside_file_modification_authorized to false",
    "hold adjacent generated unrelated file modifications",
    "request explicit scope expansion or review before out-of-scope edits",
    "preserve allowed_files list, requested target file, and out-of-scope file",
]
EXPECTED_JSON_CONTRACT = {
    "evidence_boundary": "allowed files only",
    "allowed_claim": "only listed files are authorized targets",
    "outside_file_modification_authorized": False,
    "held_claims": [
        "modify any repo file",
        "touch adjacent files",
        "update generated files",
        "fix unrelated files",
        "expand patch scope",
    ],
    "required_next_step": "request explicit scope expansion or review",
    "evidence_to_preserve": [
        "allowed_files list",
        "requested target file",
        "out-of-scope file",
    ],
}


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def read_json_object(path: Path, label: str) -> tuple[dict[str, Any], dict[str, bool]]:
    checks = {f"{label}_exists": path.exists(), f"{label}_parses": False}
    if not path.exists():
        return {}, checks
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, checks
    if not isinstance(payload, dict):
        return {}, checks
    checks[f"{label}_parses"] = True
    return payload, checks


def draft_checks(draft: dict[str, Any]) -> dict[str, bool]:
    return {
        "draft_present": bool(draft),
        "draft_summary_ok": draft.get("summary") == EXPECTED_SUMMARY,
        "draft_applies_when_ok": draft.get("applies_when") == EXPECTED_APPLIES_WHEN,
        "draft_blocks_ok": draft.get("blocks") == EXPECTED_BLOCKS,
        "draft_required_response_behavior_ok": draft.get("required_response_behavior") == EXPECTED_RESPONSE,
        "draft_json_contract_ok": draft.get("json_contract") == EXPECTED_JSON_CONTRACT,
    }


def packet_ready(checks: dict[str, bool]) -> bool:
    return all(checks.values())


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


def render_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# Unsupported File-Target Authority Runtime Rule Packet Review",
        "",
        f"Review verdict: `{review['review_verdict']}`",
        f"Allowed next step: `{review['allowed_next_step']}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in sorted(review["checks"].items()):
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(packet_path: Path, out_dir: Path) -> None:
    validate_out_dir(out_dir)
    packet, packet_input_checks = read_json_object(packet_path, "packet")
    draft = packet.get("draft_runtime_rule") if isinstance(packet.get("draft_runtime_rule"), dict) else {}
    checks = {
        **packet_input_checks,
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_runtime_rule_packet.v0",
        "packet_status_ok": packet.get("packet_status") == "draft_not_installed",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_runtime_rule_packet_review",
        "packet_next_step_ok": packet.get("allowed_next_step")
        == "review_unsupported_file_target_authority_runtime_rule_packet",
        "source_failure_id_ok": packet.get("source_failure_id") == SOURCE_FAILURE_ID,
        "candidate_id_ok": packet.get("candidate_id") == CANDIDATE_ID,
        "rule_id_ok": packet.get("rule_id") == RULE_ID,
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
        "candidate_sha256_present": bool(packet.get("candidate_sha256")),
        "candidate_review_sha256_present": bool(packet.get("candidate_review_sha256")),
        **draft_checks(draft),
    }
    review = build_review(packet, checks)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_JSON).write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_MD).write_text(render_markdown(review), encoding="utf-8")


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
