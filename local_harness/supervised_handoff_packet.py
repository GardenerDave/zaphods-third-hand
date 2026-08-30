#!/usr/bin/env python3
"""Model-free supervised handoff packet builder and validator."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from local_harness.supervised_downstream_use_gate import (
    SupervisedDownstreamUseGateError,
    validate_supervised_downstream_use_gate_record,
)


ALLOWED_HANDOFF_STATUSES = {"prepared", "blocked"}
REQUIRED_HANDOFF_PACKET_KEYS = {
    "handoff_id",
    "gate_id",
    "decision_id",
    "attempt_id",
    "validation_id",
    "triage_id",
    "orchestration_id",
    "gate_status",
    "handoff_status",
    "handoff_scope",
    "next_step_type",
    "next_step_summary",
    "handoff_payload",
    "operator_metadata",
    "handoff_reason",
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
    "Handoff packet is not command execution authority.",
    "Handoff packet is not file modification authority.",
    "Handoff packet is not patch application authority.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Next step must remain supervised.",
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


class SupervisedHandoffPacketError(ValueError):
    """Raised when supervised handoff packets are malformed or unsafe."""


def _require_nonempty_str(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SupervisedHandoffPacketError(f"record field {key!r} must be a non-empty string")
    return value


def _require_str_list(record: dict[str, Any], key: str, *, allow_empty: bool = False) -> list[str]:
    value = record.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise SupervisedHandoffPacketError(f"record field {key!r} must be a list of non-empty strings")
    if not value and not allow_empty:
        raise SupervisedHandoffPacketError(f"record field {key!r} must not be empty")
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


def validate_supervised_handoff_packet(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise SupervisedHandoffPacketError("supervised handoff packet must be a JSON object")

    missing = sorted(REQUIRED_HANDOFF_PACKET_KEYS - set(record))
    if missing:
        raise SupervisedHandoffPacketError(f"record missing required fields: {', '.join(missing)}")

    forbidden = sorted(FORBIDDEN_AUTHORITY_KEYS & set(record))
    if forbidden:
        raise SupervisedHandoffPacketError(
            f"record contains forbidden authority fields: {', '.join(forbidden)}"
        )

    _require_nonempty_str(record, "handoff_id")
    _require_nonempty_str(record, "gate_id")
    _require_nonempty_str(record, "decision_id")
    _require_nonempty_str(record, "attempt_id")
    _require_nonempty_str(record, "validation_id")
    _require_nonempty_str(record, "triage_id")
    _require_nonempty_str(record, "orchestration_id")
    _require_nonempty_str(record, "gate_status")
    _require_nonempty_str(record, "handoff_status")
    _require_nonempty_str(record, "handoff_scope")
    _require_nonempty_str(record, "next_step_type")
    _require_nonempty_str(record, "next_step_summary")
    if "next_step_objective" in record and record["next_step_objective"] is not None:
        _require_nonempty_str(record, "next_step_objective")
    _require_nonempty_str(record, "handoff_reason")

    if "prompt_packet_id" in record and record["prompt_packet_id"] is not None:
        _require_nonempty_str(record, "prompt_packet_id")

    gate_status = record.get("gate_status")
    if gate_status not in {"allowed", "blocked"}:
        raise SupervisedHandoffPacketError("gate_status must be 'allowed' or 'blocked'")

    handoff_status = record.get("handoff_status")
    if handoff_status not in ALLOWED_HANDOFF_STATUSES:
        raise SupervisedHandoffPacketError("handoff_status must be 'prepared' or 'blocked'")

    if handoff_status == "prepared" and gate_status != "allowed":
        raise SupervisedHandoffPacketError("handoff_status 'prepared' requires gate_status 'allowed'")
    if gate_status == "blocked" and handoff_status != "blocked":
        raise SupervisedHandoffPacketError("gate_status 'blocked' requires handoff_status 'blocked'")

    handoff_payload = record.get("handoff_payload")
    if not isinstance(handoff_payload, dict) or not handoff_payload:
        raise SupervisedHandoffPacketError("handoff_payload must be a non-empty object")
    _require_nonempty_str(handoff_payload, "payload_kind")
    _require_nonempty_str(handoff_payload, "source_attempt_id")
    _require_nonempty_str(handoff_payload, "source_validation_id")
    _require_nonempty_str(handoff_payload, "source_decision_id")
    _require_nonempty_str(handoff_payload, "source_gate_id")

    if handoff_payload["source_attempt_id"] != record["attempt_id"]:
        raise SupervisedHandoffPacketError("handoff_payload.source_attempt_id must match attempt_id")
    if handoff_payload["source_validation_id"] != record["validation_id"]:
        raise SupervisedHandoffPacketError("handoff_payload.source_validation_id must match validation_id")
    if handoff_payload["source_decision_id"] != record["decision_id"]:
        raise SupervisedHandoffPacketError("handoff_payload.source_decision_id must match decision_id")
    if handoff_payload["source_gate_id"] != record["gate_id"]:
        raise SupervisedHandoffPacketError("handoff_payload.source_gate_id must match gate_id")

    operator_metadata = record.get("operator_metadata")
    if not isinstance(operator_metadata, dict) or not operator_metadata:
        raise SupervisedHandoffPacketError("operator_metadata must be a non-empty object")
    if operator_metadata.get("review_required") is not True:
        raise SupervisedHandoffPacketError("operator_metadata.review_required must be true")
    if not isinstance(operator_metadata.get("operator"), str) or not operator_metadata["operator"].strip():
        raise SupervisedHandoffPacketError("operator_metadata.operator must be a non-empty string")

    _require_str_list(record, "allowed_downstream_use")

    prohibited_downstream_use = _require_str_list(record, "prohibited_downstream_use")
    missing_prohibited = [
        item for item in REQUIRED_PROHIBITED_DOWNSTREAM_USE if item not in prohibited_downstream_use
    ]
    if missing_prohibited:
        raise SupervisedHandoffPacketError(
            "record missing required prohibited_downstream_use entries: " + ", ".join(missing_prohibited)
        )

    authority_boundaries = _require_str_list(record, "authority_boundaries")
    missing_boundaries = [
        boundary for boundary in REQUIRED_AUTHORITY_BOUNDARIES if boundary not in authority_boundaries
    ]
    if missing_boundaries:
        raise SupervisedHandoffPacketError(
            "record missing required authority boundaries: " + ", ".join(missing_boundaries)
        )

    provenance = record.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise SupervisedHandoffPacketError("provenance must be a non-empty object")
    if provenance.get("input_gate_id") != record["gate_id"]:
        raise SupervisedHandoffPacketError("provenance.input_gate_id must match gate_id")

    lowered_strings = [value.lower() for value in _iter_strings(record)]
    for term in sorted(FORBIDDEN_AUTHORITY_TERMS):
        if any(term in value for value in lowered_strings):
            raise SupervisedHandoffPacketError(
                f"record contains forbidden authority language: {term}"
            )

    return record


def build_supervised_handoff_packet(
    *,
    handoff_id: str,
    gate_record: dict[str, Any],
    next_step_type: str,
    next_step_summary: str,
    handoff_payload: dict[str, Any],
    operator_metadata: dict[str, Any],
    handoff_reason: str,
    next_step_objective: str | None = None,
    handoff_status: str | None = None,
    handoff_scope: str = "bounded_supervised_input_only",
    allowed_downstream_use: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        validated_gate = validate_supervised_downstream_use_gate_record(gate_record)
    except SupervisedDownstreamUseGateError as exc:
        raise SupervisedHandoffPacketError(str(exc)) from exc

    gate_status = validated_gate["gate_status"]

    if handoff_status is None:
        handoff_status = "prepared" if gate_status == "allowed" else "blocked"

    if handoff_status == "prepared" and gate_status != "allowed":
        raise SupervisedHandoffPacketError("handoff_status 'prepared' requires gate_status 'allowed'")

    if allowed_downstream_use is None:
        if handoff_status == "prepared":
            allowed_downstream_use = [
                "may_be_used_as_reviewed_input_for_next_supervised_step",
            ]
        else:
            allowed_downstream_use = [
                "not_authorized_for_next_supervised_step_input",
            ]

    payload = deepcopy(handoff_payload)
    payload["source_attempt_id"] = validated_gate["attempt_id"]
    payload["source_validation_id"] = validated_gate["validation_id"]
    payload["source_decision_id"] = validated_gate["decision_id"]
    payload["source_gate_id"] = validated_gate["gate_id"]

    record = {
        "handoff_id": handoff_id,
        "gate_id": validated_gate["gate_id"],
        "decision_id": validated_gate["decision_id"],
        "attempt_id": validated_gate["attempt_id"],
        "validation_id": validated_gate["validation_id"],
        "triage_id": validated_gate["triage_id"],
        "orchestration_id": validated_gate["orchestration_id"],
        "prompt_packet_id": validated_gate.get("prompt_packet_id"),
        "gate_status": gate_status,
        "handoff_status": handoff_status,
        "handoff_scope": handoff_scope,
        "next_step_type": next_step_type,
        "next_step_summary": next_step_summary,
        "next_step_objective": next_step_objective,
        "handoff_payload": payload,
        "operator_metadata": deepcopy(operator_metadata),
        "handoff_reason": handoff_reason,
        "allowed_downstream_use": list(allowed_downstream_use),
        "prohibited_downstream_use": list(REQUIRED_PROHIBITED_DOWNSTREAM_USE),
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": deepcopy(provenance)
        if provenance is not None
        else {
            "source": "supervised_handoff_packet",
            "input_gate_id": validated_gate["gate_id"],
        },
    }
    return validate_supervised_handoff_packet(record)
