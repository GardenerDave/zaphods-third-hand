#!/usr/bin/env python3
"""Paired semantic-versus-neutral field-name isolation for scope predicates."""

from __future__ import annotations

import argparse
import difflib
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
from local_harness.icm_spec import OPENAI_CHAT, SYSTEM_PROMPT, WorkerResponse, completion_url, maybe_append_no_think
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as clean
from scripts import zth_qwen3_1_7b_crossed_scope_factorial_probe as crossed
from scripts import zth_qwen3_1_7b_neutral_constrained_scope_probe as neutral
from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import EXPECTED_EFFECTIVE_CTX, EXPECTED_MODEL_ID, EXPECTED_MODEL_SHA, EXPECTED_PARAMS, EXPECTED_REQUESTED_CTX, EXPECTED_TRAIN_CTX, RUNTIME_FREEZE, RUNTIME_FREEZE_SHA
from scripts.zth_qwen3_1_7b_single_predicate_scope_probe import PREDICATE_TEXT

ROOT = clean.ROOT
TASK_MANIFEST = crossed.TASK_MANIFEST
EXPECTED_GPU_UUID = clean.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = clean.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = clean.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = clean.POWER_INTERVAL_SECONDS
IDLE_SECONDS = clean.IDLE_SECONDS
SEMANTIC_FIELD = "scope_expansion_required"
NEUTRAL_FIELD = "decision_flag"
ORDER_SEED = "zth-field-name-isolation-v1"
WRAPPER_NAME = "scope_field_name_isolation_object"


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


def field_prompt(task: dict[str, Any], field: str) -> str:
    suffix = neutral.PROMPT_SUFFIX.replace(SEMANTIC_FIELD, field)
    predicate = PREDICATE_TEXT.replace(SEMANTIC_FIELD, field)
    return clean.task_specific_text(task) + "\n\n" + suffix + "\n\n" + predicate


def schema_for(field: str) -> dict[str, Any]:
    return {"type": "object", "properties": {field: {"type": "boolean"}}, "required": [field], "additionalProperties": False}


def response_format_for(schema: dict[str, Any]) -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": WRAPPER_NAME, "schema": schema}}


def arm_order(task_id: str) -> list[str]:
    return ["S", "N"] if int(hashlib.sha256((ORDER_SEED + task_id).encode()).hexdigest()[-1], 16) % 2 == 0 else ["N", "S"]


def validate_inputs() -> dict[str, Any]:
    payload = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    audit = crossed.validate_factorial_manifest(payload)
    tasks = payload["tasks"]
    prompts = {arm: {t["task_id"]: field_prompt(t, field) for t in tasks} for arm, field in (("S", SEMANTIC_FIELD), ("N", NEUTRAL_FIELD))}
    schemas = {"S": schema_for(SEMANTIC_FIELD), "N": schema_for(NEUTRAL_FIELD)}
    formats = {arm: response_format_for(schema) for arm, schema in schemas.items()}
    for task in tasks:
        s = prompts["S"][task["task_id"]]
        n = prompts["N"][task["task_id"]]
        if n.replace(NEUTRAL_FIELD, SEMANTIC_FIELD) != s:
            raise ValueError(f"prompt rename drift: {task['task_id']}")
    if formats["S"]["json_schema"]["name"] != formats["N"]["json_schema"]["name"]:
        raise ValueError("response wrapper name is not common")
    for schema in schemas.values():
        if set(schema) != {"type", "properties", "required", "additionalProperties"} or schema["type"] != "object" or schema["properties"] not in ({SEMANTIC_FIELD: {"type": "boolean"}}, {NEUTRAL_FIELD: {"type": "boolean"}}) or schema["additionalProperties"] is not False:
            raise ValueError("schema structure mismatch")
        encoded = json.dumps(schema, sort_keys=True)
        if any(token in encoded for token in ('"default"', '"const"', '"example"', '"examples"', '"enum"')):
            raise ValueError("value cue in schema")
    combined = "\n".join(prompts[arm][tid] for arm in prompts for tid in prompts[arm]).casefold()
    if '"scope_expansion_required": true' in combined or '"scope_expansion_required": false' in combined or '"decision_flag": true' in combined or '"decision_flag": false' in combined:
        raise ValueError("worked boolean exemplar")
    if max(len(p) for arm in prompts.values() for p in arm.values()) + MAX_OUTPUT_TOKENS >= EXPECTED_EFFECTIVE_CTX:
        raise ValueError("context could bind probe")
    orders = {t["task_id"]: arm_order(t["task_id"]) for t in tasks}
    if sum(v == ["S", "N"] for v in orders.values()) != 8:
        raise ValueError("temporal order imbalance")
    normalized_diff = {"prompt_diffs": [], "schema_diff": list(difflib.unified_diff(json.dumps(schemas["S"], indent=2, sort_keys=True).splitlines(True), json.dumps(schemas["N"], indent=2, sort_keys=True).splitlines(True), fromfile="S", tofile="N")), "wrapper_diff": list(difflib.unified_diff(json.dumps(formats["S"], indent=2, sort_keys=True).splitlines(True), json.dumps(formats["N"], indent=2, sort_keys=True).splitlines(True), fromfile="S", tofile="N"))}
    for task in tasks:
        normalized_diff["prompt_diffs"].append({"task_id": task["task_id"], "diff": list(difflib.unified_diff(prompts["S"][task["task_id"]].splitlines(True), prompts["N"][task["task_id"]].splitlines(True), fromfile="S", tofile="N"))})
    normalized = json.loads(json.dumps(normalized_diff).replace(NEUTRAL_FIELD, SEMANTIC_FIELD))
    # Replacing the neutral label in N makes all prompt and schema content equal.
    if any(p["diff"] and prompts["N"][p["task_id"]].replace(NEUTRAL_FIELD, SEMANTIC_FIELD) != prompts["S"][p["task_id"]] for p in normalized_diff["prompt_diffs"]):
        raise ValueError("substantive prompt difference")
    return {"payload": payload, "audit": audit, "tasks": tasks, "prompts": prompts, "schemas": schemas, "formats": formats, "orders": orders, "task_manifest_sha256": sha_file(TASK_MANIFEST), "predicate_sha256": sha_bytes(PREDICATE_TEXT.encode()), "prompt_suffix_sha256": sha_bytes(neutral.PROMPT_SUFFIX.encode()), "schema_sha256": {a: sha_bytes(canonical(schemas[a])) for a in ("S", "N")}, "response_format_sha256": {a: sha_bytes(canonical(formats[a])) for a in ("S", "N")}, "normalized_rename_diff": normalized_diff, "normalized_rename_diff_sha256": sha_bytes(canonical(normalized_diff)), "field_rename_only": True}


def runtime_payload() -> dict[str, Any]:
    payload = json.loads(RUNTIME_FREEZE.read_text(encoding="utf-8"))
    if sha_file(RUNTIME_FREEZE) != RUNTIME_FREEZE_SHA or payload["operative_supplier"]["n_params"] != EXPECTED_PARAMS or payload["context"]["effective_n_ctx"] != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("runtime binding mismatch")
    return payload


def structured_call(spec: Any, prompt: str, response_format: dict[str, Any], max_tokens: int, timeout: int) -> WorkerResponse:
    if spec.api != OPENAI_CHAT:
        raise RuntimeError("field isolation requires OpenAI-compatible chat")
    actual_prompt = maybe_append_no_think(prompt, spec.append_no_think)
    payload = {"model": spec.model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": actual_prompt}], "max_tokens": max_tokens, "temperature": 0.2, "stream": False, "response_format": response_format}
    request_url = completion_url(spec)
    provenance = {"prompt_sha256": sha_bytes(actual_prompt.encode()), "prompt_length": len(actual_prompt), "api": spec.api, "model": spec.model, "configured_model": spec.configured_model, "max_tokens": max_tokens, "temperature": 0.2, "response_format_sha256": sha_bytes(canonical(response_format)), "endpoint_alias": "JARVIS_LOCAL"}
    request = urllib.request.Request(request_url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer dummy"}, method="POST")
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
        return WorkerResponse(status="ok" if content else "empty_content", content=content, request_url=request_url, model=result.get("model", spec.model), configured_model=spec.configured_model, finish_reason=choice.get("finish_reason"), usage=result.get("usage"), timings=result.get("timings"), raw_response=result, request_provenance=provenance)
    except Exception as exc:
        return WorkerResponse(status="request_error", content=f"[response error]\n{exc}", request_url=request_url, model=spec.model, configured_model=spec.configured_model, finish_reason=None, usage=None, timings=None, raw_response=result, error=str(exc), request_provenance=provenance)


def validate_raw(raw: str, field: str, expected: bool) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        parse_valid = True
        parse_error = None
    except json.JSONDecodeError as exc:
        parsed = None
        parse_valid = False
        parse_error = str(exc)
    contract_valid = isinstance(parsed, dict) and set(parsed) == {field} and isinstance(parsed.get(field), bool)
    observed = parsed.get(field) if contract_valid else None
    semantic_valid = bool(contract_valid and observed == expected)
    return {"validation_status": "passed" if semantic_valid else "failed", "parse_valid": parse_valid, "contract_valid": contract_valid, "observed": observed, "expected": expected, "field": field, "checks": [{"check": "json_parse", "status": "passed" if parse_valid else "failed"}, {"check": "field_contract", "status": "passed" if contract_valid else "failed"}, {"check": "reference_boolean", "status": "passed" if semantic_valid else "failed"}], "diagnostics": ([parse_error] if parse_error else []) + ([] if semantic_valid else ["deterministic expected boolean mismatch"])}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = validate_inputs()
    runtime = runtime_payload()
    for arm in ("S", "N"):
        write_json(out / f"schema_{arm}.json", binding["schemas"][arm])
        write_json(out / f"response_format_{arm}.json", binding["formats"][arm])
    rows = []
    for task in binding["tasks"]:
        d = out / "tasks" / task["task_id"]
        d.mkdir(parents=True, exist_ok=True)
        write_json(d / "fixture.snapshot.json", task)
        row = {"task_id": task["task_id"], "expected": task["expected_scope_expansion_required"], "arm_order": binding["orders"][task["task_id"]], "prompt_sha256": {}}
        for arm in ("S", "N"):
            (d / arm).mkdir()
            (d / arm / "prompt.txt").write_text(binding["prompts"][arm][task["task_id"]], encoding="utf-8")
            row["prompt_sha256"][arm] = sha_file(d / arm / "prompt.txt")
        rows.append(row)
    manifest = {"schema": "zth_qwen3_1_7b_scope_field_name_isolation_manifest_v1", "status": "prepared_exploratory_not_confirmatory", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_sha256": binding["task_manifest_sha256"], "task_count": 16, "expected_true": 8, "expected_false": 8, "task_order": [t["task_id"] for t in binding["tasks"]], "predicate_sha256": binding["predicate_sha256"], "prompt_suffix_sha256": binding["prompt_suffix_sha256"], "schema_sha256": binding["schema_sha256"], "response_format_sha256": binding["response_format_sha256"], "normalized_rename_diff_sha256": binding["normalized_rename_diff_sha256"], "field_rename_only": True, "worked_boolean_exemplars": 0, "structured_constraint_allows_true": True, "structured_constraint_allows_false": True, "temporal_order_balance": {"S_then_N": 8, "N_then_S": 8}, "context_limit_non_binding": True, "runtime_freeze_sha256": sha_file(RUNTIME_FREEZE), "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX, "requested_n_ctx": EXPECTED_REQUESTED_CTX, "llama_cpp_version": runtime["runtime"]["llama_cpp_version"], "build_revision": runtime["runtime"]["build_revision"]}, "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS}, "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False}, "execution_policy": {"supplier_model_calls": 32, "teacher_calls": 0, "retries": 0, "escalations": 0}, "tasks": rows, "model_calls_made": False}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "probe_manifest.json", manifest)
    write_json(out / "rename_audit.json", {"semantic_field": SEMANTIC_FIELD, "neutral_field": NEUTRAL_FIELD, "field_rename_only": True, "normalized_diff_sha256": binding["normalized_rename_diff_sha256"], "normalized_diff": binding["normalized_rename_diff"]})
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 16, "arms": 2, "calls": 32, "field_rename_only": True, "model_calls": 0}, indent=2))


def execute(out: Path) -> None:
    manifest = json.loads((out / "probe_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("manifest hash mismatch")
    binding = validate_inputs()
    for key in ("task_manifest_sha256", "predicate_sha256", "normalized_rename_diff_sha256"):
        if manifest[key] != binding[key]:
            raise RuntimeError(f"binding changed: {key}")
    for row in manifest["tasks"]:
        for arm in ("S", "N"):
            if sha_file(out / "tasks" / row["task_id"] / arm / "prompt.txt") != row["prompt_sha256"][arm]:
                raise RuntimeError("prompt drift")
    spec = clean.worker_spec()
    models = list_models(spec, timeout=30)
    candidate = next((x for x in models.get("data", []) if x.get("id") == EXPECTED_MODEL_ID), None)
    if candidate is None or (candidate.get("meta") or {}).get("n_params") != EXPECTED_PARAMS or (candidate.get("meta") or {}).get("n_ctx") != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("runtime endpoint mismatch")
    telemetry_url = clean.telemetry_base_url()
    telemetry = clean.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = clean.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(out / "preflight.json", {"schema": "zth_qwen3_1_7b_scope_field_name_isolation_execution_v1", "prepared_manifest_sha256": sha_file(out / "probe_manifest.json"), "model_meta": candidate.get("meta"), "telemetry": telemetry, "task_manifest_sha256": manifest["task_manifest_sha256"], "predicate_sha256": manifest["predicate_sha256"], "schema_sha256": manifest["schema_sha256"], "normalized_rename_diff_sha256": manifest["normalized_rename_diff_sha256"], "execution_policy": manifest["execution_policy"]})
    write_json(out / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(out / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    task_by_id = {t["task_id"]: t for t in binding["tasks"]}
    for task_id in manifest["task_order"]:
        task = task_by_id[task_id]
        for arm in next(row["arm_order"] for row in manifest["tasks"] if row["task_id"] == task_id):
            field = SEMANTIC_FIELD if arm == "S" else NEUTRAL_FIELD
            d = out / "tasks" / task_id / arm
            prompt = (d / "prompt.txt").read_text(encoding="utf-8")
            sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
            started = time.monotonic()
            started_at = now()
            sampler.start()
            response = structured_call(spec, prompt, binding["formats"][arm], MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
            captured = time.monotonic()
            samples = sampler.stop()
            energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
            metadata = response.metadata()
            metadata["request_url"] = None
            raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
            write_json(d / "response.json", raw)
            transport = metadata.get("transport_classification") == "model_response"
            validation = validate_raw(response.content, field, task["expected_scope_expansion_required"]) if transport else {"validation_status": "failed", "parse_valid": False, "contract_valid": False, "observed": None, "expected": task["expected_scope_expansion_required"], "field": field, "diagnostics": ["transport failure"]}
            write_json(d / "validation.json", validation)
            observed = validation["observed"]
            write_json(d / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "monotonic_seconds": s.monotonic_seconds, "gpu_uuid": s.gpu_uuid, "power_watts": s.power_watts, "sequence": s.sequence} for s in samples]})
            write_json(d / "scorecard.json", {"schema": "zth_qwen3_1_7b_scope_field_name_task_scorecard_v1", "task_id": task_id, "arm": arm, "field": field, "expected": task["expected_scope_expansion_required"], "operation_factor": task["operation_factor"], "authority_factor": task["authority_factor"], "distractor_factor": task["distractor_factor"], "transport_valid": transport, "raw_parse_valid": validation["parse_valid"] if transport else False, "contract_valid": validation["contract_valid"] if transport else False, "observed": observed, "correct": bool(transport and validation["contract_valid"] and observed == task["expected_scope_expansion_required"]), "failure_class": None if transport and validation["contract_valid"] and observed == task["expected_scope_expansion_required"] else (("SERIALIZATION_FAILURE" if transport and not validation["parse_valid"] else "INVALID_CONTRACT") if not validation["contract_valid"] else "SCOPE_DECISION_FAILURE"), "validator_status": validation["validation_status"], "wall_elapsed_ms": raw["wall_elapsed_ms"], "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"), "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"), "power_summary": {"sample_count": len(samples), "mean_active_watts": statistics.mean(s.power_watts for s in samples), "peak_observed_watts": max(s.power_watts for s in samples), "gross_energy_joules": energy}, "retry_count": 0, "escalation_count": 0, "teacher_calls": 0})
    write_json(out / "aggregate.json", aggregate(out, manifest, idle_summary))
    write_json(out / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 32, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "calls": 32}, indent=2))


def aggregate(out: Path, manifest: dict[str, Any], idle: dict[str, Any]) -> dict[str, Any]:
    rows = [json.loads(p.read_text()) for p in sorted(out.glob("tasks/*/*/scorecard.json"))]
    by = {arm: [r for r in rows if r["arm"] == arm] for arm in ("S", "N")}
    def sub(rs: list[dict[str, Any]], **filters: str) -> list[dict[str, Any]]:
        return [r for r in rs if all(r[k] == v for k, v in filters.items())]
    def summary(rs: list[dict[str, Any]]) -> dict[str, Any]:
        lat = [r["wall_elapsed_ms"] for r in rs]
        energy = [r["power_summary"]["gross_energy_joules"] for r in rs]
        ordered = sorted(lat)
        return {"true_selected": sum(r["observed"] is True for r in rs), "false_selected": sum(r["observed"] is False for r in rs), "correct": sum(r["correct"] for r in rs), "inside_correct": sum(r["correct"] for r in sub(rs, authority_factor="INSIDE_AUTHORITY")), "outside_correct": sum(r["correct"] for r in sub(rs, authority_factor="OUTSIDE_AUTHORITY")), "read_correct": sum(r["correct"] for r in sub(rs, operation_factor="READ")), "mutate_correct": sum(r["correct"] for r in sub(rs, operation_factor="MUTATE")), "distractor_present_correct": sum(r["correct"] for r in sub(rs, distractor_factor="HELD_DISTRACTOR_PRESENT")), "distractor_absent_correct": sum(r["correct"] for r in sub(rs, distractor_factor="HELD_DISTRACTOR_ABSENT")), "cells": {f"{op}_{auth}": {"correct": sum(r["correct"] for r in sub(rs, operation_factor=op, authority_factor=auth)), "total": len(sub(rs, operation_factor=op, authority_factor=auth))} for op in ("READ", "MUTATE") for auth in ("INSIDE_AUTHORITY", "OUTSIDE_AUTHORITY")}, "parse_valid": sum(r["raw_parse_valid"] for r in rs), "contract_valid": sum(r["contract_valid"] for r in rs), "confusion_matrix": {"TP": sum(r["expected"] and r["observed"] is True for r in rs), "FN": sum(r["expected"] and r["observed"] is False for r in rs), "FP": sum(not r["expected"] and r["observed"] is True for r in rs), "TN": sum(not r["expected"] and r["observed"] is False for r in rs)}, "serialization_failures": sum(r["failure_class"] == "SERIALIZATION_FAILURE" for r in rs), "contract_failures": sum(r["failure_class"] == "INVALID_CONTRACT" for r in rs), "scope_decision_failures": sum(r["failure_class"] == "SCOPE_DECISION_FAILURE" for r in rs), "latency_ms": {"median": statistics.median(lat), "mean": statistics.mean(lat), "p95": ordered[round((len(ordered) - 1) * 0.95)]}, "energy_joules": {"mean_per_action": statistics.mean(energy), "median_per_action": statistics.median(energy), "total": sum(energy)}}
    paired = {}
    for task_id in manifest["task_order"]:
        s = next(r for r in by["S"] if r["task_id"] == task_id)
        n = next(r for r in by["N"] if r["task_id"] == task_id)
        if s["correct"] and n["correct"]: label = "SAME_CORRECT"
        elif not s["correct"] and not n["correct"]: label = "SAME_INCORRECT"
        elif not s["correct"] and n["correct"]: label = "SEMANTIC_INCORRECT_NEUTRAL_CORRECT"
        elif s["correct"] and not n["correct"]: label = "SEMANTIC_CORRECT_NEUTRAL_INCORRECT"
        else: label = "OTHER"
        if s["observed"] != n["observed"] and s["correct"] == n["correct"]: label = "OUTPUT_FLIP_NO_ACCURACY_CHANGE"
        paired[task_id] = {"expected": s["expected"], "semantic_field_observed": s["observed"], "neutral_field_observed": n["observed"], "semantic_correct": s["correct"], "neutral_correct": n["correct"], "classification": label}
    return {"schema": "zth_qwen3_1_7b_scope_field_name_isolation_aggregate_v1", "exploratory_not_confirmatory": True, "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA}, "arms": {"S": summary(by["S"]), "N": summary(by["N"])}, "paired": paired, "s_to_n_output_flips": sum(v["semantic_field_observed"] != v["neutral_field_observed"] for v in paired.values()), "execution": {"supplier_model_calls": 32, "teacher_calls": 0, "retries": 0, "escalations": 0}, "idle_power": idle}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output_dir) if args.prepare else execute(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
