#!/usr/bin/env python3
"""Extract two local action/object relations, then select by frozen target."""

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
TASKS = ROOT / "docs/research/ACTION_OBJECT_RELATION_EXTRACTION_TASKS_2026-08-22.json"
FIELDS = ("action_1", "object_1", "action_2", "object_2")
SCHEMA_NAME = "action_object_relation_extraction"
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


def norm(value: Any) -> str:
    return " ".join(str(value).casefold().strip().split())


def schema() -> dict[str, Any]:
    return {"type": "object", "properties": {field: {"type": "string"} for field in FIELDS}, "required": list(FIELDS), "additionalProperties": False}


def response_format() -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": SCHEMA_NAME, "schema": schema()}}


def prompt_for(task: dict[str, Any]) -> str:
    return f"Request sentence:\n{task['sentence']}\n\nExtract the two factual action/object relations expressed in the sentence, in sentence order. Return the required structured relation fields only.\n/no_think"


def validate_model_free() -> dict[str, Any]:
    payload = json.loads(TASKS.read_text(encoding="utf-8"))
    tasks = payload.get("tasks", [])
    if len(tasks) != 8 or len({task["task_id"] for task in tasks}) != 8:
        raise RuntimeError("relation task count or IDs invalid")
    pairs: dict[str, list[dict[str, Any]]] = {}
    all_actions: set[str] = set()
    for task in tasks:
        if len({task["action_1"], task["action_2"]}) != 2:
            raise RuntimeError(f"task does not contain two distinct actions: {task['task_id']}")
        if task["expected_selected_operation"] not in {task["action_1"], task["action_2"]}:
            raise RuntimeError(f"selected action is not in relation actions: {task['task_id']}")
        if task["secondary_action"] not in {task["action_1"], task["action_2"]} or task["secondary_action"] == task["expected_selected_operation"]:
            raise RuntimeError(f"secondary action invalid: {task['task_id']}")
        if task["expected_selected_position"] not in {"first", "second"}:
            raise RuntimeError(f"selected position invalid: {task['task_id']}")
        expected_position_action = task["action_1"] if task["expected_selected_position"] == "first" else task["action_2"]
        if expected_position_action != task["expected_selected_operation"]:
            raise RuntimeError(f"selected position/action mismatch: {task['task_id']}")
        if sum(task[key] == task["requested_target"] for key in ("object_1", "object_2")) != 1:
            raise RuntimeError(f"task does not have exactly one target-bound relation: {task['task_id']}")
        if task["expected_selected_operation"] == task["action_1"] and task["object_1"] != task["requested_target"]:
            raise RuntimeError(f"first relation is not target-bound: {task['task_id']}")
        if task["expected_selected_operation"] == task["action_2"] and task["object_2"] != task["requested_target"]:
            raise RuntimeError(f"second relation is not target-bound: {task['task_id']}")
        for action in (task["action_1"], task["action_2"]):
            all_actions.add(action)
            if norm(action) not in {norm(word) for word in task["sentence"].replace(",", " ").replace(".", " ").split()}:
                raise RuntimeError(f"action absent from sentence: {task['task_id']}")
        pairs.setdefault(task["pair_id"], []).append(task)
    if len(pairs) != 4 or any(len(rows) != 2 for rows in pairs.values()):
        raise RuntimeError("pair balance invalid")
    for pair_id, rows in pairs.items():
        if rows[0]["requested_target"] != rows[1]["requested_target"]:
            raise RuntimeError(f"pair target mismatch: {pair_id}")
        if {rows[0]["action_1"], rows[0]["action_2"]} != {rows[1]["action_1"], rows[1]["action_2"]}:
            raise RuntimeError(f"pair action mismatch: {pair_id}")
        if {row["expected_selected_operation"] for row in rows} != {rows[0]["action_1"], rows[0]["action_2"]}:
            raise RuntimeError(f"pair does not reverse target-bound action: {pair_id}")
        if {row["expected_selected_position"] for row in rows} != {"first", "second"}:
            raise RuntimeError(f"pair does not reverse selected position: {pair_id}")
        if any(row["secondary_action"] != (set((row["action_1"], row["action_2"])) - {row["expected_selected_operation"]}).pop() for row in rows):
            raise RuntimeError(f"pair secondary action mismatch: {pair_id}")
    for action in all_actions:
        roles = [task["expected_selected_operation"] == action for task in tasks if action in {task["action_1"], task["action_2"]}]
        if roles.count(True) != roles.count(False):
            raise RuntimeError(f"action lexical role imbalance: {action}")
    if sum(task["expected_selected_position"] == "first" for task in tasks) != 4 or sum(task["expected_selected_position"] == "second" for task in tasks) != 4:
        raise RuntimeError("selected-position balance invalid")
    for action_key in ("action_1", "action_2"):
        for action in all_actions:
            rows = [task for task in tasks if task[action_key] == action]
            if rows and ({task["expected_selected_operation"] == action for task in rows} != {True, False}):
                raise RuntimeError(f"{action_key} shortcut predicts selection: {action}")
    prompts = {task["task_id"]: prompt_for(task) for task in tasks}
    prompt_text = " ".join(prompts.values()).casefold()
    for forbidden in ("authorization", "scope", "membership", "policy", "allowed", "review"):
        if forbidden in prompt_text:
            raise RuntimeError(f"forbidden prompt term: {forbidden}")
    encoded_schema = json.dumps(schema(), sort_keys=True)
    if any(token in encoded_schema for token in ('"enum"', '"example"', '"examples"', '"default"', '"const"')):
        raise RuntimeError("schema value cue")
    max_prompt_chars = max(len(prompt) for prompt in prompts.values())
    if max_prompt_chars + MAX_OUTPUT_TOKENS >= EXPECTED_CTX:
        raise RuntimeError("context bound is not non-binding")
    return {"payload": payload, "tasks": tasks, "pairs": pairs, "prompts": prompts, "schema": schema(), "format": response_format(), "task_sha256": sha_file(TASKS), "schema_sha256": sha_bytes(canonical(schema())), "format_sha256": sha_bytes(canonical(response_format())), "prompt_sha256": {task_id: sha_bytes(prompt.encode()) for task_id, prompt in prompts.items()}, "max_prompt_chars": max_prompt_chars, "context_bound": max_prompt_chars + MAX_OUTPUT_TOKENS}


def runtime_payload() -> dict[str, Any]:
    return runtime.runtime_payload()


def parse_raw(raw: str) -> tuple[dict[str, Any] | None, bool, bool, list[str]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    valid = isinstance(parsed, dict) and set(parsed) == set(FIELDS) and all(isinstance(parsed.get(field), str) for field in FIELDS)
    return (parsed if valid else None), True, valid, ([] if valid else ["exact four-string relation contract failed"])


def select_target_relation(parsed: dict[str, Any] | None, target: str) -> dict[str, Any]:
    if parsed is None:
        return {"selected_operation": None, "selected_position": None, "evaluable": False, "ambiguous": False, "classification": "INVALID_EXTRACTION_CONTRACT"}
    matches = [index for index in (1, 2) if norm(parsed[f"object_{index}"]) == norm(target)]
    if len(matches) == 1:
        index = matches[0]
        return {"selected_operation": parsed[f"action_{index}"], "selected_position": "first" if index == 1 else "second", "evaluable": True, "ambiguous": False, "classification": "EVALUABLE"}
    if len(matches) > 1:
        return {"selected_operation": None, "selected_position": None, "evaluable": False, "ambiguous": True, "classification": "AMBIGUOUS_RELATION_BINDING"}
    return {"selected_operation": None, "selected_position": None, "evaluable": False, "ambiguous": False, "classification": "UNEVALUABLE_NO_TARGET_RELATION"}


def score(parsed: dict[str, Any] | None, parse_valid: bool, contract_valid: bool, task: dict[str, Any]) -> dict[str, Any]:
    if not contract_valid or parsed is None:
        return {"field_correct": {field: False for field in FIELDS}, "all_relations_correct": False, **select_target_relation(None, task["requested_target"]), "failure_class": "INVALID_EXTRACTION_CONTRACT" if parse_valid else "SERIALIZATION_FAILURE"}
    field_correct = {field: norm(parsed[field]) == norm(task[field]) for field in FIELDS}
    selection = select_target_relation(parsed, task["requested_target"])
    selected_correct = selection["selected_operation"] is not None and norm(selection["selected_operation"]) == norm(task["expected_selected_operation"])
    if all(field_correct.values()) and selected_correct:
        classification = "RELATIONS_CORRECT_SELECTION_CORRECT"
    elif not all(field_correct.values()) and selected_correct:
        classification = "RELATION_EXTRACTION_ERROR_SELECTION_STILL_CORRECT"
    elif not selection["evaluable"]:
        classification = "RELATION_EXTRACTION_ERROR_SELECTION_UNEVALUABLE"
    else:
        classification = "RELATION_EXTRACTION_ERROR_SELECTION_INCORRECT"
    return {"field_correct": field_correct, "all_relations_correct": all(field_correct.values()), "selected_correct": selected_correct, **selection, "failure_class": classification}


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    binding = validate_model_free()
    runtime_data = runtime_payload()
    for task in binding["tasks"]:
        task_dir = output_dir / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "prompt.txt").write_text(binding["prompts"][task["task_id"]], encoding="utf-8")
        write_json(task_dir / "fixture.snapshot.json", task)
    write_json(output_dir / "schema_action_object_relation.json", binding["schema"])
    write_json(output_dir / "response_format_action_object_relation.json", binding["format"])
    manifest = {"schema": "zth_qwen3_1_7b_action_object_relation_extraction_manifest_v1", "status": "prepared_exploratory_not_confirmatory", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_sha256": binding["task_sha256"], "task_count": 8, "pair_count": 4, "task_order": [task["task_id"] for task in binding["tasks"]], "schema_sha256": binding["schema_sha256"], "response_format_sha256": binding["format_sha256"], "prompt_sha256": binding["prompt_sha256"], "context_limit_non_binding": True, "runtime_freeze_sha256": sha_file(runtime.RUNTIME_FREEZE), "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX}, "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS}, "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False}, "execution_policy": {"supplier_model_calls": 8, "teacher_calls": 0, "retries": 0, "escalations": 0, "adaptation": 0}, "model_calls_made": False, "runtime_metadata": runtime_data["runtime"]}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(output_dir / "probe_manifest.json", manifest)
    write_json(output_dir / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 8, "pairs": 4, "model_calls": 0}, indent=2))


def execute(output_dir: Path) -> None:
    manifest = json.loads((output_dir / "probe_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("manifest hash mismatch")
    binding = validate_model_free()
    if manifest["task_manifest_sha256"] != binding["task_sha256"] or manifest["prompt_sha256"] != binding["prompt_sha256"]:
        raise RuntimeError("frozen relation binding drift")
    spec = runtime.worker_spec()
    models = list_models(spec, timeout=30)
    candidate = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
    meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
        raise RuntimeError("runtime binding mismatch")
    telemetry_url = base.telemetry_base_url()
    telemetry = base.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = base.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(output_dir / "preflight.json", {"schema": "zth_qwen3_1_7b_action_object_relation_execution_v1", "prepared_manifest_sha256": sha_file(output_dir / "probe_manifest.json"), "model_meta": meta, "telemetry": telemetry, "task_manifest_sha256": binding["task_sha256"], "execution_policy": manifest["execution_policy"]})
    write_json(output_dir / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": [{"timestamp_utc": sample.timestamp_utc, "monotonic_seconds": sample.monotonic_seconds, "gpu_uuid": sample.gpu_uuid, "power_watts": sample.power_watts, "sequence": sample.sequence} for sample in idle_samples]})
    write_json(output_dir / "lifecycle.json", {"status": "running", "started_at": now(), "model_calls_made": False})
    rows: list[dict[str, Any]] = []
    for task in binding["tasks"]:
        task_dir = output_dir / "tasks" / task["task_id"]
        prompt = (task_dir / "prompt.txt").read_text(encoding="utf-8")
        sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
        started = time.monotonic(); started_at = now(); sampler.start()
        response = decomposition.structured_call(spec, prompt, binding["format"], MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
        captured = time.monotonic(); samples = sampler.stop()
        energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
        metadata = response.metadata(); metadata["request_url"] = None
        raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": started_at, "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
        write_json(task_dir / "response.json", raw)
        transport_valid = metadata.get("transport_classification") == "model_response"
        parsed, parse_valid, contract_valid, diagnostics = parse_raw(response.content) if transport_valid else (None, False, False, ["transport failure"])
        scored = score(parsed, parse_valid, contract_valid, task)
        write_json(task_dir / "validation.json", {"validation_status": "passed" if transport_valid and contract_valid else "failed", "parse_valid": parse_valid, "contract_valid": contract_valid, "diagnostics": diagnostics, "task_id": task["task_id"]})
        write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": sample.timestamp_utc, "monotonic_seconds": sample.monotonic_seconds, "gpu_uuid": sample.gpu_uuid, "power_watts": sample.power_watts, "sequence": sample.sequence} for sample in samples]})
        scorecard = {"schema": "zth_qwen3_1_7b_action_object_relation_task_scorecard_v1", "task_id": task["task_id"], "pair_id": task["pair_id"], "requested_target": task["requested_target"], "expected_relations": {field: task[field] for field in FIELDS}, "expected_selected_operation": task["expected_selected_operation"], "expected_selected_position": task["expected_selected_position"], "secondary_action": task["secondary_action"], "transport_valid": transport_valid, "raw_parse_valid": parse_valid, "contract_valid": contract_valid, "observed_relations": parsed, **scored, "wall_elapsed_ms": raw["wall_elapsed_ms"], "prompt_tokens": (metadata.get("usage") or {}).get("prompt_tokens"), "completion_tokens": (metadata.get("usage") or {}).get("completion_tokens"), "power_summary": {"sample_count": len(samples), "mean_active_watts": statistics.mean(sample.power_watts for sample in samples), "peak_observed_watts": max(sample.power_watts for sample in samples), "gross_energy_joules": energy}, "retry_count": 0, "escalation_count": 0, "teacher_calls": 0}
        write_json(task_dir / "scorecard.json", scorecard)
        rows.append(scorecard)
    write_json(output_dir / "aggregate.json", aggregate(rows, idle_summary, manifest))
    write_json(output_dir / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": True, "supplier_model_calls": 8, "unique_called_tasks": 8, "duplicate_called_tasks": 0, "teacher_calls": 0, "retries": 0, "escalations": 0})
    print(json.dumps({"status": "terminal", "tasks": 8, "model_calls": 8}, indent=2))


def aggregate(rows: list[dict[str, Any]], idle: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    def summary(subset: list[dict[str, Any]]) -> dict[str, Any]:
        latencies = [row["wall_elapsed_ms"] for row in subset]; energies = [row["power_summary"]["gross_energy_joules"] for row in subset]; ordered = sorted(latencies)
        return {"count": len(subset), "parse_valid": sum(row["raw_parse_valid"] for row in subset), "contract_valid": sum(row["contract_valid"] for row in subset), "field_correct": {field: sum(row["field_correct"][field] for row in subset) for field in FIELDS}, "all_relations_correct": sum(row["all_relations_correct"] for row in subset), "selected_operation_correct": sum(row.get("selected_correct", False) for row in subset), "evaluable": sum(row["evaluable"] for row in subset), "unevaluable": sum(not row["evaluable"] and not row["ambiguous"] for row in subset), "ambiguous": sum(row["ambiguous"] for row in subset), "secondary_action_selections": sum(row.get("selected_operation") is not None and norm(row["selected_operation"]) == norm(row["secondary_action"]) for row in subset), "latency_ms": {"median": statistics.median(latencies), "mean": statistics.mean(latencies), "p95": ordered[min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))]}, "energy_joules": {"mean_per_action": statistics.mean(energies), "median_per_action": statistics.median(energies), "total": sum(energies)}}
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_pair.setdefault(row["pair_id"], []).append(row)
    pair_results = {}
    for pair_id, pair_rows in by_pair.items():
        correct = [row.get("selected_correct", False) for row in pair_rows]
        observed = [row.get("selected_operation") for row in pair_rows]
        if all(correct): classification = "BOTH_RELATIONS_CORRECT"
        elif any(correct): classification = "ONE_DIRECTION_CORRECT"
        elif observed[0] is not None and observed[0] == observed[1] == pair_rows[0]["secondary_action"]: classification = "BOTH_SELECT_SECONDARY_ACTION"
        elif observed[0] is not None and observed[0] == observed[1]: classification = "BOTH_SELECT_SAME_VERB"
        else: classification = "OTHER"
        pair_results[pair_id] = {"classification": classification, "tasks": [row["task_id"] for row in pair_rows], "selected_operations": observed, "selected_correct": correct}
    return {"schema": "zth_qwen3_1_7b_action_object_relation_aggregate_v1", "exploratory_not_confirmatory": True, "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA}, "task_count": len(rows), "parse_valid": sum(row["raw_parse_valid"] for row in rows), "contract_valid": sum(row["contract_valid"] for row in rows), "all_relations_correct": sum(row["all_relations_correct"] for row in rows), "selected_operation_correct": sum(row.get("selected_correct", False) for row in rows), "evaluable": sum(row["evaluable"] for row in rows), "unevaluable": sum(not row["evaluable"] and not row["ambiguous"] for row in rows), "ambiguous": sum(row["ambiguous"] for row in rows), "secondary_action_selections": sum(row.get("selected_operation") is not None and norm(row["selected_operation"]) == norm(row["secondary_action"]) for row in rows), "fields": {field: sum(row["field_correct"][field] for row in rows) for field in FIELDS}, "classification_counts": {name: sum(row["failure_class"] == name for row in rows) for name in ("RELATIONS_CORRECT_SELECTION_CORRECT", "RELATION_EXTRACTION_ERROR_SELECTION_STILL_CORRECT", "RELATION_EXTRACTION_ERROR_SELECTION_INCORRECT", "RELATION_EXTRACTION_ERROR_SELECTION_UNEVALUABLE", "INVALID_EXTRACTION_CONTRACT", "SERIALIZATION_FAILURE")}, "by_expected_position": {position: summary([row for row in rows if row["expected_selected_position"] == position]) for position in ("first", "second")}, "by_selected_action_position": {position: summary([row for row in rows if row["expected_selected_position"] == position]) for position in ("first", "second")}, "by_pair": pair_results, "execution": {"supplier_model_calls": 8, "teacher_calls": 0, "retries": 0, "escalations": 0}, "idle_power": idle, "context_limit_non_binding_for_probe": True, "manifest_sha256": sha_file(Path(manifest.get("path", "probe_manifest.json"))) if manifest.get("path") else None}


def main() -> int:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); parser.add_argument("--output-dir", type=Path, required=True); args = parser.parse_args()
    (prepare if args.prepare else execute)(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
