#!/usr/bin/env python3
"""Isolated, calibration-only Run 4A intervention arms.

This path is deliberately separate from ``run_capability_loop``.  One arm
accepts one immutable valid baseline failure, performs exactly one selected
intervention, makes exactly one worker retry, validates it, and terminates.
It never escalates, merges evidence, promotes patches, trains, queues work, or
changes routing behavior.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from local_harness.distilled_retry_packet import render_distilled_retry_prompt
from local_harness.icm_call import call_worker
from local_harness.icm_spec import WorkerResponse, classify_worker_response, resolve_worker_spec
from local_harness.resource_telemetry import build_resource_telemetry
from local_harness.run4_cost_audit import immediate_action_cost
from local_harness.supervised_capability_loop import (
    REQUIRED_AUTHORITY,
    _parse_teacher,
    _resolve_deterministic_retry_patch,
    _teacher_prompt,
    _validator_result,
    _hardware_identity,
    sha256_text,
)


ARM_SOURCES = ("deterministic_patch_retry", "local_teacher", "external_teacher")
EXTERNAL_TIMEOUT_SECONDS = 120
TERMINAL_ARM_DISPOSITIONS = {"ready_for_review", "unresolved", "infrastructure_error"}


class Run4AIncompleteError(RuntimeError):
    """A started call lacks a durable response or infrastructure artifact."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_write(path: Path, payload: Any) -> str:
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    return hashlib.sha256(data.encode()).hexdigest()


def _append_transition(path: Path, transition: str, **fields: Any) -> None:
    record = {"transition": transition, "timestamp": _utc_now(), **fields}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _read_transitions(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_no_ambiguous_started(trajectory: Path) -> None:
    transitions = _read_transitions(trajectory)
    captured = {row.get("call_id") for row in transitions if row.get("transition") in {"response_captured", "infrastructure_failed"}}
    started = [row for row in transitions if row.get("transition") == "call_started"]
    ambiguous = [row for row in started if row.get("call_id") not in captured]
    if ambiguous:
        raise Run4AIncompleteError("Run 4A arm has a started call without response/infrastructure artifact")


def _response_payload(response: WorkerResponse, *, role: str, started: float, captured: float, timeout_seconds: int, adapter_identity: str | None = None) -> dict[str, Any]:
    metadata = response.metadata()
    metadata["request_url"] = None
    metadata["endpoint_alias"] = os.environ.get("ZTH_PUBLIC_HOST_ALIAS", "JARVIS_LOCAL") if role != "external_teacher" else None
    classification = metadata.get("transport_classification") or classify_worker_response(response.status, response.error)
    metadata["transport_classification"] = classification
    metadata["resource_telemetry"] = build_resource_telemetry(
        role=role,
        request_start_monotonic=started,
        response_capture_monotonic=captured,
        response_metadata=metadata,
        model_identity=adapter_identity or metadata.get("resolved_model") or metadata.get("model"),
        adapter_server_identity=(metadata.get("endpoint_alias") if role != "external_teacher" else os.environ.get("ZTH_EXTERNAL_TEACHER_SERVICE_CLASS")),
        timeout_seconds=timeout_seconds,
        transport_classification=classification,
        hardware_device_identity=_hardware_identity(role),
    )
    return {"status": response.status, "content": response.content, "metadata": metadata}


def _teacher_payload(raw: str, *, identity: str, role: str, started: float, captured: float, response_metadata: Mapping[str, Any] | None = None, raw_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    classification = "model_response" if isinstance(raw, str) and raw.strip() else "empty_model_response"
    telemetry = build_resource_telemetry(
        role=role,
        request_start_monotonic=started,
        response_capture_monotonic=captured,
        response_metadata=response_metadata or {"model": identity, "transport_classification": classification},
        model_identity=identity,
        adapter_server_identity=os.environ.get("ZTH_EXTERNAL_TEACHER_SERVICE_CLASS") if role == "external_teacher" else "JARVIS_LOCAL",
        timeout_seconds=EXTERNAL_TIMEOUT_SECONDS if role == "external_teacher" else int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")),
        transport_classification=classification,
        hardware_device_identity=_hardware_identity(role),
    )
    return {"identity": identity, "raw_text": raw, "raw": dict(raw_payload or {}), "parsed": _parse_teacher(raw), "transport_valid": classification == "model_response", "transport_classification": classification, "resource_telemetry": telemetry}


def _default_worker(prompt: str) -> WorkerResponse:
    spec = resolve_worker_spec(
        os.environ.get("ZTH_CAPABILITY_WORKER_NAME", "router"),
        base_url=os.environ.get("ZTH_CAPABILITY_WORKER_BASE_URL"),
        model=os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"),
    )
    return call_worker(spec, prompt, int(os.environ.get("ZTH_CAPABILITY_WORKER_MAX_TOKENS", "768")), timeout=int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", "900")))


def _default_local_teacher(prompt: str) -> WorkerResponse:
    spec = resolve_worker_spec(
        os.environ.get("ZTH_CAPABILITY_TEACHER_NAME", "handoff"),
        base_url=os.environ.get("ZTH_CAPABILITY_TEACHER_BASE_URL"),
        model=os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"),
    )
    return call_worker(spec, prompt, int(os.environ.get("ZTH_CAPABILITY_TEACHER_MAX_TOKENS", "1200")), timeout=int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")))


def _default_external_teacher(prompt: str) -> tuple[str, str]:
    command = os.environ.get("ZTH_EXTERNAL_TEACHER_COMMAND")
    if not command:
        raise RuntimeError("external teacher command is not configured")
    completed = subprocess.run(shlex.split(command), input=prompt, text=True, capture_output=True, timeout=EXTERNAL_TIMEOUT_SECONDS, check=False)
    if completed.returncode != 0:
        error = RuntimeError(f"external teacher command failed with exit code {completed.returncode}")
        error.exit_code = completed.returncode  # type: ignore[attr-defined]
        error.stderr = completed.stderr  # type: ignore[attr-defined]
        raise error
    if not completed.stdout.strip():
        raise RuntimeError("external teacher returned an empty response")
    return os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY", "codex-cli-0.146.0"), completed.stdout


def _write_infrastructure_failure(out_dir: Path, trajectory: Path, *, call_id: str, role: str, started_at: str, started: float, exc: BaseException, timeout_seconds: int, response_present: bool = False, response_artifact: str | None = None) -> dict[str, Any]:
    if isinstance(exc, subprocess.TimeoutExpired):
        classification = "transport_timeout"
    elif isinstance(exc, OSError):
        classification = "transport_launch_failure"
    elif "empty response" in str(exc).casefold():
        classification = "empty_model_response"
    elif "exit code" in str(exc).casefold():
        classification = "transport_nonzero_exit"
    else:
        classification = "other_infrastructure_error"
    artifact = {
        "schema": "zth_run4a_infrastructure_failure_v1",
        "call_id": call_id,
        "role": role,
        "classification": classification,
        "started_at": started_at,
        "completed_at": _utc_now(),
        "timeout_seconds": timeout_seconds,
        "adapter_identity": os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY") if role == "external_teacher" else None,
        "exit_code": getattr(exc, "exit_code", None),
        "stderr": str(getattr(exc, "stderr", ""))[-4000:],
        "error": str(exc)[-4000:],
        "response_present": response_present,
        "capability_verdict_available": False,
        "resource_telemetry": build_resource_telemetry(
            role=role,
            request_start_monotonic=started,
            response_capture_monotonic=time.monotonic(),
            response_metadata={"model": None, "transport_classification": classification},
            timeout_seconds=timeout_seconds,
            transport_classification=classification,
            hardware_device_identity=_hardware_identity(role),
        ),
    }
    path = out_dir / f"{role}.infrastructure.json"
    if response_artifact is not None:
        artifact["response_artifact"] = response_artifact
    artifact["artifact_ref"] = path.name
    digest = _json_write(path, artifact)
    _append_transition(trajectory, "infrastructure_failed", call_id=call_id, role=role, artifact_ref=path.name, artifact_sha256=digest, classification=classification, capability_verdict_available=False)
    return artifact


def _call_worker(out_dir: Path, trajectory: Path, task: Mapping[str, Any], prompt: str, *, worker: Callable[[str], WorkerResponse], attempt_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    prompt_path = out_dir / f"{attempt_id}.prompt.txt"
    raw_path = out_dir / f"{attempt_id}.raw.json"
    validation_path = out_dir / f"{attempt_id}.validation.json"
    prompt_digest = prompt_path.write_text(prompt, encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    call_id = f"worker:{attempt_id}"
    started_at = _utc_now()
    started = time.monotonic()
    _append_transition(trajectory, "call_started", call_id=call_id, role="worker", prompt_ref=prompt_path.name, prompt_sha256=prompt_hash, started_at=started_at)
    try:
        response = worker(prompt)
        captured = time.monotonic()
        raw = _response_payload(response, role="worker", started=started, captured=captured, timeout_seconds=int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", "900")))
    except Exception as exc:
        artifact = _write_infrastructure_failure(out_dir, trajectory, call_id=call_id, role="worker", started_at=started_at, started=started, exc=exc, timeout_seconds=int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", "900")))
        return None, artifact
    raw_digest = _json_write(raw_path, raw)
    if raw["metadata"]["transport_classification"] != "model_response":
        artifact = _write_infrastructure_failure(out_dir, trajectory, call_id=call_id, role="worker", started_at=started_at, started=started, exc=RuntimeError(raw["metadata"].get("error") or raw["metadata"]["transport_classification"]), timeout_seconds=int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", "900")), response_present=True, response_artifact=raw_path.name)
        return None, artifact
    validation = _validator_result(raw["content"], task, attempt_id=attempt_id)
    validation_digest = _json_write(validation_path, validation)
    _append_transition(trajectory, "response_captured", call_id=call_id, role="worker", artifact_ref=raw_path.name, artifact_sha256=raw_digest, validation_ref=validation_path.name, validation_sha256=validation_digest, transport_valid=True)
    return {"raw": raw, "validation": validation, "raw_ref": raw_path.name, "validation_ref": validation_path.name, "telemetry": raw["metadata"]["resource_telemetry"]}, None


def _call_teacher(out_dir: Path, trajectory: Path, task: Mapping[str, Any], prompt: str, *, role: str, local_teacher: Callable[[str], WorkerResponse], external_teacher: Callable[[str], tuple[str, str]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    prompt_path = out_dir / f"{role}.prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    call_id = f"{role}:1"
    started_at = _utc_now()
    started = time.monotonic()
    _append_transition(trajectory, "call_started", call_id=call_id, role=role, prompt_ref=prompt_path.name, prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(), started_at=started_at)
    try:
        if role == "local_teacher":
            response = local_teacher(prompt)
            captured = time.monotonic()
            raw = _response_payload(response, role=role, started=started, captured=captured, timeout_seconds=int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")))
            if raw["metadata"]["transport_classification"] != "model_response":
                raise RuntimeError(raw["metadata"].get("error") or raw["metadata"]["transport_classification"])
            payload = _teacher_payload(raw["content"], identity=raw["metadata"].get("resolved_model") or "local_teacher", role=role, started=started, captured=captured, response_metadata=raw["metadata"], raw_payload=raw)
        else:
            identity, text = external_teacher(prompt)
            captured = time.monotonic()
            payload = _teacher_payload(text, identity=identity, role=role, started=started, captured=captured)
            if not payload["transport_valid"]:
                raise RuntimeError("external teacher returned an empty response")
    except Exception as exc:
        return None, _write_infrastructure_failure(out_dir, trajectory, call_id=call_id, role=role, started_at=started_at, started=started, exc=exc, timeout_seconds=EXTERNAL_TIMEOUT_SECONDS if role == "external_teacher" else int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")))
    ref = out_dir / f"{role}.raw.json"
    digest = _json_write(ref, payload)
    _append_transition(trajectory, "response_captured", call_id=call_id, role=role, artifact_ref=ref.name, artifact_sha256=digest, transport_valid=True)
    return payload, None


def _validate_baseline(baseline: Mapping[str, Any], task: Mapping[str, Any]) -> None:
    if baseline.get("task_id") != task["task_id"]:
        raise ValueError("baseline task identity mismatch")
    if baseline.get("transport_valid") is not True or baseline.get("transport_classification") != "model_response":
        raise ValueError("Run 4A arm requires a transport-valid model baseline")
    if baseline.get("validation", {}).get("validation_status") != "failed":
        raise ValueError("Run 4A arm requires a deterministic baseline failure")


def run_isolated_intervention_arm(
    task: Mapping[str, Any],
    baseline: Mapping[str, Any],
    *,
    intervention: str,
    out_dir: Path,
    worker: Callable[[str], WorkerResponse] | None = None,
    local_teacher: Callable[[str], WorkerResponse] | None = None,
    external_teacher: Callable[[str], tuple[str, str]] | None = None,
    deterministic_patch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if intervention not in ARM_SOURCES:
        raise ValueError(f"unsupported Run 4A intervention: {intervention}")
    _validate_baseline(baseline, task)
    out_dir.mkdir(parents=True, exist_ok=True)
    trajectory = out_dir / "trajectory.jsonl"
    _assert_no_ambiguous_started(trajectory)
    summary_path = out_dir / "arm_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("disposition") in TERMINAL_ARM_DISPOSITIONS:
            return summary
    baseline_copy = dict(baseline)
    baseline_copy["raw"] = dict(baseline.get("raw", {}))
    _json_write(out_dir / "baseline_reference.json", baseline_copy)
    worker = worker or _default_worker
    local_teacher = local_teacher or _default_local_teacher
    external_teacher = external_teacher or _default_external_teacher
    intervention_prompt: str
    teacher_payload: dict[str, Any] | None = None
    infrastructure: dict[str, Any] | None = None
    if intervention == "deterministic_patch_retry":
        if not deterministic_patch:
            raise ValueError("deterministic_patch_retry requires a frozen patch binding")
        patch_id, patch_hash, patch_delta = _resolve_deterministic_retry_patch(deterministic_patch)
        intervention_prompt = render_distilled_retry_prompt(task, baseline["validation"], patch_delta)
        worker_result, infrastructure = _call_worker(out_dir, trajectory, task, intervention_prompt, worker=worker, attempt_id="worker-retry")
        patch_binding = {"patch_id": patch_id, "patch_sha256": patch_hash}
    else:
        intervention_prompt = _teacher_prompt(task, role=intervention, failed_transitions=[{"validation": baseline["validation"], "intervention_id": "none:1"}], patch_records=[])
        teacher_payload, infrastructure = _call_teacher(out_dir, trajectory, task, intervention_prompt, role=intervention, local_teacher=local_teacher, external_teacher=external_teacher)
        patch_binding = None
        if teacher_payload is not None:
            retry_prompt = json.dumps({"task_prompt": task["prompt"], "output_contract": task["output_contract"], "reference_facts": task["validator"].get("reference_facts", {}), "baseline_diagnostics": baseline["validation"].get("diagnostics", []), "intervention": teacher_payload.get("parsed", {}), "authority": REQUIRED_AUTHORITY}, indent=2, sort_keys=True)
            worker_result, infrastructure = _call_worker(out_dir, trajectory, task, retry_prompt, worker=worker, attempt_id="worker-retry")
        else:
            worker_result = None
    if infrastructure is not None:
        summary = {
            "schema": "zth_run4a_arm_summary_v1",
            "task_id": task["task_id"], "task_family": task["task_family"], "intervention": intervention,
            "capability_verdict_available": False, "deterministically_validated_rescue": False,
            "transport_valid": False, "disposition": "infrastructure_error", "infrastructure_artifact": infrastructure.get("artifact_ref"),
            "patch_binding": patch_binding, "baseline_reference": "baseline_reference.json",
            "expected_action_cost_ms": immediate_action_cost(intervention, {"worker_time_ms": 5276.567, "local_teacher_time_ms": 16220.624, "external_teacher_time_ms": 28704.012}),
            "authority": "calibration_only_review_required",
        }
    else:
        validation = worker_result["validation"]
        summary = {
            "schema": "zth_run4a_arm_summary_v1",
            "task_id": task["task_id"], "task_family": task["task_family"], "intervention": intervention,
            "capability_verdict_available": True, "transport_valid": True, "transport_classification": "model_response",
            "deterministically_validated_rescue": validation["validation_status"] == "passed",
            "validation_status": validation["validation_status"], "failed_checks": [check["check_id"] for check in validation.get("checks", []) if check.get("status") == "failed"],
            "baseline_reference": "baseline_reference.json", "patch_binding": patch_binding,
            "expected_action_cost_ms": immediate_action_cost(intervention, {"worker_time_ms": 5276.567, "local_teacher_time_ms": 16220.624, "external_teacher_time_ms": 28704.012}),
            "realized_elapsed_ms": worker_result["telemetry"]["elapsed_ms"] + (teacher_payload["resource_telemetry"]["elapsed_ms"] if teacher_payload else 0),
            "resource_telemetry": {"worker": worker_result["telemetry"], **({intervention: teacher_payload["resource_telemetry"]} if teacher_payload else {})},
            "disposition": "ready_for_review" if validation["validation_status"] == "passed" else "unresolved",
            "authority": "calibration_only_review_required",
        }
    _append_transition(trajectory, summary["disposition"], task_id=task["task_id"], intervention=intervention, capability_verdict_available=summary["capability_verdict_available"])
    _json_write(summary_path, summary)
    return summary


def main() -> int:
    raise SystemExit("Run 4A harness requires an explicit experiment driver; no standalone model execution is enabled in preparation mode.")


if __name__ == "__main__":
    main()
