#!/usr/bin/env python3
"""Fail-closed validator for design-only queue handoff review artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

VALIDATION_SCHEMA = "queue_handoff_review_validation_v1"
REVIEW_SCHEMA = "queue_handoff_review_v1"
SOURCE_REVIEW_SCHEMA = "front_door_chain_review_v1"
ALLOWED_STATUSES = {
    "approved_for_queue_candidate",
    "rejected_for_queue",
    "needs_repair_before_queue_review",
}
REQUIRED_AUTHORITY_TERMS = {
    "no_unattended_execution",
    "no_repo_mutation_without_review",
    "no_training_capture",
    "no_promotion",
    "no_deployment",
    "no_downstream_use_authority",
    "no_queue_insertion_without_explicit_approval",
}
REQUIRED_LIFECYCLE_STATUSES = {
    "automation_status": "not_automated",
    "queue_handoff_status": "not_inserted",
    "repo_mutation_status": "not_authorized",
    "downstream_use_status": "prohibited_until_review",
}
UNSAFE_PATTERNS = [
    r"\binserted\b",
    r"\bqueued\b",
    r"\bscheduled\b",
    r"\bexecuted\b",
    r"\bmutated\b",
    r"\bmerged\b",
    r"\bimported\b",
    r"\btrained\b",
    r"\bpromoted\b",
    r"\bdeployed\b",
    r"\bdownstream use granted\b",
    r"\bauthorized repo mutation\b",
    r"\bautomatic queue handoff\b",
    r"\brouter automation\b",
    r"\bqueue insertion\b",
    r"\binsert into queue\b",
]
SAFE_BLOCK_MARKERS = (
    "blocked",
    "forbidden",
    "rejected",
    "not authorized",
    "not implemented",
)


class QueueHandoffReviewError(ValueError):
    """Raised when a queue handoff review artifact is unsafe or malformed."""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise QueueHandoffReviewError("review artifact must be a JSON object")
    return payload


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise QueueHandoffReviewError(f"review artifact field {key!r} must be a non-empty string")
    return value.strip()


def _require_nonempty_list_of_str(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise QueueHandoffReviewError(f"review artifact field {key!r} must be a non-empty list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise QueueHandoffReviewError(f"review artifact field {key!r} must be a non-empty list of strings")
    return [item.strip() for item in value]


def _require_list_of_str(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise QueueHandoffReviewError(f"review artifact field {key!r} must be a list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise QueueHandoffReviewError(f"review artifact field {key!r} must be a list of strings")
    return [item.strip() for item in value]


def _has_unsafe_language(text: str) -> str | None:
    lowered = text.lower()
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


def _failure_result(path: Path, diagnostics: list[str], review_schema: str | None = None) -> dict[str, Any]:
    return {
        "validation_schema": VALIDATION_SCHEMA,
        "validation_status": "failed",
        "review_path": str(path),
        "review_schema": review_schema,
        "diagnostics": diagnostics,
    }


def validate_queue_handoff_review(
    review: Any,
    *,
    review_path: Path | None = None,
) -> dict[str, Any]:
    payload = _require_object(review)

    missing = [
        key
        for key in {
            "review_schema",
            "source_review_schema",
            "source_review_path",
            "queue_handoff_review_status",
            "approval_scope",
            "reviewer_note",
            "required_checks",
            "authority_boundary",
            "automation_status",
            "queue_handoff_status",
            "repo_mutation_status",
            "downstream_use_status",
            "diagnostics",
            "recommended_next_step",
        }
        if key not in payload
    ]
    if missing:
        raise QueueHandoffReviewError(
            f"review artifact missing required fields: {', '.join(sorted(missing))}"
        )

    review_schema = _require_str(payload, "review_schema")
    if review_schema != REVIEW_SCHEMA:
        raise QueueHandoffReviewError(
            f"review_schema must be {REVIEW_SCHEMA!r}, got {review_schema!r}"
        )

    source_review_schema = _require_str(payload, "source_review_schema")
    if source_review_schema != SOURCE_REVIEW_SCHEMA:
        raise QueueHandoffReviewError(
            f"source_review_schema must be {SOURCE_REVIEW_SCHEMA!r}, got {source_review_schema!r}"
        )

    source_review_path = _require_str(payload, "source_review_path")
    queue_handoff_review_status = _require_str(payload, "queue_handoff_review_status")
    if queue_handoff_review_status not in ALLOWED_STATUSES:
        raise QueueHandoffReviewError(
            "queue_handoff_review_status must be one of: "
            + ", ".join(sorted(ALLOWED_STATUSES))
        )

    approval_scope = _require_str(payload, "approval_scope")
    reviewer_note = _require_str(payload, "reviewer_note")
    required_checks = _require_nonempty_list_of_str(payload, "required_checks")
    authority_boundary = _require_nonempty_list_of_str(payload, "authority_boundary")
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise QueueHandoffReviewError("diagnostics must be a list")
    if any(not isinstance(item, str) for item in diagnostics):
        raise QueueHandoffReviewError("diagnostics must be a list of strings")
    recommended_next_step = _require_str(payload, "recommended_next_step")

    for field, expected in REQUIRED_LIFECYCLE_STATUSES.items():
        value = payload.get(field)
        if value != expected:
            raise QueueHandoffReviewError(f"review artifact field {field!r} must be {expected!r}")

    missing_terms = sorted(REQUIRED_AUTHORITY_TERMS - set(authority_boundary))
    if missing_terms:
        raise QueueHandoffReviewError(
            "review artifact missing required authority boundary terms: "
            + ", ".join(missing_terms)
        )

    if queue_handoff_review_status == "approved_for_queue_candidate":
        if diagnostics:
            raise QueueHandoffReviewError(
                "approved_for_queue_candidate review artifacts must have empty diagnostics"
            )
        approval_scope_lower = approval_scope.lower()
        if "candidate-only" not in approval_scope_lower and "candidate only" not in approval_scope_lower:
            raise QueueHandoffReviewError(
                "approval_scope for approved_for_queue_candidate must describe candidate-only scope"
            )
        unsafe = _has_unsafe_language(recommended_next_step)
        if unsafe is not None:
            raise QueueHandoffReviewError(
                f"review artifact contains unsafe authority-granting language: {unsafe}"
            )
    elif queue_handoff_review_status in {"rejected_for_queue", "needs_repair_before_queue_review"}:
        if not diagnostics:
            raise QueueHandoffReviewError(
                f"{queue_handoff_review_status} review artifacts must include diagnostics"
            )

    for text in _collect_strings(payload):
        if text in {"not_inserted", "approved_for_queue_candidate"}:
            continue
        unsafe = _has_unsafe_language(text)
        if unsafe is not None:
            raise QueueHandoffReviewError(
                f"review artifact contains unsafe authority-granting language: {unsafe}"
            )

    return {
        "validation_schema": VALIDATION_SCHEMA,
        "validation_status": "passed",
        "review_path": str(review_path) if review_path is not None else "<in-memory-queue-handoff-review>",
        "diagnostics": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_path", type=Path)
    args = parser.parse_args(argv)
    review = None
    try:
        review = _read_json(args.review_path)
        result = validate_queue_handoff_review(review, review_path=args.review_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        diagnostics = [str(exc)]
        if isinstance(exc, json.JSONDecodeError):
            diagnostics.insert(0, "malformed JSON packet")
        review_schema = review.get("review_schema") if isinstance(review, dict) else None
        result = _failure_result(args.review_path, diagnostics, review_schema=review_schema)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
