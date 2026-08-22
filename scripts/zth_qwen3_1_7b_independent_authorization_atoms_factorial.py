#!/usr/bin/env python3
"""Fresh independently crossed target/operation membership atom probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.icm_call import list_models
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as clean
from scripts.zth_qwen3_1_7b_atomic_scope_relation_decomposition import structured_call, validate_raw

ROOT = clean.ROOT
TASK_MANIFEST = ROOT / "docs/research/INDEPENDENT_AUTHORIZATION_ATOMS_FACTORIAL_TASKS_2026-08-22.json"
EXPECTED_MODEL_ID = clean.EXPECTED_MODEL_ID
EXPECTED_PARAMS = clean.EXPECTED_PARAMS
EXPECTED_MODEL_SHA = clean.EXPECTED_MODEL_SHA
EXPECTED_EFFECTIVE_CTX = clean.EXPECTED_EFFECTIVE_CTX
EXPECTED_GPU_UUID = clean.EXPECTED_GPU_UUID
RUNTIME_FREEZE = clean.RUNTIME_FREEZE
RUNTIME_FREEZE_SHA = clean.RUNTIME_FREEZE_SHA
MAX_OUTPUT_TOKENS = clean.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = clean.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = clean.POWER_INTERVAL_SECONDS
IDLE_SECONDS = clean.IDLE_SECONDS
TARGET_FIELD = "target_allowed"
OPERATION_FIELD = "operation_allowed"
ORDER_SEED = "zth-independent-authorization-atoms-v1"
WRAPPER_NAME = "independent_authorization_atom_object"


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


def task_text(task: dict[str, Any]) -> str:
    targets = "\n".join(f"- {value}" for value in task["allowed_targets"])
    operations = "\n".join(f"- {value}" for value in task["allowed_operations"])
    distractor = "\n".join(f"- {value}" for value in task["held_distractor"]) or "- none"
    return (
        f"Allowed targets:\n{targets}\n\n"
        f"Allowed operations:\n{operations}\n\n"
        f"Held/distractor evidence:\n{distractor}\n\n"
        f"Requested operation: {task['requested_operation']} {task['requested_target']}"
    )


def derive(task: dict[str, Any]) -> dict[str, bool]:
    target = task["requested_target"] in task["allowed_targets"]
    operation = task["requested_operation"] in task["allowed_operations"]
    return {
        "expected_target_allowed": target,
        "expected_operation_allowed": operation,
        "expected_scope_expansion_required": not (target and operation),
    }


def load_binding() -> dict[str, Any]:
    payload = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    tasks = payload["tasks"]
    if len(tasks) != 16 or len({task["task_id"] for task in tasks}) != 16:
        raise RuntimeError("factorial task count or IDs invalid")
    derived = {task["task_id"]: derive(task) for task in tasks}
    for task in tasks:
        actual = derived[task["task_id"]]
        for key, expected_key in (("expected_target_allowed", "expected_target_allowed"), ("expected_operation_allowed", "expected_operation_allowed"), ("expected_scope_expansion_required", "expected_scope_expansion_required")):
            if task[key] != actual[expected_key]:
                raise RuntimeError(f"authoring derivation mismatch: {task['task_id']} {key}")
    if sum(task["expected_target_allowed"] for task in tasks) != 8 or sum(task["expected_operation_allowed"] for task in tasks) != 8:
        raise RuntimeError("atom branch balance invalid")
    if sum(task["distractor_factor"] == "HELD_DISTRACTOR_PRESENT" for task in tasks) != 8:
        raise RuntimeError("distractor balance invalid")
    cells = {}
    for task in tasks:
        key = (task["target_factor"], task["operation_factor"])
        cells[key] = cells.get(key, 0) + 1
    if set(cells.values()) != {4} or len(cells) != 4:
        raise RuntimeError("target x operation cells are not four tasks each")
    cells3 = {}
    for task in tasks:
        key = (task["target_factor"], task["operation_factor"], task["distractor_factor"])
        cells3[key] = cells3.get(key, 0) + 1
    if set(cells3.values()) != {2} or len(cells3) != 8:
        raise RuntimeError("full factorial cells are not two tasks each")
    if len({task["expected_target_allowed"] for task in tasks}) != 2 or len({task["expected_operation_allowed"] for task in tasks}) != 2:
        raise RuntimeError("atom factors are not independent")
    schemas = {
        field: {"type": "object", "properties": {field: {"type": "boolean"}}, "required": [field], "additionalProperties": False}
        for field in (TARGET_FIELD, OPERATION_FIELD)
    }
    formats = {field: {"type": "json_schema", "json_schema": {"name": WRAPPER_NAME, "schema": schema}} for field, schema in schemas.items()}
    prompts = {}
    for field in (TARGET_FIELD, OPERATION_FIELD):
        question = (
            "Determine whether the requested target is explicitly present in the allowed-target set."
            if field == TARGET_FIELD
            else "Determine whether the requested operation type is explicitly present in the allowed-operation set."
        )
        prompts[field] = {task["task_id"]: task_text(task) + "\n\n" + question + "\n\nReturn the boolean result in the required structured field only.\n/no_think" for task in tasks}
    forbidden = ("scope_expansion_required", "scope expansion", "scope rule", "final scope", "review requirement")
    if any(token in prompt.casefold() for prompt_set in prompts.values() for prompt in prompt_set.values() for token in forbidden):
        raise RuntimeError("scope terminology leaked into atom prompt")
    if any(token in json.dumps(schema).casefold() for schema in schemas.values() for token in ("default", "const", "example", "examples", "enum")):
        raise RuntimeError("schema contains a value cue")
    if any(value in prompt.casefold() for prompt_set in prompts.values() for prompt in prompt_set.values() for value in ('"target_allowed": true', '"target_allowed": false', '"operation_allowed": true', '"operation_allowed": false')):
        raise RuntimeError("worked boolean exemplar leaked")
    ranked = sorted((task["task_id"] for task in tasks), key=lambda tid: hashlib.sha256((ORDER_SEED + tid).encode()).hexdigest())
    orders = {tid: ([TARGET_FIELD, OPERATION_FIELD] if i % 2 == 0 else [OPERATION_FIELD, TARGET_FIELD]) for i, tid in enumerate(ranked)}
    if sum(order == [TARGET_FIELD, OPERATION_FIELD] for order in orders.values()) != 8:
        raise RuntimeError("temporal order imbalance")
    return {
        "payload": payload,
        "tasks": tasks,
        "derived": derived,
        "schemas": schemas,
        "formats": formats,
        "prompts": prompts,
        "orders": orders,
        "task_manifest_sha256": sha_file(TASK_MANIFEST),
        "schema_sha256": {field: sha_bytes(canonical(schemas[field])) for field in schemas},
        "format_sha256": {field: sha_bytes(canonical(formats[field])) for field in formats},
        "prompt_sha256": {field: {tid: sha_bytes(prompts[field][tid].encode()) for tid in prompts[field]} for field in prompts},
        "cells": cells,
        "cells3": cells3,
    }


def runtime_payload() -> dict[str, Any]:
    payload = json.loads(RUNTIME_FREEZE.read_text(encoding="utf-8"))
    if sha_file(RUNTIME_FREEZE) != RUNTIME_FREEZE_SHA or payload["operative_supplier"]["n_params"] != EXPECTED_PARAMS or payload["context"]["effective_n_ctx"] != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("runtime binding mismatch")
    return payload


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output directory must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = load_binding()
    runtime = runtime_payload()
    for field in (TARGET_FIELD, OPERATION_FIELD):
        write_json(out / f"schema_{field}.json", binding["schemas"][field])
        write_json(out / f"response_format_{field}.json", binding["formats"][field])
    for task in binding["tasks"]:
        td = out / "tasks" / task["task_id"]
        td.mkdir(parents=True, exist_ok=True)
        write_json(td / "fixture.snapshot.json", task)
        for field in (TARGET_FIELD, OPERATION_FIELD):
            fd = td / field
            fd.mkdir()
            (fd / "prompt.txt").write_text(binding["prompts"][field][task["task_id"]], encoding="utf-8")
    manifest = {
        "schema": "zth_qwen3_1_7b_independent_authorization_atoms_factorial_run_manifest_v1",
        "status": "prepared_exploratory_not_confirmatory",
        "prepared_at": now(),
        "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "driver": str(Path(__file__).relative_to(ROOT)),
        "driver_sha256": sha_file(Path(__file__).resolve()),
        "task_manifest_sha256": binding["task_manifest_sha256"],
        "task_count": 16,
        "task_order": [task["task_id"] for task in binding["tasks"]],
        "expected_target_true": 8,
        "expected_operation_true": 8,
        "schema_sha256": binding["schema_sha256"],
        "format_sha256": binding["format_sha256"],
        "prompt_sha256": binding["prompt_sha256"],
        "execution_order": {"target_then_operation": 8, "operation_then_target": 8},
        "runtime_freeze_sha256": sha_file(RUNTIME_FREEZE),
        "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "context_limit_non_binding": True, "architecture_generation_confound": True, "llama_cpp_version": runtime["runtime"]["llama_cpp_version"], "build_revision": runtime["runtime"]["build_revision"]},
        "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS},
        "execution_policy": {"supplier_model_calls": 32, "teacher_calls": 0, "retries": 0, "escalations": 0},
        "model_calls_made": False,
    }
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "probe_manifest.json", manifest)
    write_json(out / "factorial_snapshot.json", {"target_x_operation_cells": {"+".join(key): value for key, value in binding["cells"].items()}, "full_factorial_cells": {"+".join(key): value for key, value in binding["cells3"].items()}, "model_calls_made": False})
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 16, "calls": 32, "target_true": 8, "operation_true": 8, "model_calls": 0}, indent=2))


def execute(out: Path) -> None:
    manifest = json.loads((out / "probe_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("prepared manifest hash mismatch")
    binding = load_binding()
    if manifest["task_manifest_sha256"] != binding["task_manifest_sha256"]:
        raise RuntimeError("task manifest drift")
    for task in binding["tasks"]:
        for field in (TARGET_FIELD, OPERATION_FIELD):
            if sha_file(out / "tasks" / task["task_id"] / field / "prompt.txt") != binding["prompt_sha256"][field][task["task_id"]]:
                raise RuntimeError("prompt drift")
    runtime_payload()
    spec = clean.worker_spec()
    models = list_models(spec, timeout=30)
    candidate = next((row for row in models.get("data", []) if row.get("id") == EXPECTED_MODEL_ID), None)
    meta = candidate.get("meta") if candidate else {}
    if candidate is None or meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("candidate endpoint binding mismatch")
    telemetry_url = base.telemetry_base_url()
    telemetry = base.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = base.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(out / "preflight.json", {"model_meta": meta, "telemetry": telemetry, "task_manifest_sha256": manifest["task_manifest_sha256"], "execution_policy": manifest["execution_policy"], "model_calls": 0})
    write_json(out / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(out / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    task_by_id = {task["task_id"]: task for task in binding["tasks"]}
    ranked = sorted(manifest["task_order"], key=lambda tid: hashlib.sha256((ORDER_SEED + tid).encode()).hexdigest())
    orders = {tid: ([TARGET_FIELD, OPERATION_FIELD] if i % 2 == 0 else [OPERATION_FIELD, TARGET_FIELD]) for i, tid in enumerate(ranked)}
    for tid in manifest["task_order"]:
        task = task_by_id[tid]
        for field in orders[tid]:
            fd = out / "tasks" / tid / field
            expected = binding["derived"][tid]["expected_target_allowed" if field == TARGET_FIELD else "expected_operation_allowed"]
            sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
            started = time.monotonic(); started_at = now(); sampler.start()
            response = structured_call(spec, (fd / "prompt.txt").read_text(encoding="utf-8"), binding["formats"][field], MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
            elapsed = round((time.monotonic() - started) * 1000, 3); samples = sampler.stop()
            energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
            metadata = response.metadata(); metadata["request_url"] = None
            raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": elapsed}
            write_json(fd / "response.json", raw)
            transport = metadata.get("transport_classification") == "model_response"
            validation = validate_raw(response.content, field, expected) if transport else {"validation_status":"failed","parse_valid":False,"contract_valid":False,"observed":None,"expected":expected,"field":field,"diagnostics":["transport failure"]}
            write_json(fd / "validation.json", validation)
            write_json(fd / "power_samples.json", {"measurement_level":2,"measurement_boundary":"gpu_device_only","gpu_uuid":EXPECTED_GPU_UUID,"samples":[{"timestamp_utc":s.timestamp_utc,"monotonic_seconds":s.monotonic_seconds,"gpu_uuid":s.gpu_uuid,"power_watts":s.power_watts,"sequence":s.sequence} for s in samples]})
            failure = None if transport and validation["contract_valid"] and validation["observed"] == expected else ("SERIALIZATION_FAILURE" if transport and not validation["parse_valid"] else ("INVALID_CONTRACT" if not validation["contract_valid"] else "ATOMIC_JUDGMENT_FAILURE"))
            write_json(fd / "scorecard.json", {"schema":"zth_qwen3_1_7b_independent_authorization_atom_scorecard_v1","task_id":tid,"field":field,"expected":expected,"target_factor":task["target_factor"],"operation_factor":task["operation_factor"],"distractor_factor":task["distractor_factor"],"transport_valid":transport,"raw_parse_valid":validation["parse_valid"] if transport else False,"contract_valid":validation["contract_valid"] if transport else False,"observed":validation["observed"],"correct":bool(transport and validation["contract_valid"] and validation["observed"] == expected),"failure_class":failure,"wall_elapsed_ms":elapsed,"prompt_tokens":(metadata.get("usage") or {}).get("prompt_tokens"),"completion_tokens":(metadata.get("usage") or {}).get("completion_tokens"),"power_summary":{"sample_count":len(samples),"mean_active_watts":statistics.mean(s.power_watts for s in samples),"peak_observed_watts":max(s.power_watts for s in samples),"gross_energy_joules":energy},"retry_count":0,"escalation_count":0,"teacher_calls":0})
    write_json(out / "aggregate.json", aggregate(out, manifest, idle_summary))
    write_json(out / "lifecycle.json", {"status":"terminal","completed_at":now(),"model_calls_made":True,"supplier_model_calls":32,"teacher_calls":0,"retries":0,"escalations":0})
    print(json.dumps({"status":"terminal","calls":32}, indent=2))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def aggregate(out: Path, manifest: dict[str, Any], idle: dict[str, Any]) -> dict[str, Any]:
    rows = [json.loads(path.read_text()) for path in sorted(out.glob("tasks/*/*/scorecard.json"))]
    tasks = {task["task_id"]: task for task in json.loads(TASK_MANIFEST.read_text())["tasks"]}
    def summary(subset: list[dict[str, Any]]) -> dict[str, Any]:
        lat = [row["wall_elapsed_ms"] for row in subset]; energy = [row["power_summary"]["gross_energy_joules"] for row in subset]
        return {"count":len(subset),"correct":sum(row["correct"] for row in subset),"true_selected":sum(row["observed"] is True for row in subset),"false_selected":sum(row["observed"] is False for row in subset),"parse_valid":sum(row["raw_parse_valid"] for row in subset),"contract_valid":sum(row["contract_valid"] for row in subset),"serialization_failures":sum(row["failure_class"]=="SERIALIZATION_FAILURE" for row in subset),"contract_failures":sum(row["failure_class"]=="INVALID_CONTRACT" for row in subset),"judgment_failures":sum(row["failure_class"]=="ATOMIC_JUDGMENT_FAILURE" for row in subset),"confusion_matrix":{"TP":sum(row["expected"] and row["observed"] is True for row in subset),"FN":sum(row["expected"] and row["observed"] is False for row in subset),"FP":sum((not row["expected"]) and row["observed"] is True for row in subset),"TN":sum((not row["expected"]) and row["observed"] is False for row in subset)},"latency_ms":{"median":statistics.median(lat),"mean":statistics.mean(lat),"p95":percentile(lat,0.95)},"energy_joules":{"mean_per_action":statistics.mean(energy),"median_per_action":statistics.median(energy),"total":sum(energy)}}
    arms = {field: summary([row for row in rows if row["field"] == field]) for field in (TARGET_FIELD, OPERATION_FIELD)}
    for field in arms:
        subset = [row for row in rows if row["field"] == field]
        for name, key, value in (("target_allowed", "target_factor", "TARGET_ALLOWED"),("target_not_allowed", "target_factor", "TARGET_NOT_ALLOWED"),("operation_allowed", "operation_factor", "OPERATION_ALLOWED"),("operation_not_allowed", "operation_factor", "OPERATION_NOT_ALLOWED"),("held_present", "distractor_factor", "HELD_DISTRACTOR_PRESENT"),("held_absent", "distractor_factor", "HELD_DISTRACTOR_ABSENT")):
            arms[field][name] = summary([row for row in subset if row[key] == value])
        arms[field]["cells"] = {f"{tf}+{of}": summary([row for row in subset if row["target_factor"] == tf and row["operation_factor"] == of]) for tf in ("TARGET_ALLOWED","TARGET_NOT_ALLOWED") for of in ("OPERATION_ALLOWED","OPERATION_NOT_ALLOWED")}
    paired = {}
    for tid, task in tasks.items():
        target = next(row for row in rows if row["task_id"] == tid and row["field"] == TARGET_FIELD)
        operation = next(row for row in rows if row["task_id"] == tid and row["field"] == OPERATION_FIELD)
        derived = None if target["observed"] is None or operation["observed"] is None else not (target["observed"] and operation["observed"])
        expected = task["expected_scope_expansion_required"]
        paired[tid] = {"target_observed":target["observed"],"operation_observed":operation["observed"],"expected_scope":expected,"derived_scope":derived,"derived_correct":derived == expected,"target_correct":target["correct"],"operation_correct":operation["correct"],"target_factor":task["target_factor"],"operation_factor":task["operation_factor"],"distractor_factor":task["distractor_factor"]}
    def derived_subset(predicate): return [row for row in paired.values() if predicate(row)]
    all_derived = list(paired.values())
    scope = {"count":16,"correct":sum(row["derived_correct"] for row in all_derived),"true_selected":sum(row["derived_scope"] is True for row in all_derived),"false_selected":sum(row["derived_scope"] is False for row in all_derived),"confusion_matrix":{"TP":sum(row["expected_scope"] and row["derived_scope"] is True for row in all_derived),"FN":sum(row["expected_scope"] and row["derived_scope"] is False for row in all_derived),"FP":sum((not row["expected_scope"]) and row["derived_scope"] is True for row in all_derived),"TN":sum((not row["expected_scope"]) and row["derived_scope"] is False for row in all_derived)}}
    scope["cells"] = {f"{tf}+{of}": {"count":len(group),"correct":sum(row["derived_correct"] for row in group),"expected_scope_true":sum(row["expected_scope"] for row in group),"expected_scope_false":sum(not row["expected_scope"] for row in group)} for tf in ("TARGET_ALLOWED","TARGET_NOT_ALLOWED") for of in ("OPERATION_ALLOWED","OPERATION_NOT_ALLOWED") for group in [[row for row in all_derived if row["target_factor"] == tf and row["operation_factor"] == of]]}
    return {"schema":"zth_qwen3_1_7b_independent_authorization_atoms_factorial_aggregate_v1","exploratory_not_confirmatory":True,"candidate":{"model_id":EXPECTED_MODEL_ID,"operative_parameters":EXPECTED_PARAMS,"artifact_sha256":EXPECTED_MODEL_SHA},"arms":arms,"derived_scope":scope,"paired":paired,"execution":{"supplier_model_calls":32,"teacher_calls":0,"retries":0,"escalations":0},"idle_power":idle}


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
