#!/usr/bin/env python3
"""Bounded live snapshot for explicitly configured local workers.

This module collects only evidence that the current worker endpoints expose.
It does not infer administrative authority, scheduling eligibility, or
capability beyond binding verification and model advertisement.
"""

from __future__ import annotations

from copy import deepcopy
import os
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from local_harness.binding_preflight import preflight_worker_binding
from local_harness.icm_spec import resolve_worker_spec


FLEET_SNAPSHOT_SCHEMA = "zth_local_fleet_snapshot_v1"
SNAPSHOT_STALE_AFTER_SECONDS = 900


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_from_iso(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def freshness_state(*, generated_at: str, checked_at: str | None) -> dict[str, Any]:
    generated = _utc_from_iso(generated_at)
    checked = _utc_from_iso(checked_at)
    if generated is None or checked is None:
        return {"state": "unknown", "age_seconds": None, "stale": True}
    age_seconds = max(0.0, (generated - checked).total_seconds())
    stale = age_seconds > SNAPSHOT_STALE_AFTER_SECONDS
    return {"state": "fresh" if not stale else "stale", "age_seconds": age_seconds, "stale": stale}


def _availability_from_binding(result: Mapping[str, Any]) -> str:
    if result.get("binding_status") == "VERIFIED":
        return "AVAILABLE"
    if result.get("endpoint_status") == "error":
        return "UNAVAILABLE"
    if result.get("failure_class") in {"models_endpoint_unavailable", "unsupported_endpoint"}:
        return "UNKNOWN"
    if result.get("advertised_models"):
        return "AVAILABLE"
    return "UNKNOWN"


def _build_worker_entry(
    *,
    worker: str,
    spec: Mapping[str, Any],
    generated_at: str,
    opener: Any,
    timeout: int,
    checked_at_override: str | None = None,
) -> dict[str, Any]:
    expected_model = spec.get("configured_model") or spec.get("model")
    base_url = spec.get("base_url") or spec.get("url")
    entry: dict[str, Any] = {
        "worker": worker,
        "configured_base_url": base_url,
        "expected_model": expected_model,
        "binding_status": "UNVERIFIED",
        "availability": "UNKNOWN",
        "advertised_models": [],
        "failure_class": None,
        "checked_at": checked_at_override,
        "freshness": {"state": "unknown", "age_seconds": None, "stale": True},
        "capability_refs": [],
        "qualification_refs": [],
        "evidence": {"source": "static_config_only", "preflight": None},
    }

    if spec.get("api") == "native-completion":
        entry["failure_class"] = "models_endpoint_unavailable"
        entry["freshness"] = {"state": "unknown", "age_seconds": None, "stale": True}
        entry["evidence"]["preflight"] = {
            "schema": "zth_worker_binding_preflight_v1",
            "worker": worker,
            "configured_base_url": base_url,
            "expected_model": expected_model,
            "endpoint_status": "unknown",
            "advertised_models": [],
            "binding_status": "UNVERIFIED",
            "failure_class": "models_endpoint_unavailable",
            "reason": "native completion workers do not expose /v1/models",
            "checked_at": checked_at_override or generated_at,
            "evidence": {"models_url": None, "http_status": None, "response_sha256": None},
        }
        return entry

    preflight = preflight_worker_binding(
        worker=worker,
        configured_base_url=str(base_url),
        expected_model=str(expected_model),
        timeout=timeout,
        opener=opener,
    )
    entry["binding_status"] = preflight["binding_status"]
    entry["advertised_models"] = list(preflight["advertised_models"])
    entry["failure_class"] = preflight["failure_class"]
    entry["checked_at"] = preflight["checked_at"]
    entry["availability"] = _availability_from_binding(preflight)
    entry["freshness"] = freshness_state(generated_at=generated_at, checked_at=entry["checked_at"])
    entry["evidence"]["preflight"] = preflight
    if preflight.get("failure_class") == "binding_verified":
        entry["capability_refs"] = [f"binding_preflight:{worker}:{expected_model}"]
        entry["qualification_refs"] = [f"advertisement:{worker}:{expected_model}"]
    return entry


def _configured_bindings_from_env(env: Mapping[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "worker": env.get("ZTH_CAPABILITY_WORKER_NAME", "router"),
            "base_url": env.get("ZTH_CAPABILITY_WORKER_BASE_URL"),
            "model": env.get("ZTH_CAPABILITY_WORKER_MODEL"),
        },
        {
            "worker": env.get("ZTH_CAPABILITY_TEACHER_NAME", "handoff"),
            "base_url": env.get("ZTH_CAPABILITY_TEACHER_BASE_URL"),
            "model": env.get("ZTH_CAPABILITY_TEACHER_MODEL"),
        },
    ]


def collect_local_fleet_snapshot(
    *,
    bindings: Iterable[Mapping[str, Any]] | None = None,
    opener: Any,
    timeout: int = 30,
    generated_at: str | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or utc_now()
    env = env or os.environ
    binding_specs = list(bindings or _configured_bindings_from_env(env))
    workers = []
    for binding in binding_specs:
        worker = str(binding["worker"])
        spec = resolve_worker_spec(
            worker,
            base_url=binding.get("base_url"),
            model=binding.get("model"),
        )
        workers.append(
            _build_worker_entry(
                worker=worker,
                spec={
                    "api": spec.api,
                    "base_url": spec.base_url,
                    "url": spec.url,
                    "configured_model": spec.configured_model,
                    "model": spec.model,
                },
                generated_at=generated_at,
                opener=opener,
                timeout=timeout,
            )
        )
    return {"schema": FLEET_SNAPSHOT_SCHEMA, "generated_at": generated_at, "workers": workers}


def verified_workers(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    workers = snapshot.get("workers", [])
    if not isinstance(workers, list):
        return []
    admitted = []
    for worker in workers:
        if not isinstance(worker, dict):
            continue
        if worker.get("binding_status") != "VERIFIED":
            continue
        if worker.get("availability") != "AVAILABLE":
            continue
        admitted.append(deepcopy(worker))
    return admitted
