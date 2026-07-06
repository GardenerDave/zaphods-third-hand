#!/usr/bin/env python3
"""Model-free supervised review decision record builder and validator."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from local_harness.supervised_attempt_output_validator import (
    SupervisedAttemptOutputValidationError,
    validate_supervised_attempt_output_validation_record,
)
from local_harness.supervised_model_attempt import (
    SupervisedModelAttemptError,
    validate_supervised_model_attempt_record,
)


ALLOWED_DECISIONS = {"accepted", "rejected", "revision_requested"}
REQUIRED_DECISION_RECORD_KEYS = {
    "decision_id",
    "attempt_id",
    "validation_id",
    "triage_id",
    "orchestration_id",
    "validation_status",
    "decision",
    "decision_scope",
    "decided_at",
    "reviewer_metadata",
    "decision_reason",
    "allowed_downstream_use",
    "prohibited_downstream_use",
    "authority_boundaries",
    "provenance",
}
REQUIRED_PROHIBITED_DOWNSTREAM_USE = [
    "no_command_execution",
    "no_direct_file_modification",
    "no_automatic_patch_promotion",
    "no_automatic_training",
    "no_default_failure_to_curriculum_capture",
]
REQUIRED_AUTHORITY_BOUNDARIES = [
    "Review decision is not command execution authority.",
    "No direct file modification authority is granted.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Downstream use must remain supervised.",
]
FORBIDDEN_AUTHORITY_KEYS = {
    "execution_authority",
    "direct_file_modification_authority",
    "auto_promote",
    "auto_train",
    "auto_curriculum_capture",
}
FORBIDDEN_AUTHORITY_TERMS = {
    "execution authority granted",
    "direct file modification authority granted",
    "automatic patch promotion authority granted",
    "automatic training authority granted",
    "default failure-to-curriculum capture authority granted",
}


class SupervisedReviewDecisionError(ValueError):
    """Raised when supervised review decision records are malformed or unsafe."""


def _require_nonempty_str(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SupervisedReviewDecisionError(f"record field {key!r} must be a non-empty string")
    return value


def _require_str_list(record: dict[str, Any], key: str, *, allow_empty: bool = False) -> list[str]:
    value = record.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise SupervisedReviewDecisionError(f"record field {key!r} must be a list of non-empty strings")
    if not value and not allow_empty:
        raise SupervisedReviewDecisionError(f"record field {key!r} must not be empty")
    return value


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        items: list[str] = []
        for entry in value:
            items.extend(_iter_strings(entry))
        return items
    if isinstance(value, dict):
        items: list[str] = []
        for key, entry in value.items():
            if isinstance(key, str):
                items.append(key)
            items.extend(_iter_strings(entry))
        return items
    return []


def validate_supervised_review_decision_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise SupervisedReviewDecisionError("supervised review decision record must be a JSON object")

    missing = sorted(REQUIRED_DECISION_RECORD_KEYS - set(record))
    if missing:
        raise SupervisedReviewDecisionError(f"record missing required fields: {', '.join(missing)}")

    forbidden = sorted(FORBIDDEN_AUTHORITY_KEYS & set(record))
    if forbidden:
        raise SupervisedReviewDecisionError(
            f"record contains forbidden authority fields: {', '.join(forbidden)}"
        )

    _require_nonempty_str(record, "decision_id")
    _require_nonempty_str(record, "attempt_id")
    _require_nonempty_str(record, "validation_id")
    _require_nonempty_str(record, "triage_id")
    _require_nonempty_str(record, "orchestration_id")
    _require_nonempty_str(record, "decision_scope")
    _require_nonempty_str(record, "decided_at")
    _require_nonempty_str(record, "decision_reason")

    if "prompt_packet_id" in record and record["prompt_packet_id"] is not None:
        _require_nonempty_str(record, "prompt_packet_id")

    decision = record.get("decision")
    if decision not in ALLOWED_DECISIONS:
        raise SupervisedReviewDecisionError(
            "decision must be one of: accepted, rejected, revision_requested"
        )

    validation_status = record.get("validation_status")
    if validation_status not in {"passed", "failed"}:
        raise SupervisedReviewDecisionError("validation_status must be 'passed' or 'failed'")
    if decision == "accepted" and validation_status != "passed":
        raise SupervisedReviewDecisionError("accepted decision requires validation_status 'passed'")

    reviewer_metadata = record.get("reviewer_metadata")
    if not isinstance(reviewer_metadata, dict) or not reviewer_metadata:
        raise SupervisedReviewDecisionError("reviewer_metadata must be a non-empty object")
    if reviewer_metadata.get("review_required") is not True:
        raise SupervisedReviewDecisionError("reviewer_metadata.review_required must be true")
    if not isinstance(reviewer_metadata.get("reviewer"), str) or not reviewer_metadata["reviewer"].strip():
        raise SupervisedReviewDecisionError("reviewer_metadata.reviewer must be a non-empty string")

    _require_str_list(record, "allowed_downstream_use")

    prohibited_downstream_use = _require_str_list(record, "prohibited_downstream_use")
    missing_prohibited = [
        item for item in REQUIRED_PROHIBITED_DOWNSTREAM_USE if item not in prohibited_downstream_use
    ]
    if missing_prohibited:
        raise SupervisedReviewDecisionError(
            "record missing required prohibited_downstream_use entries: " + ", ".join(missing_prohibited)
        )

    authority_boundaries = _require_str_list(record, "authority_boundaries")
    missing_boundaries = [
        boundary for boundary in REQUIRED_AUTHORITY_BOUNDARIES if boundary not in authority_boundaries
    ]
    if missing_boundaries:
        raise SupervisedReviewDecisionError(
            "record missing required authority boundaries: " + ", ".join(missing_boundaries)
        )

    provenance = record.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise SupervisedReviewDecisionError("provenance must be a non-empty object")
    if provenance.get("input_attempt_id") != record["attempt_id"]:
        raise SupervisedReviewDecisionError("provenance.input_attempt_id must match attempt_id")
    if provenance.get("input_validation_id") != record["validation_id"]:
        raise SupervisedReviewDecisionError("provenance.input_validation_id must match validation_id")

    lowered_strings = [value.lower() for value in _iter_strings(record)]
    for term in sorted(FORBIDDEN_AUTHORITY_TERMS):
        if any(term in value for value in lowered_strings):
            raise SupervisedReviewDecisionError(
                f"record contains forbidden authority language: {term}"
            )

    return record


def build_supervised_review_decision_record(
    *,
    decision_id: str,
    attempt_record: dict[str, Any],
    validation_record: dict[str, Any],
    decision: str,
    decision_reason: str,
    decided_at: str,
    reviewer_metadata: dict[str, Any],
    decision_scope: str = "output_contract_only",
    allowed_downstream_use: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        validated_attempt = validate_supervised_model_attempt_record(attempt_record)
    except SupervisedModelAttemptError as exc:
        raise SupervisedReviewDecisionError(str(exc)) from exc

    try:
        validated_validation = validate_supervised_attempt_output_validation_record(validation_record)
    except SupervisedAttemptOutputValidationError as exc:
        raise SupervisedReviewDecisionError(str(exc)) from exc

    if validated_attempt["attempt_id"] != validated_validation["attempt_id"]:
        raise SupervisedReviewDecisionError("attempt_id mismatch between attempt and validation records")
    if validated_attempt["triage_id"] != validated_validation["triage_id"]:
        raise SupervisedReviewDecisionError("triage_id mismatch between attempt and validation records")
    if validated_attempt["orchestration_id"] != validated_validation["orchestration_id"]:
        raise SupervisedReviewDecisionError(
            "orchestration_id mismatch between attempt and validation records"
        )

    attempt_prompt_packet_id = validated_attempt.get("prompt_packet_id")
    validation_prompt_packet_id = validated_validation.get("prompt_packet_id")
    if attempt_prompt_packet_id and validation_prompt_packet_id:
        if attempt_prompt_packet_id != validation_prompt_packet_id:
            raise SupervisedReviewDecisionError(
                "prompt_packet_id mismatch between attempt and validation records"
            )

    if decision == "accepted" and validated_validation["validation_status"] != "passed":
        raise SupervisedReviewDecisionError("accepted decision requires validation_status 'passed'")

    if allowed_downstream_use is None:
        if decision == "accepted":
            allowed_downstream_use = [
                "may_be_used_as_reviewed_input_for_next_supervised_step",
            ]
        elif decision == "rejected":
            allowed_downstream_use = [
                "not_approved_for_downstream_use",
            ]
        else:
            allowed_downstream_use = [
                "may_be_used_for_supervised_revision_planning_only",
            ]

    record = {
        "decision_id": decision_id,
        "attempt_id": validated_attempt["attempt_id"],
        "validation_id": validated_validation["validation_id"],
        "triage_id": validated_attempt["triage_id"],
        "orchestration_id": validated_attempt["orchestration_id"],
        "prompt_packet_id": attempt_prompt_packet_id,
        "validation_status": validated_validation["validation_status"],
        "decision": decision,
        "decision_scope": decision_scope,
        "decided_at": decided_at,
        "reviewer_metadata": deepcopy(reviewer_metadata),
        "decision_reason": decision_reason,
        "allowed_downstream_use": list(allowed_downstream_use),
        "prohibited_downstream_use": list(REQUIRED_PROHIBITED_DOWNSTREAM_USE),
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": deepcopy(provenance)
        if provenance is not None
        else {
            "source": "supervised_review_decision",
            "input_attempt_id": validated_attempt["attempt_id"],
            "input_validation_id": validated_validation["validation_id"],
        },
    }
    return validate_supervised_review_decision_record(record)
