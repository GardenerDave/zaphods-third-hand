#!/usr/bin/env python3
"""Fail-closed validator for design-only queue approval path review artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

VALIDATION_SCHEMA = "queue_approval_path_validation_v1"
APPROVAL_SCHEMA = "queue_approval_path_v1"
SOURCE_REVIEW_SCHEMA = "queue_handoff_review_v1"
ALLOWED_STATUSES = {
    "approved_for_manual_queue_insertion_candidate",
    "rejected_before_queue_insertion",
    "needs_repair_before_queue_insertion_review",
}
REQUIRED_AUTHORITY_TERMS = {
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
REQUIRED_LIFECYCLE_STATUSES = {
    "automation_status": "not_automated",
    "queue_insertion_status": "not_inserted",
    "queue_writing_status": "not_implemented",
    "repo_mutation_status": "not_authorized",
    "downstream_use_status": "prohibited_until_review",
}
UNSAFE_PATTERNS = [
    r"\binserted\b",
    r"\bwrote queue\b",
    r"\bqueue written\b",
    r"\bqueued automatically\b",
    r"\bran queue\b",
    r"\bscheduled execution\b",
    r"\bautomatic handoff complete\b",
    r"\brepo mutation authorized\b",
    r"\btraining capture enabled\b",
    r"\bpromoted\b",
    r"\bdeployed\b",
    r"\bdownstream use granted\b",
    r"\bqueue insertion\b",
]
SAFE_BLOCK_MARKERS = (
    "blocked",
    "forbidden",
    "rejected",
    "not authorized",
    "not implemented",
    "not_inserted",
)
SAFE_ALLOWLIST_PHRASES = {
    "not_inserted",
    "not_implemented",
    "not_authorized",
    "prohibited_until_review",
    "approved_for_manual_queue_insertion_candidate",
}


class QueueApprovalPathError(ValueError):
    """Raised when a queue approval path artifact is unsafe or malformed."""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise QueueApprovalPathError("approval artifact must be a JSON object")
    return payload


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise QueueApprovalPathError(f"approval artifact field {key!r} must be a non-empty string")
    return value.strip()


def _require_nonempty_list_of_str(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise QueueApprovalPathError(f"approval artifact field {key!r} must be a non-empty list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise QueueApprovalPathError(f"approval artifact field {key!r} must be a non-empty list of strings")
    return [item.strip() for item in value]


def _require_list_of_str(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise QueueApprovalPathError(f"approval artifact field {key!r} must be a list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise QueueApprovalPathError(f"approval artifact field {key!r} must be a list of strings")
    return [item.strip() for item in value]


def _has_unsafe_language(text: str) -> str | None:
    lowered = text.lower()
    if lowered.strip() in SAFE_ALLOWLIST_PHRASES:
        return None
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, lowered):
            if any(marker in lowered for marker in SAFE_BLOCK_MARKERS):
                continue
            return pattern
    return None


def _collect_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, list):
        for item in value:
            strings.extend(_collect_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(_collect_strings(item))
    return strings


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
    if "source_review_schema must be" in lowered:
        return "WRONG_SOURCE_REVIEW_SCHEMA"
    if "source_review_path must be" in lowered:
        return "EMPTY_SOURCE_REVIEW_PATH"
    if "source_queue_handoff_review_status" in lowered and "approved_for_queue_candidate" in lowered:
        return "SOURCE_STATUS_NOT_APPROVED"
    if "queue_approval_status must be one of" in lowered:
        return "INVALID_QUEUE_APPROVAL_STATUS"
    if "approval_scope for approved_for_manual_queue_insertion_candidate" in lowered:
        return "INVALID_APPROVAL_SCOPE"
    if "approved_for_manual_queue_insertion_candidate approval artifacts must have empty diagnostics" in lowered:
        return "APPROVAL_DIAGNOSTICS_NOT_EMPTY"
    if "must include diagnostics" in lowered:
        return "DIAGNOSTICS_REQUIRED_FOR_STATUS"
    if "missing required authority boundary terms" in lowered:
        return "MISSING_AUTHORITY_TERMS"
    if "must be" in lowered and any(key in lowered for key in REQUIRED_LIFECYCLE_STATUSES):
        return "WRONG_LIFECYCLE_STATUS"
    if "unsafe authority-granting language" in lowered:
        return "UNSAFE_AUTHORITY_LANGUAGE"
    return "UNKNOWN_VALIDATION_ERROR"


def validate_queue_approval_path(
    approval: Any,
    *,
    approval_path: Path | None = None,
) -> dict[str, Any]:
    payload = _require_object(approval)

    missing = [
        key
        for key in {
            "approval_schema",
            "source_review_schema",
            "source_review_path",
            "source_queue_handoff_review_status",
            "queue_approval_status",
            "approval_scope",
            "reviewer_note",
            "required_checks",
            "authority_boundary",
            "automation_status",
            "queue_insertion_status",
            "queue_writing_status",
            "repo_mutation_status",
            "downstream_use_status",
            "diagnostics",
            "recommended_next_step",
        }
        if key not in payload
    ]
    if missing:
        raise QueueApprovalPathError(
            f"approval artifact missing required fields: {', '.join(sorted(missing))}"
        )

    approval_schema = _require_str(payload, "approval_schema")
    if approval_schema != APPROVAL_SCHEMA:
        raise QueueApprovalPathError(
            f"approval_schema must be {APPROVAL_SCHEMA!r}, got {approval_schema!r}"
        )

    source_review_schema = _require_str(payload, "source_review_schema")
    if source_review_schema != SOURCE_REVIEW_SCHEMA:
        raise QueueApprovalPathError(
            f"source_review_schema must be {SOURCE_REVIEW_SCHEMA!r}, got {source_review_schema!r}"
        )

    source_review_path = _require_str(payload, "source_review_path")
    source_queue_handoff_review_status = _require_str(payload, "source_queue_handoff_review_status")
    queue_approval_status = _require_str(payload, "queue_approval_status")
    if queue_approval_status not in ALLOWED_STATUSES:
        raise QueueApprovalPathError(
            "queue_approval_status must be one of: " + ", ".join(sorted(ALLOWED_STATUSES))
        )

    approval_scope = _require_str(payload, "approval_scope")
    reviewer_note = _require_str(payload, "reviewer_note")
    required_checks = _require_nonempty_list_of_str(payload, "required_checks")
    authority_boundary = _require_nonempty_list_of_str(payload, "authority_boundary")
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise QueueApprovalPathError("diagnostics must be a list")
    if any(not isinstance(item, str) for item in diagnostics):
        raise QueueApprovalPathError("diagnostics must be a list of strings")
    recommended_next_step = _require_str(payload, "recommended_next_step")

    for field, expected in REQUIRED_LIFECYCLE_STATUSES.items():
        value = payload.get(field)
        if value != expected:
            raise QueueApprovalPathError(f"approval artifact field {field!r} must be {expected!r}")

    missing_terms = sorted(REQUIRED_AUTHORITY_TERMS - set(authority_boundary))
    if missing_terms:
        raise QueueApprovalPathError(
            "approval artifact missing required authority boundary terms: "
            + ", ".join(missing_terms)
        )

    if queue_approval_status == "approved_for_manual_queue_insertion_candidate":
        if source_queue_handoff_review_status != "approved_for_queue_candidate":
            raise QueueApprovalPathError(
                "approved_for_manual_queue_insertion_candidate requires source_queue_handoff_review_status to be "
                "'approved_for_queue_candidate'"
            )
        if diagnostics:
            raise QueueApprovalPathError(
                "approved_for_manual_queue_insertion_candidate approval artifacts must have empty diagnostics"
            )
        approval_scope_lower = approval_scope.lower()
        if not any(word in approval_scope_lower for word in ("candidate", "manual", "review-only", "review only")):
            raise QueueApprovalPathError(
                "approval_scope for approved_for_manual_queue_insertion_candidate must describe candidate/manual/review-only scope"
            )
        if _has_unsafe_language(recommended_next_step) is not None:
            raise QueueApprovalPathError(
                "approval artifact contains unsafe authority-granting language"
            )
    elif queue_approval_status in {
        "rejected_before_queue_insertion",
        "needs_repair_before_queue_insertion_review",
    }:
        if not diagnostics:
            raise QueueApprovalPathError(
                f"{queue_approval_status} approval artifacts must include diagnostics"
            )

    for text in _collect_strings(payload):
        if text in SAFE_ALLOWLIST_PHRASES:
            continue
        unsafe = _has_unsafe_language(text)
        if unsafe is not None:
            raise QueueApprovalPathError(
                f"approval artifact contains unsafe authority-granting language: {unsafe}"
            )

    return {
        "validation_schema": VALIDATION_SCHEMA,
        "validation_status": "passed",
        "approval_path": str(approval_path) if approval_path is not None else "<in-memory-queue-approval>",
        "diagnostic_codes": [],
        "diagnostics": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("approval_path", type=Path)
    args = parser.parse_args(argv)
    try:
        approval = _read_json(args.approval_path)
        result = validate_queue_approval_path(approval, approval_path=args.approval_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        diagnostics = [str(exc)]
        diagnostic_code = _diagnostic_code(str(exc))
        if isinstance(exc, json.JSONDecodeError):
            diagnostics.insert(0, "malformed JSON packet")
            diagnostic_code = "MALFORMED_JSON"
        print(
            json.dumps(
                {
                    "validation_schema": VALIDATION_SCHEMA,
                    "validation_status": "failed",
                    "approval_path": str(args.approval_path),
                    "diagnostic_codes": [diagnostic_code],
                    "diagnostics": diagnostics,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
