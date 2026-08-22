#!/usr/bin/env python3
"""Fresh six-field relation-object IR extraction probe."""

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
from scripts.zth_relation_object_ir import select_direct_target

ROOT = base.ROOT
TASKS = ROOT / "docs/research/RELATION_OBJECT_IR_EXTRACTION_TASKS_2026-08-22.json"
FIELDS = ("action_1", "direct_object_1", "reference_entity_1", "action_2", "direct_object_2", "reference_entity_2")
SCHEMA_NAME = "relation_object_ir_extraction"
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
    return f"Request sentence:\n{task['sentence']}\n\nExtract the two factual action/object/reference relations expressed in the sentence, in sentence order. For each relation, provide the action, the direct object, and any separate reference entity; use an empty string when no separate reference entity is expressed. Return only the required structured fields.\n/no_think"


def validate_model_free() -> dict[str, Any]:
    payload = json.loads(TASKS.read_text(encoding="utf-8"))
    tasks = payload.get("tasks", [])
    if len(tasks) != 8 or len({task["task_id"] for task in tasks}) != 8:
        raise RuntimeError("fresh relation task count or IDs invalid")
    pairs: dict[str, list[dict[str, Any]]] = {}
    all_actions: set[str] = set()
    for task in tasks:
        if len({task["action_1"], task["action_2"]}) != 2:
            raise RuntimeError(f"two-action requirement failed: {task['task_id']}")
        if sum(task[field] == task["requested_target"] for field in ("direct_object_1", "direct_object_2")) != 1:
            raise RuntimeError(f"direct target binding is not unique: {task['task_id']}")
        position_action = task["action_1"] if task["expected_selected_relation_position"] == "first" else task["action_2"]
        if position_action != task["expected_selected_operation"]:
            raise RuntimeError(f"expected operation/position mismatch: {task['task_id']}")
        for field in FIELDS:
            if not isinstance(task.get(field), str):
                raise RuntimeError(f"non-string expected field: {task['task_id']} {field}")
        all_actions.update((task["action_1"], task["action_2"]))
        pairs.setdefault(task["pair_id"], []).append(task)
    if len(pairs) != 4 or any(len(rows) != 2 for rows in pairs.values()):
        raise RuntimeError("pair balance failed")
    for pair_id, rows in pairs.items():
        if rows[0]["requested_target"] != rows[1]["requested_target"] or {rows[0]["action_1"], rows[0]["action_2"]} != {rows[1]["action_1"], rows[1]["action_2"]}:
            raise RuntimeError(f"pair target/action mismatch: {pair_id}")
        if {row["expected_selected_operation"] for row in rows} != {rows[0]["action_1"], rows[0]["action_2"]}:
            raise RuntimeError(f"pair does not reverse target-bound action: {pair_id}")
        if {row["expected_selected_relation_position"] for row in rows} != {"first", "second"}:
            raise RuntimeError(f"pair does not reverse relation position: {pair_id}")
    if sum(task["expected_selected_relation_position"] == "first" for task in tasks) != 4 or sum(task["expected_selected_relation_position"] == "second" for task in tasks) != 4:
        raise RuntimeError("target-bound relation position imbalance")
    for action in all_actions:
        rows = [task for task in tasks if action in {task["action_1"], task["action_2"]}]
        if {task["expected_selected_operation"] == action for task in rows} != {True, False}:
            raise RuntimeError(f"action identity shortcut: {action}")
    for field in ("action_1", "action_2"):
        if {task["expected_selected_operation"] == task[field] for task in tasks} != {True, False}:
            raise RuntimeError(f"{field} shortcut")
    if {task["target_surface_profile"] for task in tasks} != {"start_and_later", "middle_and_end"}:
        raise RuntimeError("target surface placement did not vary")
    empty_ref_selected = [task["reference_entity_1"] == "" or task["reference_entity_2"] == "" for task in tasks]
    selected_position = [task["expected_selected_relation_position"] == "first" for task in tasks]
    if empty_ref_selected == selected_position or empty_ref_selected == [not value for value in selected_position]:
        raise RuntimeError("empty reference presence is a perfect shortcut")
    prompts = {task["task_id"]: prompt_for(task) for task in tasks}
    prompt_text = " ".join(prompts.values()).casefold()
    for forbidden in ("authorization", "scope", "membership", "policy", "allowed", "review", "routing", "escalation"):
        if forbidden in prompt_text:
            raise RuntimeError(f"forbidden prompt term: {forbidden}")
    encoded_schema = json.dumps(schema(), sort_keys=True)
    if any(token in encoded_schema for token in ('"enum"', '"example"', '"examples"', '"default"', '"const"')):
        raise RuntimeError("schema answer cue")
    max_prompt_chars = max(len(prompt) for prompt in prompts.values())
    if max_prompt_chars + MAX_OUTPUT_TOKENS >= EXPECTED_CTX:
        raise RuntimeError("context bound is not non-binding")
    return {"payload": payload, "tasks": tasks, "pairs": pairs, "prompts": prompts, "schema": schema(), "format": response_format(), "task_sha256": sha_file(TASKS), "schema_sha256": sha_bytes(canonical(schema())), "format_sha256": sha_bytes(canonical(response_format())), "prompt_sha256": {task_id: sha_bytes(prompt.encode()) for task_id, prompt in prompts.items()}, "max_prompt_chars": max_prompt_chars, "context_bound": max_prompt_chars + MAX_OUTPUT_TOKENS}


def parse_raw(raw: str) -> tuple[dict[str, Any] | None, bool, bool, list[str]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    valid = isinstance(parsed, dict) and set(parsed) == set(FIELDS) and all(isinstance(parsed.get(field), str) for field in FIELDS)
    return (parsed if valid else None), True, valid, ([] if valid else ["exact six-string contract failed"])


def relation_rows(parsed: dict[str, Any] | None) -> list[dict[str, str]] | None:
    if parsed is None:
        return None
    return [{"action": parsed["action_1"], "direct_object": parsed["direct_object_1"], "reference_entity": parsed["reference_entity_1"]}, {"action": parsed["action_2"], "direct_object": parsed["direct_object_2"], "reference_entity": parsed["reference_entity_2"]}]


def binding_failure(parsed: dict[str, Any] | None, task: dict[str, Any], field_correct: dict[str, bool]) -> str | None:
    if parsed is None:
        return None
    errors = [field for field, correct in field_correct.items() if not correct]
    if len(errors) > 1:
        category = "MULTIPLE_IR_FIELD_FAILURES"
    elif errors and errors[0].startswith("action_"):
        category = "ACTION_EXTRACTION_FAILURE"
    elif errors and errors[0].startswith("direct_object_"):
        category = "DIRECT_OBJECT_EXTRACTION_FAILURE"
    elif errors:
        category = "REFERENCE_ENTITY_EXTRACTION_FAILURE"
    else:
        category = None
    for index in (1, 2):
        observed_direct = norm(parsed[f"direct_object_{index}"])
        target = norm(task["requested_target"])
        expected_direct = norm(task[f"direct_object_{index}"])
        expected_ref = norm(task[f"reference_entity_{index}"])
        if observed_direct == target and expected_direct != target:
            return "REFERENCE_ENTITY_SUBSTITUTED_FOR_DIRECT_OBJECT"
        if expected_direct != target and expected_ref and expected_ref in observed_direct and norm(task[f"direct_object_{index}"]) in observed_direct:
            return "DIRECT_OBJECT_PLUS_REFERENCE_ENTITY_CONFLATION"
    return category


def score(parsed: dict[str, Any] | None, parse_valid: bool, contract_valid: bool, task: dict[str, Any]) -> dict[str, Any]:
    if not contract_valid or parsed is None:
        return {"field_correct": {field: False for field in FIELDS}, "both_action_fields_correct": False, "both_direct_object_fields_correct": False, "both_reference_entity_fields_correct": False, "all_six_fields_correct": False, "selected_correct": False, "evaluable": False, "no_direct_binding": False, "ambiguous_binding": False, "classification": "INVALID_EXTRACTION_CONTRACT" if parse_valid else "SERIALIZATION_FAILURE", "binding_failure": None}
    field_correct = {field: norm(parsed[field]) == norm(task[field]) for field in FIELDS}
    selected = select_direct_target(relation_rows(parsed) or [], task["requested_target"])
    selected_correct = selected["selected_operation"] is not None and norm(selected["selected_operation"]) == norm(task["expected_selected_operation"])
    if all(field_correct.values()) and selected_correct:
        classification = "IR_EXACT_SELECTION_CORRECT"
    elif selected_correct:
        classification = "IR_ERROR_SELECTION_STILL_CORRECT"
    elif selected["classification"] != "DIRECT_TARGET_BINDING":
        classification = "IR_ERROR_SELECTION_UNEVALUABLE"
    else:
        classification = "IR_ERROR_SELECTION_INCORRECT"
    return {"field_correct": field_correct, "both_action_fields_correct": field_correct["action_1"] and field_correct["action_2"], "both_direct_object_fields_correct": field_correct["direct_object_1"] and field_correct["direct_object_2"], "both_reference_entity_fields_correct": field_correct["reference_entity_1"] and field_correct["reference_entity_2"], "all_six_fields_correct": all(field_correct.values()), "selected_correct": selected_correct, "evaluable": selected["classification"] == "DIRECT_TARGET_BINDING", "no_direct_binding": selected["classification"] == "NO_DIRECT_TARGET_BINDING", "ambiguous_binding": selected["classification"] == "AMBIGUOUS_DIRECT_TARGET_BINDING", "selected_operation": selected["selected_operation"], "selected_index": selected["selected_index"], "classification": classification, "binding_failure": binding_failure(parsed, task, field_correct)}


def prepare(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("output directory must be fresh")
    output_dir.mkdir(parents=True, exist_ok=True)
    binding = validate_model_free()
    runtime_data = runtime.runtime_payload()
    for task in binding["tasks"]:
        task_dir = output_dir / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "prompt.txt").write_text(binding["prompts"][task["task_id"]], encoding="utf-8")
        write_json(task_dir / "fixture.snapshot.json", task)
    write_json(output_dir / "schema_relation_object_ir.json", binding["schema"])
    write_json(output_dir / "response_format_relation_object_ir.json", binding["format"])
    manifest = {"schema":"zth_qwen3_1_7b_relation_object_ir_extraction_manifest_v1","status":"prepared_exploratory_not_confirmatory","prepared_at":now(),"prepared_from_git_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"driver":str(Path(__file__).relative_to(ROOT)),"driver_sha256":sha_file(Path(__file__).resolve()),"task_manifest_sha256":binding["task_sha256"],"task_count":8,"pair_count":4,"task_order":[task["task_id"] for task in binding["tasks"]],"schema_sha256":binding["schema_sha256"],"response_format_sha256":binding["format_sha256"],"prompt_sha256":binding["prompt_sha256"],"expected_deterministic_selection":"8/8","no_perfect_surface_shortcut":True,"context_limit_non_binding":True,"runtime_freeze_sha256":sha_file(runtime.RUNTIME_FREEZE),"runtime":{"model_id":EXPECTED_MODEL_ID,"artifact_sha256":EXPECTED_MODEL_SHA,"operative_parameters":EXPECTED_PARAMS,"effective_n_ctx":EXPECTED_CTX,"n_ctx_train":EXPECTED_TRAIN_CTX},"telemetry":{"measurement_level":2,"measurement_boundary":"gpu_device_only","sample_interval_seconds":POWER_INTERVAL_SECONDS},"hardware":{"gpu_uuid":EXPECTED_GPU_UUID,"v100_touched":False},"execution_policy":{"supplier_model_calls":8,"teacher_calls":0,"retries":0,"escalations":0,"adaptation":0},"model_calls_made":False,"runtime_metadata":runtime_data["runtime"]}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest,"manifest_sha256":None}))
    write_json(output_dir / "probe_manifest.json",manifest)
    write_json(output_dir / "lifecycle.json",{"status":"prepared","model_calls_made":False,"updated_at":now()})
    print(json.dumps({"status":"prepared","tasks":8,"pairs":4,"expected_selection":"8/8","model_calls":0},indent=2))


def execute(output_dir: Path) -> None:
    manifest = json.loads((output_dir / "probe_manifest.json").read_text())
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest,"manifest_sha256":None})):
        raise RuntimeError("manifest hash mismatch")
    binding = validate_model_free()
    if manifest["task_manifest_sha256"] != binding["task_sha256"] or manifest["prompt_sha256"] != binding["prompt_sha256"]:
        raise RuntimeError("fresh relation binding drift")
    spec = runtime.worker_spec()
    models = list_models(spec, timeout=30)
    candidate = next((item for item in models.get("data",[]) if item.get("id") == EXPECTED_MODEL_ID),None)
    meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
        raise RuntimeError("runtime binding mismatch")
    telemetry_url = base.telemetry_base_url()
    telemetry = base.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = base.sample_window(IDLE_SECONDS,telemetry_url)
    write_json(output_dir / "preflight.json",{"schema":"zth_qwen3_1_7b_relation_object_ir_extraction_execution_v1","prepared_manifest_sha256":sha_file(output_dir / "probe_manifest.json"),"model_meta":meta,"telemetry":telemetry,"task_manifest_sha256":binding["task_sha256"],"execution_policy":manifest["execution_policy"]})
    write_json(output_dir / "idle_power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","summary":idle_summary,"samples":idle_samples})
    write_json(output_dir / "lifecycle.json",{"status":"running","started_at":now(),"model_calls_made":False})
    rows=[]
    for task in binding["tasks"]:
        task_dir=output_dir / "tasks" / task["task_id"]
        sampler=PowerSampler(lambda:read_gpu_power(EXPECTED_GPU_UUID,base_url=telemetry_url),expected_gpu_uuid=EXPECTED_GPU_UUID,sample_interval_seconds=POWER_INTERVAL_SECONDS)
        started=time.monotonic(); started_at=now(); sampler.start()
        response=decomposition.structured_call(spec,(task_dir/"prompt.txt").read_text(),binding["format"],MAX_OUTPUT_TOKENS,TIMEOUT_SECONDS)
        captured=time.monotonic(); samples=sampler.stop(); energy=integrate_energy_joules(samples,sample_interval_seconds=POWER_INTERVAL_SECONDS,expected_gpu_uuid=EXPECTED_GPU_UUID)
        metadata=response.metadata(); metadata["request_url"]=None
        raw={"status":response.status,"content":response.content,"metadata":metadata,"request_started_at":started_at,"response_captured_at":now(),"wall_elapsed_ms":round((captured-started)*1000,3)}
        write_json(task_dir/"response.json",raw)
        transport_valid=metadata.get("transport_classification")=="model_response"
        parsed,parse_valid,contract_valid,diagnostics=parse_raw(response.content) if transport_valid else (None,False,False,["transport failure"])
        scored=score(parsed,parse_valid,contract_valid,task)
        write_json(task_dir/"validation.json",{"validation_status":"passed" if transport_valid and contract_valid else "failed","parse_valid":parse_valid,"contract_valid":contract_valid,"diagnostics":diagnostics,"task_id":task["task_id"]})
        write_json(task_dir/"power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","gpu_uuid":EXPECTED_GPU_UUID,"samples":[{"timestamp_utc":s.timestamp_utc,"monotonic_seconds":s.monotonic_seconds,"gpu_uuid":s.gpu_uuid,"power_watts":s.power_watts,"sequence":s.sequence} for s in samples]})
        scorecard={"schema":"zth_qwen3_1_7b_relation_object_ir_extraction_task_scorecard_v1","task_id":task["task_id"],"pair_id":task["pair_id"],"requested_target":task["requested_target"],"expected_fields":{field:task[field] for field in FIELDS},"expected_selected_operation":task["expected_selected_operation"],"expected_selected_relation_position":task["expected_selected_relation_position"],"transport_valid":transport_valid,"raw_parse_valid":parse_valid,"contract_valid":contract_valid,"observed_fields":parsed,**scored,"wall_elapsed_ms":raw["wall_elapsed_ms"],"prompt_tokens":(metadata.get("usage") or {}).get("prompt_tokens"),"completion_tokens":(metadata.get("usage") or {}).get("completion_tokens"),"power_summary":{"sample_count":len(samples),"mean_active_watts":statistics.mean(s.power_watts for s in samples),"peak_observed_watts":max(s.power_watts for s in samples),"gross_energy_joules":energy},"retry_count":0,"escalation_count":0,"teacher_calls":0}
        write_json(task_dir/"scorecard.json",scorecard); rows.append(scorecard)
    write_json(output_dir/"aggregate.json",aggregate(rows,idle_summary))
    write_json(output_dir/"lifecycle.json",{"status":"terminal","completed_at":now(),"model_calls_made":True,"supplier_model_calls":8,"unique_called_tasks":8,"duplicate_called_tasks":0,"teacher_calls":0,"retries":0,"escalations":0})
    print(json.dumps({"status":"terminal","tasks":8,"model_calls":8},indent=2))


def aggregate(rows: list[dict[str,Any]], idle: dict[str,Any]) -> dict[str,Any]:
    lat=[r["wall_elapsed_ms"] for r in rows]; energy=[r["power_summary"]["gross_energy_joules"] for r in rows]; ordered=sorted(lat)
    pairs={}
    for row in rows: pairs.setdefault(row["pair_id"],[]).append(row)
    pair_metrics={}
    for pair_id,pair_rows in pairs.items():
        pair_metrics[pair_id]={"selected_operation_both_correct":all(r["selected_correct"] for r in pair_rows),"all_six_fields_both_exact":all(r["all_six_fields_correct"] for r in pair_rows),"tasks":[r["task_id"] for r in pair_rows]}
    return {"schema":"zth_qwen3_1_7b_relation_object_ir_extraction_aggregate_v1","exploratory_not_confirmatory":True,"candidate":{"model_id":EXPECTED_MODEL_ID,"operative_parameters":EXPECTED_PARAMS,"artifact_sha256":EXPECTED_MODEL_SHA},"task_count":len(rows),"parse_valid":sum(r["raw_parse_valid"] for r in rows),"contract_valid":sum(r["contract_valid"] for r in rows),"fields_correct":{field:sum(r["field_correct"][field] for r in rows) for field in FIELDS},"both_action_fields_correct":sum(r["both_action_fields_correct"] for r in rows),"both_direct_object_fields_correct":sum(r["both_direct_object_fields_correct"] for r in rows),"both_reference_entity_fields_correct":sum(r["both_reference_entity_fields_correct"] for r in rows),"all_six_fields_correct":sum(r["all_six_fields_correct"] for r in rows),"selected_operation_correct":sum(r["selected_correct"] for r in rows),"evaluable":sum(r["evaluable"] for r in rows),"no_direct_binding":sum(r["no_direct_binding"] for r in rows),"ambiguous_binding":sum(r["ambiguous_binding"] for r in rows),"classification_counts":{name:sum(r["classification"]==name for r in rows) for name in ("IR_EXACT_SELECTION_CORRECT","IR_ERROR_SELECTION_STILL_CORRECT","IR_ERROR_SELECTION_INCORRECT","IR_ERROR_SELECTION_UNEVALUABLE","INVALID_EXTRACTION_CONTRACT","SERIALIZATION_FAILURE")},"binding_failure_counts":{name:sum(r["binding_failure"]==name for r in rows) for name in ("ACTION_EXTRACTION_FAILURE","DIRECT_OBJECT_EXTRACTION_FAILURE","REFERENCE_ENTITY_EXTRACTION_FAILURE","MULTIPLE_IR_FIELD_FAILURES","REFERENCE_ENTITY_SUBSTITUTED_FOR_DIRECT_OBJECT","DIRECT_OBJECT_PLUS_REFERENCE_ENTITY_CONFLATION","TARGET_BOUND_RELATION_MISIDENTIFIED","OTHER")},"pair_metrics":pair_metrics,"latency_ms":{"median":statistics.median(lat),"mean":statistics.mean(lat),"p95":ordered[min(len(ordered)-1,round((len(ordered)-1)*.95))]},"energy_joules":{"mean_per_action":statistics.mean(energy),"median_per_action":statistics.median(energy),"total":sum(energy),"j_per_correct_six_field":sum(energy)/sum(r["all_six_fields_correct"] for r in rows) if sum(r["all_six_fields_correct"] for r in rows) else None,"j_per_correct_selected_operation":sum(energy)/sum(r["selected_correct"] for r in rows) if sum(r["selected_correct"] for r in rows) else None},"idle_power":idle,"execution":{"supplier_model_calls":8,"teacher_calls":0,"retries":0,"escalations":0,"adaptations":0}}


def main() -> int:
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare",action="store_true"); group.add_argument("--execute",action="store_true"); parser.add_argument("--output-dir",type=Path,required=True); args=parser.parse_args(); (prepare if args.prepare else execute)(args.output_dir); return 0


if __name__ == "__main__":
    raise SystemExit(main())
