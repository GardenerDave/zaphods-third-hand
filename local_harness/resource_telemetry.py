"""Common, lossless resource telemetry for supervised model calls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


RESOURCE_TELEMETRY_SCHEMA = "zth_resource_telemetry_v1"
RESOURCE_ROLES = {"worker", "local_teacher", "external_teacher"}
TELEMETRY_FIELDS = (
    "role",
    "model_identity",
    "adapter_server_identity",
    "request_start_monotonic",
    "response_capture_monotonic",
    "elapsed_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cached_tokens",
    "server_prompt_ms",
    "server_generation_ms",
    "timeout_seconds",
    "transport_classification",
    "hardware_device_identity",
)


def _usage_values(metadata: Mapping[str, Any]) -> dict[str, Any]:
    usage = metadata.get("usage") or {}
    details = usage.get("prompt_tokens_details") or {}
    timings = metadata.get("timings") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cached_tokens": details.get("cached_tokens"),
        "server_prompt_ms": timings.get("prompt_ms"),
        "server_generation_ms": timings.get("predicted_ms"),
    }


def build_resource_telemetry(
    *,
    role: str,
    request_start_monotonic: float,
    response_capture_monotonic: float,
    response_metadata: Mapping[str, Any] | None = None,
    model_identity: str | None = None,
    adapter_server_identity: str | None = None,
    timeout_seconds: int | float | None = None,
    transport_classification: str | None = None,
    hardware_device_identity: str | None = None,
) -> dict[str, Any]:
    """Build a stable record; absent telemetry remains JSON null."""
    if role not in RESOURCE_ROLES:
        raise ValueError(f"unsupported resource role: {role}")
    if response_capture_monotonic < request_start_monotonic:
        raise ValueError("response capture precedes request start")
    metadata = response_metadata or {}
    provenance = metadata.get("request_provenance") or {}
    values = _usage_values(metadata)
    record = {
        "schema": RESOURCE_TELEMETRY_SCHEMA,
        "role": role,
        "model_identity": model_identity or metadata.get("resolved_model") or metadata.get("model") or provenance.get("resolved_model"),
        "adapter_server_identity": adapter_server_identity or metadata.get("endpoint_alias") or provenance.get("endpoint_alias"),
        "request_start_monotonic": request_start_monotonic,
        "response_capture_monotonic": response_capture_monotonic,
        "elapsed_ms": round((response_capture_monotonic - request_start_monotonic) * 1000, 3),
        **values,
        "timeout_seconds": timeout_seconds,
        "transport_classification": transport_classification or metadata.get("transport_classification"),
        "hardware_device_identity": hardware_device_identity,
    }
    validate_resource_telemetry(record)
    return record


def validate_resource_telemetry(record: Mapping[str, Any]) -> None:
    if record.get("schema") != RESOURCE_TELEMETRY_SCHEMA:
        raise ValueError("resource telemetry schema mismatch")
    if record.get("role") not in RESOURCE_ROLES:
        raise ValueError("resource telemetry role is invalid")
    missing = [field for field in TELEMETRY_FIELDS if field not in record]
    if missing:
        raise ValueError(f"resource telemetry fields missing: {', '.join(missing)}")
    if record["elapsed_ms"] is not None and record["elapsed_ms"] < 0:
        raise ValueError("resource telemetry elapsed_ms cannot be negative")


def resource_weight_manifest_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_approved_resource_weights(path: Path) -> dict[str, Any]:
    """Load weights only after an explicit, frozen approval decision."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "zth_resource_weight_manifest_v1":
        raise ValueError("resource weight manifest schema mismatch")
    if payload.get("frozen") is not True or payload.get("review_status") != "approved":
        raise ValueError("resource weights require frozen approved manifest")
    weights = payload.get("weights")
    if not isinstance(weights, dict) or not weights:
        raise ValueError("approved resource weight manifest has no weights")
    for name, value in weights.items():
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"resource weight {name!r} must be a non-negative number")
    return payload
