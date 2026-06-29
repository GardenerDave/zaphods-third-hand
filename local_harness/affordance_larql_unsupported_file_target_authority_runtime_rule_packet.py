#!/usr/bin/env python3
"""Draft a runtime-rule packet for the unsupported-file-target-authority candidate.

This is packet-only. It does not install a runtime rule, call a model, write
durable memory, write training data, write dataset artifacts, promote a
candidate, mutate model weights, or perform automatic failure-to-curriculum
capture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REPORT_TYPE = "affordance_larql_runtime_rule_packet.v0"
PACKET_STATUS = "draft_not_installed"
PACKET_VERDICT = "ready_for_runtime_rule_packet_review"
ALLOWED_NEXT_STEP = "review_unsupported_file_target_authority_runtime_rule_packet"
REPAIR_NEXT_STEP = "repair_unsupported_file_target_authority_inputs"
OUTPUT_JSON = "unsupported_file_target_authority_runtime_rule_packet.json"
OUTPUT_MD = "unsupported_file_target_authority_runtime_rule_packet.md"

SOURCE_FAILURE_ID = "unsupported_file_target_authority.real"
CANDIDATE_ID = "unsupported_file_target_authority"
RULE_ID = "unsupported_file_target_authority_v0"

JSON_CONTRACT = {
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


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def build_runtime_rule_draft() -> dict[str, Any]:
    return {
        "rule_id": RULE_ID,
        "candidate_id": CANDIDATE_ID,
        "source_failure_id": SOURCE_FAILURE_ID,
        "status": "draft_not_installed",
        "rule_status": "draft_not_installed",
        "summary": "An allowed_files list authorizes only listed target files; it does not authorize modifying adjacent, generated, unrelated, or any other repo files.",
        "applies_when": [
            "allowed_files list is present",
            "a patch packet names allowed files",
            "a checklist names target files",
            "a requested target file is not in allowed_files",
            "a model response proposes adjacent file edits",
            "a workflow is tempted to do broader cleanup while here",
        ],
        "blocks": [
            "modify any repo file",
            "touch adjacent files",
            "update generated files",
            "fix unrelated files",
            "expand patch scope",
            "broader cleanup",
            "while here",
            "also fix",
            "any out-of-scope file modification unsupported by allowed_files",
        ],
        "required_response_behavior": [
            "state the allowed_files boundary",
            "state only listed files are authorized targets",
            "outside file modification is not authorized",
            "set outside_file_modification_authorized to false",
            "hold adjacent generated unrelated file modifications",
            "request explicit scope expansion or review before out-of-scope edits",
            "preserve allowed_files list, requested target file, and out-of-scope file",
        ],
        "json_contract": JSON_CONTRACT,
    }


def draft_is_safe(draft: dict[str, Any]) -> bool:
    return (
        draft.get("summary")
        == "An allowed_files list authorizes only listed target files; it does not authorize modifying adjacent, generated, unrelated, or any other repo files."
        and draft.get("applies_when")
        == [
            "allowed_files list is present",
            "a patch packet names allowed files",
            "a checklist names target files",
            "a requested target file is not in allowed_files",
            "a model response proposes adjacent file edits",
            "a workflow is tempted to do broader cleanup while here",
        ]
        and draft.get("blocks")
        == [
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
        and draft.get("required_response_behavior")
        == [
            "state the allowed_files boundary",
            "state only listed files are authorized targets",
            "outside file modification is not authorized",
            "set outside_file_modification_authorized to false",
            "hold adjacent generated unrelated file modifications",
            "request explicit scope expansion or review before out-of-scope edits",
            "preserve allowed_files list, requested target file, and out-of-scope file",
        ]
        and draft.get("json_contract") == JSON_CONTRACT
    )


def build_packet(
    candidate: dict[str, Any],
    review: dict[str, Any],
    *,
    candidate_sha256: str = "",
    candidate_review_sha256: str = "",
    input_checks: dict[str, bool] | None = None,
) -> dict[str, Any]:
    draft = build_runtime_rule_draft()
    checks = {}
    if input_checks:
        checks.update(input_checks)
    checks.update(
        {
            "candidate_report_type_ok": candidate.get("report_type") == "affordance_larql_candidate.v0",
            "candidate_status_ok": candidate.get("candidate_status") == "draft_not_installed",
            "candidate_verdict_ok": candidate.get("candidate_verdict") == "ready_for_supervised_review",
            "candidate_source_failure_id_ok": candidate.get("source_failure_id") == SOURCE_FAILURE_ID,
            "candidate_candidate_id_ok": candidate.get("candidate_id") == CANDIDATE_ID,
            "candidate_rule_id_ok": candidate.get("rule_id") == RULE_ID,
            "candidate_json_contract_drafted_true": candidate.get("json_contract_drafted") is True,
            "candidate_allowed_next_step_ok": candidate.get("allowed_next_step")
            == "review_unsupported_file_target_authority_candidate",
            "candidate_model_call_performed_false": candidate.get("model_call_performed") is False,
            "candidate_training_data_written_false": candidate.get("training_data_written") is False,
            "candidate_dataset_artifact_written_false": candidate.get("dataset_artifact_written") is False,
            "candidate_durable_memory_written_false": candidate.get("durable_memory_written") is False,
            "candidate_candidate_promotion_authorized_false": candidate.get("candidate_promotion_authorized") is False,
            "candidate_runtime_rule_modification_authorized_false": candidate.get(
                "runtime_rule_modification_authorized"
            )
            is False,
            "candidate_model_weights_mutated_false": candidate.get("model_weights_mutated") is False,
            "candidate_automatic_failure_to_curriculum_capture_authorized_false": candidate.get(
                "automatic_failure_to_curriculum_capture_authorized"
            )
            is False,
            "review_report_type_ok": review.get("report_type") == "affordance_larql_candidate_review.v0",
            "review_status_ok": review.get("review_status") == "candidate_review_only",
            "review_verdict_ok": review.get("review_verdict")
            == "approved_unsupported_file_target_authority_candidate_for_runtime_rule_draft",
            "review_next_step_ok": review.get("allowed_next_step")
            == "draft_unsupported_file_target_authority_runtime_rule_packet",
            "review_source_failure_id_ok": review.get("source_failure_id") == SOURCE_FAILURE_ID,
            "review_candidate_id_ok": review.get("candidate_id") == CANDIDATE_ID,
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
            "draft_runtime_rule_safe": draft_is_safe(draft),
            "candidate_sha256_present": bool(candidate_sha256),
            "candidate_review_sha256_present": bool(candidate_review_sha256),
        }
    )
    ready = all(checks.values())
    return {
        "report_type": REPORT_TYPE,
        "packet_status": PACKET_STATUS,
        "packet_verdict": PACKET_VERDICT if ready else "runtime_rule_packet_rejected",
        "allowed_next_step": ALLOWED_NEXT_STEP if ready else REPAIR_NEXT_STEP,
        "source_failure_id": SOURCE_FAILURE_ID,
        "candidate_id": CANDIDATE_ID,
        "rule_id": RULE_ID,
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
        "candidate_sha256": candidate_sha256,
        "candidate_review_sha256": candidate_review_sha256,
        "checks": checks,
        "draft_runtime_rule": draft,
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
    draft = packet["draft_runtime_rule"]
    lines = [
        "# Unsupported File-Target Authority Runtime Rule Packet",
        "",
        f"Packet verdict: `{packet['packet_verdict']}`",
        f"Allowed next step: `{packet['allowed_next_step']}`",
        "",
        "## Draft runtime rule",
        "",
        f"- Rule id: `{draft['rule_id']}`",
        f"- Status: `{draft['rule_status']}`",
        f"- Summary: {draft['summary']}",
        "",
        "### Applies when",
        "",
    ]
    for item in draft["applies_when"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "### Blocks", ""])
    for item in draft["blocks"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "### Required response behavior", ""])
    for item in draft["required_response_behavior"]:
        lines.append(f"- `{item}`")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(candidate_path: Path, review_path: Path, out_dir: Path) -> None:
    validate_out_dir(out_dir)
    candidate, candidate_checks = read_json_object(candidate_path, "candidate")
    review, review_checks = read_json_object(review_path, "review")
    candidate_hash = sha256_path(candidate_path) if candidate_path.exists() else ""
    review_hash = sha256_path(review_path) if review_path.exists() else ""
    packet = build_packet(
        candidate,
        review,
        candidate_sha256=candidate_hash,
        candidate_review_sha256=review_hash,
        input_checks={**candidate_checks, **review_checks},
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_JSON).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_MD).write_text(render_markdown(packet), encoding="utf-8")


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
