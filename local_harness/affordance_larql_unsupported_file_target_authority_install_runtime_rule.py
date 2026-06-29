#!/usr/bin/env python3
"""Install the unsupported-file-target-authority runtime rule as a local artifact only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REPORT_TYPE = "affordance_larql_runtime_rule_install.v0"
INSTALL_STATUS = "local_runtime_rule_artifact_install_only"
INSTALL_VERDICT = "local_runtime_rule_artifact_installed"
ALLOWED_NEXT_STEP = "draft_unsupported_file_target_authority_runtime_consultation_probe"
OUTPUT_JSON = "unsupported_file_target_authority_runtime_rule_install.json"
OUTPUT_MD = "unsupported_file_target_authority_runtime_rule_install.md"
RULE_FILENAME = "unsupported_file_target_authority_v0.json"

SOURCE_FAILURE_ID = "unsupported_file_target_authority.real"
CANDIDATE_ID = "unsupported_file_target_authority"
RULE_ID = "unsupported_file_target_authority_v0"
EXPECTED_APPROVAL_TEXT = (
    "I approve local runtime-rule artifact install only for unsupported_file_target_authority_v0. "
    "Do not write training data, dataset artifacts, durable memory, promote a candidate, mutate model weights, "
    "modify runtime rules beyond this local install artifact, or perform automatic failure-to-curriculum capture."
)

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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approval_text_is_safe(text: str) -> bool:
    lowered = text.strip().lower()
    required = EXPECTED_APPROVAL_TEXT.lower()
    forbidden = [
        "you may write training data",
        "you may write dataset artifacts",
        "you may write durable memory",
        "you may promote a candidate",
        "you may mutate model weights",
        "you may modify runtime rules beyond this local install artifact",
        "automatic failure-to-curriculum capture is allowed",
    ]
    return lowered == required and not any(phrase in lowered for phrase in forbidden)


def draft_is_safe(draft: dict[str, Any]) -> bool:
    return (
        draft.get("summary") == EXPECTED_SUMMARY
        and draft.get("applies_when") == EXPECTED_APPLIES_WHEN
        and draft.get("blocks") == EXPECTED_BLOCKS
        and draft.get("required_response_behavior") == EXPECTED_RESPONSE
        and draft.get("json_contract") == EXPECTED_JSON_CONTRACT
    )


def install_ready(checks: dict[str, bool]) -> bool:
    return all(checks.values())


def build_runtime_rule(
    packet: dict[str, Any],
    review: dict[str, Any],
    *,
    packet_path: Path,
    review_path: Path,
    approval_text: str,
) -> dict[str, Any]:
    draft = packet["draft_runtime_rule"]
    return {
        "report_type": "affordance_larql_runtime_rule.v0",
        "rule_id": RULE_ID,
        "candidate_id": CANDIDATE_ID,
        "source_failure_id": SOURCE_FAILURE_ID,
        "rule_status": "installed_local_runtime_rule_artifact",
        "runtime_rule_scope": "local_artifact_only",
        "summary": draft["summary"],
        "applies_when": draft["applies_when"],
        "blocks": draft["blocks"],
        "required_response_behavior": draft["required_response_behavior"],
        "json_contract": draft["json_contract"],
        "installed_from_packet_sha256": sha256_text(json.dumps(packet, sort_keys=True)),
        "installed_from_review_sha256": sha256_text(json.dumps(review, sort_keys=True)),
        "provenance": {
            "packet_path": str(packet_path),
            "review_path": str(review_path),
            "explicit_approval_captured": True,
            "approval_text_sha256": sha256_text(approval_text),
        },
    }


def build_install_record(
    *,
    runtime_rule_path: Path,
    approval_text: str,
    packet: dict[str, Any],
    review: dict[str, Any],
    installed_rule_sha256: str,
    checks: dict[str, bool],
) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "install_status": INSTALL_STATUS,
        "install_verdict": INSTALL_VERDICT,
        "allowed_next_step": ALLOWED_NEXT_STEP,
        "source_failure_id": SOURCE_FAILURE_ID,
        "candidate_id": CANDIDATE_ID,
        "rule_id": RULE_ID,
        "runtime_rule_status": "installed_local_runtime_rule_artifact",
        "runtime_rule_artifact_path": str(runtime_rule_path),
        "runtime_rule_install_authorized": True,
        "runtime_rule_modification_authorized": False,
        "local_artifact_install_only": True,
        "model_call_performed": False,
        "training_data_written": False,
        "dataset_artifact_written": False,
        "durable_memory_written": False,
        "candidate_promotion_authorized": False,
        "model_weights_mutated": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "approval_basis": "explicit_user_approval",
        "approval_text_sha256": sha256_text(approval_text),
        "packet_sha256": sha256_text(json.dumps(packet, sort_keys=True)),
        "review_sha256": sha256_text(json.dumps(review, sort_keys=True)),
        "installed_rule_sha256": installed_rule_sha256,
        "checks": checks,
    }


def render_markdown(record: dict[str, Any], runtime_rule: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Unsupported File-Target Authority Runtime Rule Install",
            "",
            f"Install verdict: `{record['install_verdict']}`",
            f"Allowed next step: `{record['allowed_next_step']}`",
            "",
            "This is a local runtime-rule artifact install only.",
            "No training data is written.",
            "No dataset artifacts are written.",
            "No durable memory is written.",
            "No candidate is promoted.",
            "No model weights are mutated.",
            "No runtime rules are modified beyond this local install artifact.",
            "Automatic failure-to-curriculum capture is not authorized.",
            "",
            "## Installed runtime rule",
            "",
            f"- Rule id: `{runtime_rule['rule_id']}`",
            f"- Status: `{runtime_rule['rule_status']}`",
            f"- Scope: `{runtime_rule['runtime_rule_scope']}`",
            f"- Summary: {runtime_rule['summary']}",
        ]
    )


def write_reports(packet_path: Path, review_path: Path, approval_text: str, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    packet, packet_checks = read_json_object(packet_path, "packet")
    review, review_checks = read_json_object(review_path, "review")
    draft = packet.get("draft_runtime_rule") if isinstance(packet.get("draft_runtime_rule"), dict) else {}
    checks = {
        **packet_checks,
        **review_checks,
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_runtime_rule_packet.v0",
        "packet_status_ok": packet.get("packet_status") == "draft_not_installed",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_runtime_rule_packet_review",
        "packet_allowed_next_step_ok": packet.get("allowed_next_step")
        == "review_unsupported_file_target_authority_runtime_rule_packet",
        "packet_runtime_rule_install_authorized_false": packet.get("runtime_rule_install_authorized") is False,
        "packet_runtime_rule_modification_authorized_false": packet.get("runtime_rule_modification_authorized")
        is False,
        "packet_source_failure_id_ok": packet.get("source_failure_id") == SOURCE_FAILURE_ID,
        "packet_candidate_id_ok": packet.get("candidate_id") == CANDIDATE_ID,
        "packet_rule_id_ok": packet.get("rule_id") == RULE_ID,
        "packet_model_call_performed_false": packet.get("model_call_performed") is False,
        "packet_training_data_written_false": packet.get("training_data_written") is False,
        "packet_dataset_artifact_written_false": packet.get("dataset_artifact_written") is False,
        "packet_durable_memory_written_false": packet.get("durable_memory_written") is False,
        "packet_candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized") is False,
        "packet_model_weights_mutated_false": packet.get("model_weights_mutated") is False,
        "packet_auto_capture_false": packet.get("automatic_failure_to_curriculum_capture_authorized") is False,
        "review_report_type_ok": review.get("report_type") == "affordance_larql_runtime_rule_packet_review.v0",
        "review_status_ok": review.get("review_status") == "runtime_rule_packet_review_only",
        "review_verdict_ok": review.get("review_verdict")
        == "approved_unsupported_file_target_authority_runtime_rule_packet_for_install_approval_boundary",
        "review_allowed_next_step_ok": review.get("allowed_next_step")
        == "hold_for_explicit_unsupported_file_target_authority_runtime_rule_install_approval",
        "review_runtime_rule_install_authorized_false": review.get("runtime_rule_install_authorized") is False,
        "review_runtime_rule_modification_authorized_false": review.get("runtime_rule_modification_authorized")
        is False,
        "review_source_failure_id_ok": review.get("source_failure_id") == SOURCE_FAILURE_ID,
        "review_candidate_id_ok": review.get("candidate_id") == CANDIDATE_ID,
        "review_rule_id_ok": review.get("rule_id") == RULE_ID,
        "review_model_call_performed_in_review_false": review.get("model_call_performed_in_review") is False,
        "review_training_data_written_false": review.get("training_data_written") is False,
        "review_dataset_artifact_written_false": review.get("dataset_artifact_written") is False,
        "review_durable_memory_written_false": review.get("durable_memory_written") is False,
        "review_candidate_promotion_authorized_false": review.get("candidate_promotion_authorized") is False,
        "review_model_weights_mutated_false": review.get("model_weights_mutated") is False,
        "review_auto_capture_false": review.get("automatic_failure_to_curriculum_capture_authorized") is False,
        "identifiers_match": (
            packet.get("source_failure_id") == review.get("source_failure_id") == SOURCE_FAILURE_ID
            and packet.get("candidate_id") == review.get("candidate_id") == CANDIDATE_ID
            and packet.get("rule_id") == review.get("rule_id") == RULE_ID
        ),
        "approval_text_present": bool(approval_text.strip()),
        "approval_text_safe": approval_text_is_safe(approval_text),
        "draft_present": bool(draft),
        "draft_safe": draft_is_safe(draft),
    }
    if not install_ready(checks):
        raise ValueError("install checks failed")

    out_dir.mkdir(parents=True, exist_ok=True)
    runtime_rule_path = out_dir / "runtime_rules" / RULE_FILENAME
    runtime_rule = build_runtime_rule(
        packet,
        review,
        packet_path=packet_path,
        review_path=review_path,
        approval_text=approval_text,
    )
    runtime_rule_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_rule_path.write_text(json.dumps(runtime_rule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    installed_rule_sha256 = sha256_path(runtime_rule_path)
    record = build_install_record(
        runtime_rule_path=runtime_rule_path,
        approval_text=approval_text,
        packet=packet,
        review=review,
        installed_rule_sha256=installed_rule_sha256,
        checks=checks,
    )
    (out_dir / OUTPUT_JSON).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_MD).write_text(render_markdown(record, runtime_rule) + "\n", encoding="utf-8")
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--packet-review", required=True, type=Path)
    parser.add_argument("--approval-text", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.packet, args.packet_review, args.approval_text, args.out)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
