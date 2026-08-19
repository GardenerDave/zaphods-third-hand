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


def canonical_resource_weight_manifest(payload: Mapping[str, Any]) -> str:
    """Canonical JSON digest with the self-referential digest removed."""
    canonical = dict(payload)
    canonical["manifest_sha256"] = None
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"))


def resource_weight_manifest_sha256(payload_or_path: Mapping[str, Any] | Path) -> str:
    payload = json.loads(payload_or_path.read_text(encoding="utf-8")) if isinstance(payload_or_path, Path) else payload_or_path
    return hashlib.sha256(canonical_resource_weight_manifest(payload).encode("utf-8")).hexdigest()


def load_approved_resource_weights(path: Path) -> dict[str, Any]:
    """Load weights only after an explicit, frozen approval decision."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "zth_resource_weight_manifest_v1" or payload.get("version") != 1:
        raise ValueError("resource weight manifest schema mismatch")
    if payload.get("frozen") is not True or payload.get("review_status") != "approved":
        raise ValueError("resource weights require frozen approved manifest")
    if not isinstance(payload.get("rationale"), str) or not payload["rationale"].strip():
        raise ValueError("approved resource weights require rationale")
    approval = payload.get("approval")
    if not isinstance(approval, dict) or any(not isinstance(approval.get(key), str) or not approval[key].strip() for key in ("reviewer", "approved_at", "approval_basis")):
        raise ValueError("approved resource weights require reviewer, approved_at, and approval_basis")
    provenance = payload.get("provenance")
    required_provenance = (
        "source_experiment", "source_preregistration_sha256", "worker_model",
        "local_teacher_model", "external_teacher_identity", "external_timeout_seconds",
        "telemetry_schema", "calibration_schema",
    )
    if not isinstance(provenance, dict) or any(provenance.get(key) in (None, "") for key in required_provenance):
        raise ValueError("approved resource weights require configuration provenance")
    digest = payload.get("manifest_sha256")
    if not isinstance(digest, str) or digest != resource_weight_manifest_sha256(payload):
        raise ValueError("resource weight manifest digest mismatch")
    weights = payload.get("weights")
    units = payload.get("units")
    sources = payload.get("sources")
    if not isinstance(weights, dict) or not weights or not isinstance(units, dict) or not isinstance(sources, dict):
        raise ValueError("approved resource weight manifest has no weights")
    for name, value in weights.items():
        if value is None:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ValueError(f"resource weight {name!r} must be a non-negative number")
        if not isinstance(units.get(name), str) or not units[name].strip():
            raise ValueError(f"resource weight {name!r} lacks explicit units")
        if not isinstance(sources.get(name), str) or not sources[name].strip():
            raise ValueError(f"resource weight {name!r} lacks source/basis")
    return payload


def validate_resource_weight_bindings(
    manifest: Mapping[str, Any],
    *,
    worker_model: str,
    local_teacher_model: str,
    external_teacher_identity: str,
    external_timeout_seconds: int,
) -> None:
    """Fail closed when a future preregistration binds different resources."""
    provenance = manifest.get("provenance") or {}
    expected = {
        "worker_model": worker_model,
        "local_teacher_model": local_teacher_model,
        "external_teacher_identity": external_teacher_identity,
        "external_timeout_seconds": external_timeout_seconds,
    }
    for key, actual in expected.items():
        if provenance.get(key) != actual:
            raise ValueError(f"resource-weight binding mismatch: {key}")
