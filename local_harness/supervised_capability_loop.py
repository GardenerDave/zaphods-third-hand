#!/usr/bin/env python3
"""Bounded, durable worker/teacher capability-mining primitive.

This module records evidence and review candidates only.  It does not accept
model output, promote patches, train models, write the roadmap queue, or invent
tasks.  A fixture selects the deterministic validator; model output never does.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from local_harness.icm_call import call_worker
from local_harness.icm_spec import WorkerResponse, classify_worker_response, resolve_worker_spec
from local_harness.prompt_patch_library import (
    PromptPatchError,
    PromptPatchLibrary,
    render_prompt_deltas,
)
from local_harness.supervised_attempt_output_validator import (
    validate_supervised_attempt_output_against_contract,
)
from local_harness.supervised_model_attempt import build_supervised_model_attempt_record
from local_harness.supervised_reference_fact_validator import validate_reference_facts
from local_harness.distilled_retry_packet import render_distilled_retry_prompt


TERMINAL_DISPOSITIONS = {"ready_for_review", "unresolved"}
REQUIRED_AUTHORITY = [
    "Deterministic validation is authoritative.",
    "Models cannot declare success.",
    "No automatic prompt-patch promotion or training is performed.",
    "No automatic queue insertion or invented work is performed.",
    "All outputs remain review-required evidence.",
]
PUBLIC_ENDPOINT_ALIAS = "JARVIS_LOCAL"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_write(path: Path, payload: Any) -> str:
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    return sha256_text(data)


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"fixture field {key!r} must be a non-empty string")
    return value


def load_task_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("task fixture must be a JSON object")
    for key in ("task_id", "task_family", "prompt"):
        _required_string(payload, key)
    contract = payload.get("output_contract")
    if not isinstance(contract, dict) or not contract:
        raise ValueError("fixture output_contract must be a non-empty object")
    validator = payload.get("validator", {"kind": "exact_json"})
    if not isinstance(validator, dict) or validator.get("kind") not in {"exact_json", "zth_output_contract"}:
        raise ValueError("fixture validator.kind must be exact_json or zth_output_contract")
    payload["validator"] = validator
    if validator["kind"] == "exact_json" and "expected_output" not in payload:
        raise ValueError("exact_json fixtures must contain expected_output")
    return payload


def load_patch_library(patch_dir: Path | None) -> PromptPatchLibrary:
    library = PromptPatchLibrary()
    if patch_dir is not None:
        library.load_dir(patch_dir)
    return library


def _patch_applicable(patch: dict[str, Any], task: Mapping[str, Any]) -> bool:
    applies = patch["applies_to"]
    stage = str(task.get("patch_stage", "validation"))
    task_type = str(task.get("task_type", task["task_family"]))
    model_size = str(task.get("model_size", "small"))
    return (
        stage in applies["stage"]
        and (task_type in applies["task_type"] or "any" in applies["task_type"])
        and (model_size in applies["model_size"] or "any" in applies["model_size"])
    )


def resolve_existing_patches(
    task: Mapping[str, Any],
    patch_ids: list[str],
    library: PromptPatchLibrary,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for patch_id in patch_ids:
        patch = library.get(patch_id)
        if patch["status"] not in {"candidate", "active"}:
            raise PromptPatchError(f"patch {patch_id!r} is not selectable")
        if not _patch_applicable(patch, task):
            raise PromptPatchError(f"patch {patch_id!r} is not applicable to this fixture")
        selected.append(patch)
    return selected


def _response_payload(response: WorkerResponse) -> dict[str, Any]:
    metadata = response.metadata()
    # Private request URLs are transport details, not public provenance. Keep
    # the stable camera-facing identity used by the overnight controller.
    metadata["request_url"] = None
    metadata["endpoint_alias"] = os.environ.get("ZTH_PUBLIC_HOST_ALIAS", PUBLIC_ENDPOINT_ALIAS)
    return {"status": response.status, "content": response.content, "metadata": metadata}


def _validator_result(raw_output: str, task: Mapping[str, Any], *, attempt_id: str) -> dict[str, Any]:
    """Adapt the fixture-selected validator into one stable deterministic result."""
    validator = task["validator"]
    if validator["kind"] == "exact_json":
        try:
            parsed = json.loads(raw_output)
            parse = "passed"
        except json.JSONDecodeError as exc:
            parsed = None
            parse = "failed"
            parse_error = f"JSON parse failed: {exc.msg}"
        diagnostics = [] if parse == "passed" else [parse_error]
        exact = parse == "passed" and parsed == task["expected_output"]
        if not exact:
            diagnostics.append("Output does not equal the deterministic fixture reference output.")
        checks = [{"check_id": "json_parse", "status": parse}, {"check_id": "reference_output_exact_match", "status": "passed" if exact else "failed"}]
        return {
            "validation_status": "passed" if exact else "failed",
            "validator": "deterministic_fixture_exact_match_v1",
            "checks": checks,
            "structural_checks": checks,
            "semantic_checks": [],
            "diagnostics": diagnostics,
            "reference_facts": {"expected_output": task["expected_output"]},
            "acceptance_status": "not_reviewed",
            "review_required": True,
        }

    triage_id = str(task.get("triage_id", f"triage-{task['task_id']}"))
    orchestration_id = str(task.get("orchestration_id", f"orchestration-{task['task_id']}"))
    prompt_packet_id = str(task.get("prompt_packet_id", f"prompt-{task['task_id']}"))
    attempt = build_supervised_model_attempt_record(
        attempt_id=attempt_id,
        orchestration_id=orchestration_id,
        triage_id=triage_id,
        prompt_packet_id=prompt_packet_id,
        raw_model_output=raw_output,
        model_metadata={"model_id": "bounded-worker"},
        operator_metadata={"operator": "capability-loop", "review_required": True},
        provenance={"source": "capability_loop", "raw_output_preserved": True},
    )
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=task["output_contract"],
        validation_id=f"validation-{attempt_id}",
        validated_at=utc_now(),
        authorized_targets=validator.get("authorized_targets"),
    )
    reference_result = validate_reference_facts(raw_output, validator.get("reference_facts", {}))
    structural_checks = list(record["checks"])
    semantic_checks = reference_result["checks"]
    record["structural_checks"] = structural_checks
    record["semantic_checks"] = semantic_checks
    record["checks"] = [*structural_checks, *semantic_checks]
    record["diagnostics"] = [*record.get("diagnostics", []), *reference_result["diagnostics"]]
    record["validation_status"] = "passed" if record["validation_status"] == "passed" and reference_result["validation_status"] == "passed" else "failed"
    record["reference_facts"] = validator.get("reference_facts", {})
    return record


def _resolve_deterministic_retry_patch(config: Mapping[str, Any]) -> tuple[str, str, str]:
    """Resolve an explicitly configured experimental patch, fail closed."""
    patch_id = config.get("patch_id")
    patch_path = config.get("patch_path")
    expected_hash = config.get("patch_sha256")
    if not all(isinstance(value, str) and value.strip() for value in (patch_id, patch_path, expected_hash)):
        raise ValueError("deterministic patch retry requires patch_id, patch_path, and patch_sha256")
    path = Path(patch_path)
    if not path.exists():
        raise ValueError(f"deterministic retry patch is unavailable: {patch_id}")
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"deterministic retry patch hash mismatch: {patch_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("candidate_patch_id", payload.get("patch_id")) != patch_id:
        raise ValueError(f"deterministic retry patch id mismatch: {patch_id}")
    prompt_delta = payload.get("prompt_delta")
    if not isinstance(prompt_delta, str) or not prompt_delta.strip():
        raise ValueError(f"deterministic retry patch has no prompt_delta: {patch_id}")
    return patch_id, actual_hash, prompt_delta


def _teacher_prompt(
    task: Mapping[str, Any],
    *,
    role: str,
    failed_transitions: list[dict[str, Any]],
    patch_records: list[dict[str, Any]],
) -> str:
    return json.dumps(
        {
            "role": role,
            "instruction": "Diagnose the bounded worker failure and propose a review-only intervention. Return JSON only; do not claim success or acceptance.",
            "task": {
                "task_id": task["task_id"],
                "task_family": task["task_family"],
                "prompt": task["prompt"],
                "output_contract": task["output_contract"],
                "validator_kind": task["validator"]["kind"],
                "bounded_reference_facts": task["validator"].get("reference_facts", {}),
            },
            "failed_transitions": failed_transitions,
            "existing_patch_evidence": patch_records,
            "allowed_fields": ["failure_classification", "teacher_diagnosis", "candidate_prompt_patch", "retry_guidance", "corrected_reference_output"],
            "authority": REQUIRED_AUTHORITY,
        },
        sort_keys=True,
    )


def _parse_teacher(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"teacher_parse_status": "failed", "teacher_diagnosis": f"Teacher output was not JSON: {exc.msg}"}
    if not isinstance(payload, dict):
        return {"teacher_parse_status": "failed", "teacher_diagnosis": "Teacher output was not a JSON object."}
    result = {"teacher_parse_status": "passed"}
    for key in ("failure_classification", "teacher_diagnosis", "retry_guidance", "corrected_reference_output"):
        if key in payload:
            result[key] = payload[key]
    if "candidate_prompt_patch" in payload:
        candidate = payload["candidate_prompt_patch"]
        try:
            from local_harness.prompt_patch_library import validate_patch
            result["candidate_prompt_patch"] = validate_patch(candidate)
            result["candidate_patch_status"] = "valid_candidate_not_promoted"
        except PromptPatchError as exc:
            result["candidate_patch_status"] = "invalid_candidate"
            result["candidate_patch_diagnostic"] = str(exc)
    return result


def _external_teacher(raw_prompt: str) -> tuple[str, str]:
    command = os.environ.get("ZTH_EXTERNAL_TEACHER_COMMAND")
    identity = os.environ.get("ZTH_EXTERNAL_TEACHER_IDENTITY", "codex-unconfigured")
    if not command:
        raise RuntimeError("external teacher unavailable: ZTH_EXTERNAL_TEACHER_COMMAND is not configured")
    argv = shlex.split(command)
    if not argv:
        raise RuntimeError("external teacher unavailable: configured command is empty")
    completed = subprocess.run(argv, input=raw_prompt, text=True, capture_output=True, timeout=900, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"external teacher command failed with exit code {completed.returncode}")
    return identity, completed.stdout


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        try:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        handle.write(line)
        handle.flush()


def _records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _transition(
    trajectory: Path,
    *,
    transition: str,
    task_id: str,
    attempt: int | None = None,
    source: str | None = None,
    **payload: Any,
) -> dict[str, Any]:
    record = {"record_type": "transition", "transition": transition, "task_id": task_id, "attempt": attempt, "intervention_source": source, "timestamp": utc_now(), **payload}
    _append_jsonl(trajectory, record)
    return record


def run_capability_loop(
    task: dict[str, Any],
    *,
    out_dir: Path,
    worker: Callable[[str], WorkerResponse] | None = None,
    local_teacher: Callable[[str], WorkerResponse] | None = None,
    external_teacher: Callable[[str], tuple[str, str]] | None = None,
    max_worker_attempts: int = 2,
    max_teacher_passes: int = 2,
    existing_patch_ids: list[str] | None = None,
    patch_library: PromptPatchLibrary | None = None,
    deterministic_patch_retry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if max_worker_attempts < 1 or max_teacher_passes < 0:
        raise ValueError("retry ceilings must be non-negative and worker attempts must be positive")
    task = dict(task)
    task.setdefault("validator", {"kind": "exact_json"})
    task_id = _required_string(task, "task_id")
    out_dir.mkdir(parents=True, exist_ok=True)
    trajectory = out_dir / "trajectory.jsonl"
    summary_path = out_dir / "trajectory_summary.json"
    prior = _records(trajectory)
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("task_id") == task_id and summary.get("disposition") in TERMINAL_DISPOSITIONS:
            return summary

    library = patch_library or PromptPatchLibrary()
    selected_patches = resolve_existing_patches(task, list(existing_patch_ids or []), library)
    patch_records = [{"patch_id": p["patch_id"], "patch_hash": sha256_text(json.dumps(p, sort_keys=True))} for p in selected_patches]
    deterministic_patch = _resolve_deterministic_retry_patch(deterministic_patch_retry) if deterministic_patch_retry else None
    unpatched_prompt = task["prompt"]
    patched_prompt = unpatched_prompt + ("\n\n" + render_prompt_deltas(selected_patches) if selected_patches else "")
    if worker is None:
        spec = resolve_worker_spec(os.environ.get("ZTH_CAPABILITY_WORKER_NAME", "router"), base_url=os.environ.get("ZTH_CAPABILITY_WORKER_BASE_URL"), model=os.environ.get("ZTH_CAPABILITY_WORKER_MODEL"))
        worker = lambda p, worker_spec=spec: call_worker(worker_spec, p, int(os.environ.get("ZTH_CAPABILITY_WORKER_MAX_TOKENS", "768")), timeout=int(os.environ.get("ZTH_CAPABILITY_WORKER_TIMEOUT", "900")))
    if local_teacher is None:
        spec = resolve_worker_spec(os.environ.get("ZTH_CAPABILITY_TEACHER_NAME", "deep"), base_url=os.environ.get("ZTH_CAPABILITY_TEACHER_BASE_URL"), model=os.environ.get("ZTH_CAPABILITY_TEACHER_MODEL"))
        local_teacher = lambda p, teacher_spec=spec: call_worker(teacher_spec, p, int(os.environ.get("ZTH_CAPABILITY_TEACHER_MAX_TOKENS", "1200")), timeout=int(os.environ.get("ZTH_CAPABILITY_TEACHER_TIMEOUT", "900")))
    external_teacher = external_teacher or _external_teacher
    patch_retry_attempted = False
    patch_retry_passed = False
    patch_retry_failed = False

    # Durable artifact scan turns an interruption between a write and a JSONL
    # append into a recoverable transition instead of a repeated model call.
    attempt_numbers = sorted(int(p.stem.split("-")[1]) for p in out_dir.glob("attempt-*.raw.json") if p.stem.split("-")[1].isdigit())
    attempt_count = max([0, *attempt_numbers])
    attempts: list[dict[str, Any]] = []
    teacher_records: list[dict[str, Any]] = []
    for n in range(1, attempt_count + 1):
        raw_path = out_dir / f"attempt-{n}.raw.json"
        validation_path = out_dir / f"attempt-{n}.validation.json"
        metadata_path = out_dir / f"attempt-{n}.metadata.json"
        if raw_path.exists():
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            validation = json.loads(validation_path.read_text(encoding="utf-8")) if validation_path.exists() else None
            metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {"attempt": n, "intervention_source": "none", "intervention_id": "none:1", "escalation_level": 0, "applied_patch_ids": [], "applied_patch_hashes": {}}
            attempts.append({"record_type": "worker_attempt", **metadata, "raw_output": raw["content"], "validation": validation, "artifact_refs": {"raw": raw_path.name, **({"validation": validation_path.name} if validation else {}), "metadata": metadata_path.name}, "artifact_hashes": {"raw": sha256_text(raw_path.read_text()), **({"validation": sha256_text(validation_path.read_text())} if validation else {}), "metadata": sha256_text(metadata_path.read_text()) if metadata_path.exists() else None}, "worker_model": raw.get("metadata", {}).get("model") or "unknown", "transport_valid": bool(metadata.get("transport_valid", validation is not None))})
    for teacher_path in sorted(out_dir.glob("local-teacher-*.json")):
        payload = json.loads(teacher_path.read_text(encoding="utf-8"))
        parsed = payload.get("parsed", {})
        pass_number = int(teacher_path.stem.split("-")[-1])
        teacher_records.append({"record_type": "local_teacher", "attempt": pass_number, "intervention_id": f"local_teacher:{pass_number}", "local_teacher_model": payload.get("raw", {}).get("metadata", {}).get("model"), "teacher_evidence": payload, "failure_classification": parsed.get("failure_classification"), "teacher_diagnosis": parsed.get("teacher_diagnosis"), "corrected_reference_output": parsed.get("corrected_reference_output"), "candidate_prompt_patch": parsed.get("candidate_prompt_patch"), "subsequent_worker_result": "not_run", "review_state": "ready_for_review"})
    def worker_attempt(prompt: str, source: str, escalation_level: int, intervention_id: str, *, patch_record: dict[str, str] | None = None) -> bool:
        n = len(attempts) + 1
        raw_path = out_dir / f"attempt-{n}.raw.json"
        validation_path = out_dir / f"attempt-{n}.validation.json"
        metadata_path = out_dir / f"attempt-{n}.metadata.json"
        prompt_path = out_dir / f"attempt-{n}.prompt.txt"
        if not prompt_path.exists():
            prompt_path.write_text(prompt, encoding="utf-8")
        if raw_path.exists():
            raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
        else:
            _transition(trajectory, transition="worker_call_started", task_id=task_id, attempt=n, source=source, intervention_id=intervention_id, prompt_artifact=prompt_path.name, prompt_sha256=sha256_text(prompt))
            response = worker(prompt)
            raw_payload = _response_payload(response)
            _json_write(raw_path, raw_payload)
            _transition(trajectory, transition="worker_output_captured", task_id=task_id, attempt=n, source=source, intervention_id=intervention_id, artifact_ref=raw_path.name, artifact_hash=sha256_text(raw_path.read_text()))
        transport_classification = raw_payload.get("metadata", {}).get("transport_classification") or classify_worker_response(raw_payload.get("status", ""), raw_payload.get("metadata", {}).get("error"))
        transport_valid = transport_classification == "model_response"
        validation = None
        if transport_valid:
            validation = json.loads(validation_path.read_text(encoding="utf-8")) if validation_path.exists() else _validator_result(raw_payload["content"], task, attempt_id=f"attempt-{n}")
        request_provenance = raw_payload.get("metadata", {}).get("request_provenance") or {
            "prompt_sha256": sha256_text(prompt),
            "message_structure": ["user"],
            "model": raw_payload.get("metadata", {}).get("model"),
            "configured_model": raw_payload.get("metadata", {}).get("configured_model"),
            "max_tokens": None,
            "temperature": None,
            "top_p": None,
            "seed": None,
            "stop": None,
            "settings_status": "unknown",
        }
        metadata = {"attempt": n, "intervention_source": source, "intervention_id": intervention_id, "escalation_level": escalation_level, "applied_patch_ids": [p["patch_id"] for p in selected_patches] if source == "existing_patch" else [], "applied_patch_hashes": {p["patch_id"]: p["patch_hash"] for p in patch_records} if source == "existing_patch" else {}, "deterministic_patch_id": patch_record["patch_id"] if patch_record else None, "deterministic_patch_hash": patch_record["patch_hash"] if patch_record else None, "transport_valid": transport_valid, "transport_classification": transport_classification, "validation_status": validation.get("validation_status") if validation else None, "endpoint_alias": raw_payload.get("metadata", {}).get("endpoint_alias", PUBLIC_ENDPOINT_ALIAS), "request_provenance": request_provenance, "prompt_artifact": prompt_path.name, "prompt_sha256": sha256_text(prompt)}
        if not metadata_path.exists():
            _json_write(metadata_path, metadata)
        if transport_valid and not validation_path.exists():
            _json_write(validation_path, validation)
            _transition(trajectory, transition="worker_output_validated", task_id=task_id, attempt=n, source=source, intervention_id=intervention_id, validation=validation, artifact_ref=validation_path.name, artifact_hash=sha256_text(validation_path.read_text()))
        record = {"record_type": "worker_attempt", **metadata, "raw_output": raw_payload["content"], "validation": validation, "transport_error": raw_payload.get("metadata", {}).get("error") if not transport_valid else None, "artifact_refs": {"raw": raw_path.name, "prompt": prompt_path.name, "metadata": metadata_path.name, **({"validation": validation_path.name} if transport_valid else {})}, "artifact_hashes": {"raw": sha256_text(raw_path.read_text()), "prompt": sha256_text(prompt_path.read_text()), "metadata": sha256_text(metadata_path.read_text()), **({"validation": sha256_text(validation_path.read_text())} if transport_valid else {})}, "worker_model": raw_payload.get("metadata", {}).get("model") or "unknown", "review_state": "ready_for_review" if validation and validation.get("validation_status") == "passed" else "infrastructure_error" if not transport_valid else "unresolved"}
        if not any(r.get("record_type") == "worker_attempt" and r.get("attempt") == n for r in _records(trajectory)):
            _append_jsonl(trajectory, record)
        attempts.append(record)
        return bool(validation and validation.get("validation_status") == "passed")

    external_path = out_dir / "external-teacher.json"
    baseline_pass = False
    if not attempts:
        baseline_pass = worker_attempt(unpatched_prompt, "none", 0, "none:1")
    else:
        baseline_pass = any(a.get("intervention_id", "").startswith("none:") and a.get("validation", {}).get("validation_status") == "passed" for a in attempts)
    baseline_count = sum(a.get("intervention_source") == "none" for a in attempts)
    if not baseline_pass and not selected_patches and baseline_count < max_worker_attempts:
        for retry_number in range(baseline_count + 1, max_worker_attempts + 1):
            if worker_attempt(unpatched_prompt, "none", 0, f"none:{retry_number}"):
                baseline_pass = True
                break
    model_failure = any(a.get("transport_valid") and a.get("validation", {}).get("validation_status") == "failed" for a in attempts)
    if not baseline_pass and model_failure and deterministic_patch:
        deterministic_patch_id, deterministic_patch_hash, deterministic_prompt_delta = deterministic_patch
        baseline_attempt = next(a for a in reversed(attempts) if a.get("intervention_source") == "none" and a.get("transport_valid") and a.get("validation", {}).get("validation_status") == "failed")
        retry_prompt = render_distilled_retry_prompt(task, baseline_attempt["validation"], deterministic_prompt_delta)
        patch_retry_attempted = True
        patch_retry_passed = worker_attempt(retry_prompt, "deterministic_patch_retry", 0, "deterministic_patch_retry:1", patch_record={"patch_id": deterministic_patch_id, "patch_hash": deterministic_patch_hash})
        patch_retry_failed = not patch_retry_passed
        model_failure = model_failure or any(a.get("transport_valid") and a.get("validation", {}).get("validation_status") == "failed" for a in attempts)
    existing_pass = False
    if model_failure and selected_patches:
        existing_pass = any(a.get("intervention_id") == "existing_patch:1" and a.get("validation", {}).get("validation_status") == "passed" for a in attempts)
    existing_attempt = any(a.get("intervention_id") == "existing_patch:1" for a in attempts)
    if model_failure and not baseline_pass and not existing_pass and selected_patches and not existing_attempt:
        existing_pass = worker_attempt(patched_prompt, "existing_patch", 0, "existing_patch:1")
    local_pass = any(a.get("intervention_id", "").startswith("local_teacher:") and a.get("validation", {}).get("validation_status") == "passed" for a in attempts)
    for teacher_pass in range(1, max_teacher_passes + 1):
        if baseline_pass or existing_pass or patch_retry_passed or local_pass or not model_failure:
            break
        intervention_id = f"local_teacher:{teacher_pass}"
        prior_retry = next((a for a in attempts if a.get("intervention_id") == intervention_id), None)
        if prior_retry is not None:
            if teacher_pass <= len(teacher_records):
                teacher_records[teacher_pass - 1]["subsequent_worker_result"] = "passed" if prior_retry.get("validation", {}).get("validation_status") == "passed" else "failed"
            continue
        failed = [a for a in attempts if a.get("transport_valid") and a.get("validation", {}).get("validation_status") != "passed"]
        teacher_path = out_dir / f"local-teacher-{teacher_pass}.json"
        if teacher_path.exists():
            teacher_payload = json.loads(teacher_path.read_text(encoding="utf-8"))
        else:
            _transition(trajectory, transition="local_teacher_started", task_id=task_id, attempt=teacher_pass, source="local_teacher")
            teacher_response = local_teacher(_teacher_prompt(task, role="local_teacher_reviewer", failed_transitions=failed + teacher_records, patch_records=patch_records))
            teacher_payload = {"raw": _response_payload(teacher_response), "parsed": _parse_teacher(teacher_response.content)}
            _json_write(teacher_path, teacher_payload)
            _transition(trajectory, transition="local_teacher_response_captured", task_id=task_id, attempt=teacher_pass, source="local_teacher", artifact_ref=teacher_path.name, artifact_hash=sha256_text(teacher_path.read_text()), evidence=teacher_payload)
        parsed = teacher_payload["parsed"]
        teacher_record = next((record for record in teacher_records if record.get("intervention_id") == intervention_id), None)
        if teacher_record is None:
            teacher_record = {"record_type": "local_teacher", "attempt": teacher_pass, "intervention_id": intervention_id, "local_teacher_model": teacher_payload.get("raw", {}).get("metadata", {}).get("model"), "teacher_evidence": teacher_payload, "failure_classification": parsed.get("failure_classification"), "teacher_diagnosis": parsed.get("teacher_diagnosis"), "corrected_reference_output": parsed.get("corrected_reference_output"), "candidate_prompt_patch": parsed.get("candidate_prompt_patch"), "subsequent_worker_result": "not_run", "review_state": "ready_for_review"}
            teacher_records.append(teacher_record)
        intervention = json.dumps(parsed, sort_keys=True)
        local_pass = worker_attempt(patched_prompt + "\n\n## Local teacher intervention\n" + intervention, "local_teacher", 1, intervention_id)
        teacher_record["subsequent_worker_result"] = "passed" if local_pass else "failed"
        _transition(trajectory, transition="local_teacher_retry_completed", task_id=task_id, attempt=teacher_pass, source="local_teacher", validation=attempts[-1]["validation"], worker_attempt=attempts[-1]["attempt"])
    external_pass = any(a.get("intervention_id") == "external_teacher:1" and a.get("validation", {}).get("validation_status") == "passed" for a in attempts)
    external_used = False
    external_record: dict[str, Any] | None = None
    external_teacher_call_count = sum(
        1 for record in _records(trajectory) if record.get("transition") == "external_teacher_started"
    )
    if model_failure and not baseline_pass and not existing_pass and not patch_retry_passed and not local_pass:
        external_used = True
        external_path = out_dir / "external-teacher.json"
        if external_path.exists():
            external_payload = json.loads(external_path.read_text(encoding="utf-8"))
        else:
            _transition(trajectory, transition="external_teacher_started", task_id=task_id, attempt=1, source="external_teacher")
            external_teacher_call_count += 1
            try:
                identity, raw = external_teacher(_teacher_prompt(task, role="external_teacher_reviewer", failed_transitions=[*attempts, *teacher_records], patch_records=patch_records))
                external_payload = {"identity": identity, "raw": raw, "parsed": _parse_teacher(raw)}
            except Exception as exc:
                _transition(trajectory, transition="external_teacher_unavailable", task_id=task_id, attempt=1, source="external_teacher", diagnostic=str(exc))
                external_payload = None
        if external_payload is not None:
            if not external_path.exists():
                _json_write(external_path, external_payload)
                _transition(trajectory, transition="external_teacher_response_captured", task_id=task_id, attempt=1, source="external_teacher", artifact_ref=external_path.name, artifact_hash=sha256_text(external_path.read_text()), evidence=external_payload)
            if not any(a.get("intervention_id") == "external_teacher:1" for a in attempts):
                external_pass = worker_attempt(patched_prompt + "\n\n## External teacher intervention\n" + json.dumps(external_payload["parsed"], sort_keys=True), "external_teacher", 2, "external_teacher:1")
            external_record = {"record_type": "external_teacher", "attempt": 1, "intervention_id": "external_teacher:1", "external_teacher": external_payload.get("identity"), "corrected_reference_output": external_payload["parsed"].get("corrected_reference_output"), "candidate_prompt_patch": external_payload["parsed"].get("candidate_prompt_patch"), "subsequent_worker_result": "passed" if external_pass else "failed", "review_state": "ready_for_review"}
            _transition(trajectory, transition="external_teacher_retry_completed", task_id=task_id, attempt=1, source="external_teacher", validation=attempts[-1]["validation"], worker_attempt=attempts[-1]["attempt"])

    final_pass = baseline_pass or existing_pass or patch_retry_passed or local_pass or external_pass
    source = "none" if baseline_pass else "existing_patch" if existing_pass else "deterministic_patch_retry" if patch_retry_passed else "local_teacher" if local_pass else "external_teacher" if external_pass else "none"
    intervention_attempts = {
        source_name: any(a.get("intervention_source") == source_name for a in attempts)
        for source_name in ("none", "existing_patch", "deterministic_patch_retry", "local_teacher", "external_teacher")
    }
    capability_verdict_available = any(a.get("transport_valid") for a in attempts)
    infrastructure_error_count = sum(not a.get("transport_valid") for a in attempts)
    intervention_outcome = "no-effect" if capability_verdict_available else "not-applicable"
    if source != "none":
        intervention_outcome = "helped" if final_pass else "no-effect"
    candidate_examples = []
    all_teachers = [*teacher_records, *([external_record] if external_record else [])]
    for teacher in all_teachers:
        if teacher.get("corrected_reference_output") is not None:
            candidate_examples.append({"source": teacher.get("record_type"), "intervention_id": teacher.get("intervention_id"), "teacher_attempt": teacher.get("attempt"), "corrected_reference_output": teacher["corrected_reference_output"], "subsequent_worker_result": teacher.get("subsequent_worker_result", "not_run"), "review_state": "ready_for_review"})
    candidate_patches = [t["candidate_prompt_patch"] for t in all_teachers if t.get("candidate_prompt_patch")]
    if not any(r.get("transition") in {"ready_for_review", "unresolved"} for r in _records(trajectory)):
        _transition(trajectory, transition="ready_for_review" if final_pass else "unresolved", task_id=task_id, source=source, disposition="ready_for_review" if final_pass else "unresolved", successful_intervention_source=source)
    summary = {
        "schema": "supervised_capability_trajectory_v2", "task_id": task_id, "task_family": task["task_family"], "endpoint_alias": os.environ.get("ZTH_PUBLIC_HOST_ALIAS", PUBLIC_ENDPOINT_ALIAS), "worker_model": attempts[0]["worker_model"] if attempts else None, "local_teacher_model": teacher_records[0].get("local_teacher_model") if teacher_records else None, "external_escalation_count": int(external_used), "external_teacher_call_count": external_teacher_call_count, "trials": 1, "capability_verdict_available": capability_verdict_available, "model_attempt_count": sum(bool(a.get("transport_valid")) for a in attempts), "infrastructure_error_count": infrastructure_error_count, "pass": final_pass, "first_attempt_pass": bool(attempts and (attempts[0].get("validation") or {}).get("validation_status") == "passed"), "pass_after_existing_patch": existing_pass, "patch_retry_attempted": patch_retry_attempted, "patch_retry_passed": patch_retry_passed, "patch_retry_failed": patch_retry_failed, "teacher_escalation_avoided": patch_retry_passed and not teacher_records and not external_record, "pass_after_local_teacher_intervention": local_pass, "pass_after_external_teacher_intervention": external_pass, "successful_intervention_source": source, "intervention_attempts": intervention_attempts, "intervention_outcome": intervention_outcome, "candidate_prompt_patches": candidate_patches, "candidate_curriculum_examples": candidate_examples, "unresolved": not final_pass if capability_verdict_available else False, "disposition": "ready_for_review" if final_pass else "unresolved", "attempt_count": len(attempts), "teacher_pass_count": len(teacher_records), "authority_boundaries": REQUIRED_AUTHORITY, "review_state": "ready_for_review" if final_pass else "unresolved", "trajectory_artifact": str(trajectory), "generated_at": utc_now()
    }
    _json_write(summary_path, summary)
    return summary


def aggregate_scorecard(trajectory_paths: list[Path]) -> dict[str, Any]:
    summaries = [json.loads((p.parent / "trajectory_summary.json").read_text(encoding="utf-8")) for p in trajectory_paths if (p.parent / "trajectory_summary.json").exists()]
    capability_summaries = [row for row in summaries if row.get("capability_verdict_available", True)]
    source_counts = {source: {"trials": 0, "passes": 0} for source in ("none", "existing_patch", "deterministic_patch_retry", "local_teacher", "external_teacher")}
    success_fields = {
        "passes_after_existing_patch": "pass_after_existing_patch",
        "passes_after_local_teacher_intervention": "pass_after_local_teacher_intervention",
        "passes_after_external_teacher_intervention": "pass_after_external_teacher_intervention",
    }
    global_counts = {"passes": 0, "first_attempt_passes": 0, **{field: 0 for field in success_fields}}
    groups: dict[str, dict[str, Any]] = {}
    for row in capability_summaries:
        observed = row.get("intervention_attempts", {row.get("successful_intervention_source", "none"): True})
        for source, attempted in observed.items():
            if attempted:
                source_counts.setdefault(source, {"trials": 0, "passes": 0})
                source_counts[source]["trials"] += 1
                source_counts[source]["passes"] += int(row.get("pass", False) and row.get("successful_intervention_source") == source)
        key = f"{row.get('worker_model')}::{row.get('task_family')}"
        group = groups.setdefault(key, {"trials": 0, "passes": 0, "first_attempt_passes": 0, "passes_after_existing_patch": 0, "deterministic_patch_retry_attempts": 0, "deterministic_patch_retry_passes": 0, "passes_after_local_teacher_intervention": 0, "passes_after_external_teacher_intervention": 0, "external_escalations": 0, "intervention_helped": 0, "intervention_hurt": 0, "intervention_no_effect": 0, "intervention_not_applicable": 0, "unresolved": 0})
        group["trials"] += 1
        group["passes"] += int(row.get("pass", False))
        group["first_attempt_passes"] += int(row.get("first_attempt_pass", False))
        global_counts["passes"] += int(row.get("pass", False))
        global_counts["first_attempt_passes"] += int(row.get("first_attempt_pass", False))
        for field, summary_field in success_fields.items():
            group[field] += int(row.get(summary_field, False))
            global_counts[field] += int(row.get(summary_field, False))
        group["deterministic_patch_retry_attempts"] += int(row.get("patch_retry_attempted", False))
        group["deterministic_patch_retry_passes"] += int(row.get("patch_retry_passed", False))
        group["external_escalations"] += int(row.get("external_escalation_count", 0) > 0)
        group[f"intervention_{row.get('intervention_outcome', 'no-effect').replace('-', '_')}"] += 1
        group["unresolved"] += int(row.get("unresolved", False))
    for group in groups.values():
        group["pass_rate"] = group["passes"] / group["trials"] if group["trials"] else 0.0
        group["first_attempt_pass_rate"] = group["first_attempt_passes"] / group["trials"] if group["trials"] else 0.0
    unresolved_count = sum(int(s.get("unresolved", False)) for s in capability_summaries)
    patch_attempts = sum(int(s.get("patch_retry_attempted", False)) for s in capability_summaries)
    patch_passes = sum(int(s.get("patch_retry_passed", False)) for s in capability_summaries)
    return {"schema": "supervised_capability_scorecard_v2", "trials": len(capability_summaries), "infrastructure_attempts_excluded": len(summaries) - len(capability_summaries), "pass_rate": global_counts["passes"] / len(capability_summaries) if capability_summaries else 0.0, **global_counts, "baseline_worker_passes": sum(int(s.get("first_attempt_pass", False)) for s in capability_summaries), "deterministic_patch_retry_attempts": patch_attempts, "deterministic_patch_retry_passes": patch_passes, "deterministic_patch_retry_rescue_rate": patch_passes / patch_attempts if patch_attempts else 0.0, "teacher_escalations_avoided": sum(int(s.get("teacher_escalation_avoided", False)) for s in capability_summaries), "groups": groups, "by_intervention_source": source_counts, "successful_intervention_source_counts": {source: counts["passes"] for source, counts in source_counts.items()}, "external_escalation_count": sum(int(s.get("external_escalation_count", 0)) for s in capability_summaries), "external_teacher_call_count": sum(int(s.get("external_teacher_call_count", 0)) for s in capability_summaries), "unresolved_count": unresolved_count, "intervention_helped": sum(int(s.get("intervention_outcome") == "helped") for s in capability_summaries), "intervention_hurt": sum(int(s.get("intervention_outcome") == "hurt") for s in capability_summaries), "intervention_no_effect": sum(int(s.get("intervention_outcome") == "no-effect") for s in capability_summaries), "intervention_not_applicable": sum(int(s.get("intervention_outcome") == "not-applicable") for s in summaries), "infrastructure_error_count": sum(int(s.get("infrastructure_error_count", 0)) for s in summaries), "candidate_prompt_patches": [p for s in capability_summaries for p in s.get("candidate_prompt_patches", [])], "candidate_curriculum_examples": [e for s in capability_summaries for e in s.get("candidate_curriculum_examples", [])]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--patch-dir", type=Path)
    parser.add_argument("--existing-patch-id", action="append", default=[])
    parser.add_argument("--max-worker-attempts", type=int, default=2)
    parser.add_argument("--max-teacher-passes", type=int, default=2)
    parser.add_argument("--deterministic-patch-path")
    parser.add_argument("--deterministic-patch-id")
    parser.add_argument("--deterministic-patch-sha256")
    args = parser.parse_args(argv)
    deterministic_patch_retry = None
    if any(value is not None for value in (args.deterministic_patch_path, args.deterministic_patch_id, args.deterministic_patch_sha256)):
        deterministic_patch_retry = {"patch_path": args.deterministic_patch_path, "patch_id": args.deterministic_patch_id, "patch_sha256": args.deterministic_patch_sha256}
    summary = run_capability_loop(load_task_fixture(args.fixture), out_dir=args.out_dir, max_worker_attempts=args.max_worker_attempts, max_teacher_passes=args.max_teacher_passes, existing_patch_ids=args.existing_patch_id, patch_library=load_patch_library(args.patch_dir), deterministic_patch_retry=deterministic_patch_retry)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["disposition"] == "ready_for_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
