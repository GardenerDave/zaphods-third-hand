#!/usr/bin/env python3
"""Model-free supervised downstream-use gate record builder and validator."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from local_harness.supervised_review_decision import (
    ALLOWED_DECISIONS,
    SupervisedReviewDecisionError,
    validate_supervised_review_decision_record,
)


ALLOWED_GATE_STATUSES = {"allowed", "blocked"}
REQUIRED_GATE_RECORD_KEYS = {
    "gate_id",
    "decision_id",
    "attempt_id",
    "validation_id",
    "triage_id",
    "orchestration_id",
    "review_decision",
    "requested_downstream_use",
    "gate_status",
    "gate_scope",
    "gated_at",
    "operator_metadata",
    "gate_reason",
    "allowed_downstream_use",
    "prohibited_downstream_use",
    "authority_boundaries",
    "provenance",
}
REQUIRED_PROHIBITED_DOWNSTREAM_USE = [
    "no_command_execution",
    "no_direct_file_modification",
    "no_patch_application",
    "no_automatic_patch_promotion",
    "no_automatic_training",
    "no_default_failure_to_curriculum_capture",
]
REQUIRED_AUTHORITY_BOUNDARIES = [
    "Downstream-use gate is not command execution authority.",
    "Downstream-use gate is not file modification authority.",
    "Downstream-use gate is not patch application authority.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Downstream use must remain supervised.",
]
FORBIDDEN_AUTHORITY_KEYS = {
    "execution_authority",
    "direct_file_modification_authority",
    "patch_application_authority",
    "auto_promote",
    "auto_train",
    "auto_curriculum_capture",
}
FORBIDDEN_AUTHORITY_TERMS = {
    "execution authority granted",
    "direct file modification authority granted",
    "patch application authority granted",
    "automatic patch promotion authority granted",
    "automatic training authority granted",
    "default failure-to-curriculum capture authority granted",
}


class SupervisedDownstreamUseGateError(ValueError):
    """Raised when downstream-use gate records are malformed or unsafe."""


def _require_nonempty_str(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SupervisedDownstreamUseGateError(f"record field {key!r} must be a non-empty string")
    return value


def _require_str_list(record: dict[str, Any], key: str, *, allow_empty: bool = False) -> list[str]:
    value = record.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise SupervisedDownstreamUseGateError(
            f"record field {key!r} must be a list of non-empty strings"
        )
    if not value and not allow_empty:
        raise SupervisedDownstreamUseGateError(f"record field {key!r} must not be empty")
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


def validate_supervised_downstream_use_gate_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise SupervisedDownstreamUseGateError("supervised downstream-use gate record must be a JSON object")

    missing = sorted(REQUIRED_GATE_RECORD_KEYS - set(record))
    if missing:
        raise SupervisedDownstreamUseGateError(f"record missing required fields: {', '.join(missing)}")

    forbidden = sorted(FORBIDDEN_AUTHORITY_KEYS & set(record))
    if forbidden:
        raise SupervisedDownstreamUseGateError(
            f"record contains forbidden authority fields: {', '.join(forbidden)}"
        )

    _require_nonempty_str(record, "gate_id")
    _require_nonempty_str(record, "decision_id")
    _require_nonempty_str(record, "attempt_id")
    _require_nonempty_str(record, "validation_id")
    _require_nonempty_str(record, "triage_id")
    _require_nonempty_str(record, "orchestration_id")
    _require_nonempty_str(record, "requested_downstream_use")
    _require_nonempty_str(record, "gate_scope")
    _require_nonempty_str(record, "gated_at")
    _require_nonempty_str(record, "gate_reason")

    if "prompt_packet_id" in record and record["prompt_packet_id"] is not None:
        _require_nonempty_str(record, "prompt_packet_id")

    review_decision = record.get("review_decision")
    if review_decision not in ALLOWED_DECISIONS:
        raise SupervisedDownstreamUseGateError(
            "review_decision must be one of: accepted, rejected, revision_requested"
        )

    gate_status = record.get("gate_status")
    if gate_status not in ALLOWED_GATE_STATUSES:
        raise SupervisedDownstreamUseGateError("gate_status must be 'allowed' or 'blocked'")

    if gate_status == "allowed" and review_decision != "accepted":
        raise SupervisedDownstreamUseGateError(
            "gate_status 'allowed' requires review_decision 'accepted'"
        )

    operator_metadata = record.get("operator_metadata")
    if not isinstance(operator_metadata, dict) or not operator_metadata:
        raise SupervisedDownstreamUseGateError("operator_metadata must be a non-empty object")
    if operator_metadata.get("review_required") is not True:
        raise SupervisedDownstreamUseGateError("operator_metadata.review_required must be true")
    if not isinstance(operator_metadata.get("operator"), str) or not operator_metadata["operator"].strip():
        raise SupervisedDownstreamUseGateError("operator_metadata.operator must be a non-empty string")

    _require_str_list(record, "allowed_downstream_use")

    prohibited_downstream_use = _require_str_list(record, "prohibited_downstream_use")
    missing_prohibited = [
        item for item in REQUIRED_PROHIBITED_DOWNSTREAM_USE if item not in prohibited_downstream_use
    ]
    if missing_prohibited:
        raise SupervisedDownstreamUseGateError(
            "record missing required prohibited_downstream_use entries: " + ", ".join(missing_prohibited)
        )

    authority_boundaries = _require_str_list(record, "authority_boundaries")
    missing_boundaries = [
        boundary for boundary in REQUIRED_AUTHORITY_BOUNDARIES if boundary not in authority_boundaries
    ]
    if missing_boundaries:
        raise SupervisedDownstreamUseGateError(
            "record missing required authority boundaries: " + ", ".join(missing_boundaries)
        )

    provenance = record.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise SupervisedDownstreamUseGateError("provenance must be a non-empty object")
    if provenance.get("input_decision_id") != record["decision_id"]:
        raise SupervisedDownstreamUseGateError("provenance.input_decision_id must match decision_id")

    lowered_strings = [value.lower() for value in _iter_strings(record)]
    for term in sorted(FORBIDDEN_AUTHORITY_TERMS):
        if any(term in value for value in lowered_strings):
            raise SupervisedDownstreamUseGateError(
                f"record contains forbidden authority language: {term}"
            )

    return record


def build_supervised_downstream_use_gate_record(
    *,
    gate_id: str,
    decision_record: dict[str, Any],
    requested_downstream_use: str,
    operator_metadata: dict[str, Any],
    gate_reason: str,
    gated_at: str,
    gate_status: str | None = None,
    gate_scope: str = "bounded_supervised_input_only",
    allowed_downstream_use: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        validated_decision = validate_supervised_review_decision_record(decision_record)
    except SupervisedReviewDecisionError as exc:
        raise SupervisedDownstreamUseGateError(str(exc)) from exc

    review_decision = validated_decision["decision"]

    if gate_status is None:
        gate_status = "allowed" if review_decision == "accepted" else "blocked"

    if gate_status == "allowed" and review_decision != "accepted":
        raise SupervisedDownstreamUseGateError(
            "gate_status 'allowed' requires review_decision 'accepted'"
        )

    if allowed_downstream_use is None:
        if gate_status == "allowed":
            allowed_downstream_use = [
                "may_be_used_as_reviewed_input_for_next_supervised_step",
            ]
        else:
            allowed_downstream_use = [
                "not_authorized_for_next_supervised_step_input",
            ]

    record = {
        "gate_id": gate_id,
        "decision_id": validated_decision["decision_id"],
        "attempt_id": validated_decision["attempt_id"],
        "validation_id": validated_decision["validation_id"],
        "triage_id": validated_decision["triage_id"],
        "orchestration_id": validated_decision["orchestration_id"],
        "prompt_packet_id": validated_decision.get("prompt_packet_id"),
        "review_decision": review_decision,
        "requested_downstream_use": requested_downstream_use,
        "gate_status": gate_status,
        "gate_scope": gate_scope,
        "gated_at": gated_at,
        "operator_metadata": deepcopy(operator_metadata),
        "gate_reason": gate_reason,
        "allowed_downstream_use": list(allowed_downstream_use),
        "prohibited_downstream_use": list(REQUIRED_PROHIBITED_DOWNSTREAM_USE),
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": deepcopy(provenance)
        if provenance is not None
        else {
            "source": "supervised_downstream_use_gate",
            "input_decision_id": validated_decision["decision_id"],
        },
    }
    return validate_supervised_downstream_use_gate_record(record)
