#!/usr/bin/env python3
"""Model-free supervised model attempt recording and validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


REQUIRED_RECORD_KEYS = {
    "attempt_id",
    "orchestration_id",
    "triage_id",
    "model_metadata",
    "operator_metadata",
    "raw_model_output",
    "validation_status",
    "acceptance_status",
    "authority_boundaries",
    "provenance",
}
REQUIRED_AUTHORITY_BOUNDARIES = [
    "No command execution authority is granted.",
    "No direct file modification authority is granted.",
    "No automatic patch promotion authority is granted.",
    "No automatic training authority is granted.",
    "No default failure-to-curriculum capture authority is granted.",
    "Human review is required before downstream use.",
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


class SupervisedModelAttemptError(ValueError):
    """Raised when a supervised model attempt record is malformed or unsafe."""


def validate_transport_qualification_ref(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SupervisedModelAttemptError("transport_qualification_ref must be a JSON object")
    allowed = {"artifact_ref", "artifact_sha256", "qualification_id", "qualification_selector"}
    unexpected = sorted(set(payload) - allowed)
    if unexpected:
        raise SupervisedModelAttemptError(
            "transport_qualification_ref contains unsupported fields: " + ", ".join(unexpected)
        )
    forbidden = [key for key in ("valid", "passed", "trusted", "policy_usable", "completed") if payload.get(key) is not None]
    if forbidden:
        raise SupervisedModelAttemptError(
            "transport_qualification_ref contains truth-bearing fields: " + ", ".join(forbidden)
        )
    artifact_ref = payload.get("artifact_ref")
    artifact_sha256 = payload.get("artifact_sha256")
    if not isinstance(artifact_ref, str) or not artifact_ref.strip():
        raise SupervisedModelAttemptError("transport_qualification_ref.artifact_ref must be a non-empty string")
    if not isinstance(artifact_sha256, str) or len(artifact_sha256) != 64 or any(c not in "0123456789abcdef" for c in artifact_sha256.lower()):
        raise SupervisedModelAttemptError("transport_qualification_ref.artifact_sha256 must be a 64-character hex string")
    qualification_id = payload.get("qualification_id")
    if qualification_id is not None and (not isinstance(qualification_id, str) or not qualification_id.strip()):
        raise SupervisedModelAttemptError("transport_qualification_ref.qualification_id must be a non-empty string when present")
    qualification_selector = payload.get("qualification_selector")
    if qualification_selector is not None and (not isinstance(qualification_selector, str) or not qualification_selector.strip()):
        raise SupervisedModelAttemptError("transport_qualification_ref.qualification_selector must be a non-empty string when present")
    return {
        "artifact_ref": artifact_ref,
        "artifact_sha256": artifact_sha256,
        "qualification_id": qualification_id,
        "qualification_selector": qualification_selector,
    }


def _require_nonempty_str(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SupervisedModelAttemptError(f"record field {key!r} must be a non-empty string")
    return value


def _require_str_list(record: dict[str, Any], key: str) -> list[str]:
    value = record.get(key)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise SupervisedModelAttemptError(f"record field {key!r} must be a non-empty list of strings")
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


def validate_supervised_model_attempt_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise SupervisedModelAttemptError("supervised model attempt record must be a JSON object")

    missing = sorted(REQUIRED_RECORD_KEYS - set(record))
    if missing:
        raise SupervisedModelAttemptError(f"record missing required fields: {', '.join(missing)}")

    forbidden = sorted(FORBIDDEN_AUTHORITY_KEYS & set(record))
    if forbidden:
        raise SupervisedModelAttemptError(
            f"record contains forbidden authority fields: {', '.join(forbidden)}"
        )

    _require_nonempty_str(record, "attempt_id")
    _require_nonempty_str(record, "orchestration_id")
    _require_nonempty_str(record, "triage_id")

    prompt_packet_id = record.get("prompt_packet_id")
    source_prompt_packet_path = record.get("source_prompt_packet_path")
    if not (
        isinstance(prompt_packet_id, str)
        and prompt_packet_id.strip()
        or isinstance(source_prompt_packet_path, str)
        and source_prompt_packet_path.strip()
    ):
        raise SupervisedModelAttemptError(
            "record requires prompt_packet_id or source_prompt_packet_path"
        )

    model_metadata = record.get("model_metadata")
    if not isinstance(model_metadata, dict) or not model_metadata:
        raise SupervisedModelAttemptError("record field 'model_metadata' must be a non-empty object")
    if not isinstance(model_metadata.get("model_id"), str) or not model_metadata["model_id"].strip():
        raise SupervisedModelAttemptError("model_metadata.model_id must be a non-empty string")

    operator_metadata = record.get("operator_metadata")
    if not isinstance(operator_metadata, dict) or not operator_metadata:
        raise SupervisedModelAttemptError("record field 'operator_metadata' must be a non-empty object")
    if operator_metadata.get("review_required") is not True:
        raise SupervisedModelAttemptError("operator_metadata.review_required must be true")

    raw_model_output = record.get("raw_model_output")
    if not isinstance(raw_model_output, str):
        raise SupervisedModelAttemptError("record field 'raw_model_output' must be a string")

    if record.get("validation_status") != "not_validated":
        raise SupervisedModelAttemptError("validation_status must be 'not_validated'")
    if record.get("acceptance_status") != "not_reviewed":
        raise SupervisedModelAttemptError("acceptance_status must be 'not_reviewed'")

    authority_boundaries = _require_str_list(record, "authority_boundaries")
    missing_boundaries = [
        boundary for boundary in REQUIRED_AUTHORITY_BOUNDARIES if boundary not in authority_boundaries
    ]
    if missing_boundaries:
        raise SupervisedModelAttemptError(
            "record missing required authority boundaries: " + ", ".join(missing_boundaries)
        )

    provenance = record.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise SupervisedModelAttemptError("record field 'provenance' must be a non-empty object")
    if not isinstance(provenance.get("source"), str) or not provenance["source"].strip():
        raise SupervisedModelAttemptError("provenance.source must be a non-empty string")

    lowered_strings = [value.lower() for value in _iter_strings(record)]
    for term in sorted(FORBIDDEN_AUTHORITY_TERMS):
        if any(term in value for value in lowered_strings):
            raise SupervisedModelAttemptError(
                f"record contains forbidden authority language: {term}"
            )

    return record


def build_supervised_model_attempt_record(
    *,
    attempt_id: str,
    orchestration_id: str,
    triage_id: str,
    raw_model_output: str,
    model_metadata: dict[str, Any],
    operator_metadata: dict[str, Any],
    prompt_packet_id: str | None = None,
    source_prompt_packet_path: str | None = None,
    transport_qualification_ref: dict[str, Any] | None = None,
    output_format_claim: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw_model_output, str):
        raise SupervisedModelAttemptError("raw_model_output must be a string")
    validated_transport_ref = (
        validate_transport_qualification_ref(transport_qualification_ref)
        if transport_qualification_ref is not None
        else None
    )

    record = {
        "attempt_id": attempt_id,
        "orchestration_id": orchestration_id,
        "triage_id": triage_id,
        "prompt_packet_id": prompt_packet_id,
        "source_prompt_packet_path": source_prompt_packet_path,
        "model_metadata": deepcopy(model_metadata),
        "operator_metadata": deepcopy(operator_metadata),
        "raw_model_output": raw_model_output,
        "output_format_claim": output_format_claim,
        "validation_status": "not_validated",
        "acceptance_status": "not_reviewed",
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": deepcopy(provenance)
        if provenance is not None
        else {
            "source": "manual_record",
            "input_artifact": "model_prompt_packet",
            "raw_output_preserved": True,
            "orchestration_id": orchestration_id,
            "triage_id": triage_id,
            "prompt_packet_id": prompt_packet_id,
            "source_prompt_packet_path": source_prompt_packet_path,
            "transport_qualification_ref": validated_transport_ref,
        },
    }
    return validate_supervised_model_attempt_record(record)
