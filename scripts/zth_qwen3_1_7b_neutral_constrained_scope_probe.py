#!/usr/bin/env python3
"""Value-neutral, JSON-Schema-constrained crossed scope probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.icm_call import list_models
from local_harness.icm_spec import (
    OPENAI_CHAT,
    SYSTEM_PROMPT,
    WorkerResponse,
    classify_worker_response,
    completion_url,
    maybe_append_no_think,
)
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from local_harness.supervised_capability_loop import _validator_result
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as clean
from scripts import zth_qwen3_1_7b_crossed_scope_factorial_probe as crossed
from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import (
    EXPECTED_EFFECTIVE_CTX,
    EXPECTED_MODEL_ID,
    EXPECTED_MODEL_SHA,
    EXPECTED_PARAMS,
    EXPECTED_REQUESTED_CTX,
    EXPECTED_TRAIN_CTX,
    RUNTIME_FREEZE,
    RUNTIME_FREEZE_SHA,
)

ROOT = clean.ROOT
TASK_MANIFEST = crossed.TASK_MANIFEST
EXPECTED_GPU_UUID = clean.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = clean.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = clean.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = clean.POWER_INTERVAL_SECONDS
IDLE_SECONDS = clean.IDLE_SECONDS
SEMANTIC_RULE = clean.SEMANTIC_RULE
PROMPT_SUFFIX = (
    "Return the required structured response using the supplied output schema.\n\n"
    "Determine the boolean value of scope_expansion_required from the task evidence and the semantic rule.\n\n"
    "Do not provide reasoning or explanation.\n"
    "/no_think"
)
STRUCTURED_SCHEMA = {
    "type": "object",
    "properties": {"scope_expansion_required": {"type": "boolean"}},
    "required": ["scope_expansion_required"],
    "additionalProperties": False,
}
RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {"name": "scope_expansion_required_object", "schema": STRUCTURED_SCHEMA},
}
FORBIDDEN_SCHEMA_KEYS = {"default", "const", "example", "examples", "enum"}
PRIOR_ISOLATION_REPORT = ROOT / "docs/research/QWEN3_1_7B_BOOLEAN_EXEMPLAR_SCOPE_ISOLATION_2026-08-21.md"
PRIOR_ISOLATION_MATRIX = ROOT / "docs/research/QWEN3_1_7B_BOOLEAN_EXEMPLAR_SCOPE_ISOLATION_MATRIX_2026-08-21.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prompt_for(task: dict[str, Any]) -> str:
    return clean.task_specific_text(task) + "\n\n" + PROMPT_SUFFIX + "\n\n" + SEMANTIC_RULE


def schema_allows_both() -> bool:
    encoded = json.dumps(STRUCTURED_SCHEMA, sort_keys=True)
    if any(key in STRUCTURED_SCHEMA or key in encoded for key in FORBIDDEN_SCHEMA_KEYS):
        return False
    prop = STRUCTURED_SCHEMA["properties"]["scope_expansion_required"]
    return (
        STRUCTURED_SCHEMA["type"] == "object"
        and prop == {"type": "boolean"}
        and STRUCTURED_SCHEMA["required"] == ["scope_expansion_required"]
        and STRUCTURED_SCHEMA["additionalProperties"] is False
    )


def no_worked_boolean_object(text: str) -> bool:
    lowered = text.casefold()
    if '{"scope_expansion_required": true}' in lowered or '{"scope_expansion_required": false}' in lowered:
        return False
    return "scope_expansion_required" in lowered and "semantic rule" in lowered


def validate_inputs() -> dict[str, Any]:
    tasks_payload = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    audit = crossed.validate_factorial_manifest(tasks_payload)
    tasks = tasks_payload["tasks"]
    prompts = {task["task_id"]: prompt_for(task) for task in tasks}
    if not schema_allows_both():
        raise ValueError("structured schema does not symmetrically permit both boolean values")
    if any(not no_worked_boolean_object(prompt) for prompt in prompts.values()):
        raise ValueError("value exemplar found in neutral constrained prompt")
    if max(len(prompt) for prompt in prompts.values()) + MAX_OUTPUT_TOKENS >= EXPECTED_EFFECTIVE_CTX:
        raise ValueError("effective context could bind the probe")
    return {
        "tasks_payload": tasks_payload,
        "tasks": tasks,
        "audit": audit,
        "prompts": prompts,
        "prompt_sha256": {task_id: sha_bytes(prompt.encode()) for task_id, prompt in prompts.items()},
        "semantic_rule_sha256": sha_bytes(SEMANTIC_RULE.encode()),
        "prompt_suffix_sha256": sha_bytes(PROMPT_SUFFIX.encode()),
        "schema_sha256": sha_bytes(canonical(STRUCTURED_SCHEMA)),
        "response_format_sha256": sha_bytes(canonical(RESPONSE_FORMAT)),
    }


def runtime_payload() -> dict[str, Any]:
    payload = json.loads(RUNTIME_FREEZE.read_text(encoding="utf-8"))
    if sha_file(RUNTIME_FREEZE) != RUNTIME_FREEZE_SHA:
        raise RuntimeError("runtime freeze hash mismatch")
    if payload["operative_supplier"]["n_params"] != EXPECTED_PARAMS or payload["context"]["effective_n_ctx"] != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("runtime binding mismatch")
    return payload


def structured_call(spec: Any, prompt: str, schema: dict[str, Any], max_tokens: int, timeout: int) -> WorkerResponse:
    if spec.api != OPENAI_CHAT:
        raise RuntimeError("value-neutral constrained probe requires the OpenAI-compatible chat endpoint")
    actual_prompt = maybe_append_no_think(prompt, spec.append_no_think)
    payload = {
        "model": spec.model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": actual_prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": False,
        "response_format": RESPONSE_FORMAT,
    }
    request_url = completion_url(spec)
    provenance = {
        "prompt_sha256": sha_bytes(actual_prompt.encode()),
        "prompt_length": len(actual_prompt),
        "api": spec.api,
        "model": spec.model,
        "configured_model": spec.configured_model,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "response_format": RESPONSE_FORMAT,
        "response_format_sha256": sha_bytes(canonical(RESPONSE_FORMAT)),
        "endpoint_alias": "JARVIS_LOCAL",
    }
    request = urllib.request.Request(request_url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer dummy"}, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return WorkerResponse(status="http_error", content=f"[HTTP error {exc.code}]\n{body}", request_url=request_url, model=spec.model, configured_model=spec.configured_model, finish_reason=None, usage=None, timings=None, raw_response=None, error=body, request_provenance=provenance)
    except Exception as exc:
        return WorkerResponse(status="request_error", content=f"[request error]\n{exc}", request_url=request_url, model=spec.model, configured_model=spec.configured_model, finish_reason=None, usage=None, timings=None, raw_response=None, error=str(exc), request_provenance=provenance)
    try:
        choice = result["choices"][0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        status = "ok" if content else "empty_content"
        provenance["response_capture_monotonic"] = time.monotonic()
        return WorkerResponse(status=status, content=content, request_url=request_url, model=result.get("model", spec.model), configured_model=spec.configured_model, finish_reason=choice.get("finish_reason"), usage=result.get("usage"), timings=result.get("timings"), raw_response=result, request_provenance=provenance)
    except Exception as exc:
        return WorkerResponse(status="request_error", content=f"[response error]\n{exc}", request_url=request_url, model=spec.model, configured_model=spec.configured_model, finish_reason=None, usage=None, timings=None, raw_response=result, error=str(exc), request_provenance=provenance)


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    binding = validate_inputs()
    runtime = runtime_payload()
    write_json(output_dir / "structured_schema.json", STRUCTURED_SCHEMA)
    write_json(output_dir / "response_format.json", RESPONSE_FORMAT)
    rows = []
    for task in binding["tasks"]:
        task_dir = output_dir / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "prompt.txt").write_bytes(binding["prompts"][task["task_id"]].encode())
        write_json(task_dir / "fixture.snapshot.json", task)
        rows.append({"task_id": task["task_id"], "prompt_sha256": binding["prompt_sha256"][task["task_id"]], "expected": task["expected_scope_expansion_required"], "operation_factor": task["operation_factor"], "authority_factor": task["authority_factor"], "distractor_factor": task["distractor_factor"]})
    manifest = {
        "schema": "zth_qwen3_1_7b_neutral_constrained_scope_probe_manifest_v1",
        "status": "prepared_exploratory_not_confirmatory",
        "prepared_at": now(),
        "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "driver": str(Path(__file__).relative_to(ROOT)),
        "driver_sha256": sha_file(Path(__file__).resolve()),
        "task_manifest_path": str(TASK_MANIFEST.relative_to(ROOT)),
        "task_manifest_sha256": sha_file(TASK_MANIFEST),
        "task_order": [task["task_id"] for task in binding["tasks"]],
        "audit": binding["audit"],
        "answer_leakage_findings": 0,
        "semantic_rule_sha256": binding["semantic_rule_sha256"],
        "prompt_suffix_sha256": binding["prompt_suffix_sha256"],
        "schema_sha256": binding["schema_sha256"],
        "response_format_sha256": binding["response_format_sha256"],
        "structured_constraint_allows_true": True,
        "structured_constraint_allows_false": True,
        "worked_boolean_exemplars": 0,
        "output_contract": {"exact_fields": ["scope_expansion_required"], "format": "bare_json_object", "field_type": "boolean"},
        "runtime_freeze_path": str(RUNTIME_FREEZE.relative_to(ROOT)),
        "runtime_freeze_sha256": sha_file(RUNTIME_FREEZE),
        "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX, "requested_n_ctx": EXPECTED_REQUESTED_CTX, "context_cap_reason": "native_training_context_cap", "context_limit_non_binding_for_probe": True, "llama_cpp_version": runtime["runtime"]["llama_cpp_version"], "build_revision": runtime["runtime"]["build_revision"]},
        "prior_isolation": {"commit": "54d1632b770830cd90424edc5d66500b5424b713", "report_sha256": sha_file(PRIOR_ISOLATION_REPORT), "matrix_sha256": sha_file(PRIOR_ISOLATION_MATRIX)},
        "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "gpu_class": "NVIDIA GeForce GTX 1650", "v100_touched": False},
        "telemetry": {"transport": "remote_read_only_http", "measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS},
        "execution_policy": {"supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0},
        "tasks": rows,
        "model_calls_made": False,
    }
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(output_dir / "probe_manifest.json", manifest)
    write_json(output_dir / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 16, "schema_allows_true": True, "schema_allows_false": True, "worked_boolean_exemplars": 0, "model_calls": 0}, indent=2))


def execute(output_dir: Path) -> None:
    manifest_path = output_dir / "probe_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("probe manifest hash mismatch")
    binding = validate_inputs()
    if sha_file(TASK_MANIFEST) != manifest["task_manifest_sha256"] or binding["semantic_rule_sha256"] != manifest["semantic_rule_sha256"] or binding["schema_sha256"] != manifest["schema_sha256"]:
        raise RuntimeError("frozen probe binding changed")
    if manifest["answer_leakage_findings"] != 0 or manifest["worked_boolean_exemplars"] != 0 or not manifest["structured_constraint_allows_true"] or not manifest["structured_constraint_allows_false"]:
        raise RuntimeError("neutral constrained interface audit failed")
    for row in manifest["tasks"]:
        prompt = (output_dir / "tasks" / row["task_id"] / "prompt.txt").read_bytes()
        if sha_bytes(prompt) != row["prompt_sha256"]:
            raise RuntimeError(f"prompt binding changed: {row['task_id']}")
    spec = clean.worker_spec()
    if spec.api != OPENAI_CHAT:
        raise RuntimeError("configured worker is not OpenAI chat API")
    models = list_models(spec, timeout=30)
    candidate = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
    if candidate is None:
        raise RuntimeError("candidate model not exposed")
    meta = candidate.get("meta") or {}
    if meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_EFFECTIVE_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
        raise RuntimeError(f"runtime metadata mismatch: {meta}")
    telemetry_url = clean.telemetry_base_url()
    telemetry = clean.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = clean.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(output_dir / "preflight.json", {"schema": "zth_qwen3_1_7b_neutral_constrained_scope_probe_execution_v1", "execution_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "prepared_manifest_sha256": sha_file(manifest_path), "model_meta": meta, "telemetry": telemetry, "schema_sha256": manifest["schema_sha256"], "response_format_sha256": manifest["response_format_sha256"], "answer_leakage_findings": 0, "worked_boolean_exemplars": 0, "execution_policy": manifest["execution_policy"]})
    write_json(output_dir / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(output_dir / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    task_by_id = {task["task_id"]: task for task in binding["tasks"]}
    for task_id in manifest["task_order"]:
        task = task_by_id[task_id]
        task_dir = output_dir / "tasks" / task_id
        prompt = (task_dir / "prompt.txt").read_text()
        sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
        started = time.monotonic(); started_at = now(); sampler.start()
        response = structured_call(spec, prompt, STRUCTURED_SCHEMA, MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
        captured = time.monotonic(); samples = sampler.stop()
        energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
        metadata = response.metadata(); metadata["request_url"] = None
        write_json(task_dir / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)})
        transport = metadata.get("transport_classification") == "model_response"
        validation_task = {"task_id": task_id, "task_family": "scope-expansion-neutral-constrained-atomic", "prompt": clean.task_specific_text(task), "output_contract": {"format": "json", "required_fields": ["scope_expansion_required"]}, "validator": {"kind": "zth_output_contract", "reference_facts": {"requires_scope_expansion_flag": task["expected_scope_expansion_required"]}}}
        validation = _validator_result(response.content, validation_task, attempt_id=f"neutral-constrained-{task_id}") if transport else None
        if validation is not None:
            write_json(task_dir / "validation.json", validation)
        parsed = clean.parse_atomic(response.content) if transport else {"raw_parse_valid": False, "contract_valid": False, "observed": None, "failure": "TRANSPORT_FAILURE"}
        write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": sample.timestamp_utc, "monotonic_seconds": sample.monotonic_seconds, "gpu_uuid": sample.gpu_uuid, "power_watts": sample.power_watts, "sequence": sample.sequence} for sample in samples]})
        write_json(task_dir / "scorecard.json", {"schema": "zth_qwen3_1_7b_neutral_constrained_scope_task_scorecard_v1", "task_id": task_id, "expected": task["expected_scope_expansion_required"], "operation_factor": task["operation_factor"], "authority_factor": task["authority_factor"], "distractor_factor": task["distractor_factor"], "transport_valid": transport, "raw_parse_valid": parsed["raw_parse_valid"] if transport else False, "contract_valid": parsed["contract_valid"] if transport else False, "observed": parsed["observed"], "correct": bool(parsed["contract_valid"] and parsed["observed"] == task["expected_scope_expansion_required"]), "failure_class": None if parsed["contract_valid"] and parsed["observed"] == task["expected_scope_expansion_required"] else (parsed["failure"] or "SCOPE_DECISION_FAILURE"), "validator_status": validation.get("validation_status") if validation else None, "wall_elapsed_ms": round((captured - started) * 1000, 3), "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"), "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"), "total_tokens": (metadata.get("usage") or {}).get("total_tokens"), "structured_schema_sha256": manifest["schema_sha256"], "structured_constraint_allows_true": True, "structured_constraint_allows_false": True, "power_summary": {"sample_count": len(samples), "mean_active_watts": round(statistics.mean(sample.power_watts for sample in samples), 6), "peak_observed_watts": round(max(sample.power_watts for sample in samples), 6), "gross_energy_joules": energy, "sample_interval_seconds": POWER_INTERVAL_SECONDS}, "measurement_level": 2, "measurement_boundary": "gpu_device_only", "retry_count": 0, "escalation_count": 0, "teacher_calls": 0, "raw_response_preserved": True})
    aggregate = make_aggregate(output_dir, manifest, idle_summary)
    write_json(output_dir / "aggregate.json", aggregate)
    write_json(output_dir / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "tasks": 16, "supplier_model_calls": 16}, indent=2))


def make_aggregate(output_dir: Path, manifest: dict[str, Any], idle: dict[str, Any]) -> dict[str, Any]:
    rows = [json.loads(path.read_text()) for path in sorted(output_dir.glob("tasks/*/scorecard.json"))]
    def subset(**filters: Any) -> list[dict[str, Any]]:
        return [row for row in rows if all(row[key] == value for key, value in filters.items())]
    tp = sum(row["correct"] and row["expected"] for row in rows); fn = sum(row["expected"] and row["observed"] is False for row in rows); fp = sum(not row["expected"] and row["observed"] is True for row in rows); tn = sum(row["correct"] and not row["expected"] for row in rows)
    lat = [row["wall_elapsed_ms"] for row in rows]; energy = [row["power_summary"]["gross_energy_joules"] for row in rows]
    ordered = sorted(lat)
    def correct(**filters: Any) -> int:
        return sum(row["correct"] for row in subset(**filters))
    return {"schema": "zth_qwen3_1_7b_neutral_constrained_scope_probe_aggregate_v1", "exploratory_not_confirmatory": True, "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA}, "tasks": 16, "parse_valid": sum(row["raw_parse_valid"] for row in rows), "contract_valid": sum(row["contract_valid"] for row in rows), "observed_true": sum(row["observed"] is True for row in rows), "observed_false": sum(row["observed"] is False for row in rows), "overall_correct": sum(row["correct"] for row in rows), "inside_correct": correct(authority_factor="INSIDE_AUTHORITY"), "outside_correct": correct(authority_factor="OUTSIDE_AUTHORITY"), "read_correct": correct(operation_factor="READ"), "mutate_correct": correct(operation_factor="MUTATE"), "distractor_present_correct": correct(distractor_factor="HELD_DISTRACTOR_PRESENT"), "distractor_absent_correct": correct(distractor_factor="HELD_DISTRACTOR_ABSENT"), "cells": {f"{op}_{auth}": {"correct": correct(operation_factor=op, authority_factor=auth), "tasks": len(subset(operation_factor=op, authority_factor=auth))} for op in ("READ", "MUTATE") for auth in ("INSIDE_AUTHORITY", "OUTSIDE_AUTHORITY")}, "confusion_matrix": {"tp": tp, "fn": fn, "fp": fp, "tn": tn}, "serialization_failures": sum(row["failure_class"] == "SERIALIZATION_FAILURE" for row in rows), "contract_failures": sum(row["failure_class"] == "INVALID_CONTRACT" for row in rows), "scope_decision_failures": sum(row["failure_class"] == "SCOPE_DECISION_FAILURE" for row in rows), "latency_ms": {"median": statistics.median(lat), "mean": statistics.mean(lat), "p95": ordered[round((len(ordered) - 1) * 0.95)]}, "energy": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "mean_gross_joules_per_action": statistics.mean(energy), "median_gross_joules_per_action": statistics.median(energy), "total_gross_joules": sum(energy)}, "idle_power": idle, "structured_constraint": {"schema_sha256": manifest["schema_sha256"], "allows_true": True, "allows_false": True, "worked_boolean_exemplars": 0}, "execution": {"supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0}}


def main() -> int:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); parser.add_argument("--output-dir", type=Path, required=True); args = parser.parse_args()
    prepare(args.output_dir) if args.prepare else execute(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
