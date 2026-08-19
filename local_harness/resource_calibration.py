"""Model-free calibration from resource telemetry only."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from local_harness.resource_telemetry import resource_weight_manifest_sha256


def _timestamp(value: str) -> float:
    from datetime import datetime

    return datetime.fromisoformat(value).timestamp()


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _transition_durations(path: Path, started: str, captured: str) -> list[float]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    starts: dict[tuple[Any, Any], float] = {}
    durations = []
    for record in records:
        transition = record.get("transition")
        key = (record.get("attempt"), record.get("intervention_id"), record.get("intervention_source"))
        if transition == started:
            starts[key] = _timestamp(record["timestamp"])
        elif transition == captured and key in starts:
            durations.append((record["timestamp"], starts.pop(key)))
    return [( _timestamp(end) - start) * 1000 for end, start in durations]


def _all_transition_durations(task_dir: Path, role: str) -> list[float]:
    trajectory = task_dir / "trajectory.jsonl"
    if not trajectory.is_file():
        return []
    if role == "worker":
        started, captured = "worker_call_started", "worker_output_captured"
    elif role == "local_teacher":
        started, captured = "local_teacher_started", "local_teacher_response_captured"
    else:
        started, captured = "external_teacher_started", "external_teacher_response_captured"
    return _transition_durations(trajectory, started, captured)


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"call_count": 0, "elapsed_ms_coverage": 0, "median_elapsed_ms": None, "mean_elapsed_ms": None, "p25_elapsed_ms": None, "p75_elapsed_ms": None, "minimum_elapsed_ms": None, "maximum_elapsed_ms": None}
    return {
        "call_count": len(values),
        "elapsed_ms_coverage": len(values),
        "median_elapsed_ms": statistics.median(values),
        "mean_elapsed_ms": statistics.mean(values),
        "p25_elapsed_ms": _percentile(values, 0.25),
        "p75_elapsed_ms": _percentile(values, 0.75),
        "minimum_elapsed_ms": min(values),
        "maximum_elapsed_ms": max(values),
    }


def _identity_values(root: Path, role: str) -> list[str]:
    values: list[str] = []
    for raw in root.glob("*/*/*.raw.json"):
        payload = json.loads(raw.read_text(encoding="utf-8"))
        metadata = payload.get("metadata") or {}
        if role == "worker" and metadata.get("model"):
            values.append(metadata["model"])
    if role == "local_teacher":
        for path in root.glob("*/*/local-teacher-*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            model = ((payload.get("raw") or {}).get("metadata") or {}).get("model")
            if model:
                values.append(model)
    if role == "external_teacher":
        for path in root.glob("*/*/external-teacher.json"):
            identity = json.loads(path.read_text(encoding="utf-8")).get("identity")
            if identity:
                values.append(identity)
    return sorted(set(values))


def calibrate_resource_telemetry(root: Path) -> dict[str, Any]:
    """Extract only call metadata and start/capture timing transitions."""
    values: dict[str, list[float]] = defaultdict(list)
    for arm in ("control", "treatment"):
        for task_dir in sorted((root / arm).glob("*")):
            if not task_dir.is_dir():
                continue
            for role in ("worker", "local_teacher", "external_teacher"):
                values[role].extend(_all_transition_durations(task_dir, role))
    roles = {role: _stats(values[role]) for role in ("worker", "local_teacher", "external_teacher")}
    for role in roles:
        roles[role]["model_identities"] = _identity_values(root, role)
        roles[role]["hardware_identity"] = None
    return {
        "schema": "zth_resource_calibration_v1",
        "source": str(root),
        "resource_roles": roles,
        "basis": "median_observed_elapsed_ms_per_call",
        "used_fields": ["role", "model_identity", "trajectory.start_timestamp", "trajectory.capture_timestamp", "elapsed_ms"],
        "excluded_fields": ["validation", "pass", "unresolved", "routing", "task_family", "intervention_success"],
    }


def calibration_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def expected_decision_cost(manifest: dict[str, Any], expected_calls: dict[str, int]) -> float:
    """Compute planning cost only from an approved frozen time manifest."""
    if manifest.get("frozen") is not True or manifest.get("review_status") != "approved":
        raise ValueError("expected decision cost requires an approved frozen manifest")
    weights = manifest.get("weights") or {}
    mapping = {"worker": "worker_time_ms", "local_teacher": "local_teacher_time_ms", "external_teacher": "external_teacher_time_ms"}
    total = 0.0
    for role, calls in expected_calls.items():
        weight = weights.get(mapping[role])
        if not isinstance(weight, (int, float)):
            raise ValueError(f"missing approved time weight for {role}")
        total += calls * weight
    return total


def realized_resource_cost(elapsed_ms_by_role: dict[str, list[float]]) -> float:
    """Compute realized elapsed cost from actual call intervals only."""
    return sum(sum(values) for values in elapsed_ms_by_role.values())
