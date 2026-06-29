#!/usr/bin/env python3
"""Install the unsupported-certainty runtime rule as a local artifact only."""

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
ALLOWED_NEXT_STEP = "draft_unsupported_certainty_runtime_consultation_probe"
OUTPUT_FILES = (
    "unsupported_certainty_scope_claim_runtime_rule_install.json",
    "unsupported_certainty_scope_claim_runtime_rule_install.md",
)
RULE_FILENAME = "unsupported_certainty_scope_claim_v0.json"

SOURCE_FAILURE_ID = "unsupported_certainty_scope_claim.real"
CANDIDATE_ID = "unsupported_certainty_scope_claim"
RULE_ID = "unsupported_certainty_scope_claim_v0"


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def approval_text_is_safe(text: str) -> bool:
    lowered = text.lower()
    required = [
        "i approve local runtime-rule artifact install only for unsupported_certainty_scope_claim_v0.",
        "do not write training data, dataset artifacts, durable memory, promote a candidate, mutate model weights, modify runtime rules beyond this local install artifact, or perform automatic failure-to-curriculum capture.",
    ]
    forbidden = [
        "you may write training data",
        "you may write dataset artifacts",
        "you may write durable memory",
        "you may promote a candidate",
        "you may mutate model weights",
        "you may modify runtime rules beyond this local install artifact",
        "automatic failure-to-curriculum capture is allowed",
    ]
    return all(phrase in lowered for phrase in required) and not any(phrase in lowered for phrase in forbidden)


def draft_is_safe(draft: dict[str, Any]) -> bool:
    applies_when = "\n".join(map(str, draft.get("applies_when") or [])).lower()
    blocks = "\n".join(map(str, draft.get("blocks") or [])).lower()
    response = "\n".join(map(str, draft.get("required_response_behavior") or [])).lower()
    contract = draft.get("json_contract") if isinstance(draft.get("json_contract"), dict) else {}
    return all(
        [
            "checked scope only" in applies_when,
            "a validation command checked only part of the repo" in applies_when,
            "a test suite checked only a specific subset" in applies_when,
            "a file inspection covered only named files" in applies_when,
            "search results covered only a limited scope" in applies_when,
            "a model response is tempted to summarize partial evidence as complete success" in applies_when,
            "all issues are fixed" in blocks,
            "no problems remain" in blocks,
            "whole repo is clean" in blocks,
            "safe to merge" in blocks,
            "task complete" in blocks,
            "guaranteed" in blocks,
            "always" in blocks,
            "never" in blocks,
            "any global certainty claim unsupported by the checked scope" in blocks,
            "state the checked scope" in response,
            "state only the checked scope passed" in response,
            "global claim is not authorized" in response,
            "set global_claim_authorized to false" in response,
            "hold global completion merge cleanliness claims" in response,
            "require broader validation or review before global claims" in response,
            "preserve checked scope, validation output, and unreviewed scope" in response,
            contract.get("evidence_boundary") == "checked scope only",
            contract.get("allowed_claim") == "the checked scope passed",
            contract.get("global_claim_authorized") is False,
            contract.get("held_claims") == [
                "all issues are fixed",
                "no problems remain",
                "whole repo is clean",
                "safe to merge",
                "task complete",
            ],
            contract.get("required_next_step") == "broader validation or review",
            contract.get("evidence_to_preserve") == ["checked scope", "validation output", "unreviewed scope"],
        ]
    )


def packet_review_ready(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "packet_report_type_ok",
        "packet_status_ok",
        "packet_verdict_ok",
        "packet_next_step_ok",
        "packet_runtime_rule_install_authorized_false",
        "packet_runtime_rule_modification_authorized_false",
        "review_exists",
        "review_parses",
        "review_report_type_ok",
        "review_status_ok",
        "review_verdict_ok",
        "review_next_step_ok",
        "review_runtime_rule_install_authorized_false",
        "review_runtime_rule_modification_authorized_false",
        "ids_match",
        "approval_text_present",
        "approval_text_safe",
        "review_candidate_promotion_authorized_false",
        "review_durable_memory_authorized_false",
        "review_lora_training_authorized_false",
        "review_model_weight_mutation_authorized_false",
        "review_no_model_call",
        "review_no_training_data_write",
        "review_no_dataset_artifact_write",
        "review_no_auto_capture",
    ]
    return all(checks.get(name, False) for name in required)


def build_runtime_rule(packet: dict[str, Any], review: dict[str, Any], approval_text: str, packet_path: Path, review_path: Path) -> dict[str, Any]:
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
            "explicit_user_approval_captured": True,
            "approval_text_sha256": sha256_text(approval_text),
        },
    }


def build_install_record(
    packet: dict[str, Any],
    review: dict[str, Any],
    runtime_rule_path: Path,
    approval_text: str,
    checks: dict[str, bool],
    runtime_rule_sha: str,
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
        "installed_rule_sha256": runtime_rule_sha,
        "checks": checks,
        "disallowed_actions": [
            "write_training_data",
            "write_dataset_artifact",
            "write_durable_memory",
            "promote_candidate",
            "train_lora_adapter",
            "mutate_model_weights",
            "modify_runtime_rule",
            "commit_or_push",
        ],
    }


def render_markdown(record: dict[str, Any], runtime_rule: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Unsupported Certainty Runtime Rule Install Record",
            "",
            f"Source failure id: `{record['source_failure_id']}`",
            f"Candidate id: `{record['candidate_id']}`",
            f"Rule id: `{record['rule_id']}`",
            f"Install verdict: `{record['install_verdict']}`",
            f"Allowed next step: `{record['allowed_next_step']}`",
            "",
            "This is a local runtime-rule artifact install only.",
            "The runtime rule is installed for consultation only.",
            "No durable memory is written.",
            "No candidate is promoted.",
            "No LoRA is trained.",
            "No model weights are mutated.",
            "No training data is written.",
            "No dataset artifacts are written.",
            "No model call is performed.",
            "Automatic failure-to-curriculum capture is not authorized.",
            "",
            "## Installed runtime rule",
            "",
            f"- Rule id: `{runtime_rule['rule_id']}`",
            f"- Status: `{runtime_rule['rule_status']}`",
            f"- Runtime rule scope: `{runtime_rule['runtime_rule_scope']}`",
            f"- Summary: {runtime_rule['summary']}",
            "- Applies when: checked scope only; partial validation, partial file inspection, or limited search results.",
            "- Blocks: global completion claims from partial evidence.",
            "- Required response behavior: state the checked scope, keep global claims held, and require broader validation or review.",
        ]
    )


def write_reports(packet_path: Path, review_path: Path, approval_text: str, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    review, review_checks, review_notes = read_json_object(review_path, "review")
    checks = {
        **packet_checks,
        **review_checks,
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_runtime_rule_packet.v0",
        "packet_status_ok": packet.get("packet_status") == "draft_not_installed",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_runtime_rule_packet_review",
        "packet_next_step_ok": packet.get("allowed_next_step") == "review_unsupported_certainty_scope_claim_runtime_rule_packet",
        "packet_runtime_rule_install_authorized_false": packet.get("runtime_rule_install_authorized") is False,
        "packet_runtime_rule_modification_authorized_false": packet.get("runtime_rule_modification_authorized") is False,
        "review_report_type_ok": review.get("report_type") == "affordance_larql_runtime_rule_packet_review.v0",
        "review_status_ok": review.get("review_status") == "runtime_rule_packet_review_only",
        "review_verdict_ok": review.get("review_verdict")
        == "approved_unsupported_certainty_scope_claim_runtime_rule_packet_for_install_approval_boundary",
        "review_next_step_ok": review.get("allowed_next_step")
        == "hold_for_explicit_unsupported_certainty_runtime_rule_install_approval",
        "review_runtime_rule_install_authorized_false": review.get("runtime_rule_install_authorized") is False,
        "review_runtime_rule_modification_authorized_false": review.get("runtime_rule_modification_authorized") is False,
        "review_candidate_promotion_authorized_false": review.get("candidate_promotion_authorized") is False,
        "review_durable_memory_authorized_false": review.get("durable_memory_written") is False,
        "review_lora_training_authorized_false": review.get("lora_training_authorized") in {False, None},
        "review_model_weight_mutation_authorized_false": review.get("model_weights_mutated") is False,
        "review_no_model_call": review.get("model_call_performed_in_review") is False,
        "review_no_training_data_write": review.get("training_data_written") is False,
        "review_no_dataset_artifact_write": review.get("dataset_artifact_written") is False,
        "review_no_auto_capture": review.get("automatic_failure_to_curriculum_capture_authorized") is False,
        "ids_match": all(
            packet.get(key) == review.get(key) == expected
            for key, expected in (
                ("source_failure_id", SOURCE_FAILURE_ID),
                ("candidate_id", CANDIDATE_ID),
                ("rule_id", RULE_ID),
            )
        ),
        "approval_text_present": bool(approval_text.strip()),
        "approval_text_safe": approval_text_is_safe(approval_text),
        "draft_present": isinstance(packet.get("draft_runtime_rule"), dict),
        "draft_safe": draft_is_safe(packet.get("draft_runtime_rule") or {}),
    }
    ready = packet_review_ready(checks)
    if not ready:
        raise ValueError("install checks failed")
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime_rule_path = out_dir / "runtime_rules" / RULE_FILENAME
    runtime_rule = build_runtime_rule(packet, review, approval_text, packet_path, review_path)
    runtime_rule_sha = sha256_text(json.dumps(runtime_rule, sort_keys=True))
    runtime_rule_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_rule_path.write_text(json.dumps(runtime_rule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record = build_install_record(packet, review, runtime_rule_path, approval_text, checks, runtime_rule_sha)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(record, runtime_rule), encoding="utf-8")
    record["notes"] = [*packet_notes, *review_notes, "Local artifact install only; no runtime rule is modified."]
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
