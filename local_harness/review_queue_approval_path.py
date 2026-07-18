#!/usr/bin/env python3
"""Read-only wrapper that validates queue approval path review artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.validate_queue_approval_path import (  # noqa: E402
    validate_queue_approval_path,
)

REVIEW_SCHEMA = "queue_approval_path_review_v1"
SOURCE_REQUIRED_AUTHORITY_TERMS = {
    "no_unattended_execution",
    "no_repo_mutation_without_review",
    "no_training_capture",
    "no_promotion",
    "no_deployment",
    "no_downstream_use_authority",
    "no_queue_insertion_without_explicit_approval",
    "no_queue_writing",
    "no_automatic_queue_handoff",
    "no_queue_running",
}

OUTPUT_AUTHORITY_TERMS = SOURCE_REQUIRED_AUTHORITY_TERMS | {
    "explicit_review_output_only",
}


def _diagnostic_code(message: str) -> str:
    lowered = message.lower()
    if "malformed json packet" in lowered:
        return "MALFORMED_JSON"
    if "approval artifact must be a json object" in lowered:
        return "NON_OBJECT_JSON"
    if "missing required fields" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval_schema must be" in lowered:
        return "WRONG_APPROVAL_SCHEMA"
    if "approval artifact field 'queue_approval_status'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "queue_approval_status must be one of" in lowered:
        return "INVALID_QUEUE_APPROVAL_STATUS"
    if "approval artifact field 'approval_scope'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'reviewer_note'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'required_checks'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'authority_boundary'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'automation_status'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'queue_insertion_status'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'queue_writing_status'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'repo_mutation_status'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'downstream_use_status'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'diagnostics'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "approval artifact field 'recommended_next_step'" in lowered:
        return "MISSING_REQUIRED_FIELDS"
    if "source_review_schema must be" in lowered:
        return "WRONG_SOURCE_REVIEW_SCHEMA"
    if "source_review_path must be" in lowered:
        return "EMPTY_SOURCE_REVIEW_PATH"
    if "source_queue_handoff_review_status" in lowered and "approved_for_queue_candidate" in lowered:
        return "SOURCE_STATUS_NOT_APPROVED"
    if "approval_scope for approved_for_manual_queue_insertion_candidate" in lowered:
        return "INVALID_APPROVAL_SCOPE"
    if "approved_for_manual_queue_insertion_candidate approval artifacts must have empty diagnostics" in lowered:
        return "APPROVAL_DIAGNOSTICS_NOT_EMPTY"
    if "must include diagnostics" in lowered:
        return "DIAGNOSTICS_REQUIRED_FOR_STATUS"
    if "missing required authority boundary terms" in lowered:
        return "MISSING_AUTHORITY_TERMS"
    if "must be" in lowered:
        return "WRONG_LIFECYCLE_STATUS"
    if "unsafe authority-granting language" in lowered:
        return "UNSAFE_AUTHORITY_LANGUAGE"
    return "UNKNOWN_VALIDATION_ERROR"


def _is_unsafe_output_path(source_path: Path, output_path: Path) -> bool:
    if output_path.resolve() == source_path.resolve():
        return True
    if output_path.exists() and output_path.is_dir():
        return True
    parts = output_path.resolve().parts
    if len(parts) >= 2 and parts[0] == ".work" and parts[1] == "queues":
        return True
    if parts[:1] == ("queues",):
        return True
    for index in range(len(parts) - 1):
        if parts[index : index + 2] == ("local_harness", "fixtures"):
            return True
        if parts[index : index + 2] in {("queue", "approval"), ("queue", "handoff"), ("queue", "approval_review")}:
            return True
    if any(part in {"queue", "queues"} for part in parts):
        return True
    return False


def _write_review(
    *,
    approval_path: Path,
    output_path: Path,
    approval_payload: dict[str, Any],
    validation_result: dict[str, Any],
) -> dict[str, Any]:
    queue_approval_status = approval_payload.get("queue_approval_status")
    validation_status = validation_result.get("validation_status", "failed")
    diagnostics = list(validation_result.get("diagnostics", []))
    diagnostic_codes = list(validation_result.get("diagnostic_codes", []))
    source_authority_boundary = approval_payload.get("authority_boundary", [])
    authority_boundary = sorted(set(source_authority_boundary) | OUTPUT_AUTHORITY_TERMS)
    approval_scope = approval_payload.get("approval_scope")

    if validation_status == "passed":
        if queue_approval_status == "approved_for_manual_queue_insertion_candidate":
            review_status = "ready_for_manual_queue_insertion_review"
            recommended_next_step = (
                "Retain as a candidate-only review artifact for separate manual approval."
            )
        elif queue_approval_status == "rejected_before_queue_insertion":
            review_status = "rejected_before_queue_insertion"
            recommended_next_step = "Keep the item review-only and repair the approval artifact if needed."
        elif queue_approval_status == "needs_repair_before_queue_insertion_review":
            review_status = "needs_repair_before_queue_insertion_review"
            recommended_next_step = "Repair the approval artifact before another review pass."
        else:
            review_status = "blocked_needs_repair"
            recommended_next_step = "Review the approval artifact and repair the queue approval status."
            if not diagnostics:
                diagnostics = [
                    "validation passed but queue_approval_status is not a supported review status"
                ]
    else:
        review_status = "blocked_needs_repair"
        if not diagnostics:
            diagnostics = ["queue approval validation failed"]
        recommended_next_step = "Repair the approval artifact and rerun the read-only review command."

    payload = {
        "review_schema": REVIEW_SCHEMA,
        "source_approval_schema": "queue_approval_path_v1",
        "source_approval_path": str(approval_path),
        "validation_status": validation_status,
        "diagnostic_codes": diagnostic_codes,
        "diagnostics": diagnostics,
        "queue_approval_status": queue_approval_status,
        "review_status": review_status,
        "approval_scope": approval_scope,
        "authority_boundary": authority_boundary,
        "output_path": str(output_path),
        "automation_status": "not_automated",
        "queue_insertion_status": "not_inserted",
        "queue_writing_status": "not_implemented",
        "queue_running_status": "not_run",
        "repo_mutation_status": "explicit_review_output_only",
        "fixture_import_status": "not_imported",
        "training_capture_status": "not_captured",
        "promotion_status": "not_promoted",
        "deployment_status": "not_deployed",
        "downstream_use_status": "prohibited_until_review",
        "recommended_next_step": recommended_next_step,
    }
    missing_terms = sorted(SOURCE_REQUIRED_AUTHORITY_TERMS - set(source_authority_boundary))
    if missing_terms and validation_status == "passed":
        payload["review_status"] = "blocked_needs_repair"
        payload["diagnostics"] = diagnostics + [
            "approval artifact missing required authority boundary terms: " + ", ".join(missing_terms)
        ]
        payload["diagnostic_codes"] = diagnostic_codes + ["MISSING_AUTHORITY_TERMS"]
        payload["recommended_next_step"] = "Repair the approval artifact and rerun the read-only review command."
        payload["validation_status"] = "failed"
    return payload


def review_queue_approval_path(
    *,
    approval_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if _is_unsafe_output_path(approval_path, output_path):
        raise ValueError("output path is unsafe for a queue approval review artifact")

    approval_payload = json.loads(approval_path.read_text(encoding="utf-8"))
    validation_result = None
    try:
        validation_result = validate_queue_approval_path(
            approval_payload,
            approval_path=approval_path,
        )
    except Exception as exc:  # noqa: BLE001
        validation_result = {
            "validation_schema": "queue_approval_path_validation_v1",
            "validation_status": "failed",
            "approval_path": str(approval_path),
            "diagnostic_codes": [_diagnostic_code(str(exc))],
            "diagnostics": [str(exc)],
        }
    payload = _write_review(
        approval_path=approval_path,
        output_path=output_path,
        approval_payload=approval_payload,
        validation_result=validation_result,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("approval_path", type=Path)
    parser.add_argument("output_path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload = review_queue_approval_path(
            approval_path=args.approval_path,
            output_path=args.output_path,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["review_status"] == "ready_for_manual_queue_insertion_review" else 1
    except Exception as exc:  # noqa: BLE001
        diagnostics = [str(exc)]
        payload = {
            "review_schema": REVIEW_SCHEMA,
            "source_approval_schema": "queue_approval_path_v1",
            "source_approval_path": str(args.approval_path),
            "validation_status": "failed",
            "diagnostic_codes": [_diagnostic_code(str(exc))],
            "diagnostics": diagnostics,
            "queue_approval_status": None,
            "review_status": "blocked_needs_repair",
            "approval_scope": None,
            "authority_boundary": sorted(OUTPUT_AUTHORITY_TERMS),
            "output_path": str(args.output_path),
            "automation_status": "not_automated",
            "queue_insertion_status": "not_inserted",
            "queue_writing_status": "not_implemented",
            "queue_running_status": "not_run",
            "repo_mutation_status": "explicit_review_output_only",
            "fixture_import_status": "not_imported",
            "training_capture_status": "not_captured",
            "promotion_status": "not_promoted",
            "deployment_status": "not_deployed",
            "downstream_use_status": "prohibited_until_review",
            "recommended_next_step": "Repair the approval artifact and rerun the read-only review command.",
        }
        if not _is_unsafe_output_path(args.approval_path, args.output_path):
            args.output_path.parent.mkdir(parents=True, exist_ok=True)
            args.output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
