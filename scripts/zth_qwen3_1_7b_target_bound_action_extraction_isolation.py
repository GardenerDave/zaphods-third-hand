#!/usr/bin/env python3
"""Target-bound action-head extraction isolation probe."""

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
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = base.ROOT
TASKS = ROOT / "docs/research/TARGET_BOUND_ACTION_EXTRACTION_ISOLATION_TASKS_2026-08-22.json"
FIELD = "target_bound_operation"
SCHEMA_NAME = "target_bound_action_extraction"
EXPECTED_MODEL_ID = runtime.EXPECTED_MODEL_ID
EXPECTED_MODEL_SHA = runtime.EXPECTED_MODEL_SHA
EXPECTED_PARAMS = runtime.EXPECTED_PARAMS
EXPECTED_CTX = runtime.EXPECTED_EFFECTIVE_CTX
EXPECTED_TRAIN_CTX = runtime.EXPECTED_TRAIN_CTX
EXPECTED_GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = runtime.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = runtime.POWER_INTERVAL_SECONDS
IDLE_SECONDS = runtime.IDLE_SECONDS


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


def schema() -> dict[str, Any]:
    return {"type": "object", "properties": {FIELD: {"type": "string"}}, "required": [FIELD], "additionalProperties": False}


def response_format() -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": SCHEMA_NAME, "schema": schema()}}


def prompt_for(task: dict[str, Any]) -> str:
    return f"Request sentence:\n{task['sentence']}\n\nExtract the operation directly applied to the named target. Return the required structured string only.\n/no_think"


def validate_model_free() -> dict[str, Any]:
    payload = json.loads(TASKS.read_text(encoding="utf-8"))
    tasks = payload.get("tasks", [])
    if len(tasks) != 8 or len({t["task_id"] for t in tasks}) != 8:
        raise RuntimeError("action-head task count or IDs invalid")
    pairs = {}
    for task in tasks:
        if len({task["verb_a"], task["verb_b"]}) != 2:
            raise RuntimeError(f"pair verbs not distinct: {task['task_id']}")
        if task["expected_target_bound_operation"] not in {task["verb_a"], task["verb_b"]} or task["secondary_action"] not in {task["verb_a"], task["verb_b"]}:
            raise RuntimeError(f"role fields invalid: {task['task_id']}")
        if {task["expected_target_bound_operation"], task["secondary_action"]} != {task["verb_a"], task["verb_b"]}:
            raise RuntimeError(f"role partition invalid: {task['task_id']}")
        if task["expected_answer_position"] not in {"first", "second"}:
            raise RuntimeError(f"answer position invalid: {task['task_id']}")
        if task["first_action"] not in {task["verb_a"], task["verb_b"]} or task["second_action"] not in {task["verb_a"], task["verb_b"]}:
            raise RuntimeError(f"action order invalid: {task['task_id']}")
        pairs.setdefault(task["pair_id"], []).append(task)
    if len(pairs) != 4 or any(len(rows) != 2 for rows in pairs.values()):
        raise RuntimeError("pair balance invalid")
    for pair_id, rows in pairs.items():
        if rows[0]["requested_target"] != rows[1]["requested_target"] or {rows[0]["verb_a"], rows[0]["verb_b"]} != {rows[1]["verb_a"], rows[1]["verb_b"]}:
            raise RuntimeError(f"pair lexical binding invalid: {pair_id}")
        if {rows[0]["expected_target_bound_operation"], rows[1]["expected_target_bound_operation"]} != {rows[0]["verb_a"], rows[0]["verb_b"]}:
            raise RuntimeError(f"pair role reversal invalid: {pair_id}")
    all_verbs = {task["verb_a"] for task in tasks} | {task["verb_b"] for task in tasks}
    for verb in all_verbs:
        roles = [task["expected_target_bound_operation"] == verb for task in tasks if verb in {task["verb_a"], task["verb_b"]}]
        if roles.count(True) != roles.count(False):
            raise RuntimeError(f"lexical role balance invalid: {verb}")
    if len({task["expected_answer_position"] for task in tasks}) != 2:
        raise RuntimeError("answer position has no variation")
    if all(task["expected_target_bound_operation"] == task["first_action"] for task in tasks) or all(task["expected_target_bound_operation"] == task["second_action"] for task in tasks):
        raise RuntimeError("action position perfectly predicts answer")
    prompts = {task["task_id"]: prompt_for(task) for task in tasks}
    prompt_text = " ".join(prompts.values()).casefold()
    for forbidden in ("authorization", "scope", "membership", "policy", "allowed", "review", "first", "main", "primary"):
        if forbidden in prompt_text:
            raise RuntimeError(f"forbidden prompt term: {forbidden}")
    encoded = json.dumps(schema(), sort_keys=True)
    if any(token in encoded for token in ('"enum"', '"example"', '"examples"', '"default"', '"const"')):
        raise RuntimeError("schema value cue")
    lengths = [len(p) for p in prompts.values()]
    if max(lengths) + MAX_OUTPUT_TOKENS >= EXPECTED_CTX:
        raise RuntimeError("context bound is not non-binding")
    return {"payload": payload, "tasks": tasks, "pairs": pairs, "prompts": prompts, "schema": schema(), "format": response_format(), "task_sha256": sha_file(TASKS), "schema_sha256": sha_bytes(canonical(schema())), "format_sha256": sha_bytes(canonical(response_format())), "prompt_sha256": {tid: sha_bytes(p.encode()) for tid, p in prompts.items()}, "max_prompt_chars": max(lengths), "context_bound": max(lengths) + MAX_OUTPUT_TOKENS}


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    binding = validate_model_free()
    runtime_payload = runtime.runtime_payload()
    for task in binding["tasks"]:
        task_dir = output_dir / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "prompt.txt").write_text(binding["prompts"][task["task_id"]], encoding="utf-8")
        write_json(task_dir / "fixture.snapshot.json", task)
    write_json(output_dir / "schema_target_bound_operation.json", binding["schema"])
    write_json(output_dir / "response_format_target_bound_operation.json", binding["format"])
    manifest = {"schema": "zth_qwen3_1_7b_target_bound_action_extraction_manifest_v1", "status": "prepared_exploratory_not_confirmatory", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_sha256": binding["task_sha256"], "task_count": 8, "pair_count": 4, "task_order": [t["task_id"] for t in binding["tasks"]], "schema_sha256": binding["schema_sha256"], "response_format_sha256": binding["format_sha256"], "prompt_sha256": binding["prompt_sha256"], "context_limit_non_binding": True, "runtime_freeze_sha256": sha_file(runtime.RUNTIME_FREEZE), "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX}, "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS}, "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False}, "execution_policy": {"supplier_model_calls": 8, "teacher_calls": 0, "retries": 0, "escalations": 0}, "model_calls_made": False, "runtime_metadata": runtime_payload["runtime"]}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(output_dir / "probe_manifest.json", manifest)
    write_json(output_dir / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 8, "pairs": 4, "model_calls": 0}, indent=2))


def parse_raw(raw: str) -> tuple[str | None, bool, bool, list[str]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    valid = isinstance(parsed, dict) and set(parsed) == {FIELD} and isinstance(parsed.get(FIELD), str)
    return (parsed.get(FIELD) if valid else None), True, valid, ([] if valid else ["exact string contract failed"])


def classify_pair(rows: list[dict[str, Any]]) -> str:
    correct = [row["correct"] for row in rows]
    if all(correct):
        return "BOTH_RELATIONS_CORRECT"
    if any(correct):
        return "ONE_DIRECTION_CORRECT"
    if rows[0]["observed"] == rows[1]["observed"] and rows[0]["observed"] is not None:
        if all(row["observed"] == row["secondary_action"] for row in rows):
            return "BOTH_SELECT_SECONDARY_ACTION"
        return "BOTH_SELECT_SAME_VERB"
    return "OTHER"


def execute(output_dir: Path) -> None:
    manifest = json.loads((output_dir / "probe_manifest.json").read_text())
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("manifest hash mismatch")
    binding = validate_model_free()
    spec = runtime.worker_spec()
    models = list_models(spec, timeout=30)
    candidate = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
    if candidate is None or (candidate.get("meta") or {}).get("n_params") != EXPECTED_PARAMS or (candidate.get("meta") or {}).get("n_ctx") != EXPECTED_CTX or (candidate.get("meta") or {}).get("n_ctx_train") != EXPECTED_TRAIN_CTX:
        raise RuntimeError("runtime binding mismatch")
    telemetry_url = base.telemetry_base_url()
    telemetry = base.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = base.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(output_dir / "preflight.json", {"schema": "zth_target_bound_action_extraction_execution_v1", "prepared_manifest_sha256": sha_file(output_dir / "probe_manifest.json"), "model_meta": candidate.get("meta"), "telemetry": telemetry, "task_manifest_sha256": manifest["task_manifest_sha256"], "execution_policy": manifest["execution_policy"]})
    write_json(output_dir / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
    write_json(output_dir / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    rows = []
    for task in binding["tasks"]:
        task_dir = output_dir / "tasks" / task["task_id"]
        sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
        started = time.monotonic(); started_at = now(); sampler.start()
        response = decomposition.structured_call(spec, (task_dir / "prompt.txt").read_text(), binding["format"], MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
        captured = time.monotonic(); samples = sampler.stop()
        energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
        metadata = response.metadata(); metadata["request_url"] = None
        raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
        write_json(task_dir / "response.json", raw)
        transport = metadata.get("transport_classification") == "model_response"
        observed, parse_valid, contract_valid, diagnostics = parse_raw(response.content) if transport else (None, False, False, ["transport failure"])
        expected = task["expected_target_bound_operation"]
        score = {"schema": "zth_target_bound_action_extraction_scorecard_v1", "task_id": task["task_id"], "pair_id": task["pair_id"], "expected": expected, "observed": observed, "correct": bool(contract_valid and observed == expected), "parse_valid": parse_valid, "contract_valid": contract_valid, "transport_valid": transport, "diagnostics": diagnostics, "expected_answer_position": task["expected_answer_position"], "first_action": task["first_action"], "second_action": task["second_action"], "secondary_action": task["secondary_action"], "wall_elapsed_ms": raw["wall_elapsed_ms"], "power_summary": {"sample_count": len(samples), "mean_active_watts": statistics.mean(s.power_watts for s in samples), "peak_observed_watts": max(s.power_watts for s in samples), "gross_energy_joules": energy}, "retry_count": 0, "escalation_count": 0, "teacher_calls": 0}
        write_json(task_dir / "validation.json", {"schema": "zth_target_bound_action_extraction_validation_v1", **score})
        write_json(task_dir / "scorecard.json", score)
        write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "monotonic_seconds": s.monotonic_seconds, "gpu_uuid": s.gpu_uuid, "power_watts": s.power_watts, "sequence": s.sequence} for s in samples]})
        rows.append(score)
    pairs = {}
    for row in rows:
        pairs.setdefault(row["pair_id"], []).append(row)
    pair_results = {pair_id: {"classification": classify_pair(pair_rows), "task_ids": [row["task_id"] for row in pair_rows]} for pair_id, pair_rows in pairs.items()}
    lat = sorted(row["wall_elapsed_ms"] for row in rows); energy = [row["power_summary"]["gross_energy_joules"] for row in rows]
    aggregate = {"schema": "zth_target_bound_action_extraction_aggregate_v1", "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA}, "counts": {"tasks": 8, "parse_valid": sum(r["parse_valid"] for r in rows), "contract_valid": sum(r["contract_valid"] for r in rows), "correct": sum(r["correct"] for r in rows), "secondary_action_selections": sum(r["observed"] == r["secondary_action"] for r in rows), "expected_position_first_correct": sum(r["correct"] and r["expected_answer_position"] == "first" for r in rows), "expected_position_second_correct": sum(r["correct"] and r["expected_answer_position"] == "second" for r in rows), "first_action_correct": sum(r["correct"] and r["observed"] == r["first_action"] for r in rows), "second_action_correct": sum(r["correct"] and r["observed"] == r["second_action"] for r in rows)}, "by_pair": pair_results, "by_verb_pair": {pair_id: {"task_ids": [row["task_id"] for row in pair_rows], "correct": sum(row["correct"] for row in pair_rows), "secondary_selections": sum(row["observed"] == row["secondary_action"] for row in pair_rows)} for pair_id, pair_rows in pairs.items()}, "latency_ms": {"median": statistics.median(lat), "mean": statistics.mean(lat), "p95": lat[min(len(lat)-1, round((len(lat)-1)*0.95))]}, "energy_joules": {"mean_per_action": statistics.mean(energy), "median_per_action": statistics.median(energy), "total": sum(energy)}, "idle_power": idle_summary, "execution": {"supplier_model_calls": 8, "teacher_calls": 0, "retries": 0, "escalations": 0}}
    write_json(output_dir / "aggregate.json", aggregate)
    write_json(output_dir / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 8, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "calls": 8}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); parser.add_argument("--output-dir", type=Path, required=True); args = parser.parse_args(); (prepare if args.prepare else execute)(args.output_dir); return 0


if __name__ == "__main__":
    raise SystemExit(main())
