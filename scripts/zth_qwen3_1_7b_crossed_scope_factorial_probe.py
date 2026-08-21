#!/usr/bin/env python3
"""Crossed 2x2x2 exploratory scope-expansion probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.icm_call import call_worker, list_models
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from local_harness.supervised_capability_loop import _validator_result
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as clean
from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import EXPECTED_MODEL_ID, EXPECTED_MODEL_SHA, EXPECTED_PARAMS, EXPECTED_EFFECTIVE_CTX, EXPECTED_TRAIN_CTX, EXPECTED_REQUESTED_CTX, RUNTIME_FREEZE, RUNTIME_FREEZE_SHA

ROOT = clean.ROOT
TASK_MANIFEST = ROOT / "docs/research/CROSSED_SCOPE_FACTORIAL_PROBE_TASKS_2026-08-21.json"
EXPECTED_GPU_UUID = clean.EXPECTED_GPU_UUID
POWER_INTERVAL_SECONDS = clean.POWER_INTERVAL_SECONDS
IDLE_SECONDS = clean.IDLE_SECONDS
MAX_OUTPUT_TOKENS = clean.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = clean.TIMEOUT_SECONDS
LEAK_PATTERNS = clean.LEAK_PATTERNS


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


def task_prompt(task: dict[str, Any]) -> str:
    return clean.task_specific_text(task) + "\n\n" + clean.PROMPT_SUFFIX


def leakage_findings(task: dict[str, Any]) -> list[str]:
    text = clean.task_specific_text(task).casefold()
    return [pattern for pattern in LEAK_PATTERNS if pattern in text]


def validate_factorial_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != "zth_crossed_scope_factorial_probe_task_set_v1":
        raise ValueError("factorial manifest schema mismatch")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 16:
        raise ValueError("factorial probe requires 16 tasks")
    if len({task.get("task_id") for task in tasks}) != 16:
        raise ValueError("factorial task IDs must be unique")
    for task in tasks:
        if task.get("operation_factor") not in {"READ", "MUTATE"}:
            raise ValueError("invalid operation factor")
        if task.get("authority_factor") not in {"INSIDE_AUTHORITY", "OUTSIDE_AUTHORITY"}:
            raise ValueError("invalid authority factor")
        if task.get("distractor_factor") not in {"HELD_DISTRACTOR_PRESENT", "HELD_DISTRACTOR_ABSENT"}:
            raise ValueError("invalid distractor factor")
        if task["expected_scope_expansion_required"] != (task["authority_factor"] == "OUTSIDE_AUTHORITY"):
            raise ValueError(f"expected result does not follow authority factor: {task['task_id']}")
        if not task.get("authority_evidence") or not task.get("requested_operation") or not task.get("derivation_note"):
            raise ValueError(f"missing authoring fields: {task['task_id']}")
        found = leakage_findings(task)
        if found:
            raise ValueError(f"answer leakage in {task['task_id']}: {found}")
    def count(**filters: str) -> int:
        return sum(all(task[key] == value for key, value in filters.items()) for task in tasks)
    if sum(task["expected_scope_expansion_required"] for task in tasks) != 8:
        raise ValueError("expected branch balance is not 8/8")
    if sum(task["operation_factor"] == "READ" for task in tasks) != 8 or sum(task["operation_factor"] == "MUTATE" for task in tasks) != 8:
        raise ValueError("operation balance is not 8/8")
    if sum(task["authority_factor"] == "INSIDE_AUTHORITY" for task in tasks) != 8 or sum(task["authority_factor"] == "OUTSIDE_AUTHORITY" for task in tasks) != 8:
        raise ValueError("authority balance is not 8/8")
    if sum(task["distractor_factor"] == "HELD_DISTRACTOR_PRESENT" for task in tasks) != 8 or sum(task["distractor_factor"] == "HELD_DISTRACTOR_ABSENT" for task in tasks) != 8:
        raise ValueError("distractor balance is not 8/8")
    for operation in ("READ", "MUTATE"):
        for authority in ("INSIDE_AUTHORITY", "OUTSIDE_AUTHORITY"):
            if count(operation_factor=operation, authority_factor=authority) != 4:
                raise ValueError("operation x authority cell is not 4")
            for distractor in ("HELD_DISTRACTOR_PRESENT", "HELD_DISTRACTOR_ABSENT"):
                if count(operation_factor=operation, authority_factor=authority, distractor_factor=distractor) != 2:
                    raise ValueError("full factorial cell is not 2")
    max_prompt_chars = max(len(task_prompt(task)) for task in tasks)
    return {"task_count": 16, "true_count": 8, "false_count": 8, "read_count": 8, "mutate_count": 8, "inside_count": 8, "outside_count": 8, "distractor_present_count": 8, "distractor_absent_count": 8, "answer_leakage_findings": 0, "semantic_rule_sha256": sha_bytes(clean.SEMANTIC_RULE.encode()), "prompt_suffix_sha256": sha_bytes(clean.PROMPT_SUFFIX.encode()), "max_prompt_chars": max_prompt_chars, "conservative_prompt_plus_completion_bound": max_prompt_chars + MAX_OUTPUT_TOKENS}


def runtime_payload() -> dict[str, Any]:
    payload = json.loads(RUNTIME_FREEZE.read_text())
    if sha_file(RUNTIME_FREEZE) != RUNTIME_FREEZE_SHA:
        raise RuntimeError("runtime freeze hash mismatch")
    return payload


def worker_spec():
    return clean.worker_spec()


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("crossed probe output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = json.loads(TASK_MANIFEST.read_text())
    audit = validate_factorial_manifest(tasks)
    runtime = runtime_payload()
    if audit["conservative_prompt_plus_completion_bound"] >= EXPECTED_EFFECTIVE_CTX:
        raise RuntimeError("effective context could bind the factorial probe")
    task_rows = []
    for task in tasks["tasks"]:
        directory = output_dir / "tasks" / task["task_id"]; directory.mkdir(parents=True, exist_ok=True)
        prompt = task_prompt(task); (directory / "prompt.txt").write_bytes(prompt.encode()); write_json(directory / "fixture.snapshot.json", task)
        task_rows.append({"task_id": task["task_id"], "prompt_sha256": sha_bytes(prompt.encode()), "operation_factor": task["operation_factor"], "authority_factor": task["authority_factor"], "distractor_factor": task["distractor_factor"], "expected": task["expected_scope_expansion_required"]})
    manifest = {"schema": "zth_qwen3_1_7b_crossed_scope_factorial_probe_manifest_v1", "status": "prepared_exploratory_not_confirmatory", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_path": str(TASK_MANIFEST.relative_to(ROOT)), "task_manifest_sha256": sha_file(TASK_MANIFEST), "task_order": [row["task_id"] for row in task_rows], "audit": audit, "semantic_rule_sha256": audit["semantic_rule_sha256"], "prompt_suffix_sha256": audit["prompt_suffix_sha256"], "output_contract": {"exact_fields": ["scope_expansion_required"], "format": "bare_json_object", "field_type": "boolean"}, "runtime_freeze_path": str(RUNTIME_FREEZE.relative_to(ROOT)), "runtime_freeze_sha256": sha_file(RUNTIME_FREEZE), "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX, "requested_n_ctx": EXPECTED_REQUESTED_CTX, "context_cap_reason": "native_training_context_cap", "context_limit_non_binding_for_probe": True, "architecture_generation_confound": True, "llama_cpp_version": runtime["runtime"]["llama_cpp_version"], "build_revision": runtime["runtime"]["build_revision"]}, "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "gpu_class": "NVIDIA GeForce GTX 1650", "v100_touched": False}, "telemetry": {"transport": "remote_read_only_http", "measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS}, "execution_policy": {"supplier_model_calls": 16, "teacher_calls": 0, "retries": 0, "escalations": 0}, "tasks": task_rows, "model_calls_made": False}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None})); write_json(output_dir / "probe_manifest.json", manifest); write_json(output_dir / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "task_count": 16, "factorial_design_balanced": True, "answer_leakage_findings": 0, "context_limit_non_binding_for_probe": True, "model_calls": 0}, indent=2))


def execute(output_dir: Path) -> None:
    manifest_path = output_dir / "probe_manifest.json"; manifest = json.loads(manifest_path.read_text())
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("crossed probe manifest hash mismatch")
    tasks = json.loads(TASK_MANIFEST.read_text()); audit = validate_factorial_manifest(tasks); runtime_payload()
    if sha_file(TASK_MANIFEST) != manifest["task_manifest_sha256"]:
        raise RuntimeError("factorial binding changed")
    if manifest["runtime"]["context_limit_non_binding_for_probe"] is not True:
        raise RuntimeError("effective context binding is not proven non-binding")
    if audit["semantic_rule_sha256"] != manifest["semantic_rule_sha256"] or audit["answer_leakage_findings"] != 0:
        raise RuntimeError("semantic or leakage binding changed")
    for task in tasks["tasks"]:
        prompt = (output_dir / "tasks" / task["task_id"] / "prompt.txt").read_bytes()
        if sha_bytes(prompt) != next(row["prompt_sha256"] for row in manifest["tasks"] if row["task_id"] == task["task_id"]):
            raise RuntimeError(f"prompt binding changed: {task['task_id']}")
    spec = worker_spec(); models = list_models(spec, timeout=30); candidate = next((row for row in models.get("data", []) if row.get("id") == EXPECTED_MODEL_ID), None) if isinstance(models, dict) else None
    if candidate is None:
        raise RuntimeError("1.7B supplier not exposed")
    meta = candidate.get("meta") or {}
    if meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_EFFECTIVE_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
        raise RuntimeError(f"runtime metadata mismatch: {meta}")
    telemetry_url = clean.telemetry_base_url(); telemetry = clean.telemetry_preflight(telemetry_url); idle_samples, idle = clean.sample_window(IDLE_SECONDS, telemetry_url)
    preflight = {"schema": "zth_qwen3_1_7b_crossed_scope_factorial_probe_execution_manifest_v1", "execution_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "prepared_manifest_sha256": sha_file(manifest_path), "model_meta": meta, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "task_manifest_sha256": manifest["task_manifest_sha256"], "semantic_rule_sha256": manifest["semantic_rule_sha256"], "prompt_suffix_sha256": manifest["prompt_suffix_sha256"], "answer_leakage_findings": 0, "factorial_audit": manifest["audit"], "telemetry": telemetry, "execution_policy": manifest["execution_policy"]}
    write_json(output_dir / "preflight.json", preflight); write_json(output_dir / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle, "samples": idle_samples}); write_json(output_dir / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    by_id = {task["task_id"]: task for task in tasks["tasks"]}; summaries = []
    for task_id in manifest["task_order"] if "task_order" in manifest else [row["task_id"] for row in manifest["tasks"]]:
        task = by_id[task_id]; directory = output_dir / "tasks" / task_id; prompt = (directory / "prompt.txt").read_text(); sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS); started=time.monotonic(); started_at=now(); sampler.start(); response=call_worker(spec,prompt,MAX_OUTPUT_TOKENS,timeout=TIMEOUT_SECONDS); captured=time.monotonic(); samples=sampler.stop(); energy=integrate_energy_joules(samples,sample_interval_seconds=POWER_INTERVAL_SECONDS,expected_gpu_uuid=EXPECTED_GPU_UUID); metadata=response.metadata(); metadata["request_url"]=None; raw={"status":response.status,"content":response.content,"metadata":metadata,"request_started_at":started_at,"response_captured_at":now(),"wall_elapsed_ms":round((captured-started)*1000,3)}; write_json(directory/"response.json",raw); transport=metadata.get("transport_classification")=="model_response"; validation_task={"task_id":task_id,"task_family":"scope-expansion-crossed-factorial-atomic","prompt":clean.task_specific_text(task),"output_contract":{"format":"json","required_fields":["scope_expansion_required"]},"validator":{"kind":"zth_output_contract","reference_facts":{"requires_scope_expansion_flag":task["expected_scope_expansion_required"]}}}; validation=_validator_result(response.content,validation_task,attempt_id=f"cross-scope-{task_id}") if transport else None
        if validation is not None: write_json(directory/"validation.json",validation)
        parsed=clean.parse_atomic(response.content) if transport else {"raw_parse_valid":False,"contract_valid":False,"observed":None,"failure":"TRANSPORT_FAILURE"}; correct=parsed["contract_valid"] and parsed["observed"]==task["expected_scope_expansion_required"]; score={"schema":"zth_qwen3_1_7b_crossed_scope_factorial_task_scorecard_v1","task_id":task_id,"operation_factor":task["operation_factor"],"authority_factor":task["authority_factor"],"distractor_factor":task["distractor_factor"],"expected_scope_expansion_required":task["expected_scope_expansion_required"],"transport_valid":transport,"raw_parse_valid":parsed["raw_parse_valid"] if transport else False,"contract_valid":parsed["contract_valid"] if transport else False,"observed_scope_expansion_required":parsed["observed"],"correct":bool(correct),"failure_class":None if correct else (parsed["failure"] or "SCOPE_DECISION_FAILURE"),"validator_status":validation.get("validation_status") if validation else None,"wall_elapsed_ms":raw["wall_elapsed_ms"],"prompt_tokens":(metadata.get("usage") or {}).get("prompt_tokens"),"completion_tokens":(metadata.get("usage") or {}).get("completion_tokens"),"total_tokens":(metadata.get("usage") or {}).get("total_tokens"),"power_summary":{"sample_count":len(samples),"mean_active_watts":round(statistics.mean(sample.power_watts for sample in samples),6),"peak_observed_watts":round(max(sample.power_watts for sample in samples),6),"gross_energy_joules":energy,"sample_interval_seconds":POWER_INTERVAL_SECONDS},"measurement_level":2,"measurement_boundary":"gpu_device_only","retry_count":0,"escalation_count":0,"teacher_calls":0,"raw_response_preserved":True,"exploratory_not_confirmatory":True}; write_json(directory/"power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","gpu_uuid":EXPECTED_GPU_UUID,"samples":[{"timestamp_utc":s.timestamp_utc,"monotonic_seconds":s.monotonic_seconds,"gpu_uuid":s.gpu_uuid,"power_watts":s.power_watts,"sequence":s.sequence} for s in samples]}); write_json(directory/"scorecard.json",score); summaries.append(score)
    write_json(output_dir/"aggregate.json",aggregate(summaries,idle)); write_json(output_dir/"lifecycle.json",{"status":"terminal","completed_at":now(),"model_calls_made":True,"supplier_model_calls":16,"teacher_calls":0,"retries":0,"escalations":0}); print(json.dumps({"status":"terminal","tasks":16,"model_calls":16},indent=2))


def aggregate(rows: list[dict[str, Any]], idle: dict[str, Any]) -> dict[str, Any]:
    def correct(rows: list[dict[str, Any]]) -> int: return sum(row["correct"] for row in rows)
    def subset(**filters: str) -> list[dict[str, Any]]: return [row for row in rows if all(row[key] == value for key, value in filters.items())]
    true_rows=subset(expected_scope_expansion_required=True); false_rows=subset(expected_scope_expansion_required=False); tp=sum(row["correct"] and row["expected_scope_expansion_required"] for row in rows); tn=sum(row["correct"] and not row["expected_scope_expansion_required"] for row in rows); fp=sum(not row["expected_scope_expansion_required"] and row["observed_scope_expansion_required"] is True for row in rows); fn=sum(row["expected_scope_expansion_required"] and row["observed_scope_expansion_required"] is False for row in rows); lat=[row["wall_elapsed_ms"] for row in rows]; energies=[row["power_summary"]["gross_energy_joules"] for row in rows]; ordered=sorted(lat)
    cell={f"{op}_{auth}": {"tasks": len(subset(operation_factor=op,authority_factor=auth)), "correct": correct(subset(operation_factor=op,authority_factor=auth)), "accuracy": correct(subset(operation_factor=op,authority_factor=auth))/len(subset(operation_factor=op,authority_factor=auth))} for op in ("READ","MUTATE") for auth in ("INSIDE_AUTHORITY","OUTSIDE_AUTHORITY")}
    conditioned={"authority": {v:{"tasks":len(subset(authority_factor=v)),"correct":correct(subset(authority_factor=v))} for v in ("INSIDE_AUTHORITY","OUTSIDE_AUTHORITY")},"operation": {v:{"tasks":len(subset(operation_factor=v)),"correct":correct(subset(operation_factor=v))} for v in ("READ","MUTATE")},"distractor": {v:{"tasks":len(subset(distractor_factor=v)),"correct":correct(subset(distractor_factor=v))} for v in ("HELD_DISTRACTOR_PRESENT","HELD_DISTRACTOR_ABSENT")}}
    return {"schema":"zth_qwen3_1_7b_crossed_scope_factorial_aggregate_v1","exploratory_not_confirmatory":True,"candidate":{"model_id":EXPECTED_MODEL_ID,"operative_parameters":EXPECTED_PARAMS,"artifact_sha256":EXPECTED_MODEL_SHA},"overall_accuracy":correct(rows)/len(rows),"branch_results":{"true":{"tasks":len(true_rows),"correct":correct(true_rows),"accuracy":correct(true_rows)/len(true_rows)},"false":{"tasks":len(false_rows),"correct":correct(false_rows),"accuracy":correct(false_rows)/len(false_rows)}},"operation_results": {"read":{"tasks":8,"correct":correct(subset(operation_factor="READ"))},"mutate":{"tasks":8,"correct":correct(subset(operation_factor="MUTATE"))}},"authority_results": {"inside":{"tasks":8,"correct":correct(subset(authority_factor="INSIDE_AUTHORITY"))},"outside":{"tasks":8,"correct":correct(subset(authority_factor="OUTSIDE_AUTHORITY"))}},"distractor_results": {"present":{"tasks":8,"correct":correct(subset(distractor_factor="HELD_DISTRACTOR_PRESENT"))},"absent":{"tasks":8,"correct":correct(subset(distractor_factor="HELD_DISTRACTOR_ABSENT"))}},"cells":cell,"conditioned":conditioned,"observed_true_count":sum(row["observed_scope_expansion_required"] is True for row in rows),"observed_false_count":sum(row["observed_scope_expansion_required"] is False for row in rows),"confusion_matrix":{"tp":tp,"fn":fn,"fp":fp,"tn":tn},"true_precision":tp/(tp+fp) if tp+fp else None,"true_recall":tp/(tp+fn) if tp+fn else None,"true_f1":2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,"false_positive_rate":fp/len(false_rows),"false_negative_rate":fn/len(true_rows),"serialization_failures":sum(row["failure_class"]=="SERIALIZATION_FAILURE" for row in rows),"invalid_contract_failures":sum(row["failure_class"]=="INVALID_CONTRACT" for row in rows),"scope_decision_failures":sum(row["failure_class"]=="SCOPE_DECISION_FAILURE" for row in rows),"latency_ms":{"median":statistics.median(lat),"mean":statistics.mean(lat),"p95":ordered[min(len(ordered)-1,round((len(ordered)-1)*.95))]},"energy":{"measurement_level":2,"measurement_boundary":"gpu_device_only","mean_joules_per_action":statistics.mean(energies),"median_joules_per_action":statistics.median(energies),"total_gross_joules":sum(energies)},"idle_power":idle,"execution":{"supplier_model_calls":16,"teacher_calls":0,"retries":0,"escalations":0},"primary_characterization":"PENDING_REVIEW"}


def main() -> int:
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare",action="store_true"); group.add_argument("--execute",action="store_true"); parser.add_argument("--output-dir",type=Path,required=True); args=parser.parse_args(); prepare(args.output_dir) if args.prepare else execute(args.output_dir); return 0


if __name__ == "__main__": raise SystemExit(main())
