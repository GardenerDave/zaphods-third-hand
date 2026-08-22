#!/usr/bin/env python3
"""Fresh single-relation extraction probe."""

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
TASKS = ROOT / "docs/research/SINGLE_RELATION_EXTRACTION_TASKS_2026-08-22.json"
FIELDS = ("action", "direct_object", "reference_entity")
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
    return {"type":"object","properties":{field:{"type":"string"} for field in FIELDS},"required":list(FIELDS),"additionalProperties":False}


def response_format() -> dict[str, Any]:
    return {"type":"json_schema","json_schema":{"name":"single_relation_extraction","schema":schema()}}


def prompt_for(task: dict[str, Any]) -> str:
    return f"Request clause:\n{task['sentence']}\n\nExtract the factual relation expressed by the clause. The action is the expressed operation. The direct_object is the thing directly acted upon. The reference_entity is a separately named entity that the direct object belongs to, comes from, describes, is contained by, or is anchored to. Use an empty string if no separate reference entity is expressed. Return only the required structured fields.\n/no_think"


def validate_model_free() -> dict[str, Any]:
    payload=json.loads(TASKS.read_text())
    tasks=payload.get("tasks",[])
    if len(tasks)!=8 or len({t["task_id"] for t in tasks})!=8:
        raise RuntimeError("single-relation task count/IDs invalid")
    if sum(t["semantic_regime"]=="DIRECT_ENTITY_OBJECT" for t in tasks)!=4 or sum(t["semantic_regime"]=="SUBOBJECT_WITH_REFERENCE" for t in tasks)!=4:
        raise RuntimeError("single-relation regime balance invalid")
    verbs={t["action_verb"] for t in tasks}
    for verb in verbs:
        rows=[t for t in tasks if t["action_verb"]==verb]
        if {t["semantic_regime"] for t in rows}!={"DIRECT_ENTITY_OBJECT","SUBOBJECT_WITH_REFERENCE"}:
            raise RuntimeError(f"action predicts regime: {verb}")
        if any(t["expected_action"]!=verb for t in rows):
            raise RuntimeError(f"expected action mismatch: {verb}")
    for t in tasks:
        if t["semantic_regime"]=="DIRECT_ENTITY_OBJECT" and t["expected_reference_entity"]!="":
            raise RuntimeError(f"direct regime reference must be empty: {t['task_id']}")
        if t["semantic_regime"]=="SUBOBJECT_WITH_REFERENCE" and not t["expected_reference_entity"]:
            raise RuntimeError(f"subobject regime reference missing: {t['task_id']}")
        if not all(isinstance(t[f"expected_{field}"],str) for field in FIELDS):
            raise RuntimeError(f"non-string expected field: {t['task_id']}")
    prompts={t["task_id"]:prompt_for(t) for t in tasks}
    prompt_text=" ".join(prompts.values()).casefold()
    for forbidden in ("authorization","scope","membership","policy","allowed","review","routing","escalation"):
        if forbidden in prompt_text:
            raise RuntimeError(f"forbidden prompt term: {forbidden}")
    encoded=json.dumps(schema(),sort_keys=True)
    if any(token in encoded for token in ('"enum"','"example"','"examples"','"default"','"const"')):
        raise RuntimeError("schema answer cue")
    max_prompt_chars=max(len(p) for p in prompts.values())
    if max_prompt_chars+MAX_OUTPUT_TOKENS>=EXPECTED_CTX:
        raise RuntimeError("context bound is not non-binding")
    return {"payload":payload,"tasks":tasks,"prompts":prompts,"schema":schema(),"format":response_format(),"task_sha256":sha_file(TASKS),"schema_sha256":sha_bytes(canonical(schema())),"format_sha256":sha_bytes(canonical(response_format())),"prompt_sha256":{tid:sha_bytes(p.encode()) for tid,p in prompts.items()},"max_prompt_chars":max_prompt_chars}


def parse_raw(raw: str) -> tuple[dict[str,Any]|None,bool,bool,list[str]]:
    try: parsed=json.loads(raw)
    except json.JSONDecodeError as exc: return None,False,False,[str(exc)]
    valid=isinstance(parsed,dict) and set(parsed)==set(FIELDS) and all(isinstance(parsed.get(field),str) for field in FIELDS)
    return (parsed if valid else None),True,valid,([] if valid else ["exact three-string contract failed"])


def score(parsed: dict[str,Any]|None, parse_valid: bool, contract_valid: bool, task: dict[str,Any]) -> dict[str,Any]:
    if not contract_valid or parsed is None:
        return {"field_correct":{field:False for field in FIELDS},"all_three_fields_correct":False,"classification":"INVALID_CONTRACT" if parse_valid else "SERIALIZATION_FAILURE","reference_entity_substituted_for_direct_object":False}
    field_correct={field:norm(parsed[field])==norm(task[f"expected_{field}"]) for field in FIELDS}
    if all(field_correct.values()): classification="SINGLE_RELATION_EXACT"
    elif sum(field_correct.values())==1: classification="MULTIPLE_SINGLE_RELATION_FIELDS_FAILED"
    elif not field_correct["action"]: classification="ACTION_EXTRACTION_FAILURE"
    elif not field_correct["direct_object"]: classification="DIRECT_OBJECT_EXTRACTION_FAILURE"
    else: classification="REFERENCE_ENTITY_EXTRACTION_FAILURE"
    substituted=(not field_correct["direct_object"] and norm(parsed["direct_object"])==norm(task["expected_reference_entity"]) and bool(task["expected_reference_entity"]))
    return {"field_correct":field_correct,"all_three_fields_correct":all(field_correct.values()),"classification":classification,"reference_entity_substituted_for_direct_object":substituted}


def prepare(output_dir:Path)->None:
    if output_dir.exists() and any(output_dir.iterdir()): raise RuntimeError("output directory must be fresh")
    output_dir.mkdir(parents=True,exist_ok=True); binding=validate_model_free(); runtime_data=runtime.runtime_payload()
    for task in binding["tasks"]:
        d=output_dir/"tasks"/task["task_id"]; d.mkdir(parents=True,exist_ok=True); (d/"prompt.txt").write_text(binding["prompts"][task["task_id"]]); write_json(d/"fixture.snapshot.json",task)
    write_json(output_dir/"schema_single_relation.json",binding["schema"]); write_json(output_dir/"response_format_single_relation.json",binding["format"])
    manifest={"schema":"zth_qwen3_1_7b_single_relation_extraction_manifest_v1","status":"prepared_exploratory_not_confirmatory","prepared_at":now(),"prepared_from_git_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"driver":str(Path(__file__).relative_to(ROOT)),"driver_sha256":sha_file(Path(__file__).resolve()),"task_manifest_sha256":binding["task_sha256"],"task_count":8,"direct_entity_object_count":4,"subobject_with_reference_count":4,"task_order":[t["task_id"] for t in binding["tasks"]],"schema_sha256":binding["schema_sha256"],"response_format_sha256":binding["format_sha256"],"prompt_sha256":binding["prompt_sha256"],"context_limit_non_binding":True,"runtime_freeze_sha256":sha_file(runtime.RUNTIME_FREEZE),"runtime":{"model_id":EXPECTED_MODEL_ID,"artifact_sha256":EXPECTED_MODEL_SHA,"operative_parameters":EXPECTED_PARAMS,"effective_n_ctx":EXPECTED_CTX,"n_ctx_train":EXPECTED_TRAIN_CTX},"telemetry":{"measurement_level":2,"measurement_boundary":"gpu_device_only","sample_interval_seconds":POWER_INTERVAL_SECONDS},"hardware":{"gpu_uuid":EXPECTED_GPU_UUID,"v100_touched":False},"execution_policy":{"supplier_model_calls":8,"teacher_calls":0,"retries":0,"escalations":0,"adaptation":0},"model_calls_made":False,"runtime_metadata":runtime_data["runtime"]}
    manifest["manifest_sha256"]=sha_bytes(canonical({**manifest,"manifest_sha256":None})); write_json(output_dir/"probe_manifest.json",manifest); write_json(output_dir/"lifecycle.json",{"status":"prepared","model_calls_made":False,"updated_at":now()}); print(json.dumps({"status":"prepared","tasks":8,"model_calls":0},indent=2))


def make_scorecard(task:dict[str,Any], raw:dict[str,Any], transport:bool, parsed:dict[str,Any]|None, parse_valid:bool, contract_valid:bool, diagnostics:list[str], power_summary:dict[str,Any]|None, recovered:bool=False)->dict[str,Any]:
    scored=score(parsed,parse_valid,contract_valid,task)
    return {"schema":"zth_qwen3_1_7b_single_relation_task_scorecard_v1","task_id":task["task_id"],"semantic_regime":task["semantic_regime"],"expected_fields":{field:task[f"expected_{field}"] for field in FIELDS},"transport_valid":transport,"raw_parse_valid":parse_valid,"contract_valid":contract_valid,"observed_fields":parsed,**scored,"wall_elapsed_ms":raw.get("wall_elapsed_ms"),"prompt_tokens":(raw.get("metadata") or {}).get("usage",{}).get("prompt_tokens"),"completion_tokens":(raw.get("metadata") or {}).get("usage",{}).get("completion_tokens"),"power_summary":power_summary,"recovered_from_existing_response":recovered,"diagnostics":diagnostics,"retry_count":0,"escalation_count":0,"teacher_calls":0}


def execute(output_dir:Path)->None:
    manifest=json.loads((output_dir/"probe_manifest.json").read_text())
    if manifest["manifest_sha256"]!=sha_bytes(canonical({**manifest,"manifest_sha256":None})): raise RuntimeError("manifest hash mismatch")
    binding=validate_model_free()
    if manifest["task_manifest_sha256"]!=binding["task_sha256"] or manifest["prompt_sha256"]!=binding["prompt_sha256"]: raise RuntimeError("binding drift")
    spec=runtime.worker_spec(); models=list_models(spec,timeout=30); candidate=next((x for x in models.get("data",[]) if x.get("id")==EXPECTED_MODEL_ID),None); meta=(candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params")!=EXPECTED_PARAMS or meta.get("n_ctx")!=EXPECTED_CTX or meta.get("n_ctx_train")!=EXPECTED_TRAIN_CTX: raise RuntimeError("runtime binding mismatch")
    telemetry_url=base.telemetry_base_url(); telemetry=base.telemetry_preflight(telemetry_url); idle_samples,idle_summary=base.sample_window(IDLE_SECONDS,telemetry_url)
    write_json(output_dir/"preflight.json",{"schema":"zth_qwen3_1_7b_single_relation_extraction_execution_v1","prepared_manifest_sha256":sha_file(output_dir/"probe_manifest.json"),"model_meta":meta,"telemetry":telemetry,"task_manifest_sha256":binding["task_sha256"],"execution_policy":manifest["execution_policy"]}); write_json(output_dir/"idle_power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","summary":idle_summary,"samples":idle_samples}); write_json(output_dir/"lifecycle.json",{"status":"running","started_at":now(),"model_calls_made":False})
    existing=[task["task_id"] for task in binding["tasks"] if (output_dir/"tasks"/task["task_id"]/"response.json").exists()]
    if existing:
        write_json(output_dir/"recovery_state.json",{"schema":"zth_single_relation_extraction_recovery_v1","recovery_reason":"scorer_crash_after_response_capture","called_task_ids":existing,"uncalled_task_ids":[task["task_id"] for task in binding["tasks"] if task["task_id"] not in existing],"response_hashes":{tid:sha_file(output_dir/"tasks"/tid/"response.json") for tid in existing},"supplier_calls_already_made":len(existing),"replayed_calls":0,"teacher_calls":0,"retries":0,"escalations":0,"failure":"expected-field lookup defect in scorer","raw_responses_modified":False})
    rows=[]
    for task in binding["tasks"]:
        d=output_dir/"tasks"/task["task_id"]
        if (d/"response.json").exists():
            raw=json.loads((d/"response.json").read_text()); metadata=raw.get("metadata") or {}; transport=metadata.get("transport_classification")=="model_response"; parsed,parse_valid,contract_valid,diagnostics=parse_raw(raw.get("content", "")) if transport else (None,False,False,["transport failure"]); write_json(d/"validation.json",{"validation_status":"passed" if transport and contract_valid else "failed","parse_valid":parse_valid,"contract_valid":contract_valid,"diagnostics":diagnostics,"task_id":task["task_id"],"recovered_model_free":True})
            card=make_scorecard(task,raw,transport,parsed,parse_valid,contract_valid,diagnostics,None,recovered=True); write_json(d/"scorecard.json",card); rows.append(card); continue
        sampler=PowerSampler(lambda:read_gpu_power(EXPECTED_GPU_UUID,base_url=telemetry_url),expected_gpu_uuid=EXPECTED_GPU_UUID,sample_interval_seconds=POWER_INTERVAL_SECONDS); started=time.monotonic(); started_at=now(); sampler.start(); response=decomposition.structured_call(spec,(d/"prompt.txt").read_text(),binding["format"],MAX_OUTPUT_TOKENS,TIMEOUT_SECONDS); captured=time.monotonic(); samples=sampler.stop(); energy=integrate_energy_joules(samples,sample_interval_seconds=POWER_INTERVAL_SECONDS,expected_gpu_uuid=EXPECTED_GPU_UUID); metadata=response.metadata(); metadata["request_url"]=None; raw={"status":response.status,"content":response.content,"metadata":metadata,"request_started_at":started_at,"response_captured_at":now(),"wall_elapsed_ms":round((captured-started)*1000,3)}; write_json(d/"response.json",raw); transport=metadata.get("transport_classification")=="model_response"; parsed,parse_valid,contract_valid,diagnostics=parse_raw(response.content) if transport else (None,False,False,["transport failure"]); write_json(d/"validation.json",{"validation_status":"passed" if transport and contract_valid else "failed","parse_valid":parse_valid,"contract_valid":contract_valid,"diagnostics":diagnostics,"task_id":task["task_id"]}); write_json(d/"power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","gpu_uuid":EXPECTED_GPU_UUID,"samples":[{"timestamp_utc":s.timestamp_utc,"monotonic_seconds":s.monotonic_seconds,"gpu_uuid":s.gpu_uuid,"power_watts":s.power_watts,"sequence":s.sequence} for s in samples]}); card=make_scorecard(task,raw,transport,parsed,parse_valid,contract_valid,diagnostics,{"sample_count":len(samples),"mean_active_watts":statistics.mean(s.power_watts for s in samples),"peak_observed_watts":max(s.power_watts for s in samples),"gross_energy_joules":energy}); write_json(d/"scorecard.json",card); rows.append(card)
    write_json(output_dir/"aggregate.json",aggregate(rows,idle_summary)); write_json(output_dir/"lifecycle.json",{"status":"terminal","completed_at":now(),"model_calls_made":True,"supplier_model_calls":8,"unique_called_tasks":8,"duplicate_called_tasks":0,"recovered_existing_responses":len(existing),"teacher_calls":0,"retries":0,"escalations":0}); print(json.dumps({"status":"terminal","tasks":8,"model_calls":8,"recovered_existing":len(existing)},indent=2))


def aggregate(rows:list[dict[str,Any]],idle:dict[str,Any])->dict[str,Any]:
    lat=[r["wall_elapsed_ms"] for r in rows]; energy=[r["power_summary"]["gross_energy_joules"] for r in rows if r.get("power_summary")]; ordered=sorted(lat)
    def regime(name):
        subset=[r for r in rows if r["semantic_regime"]==name]; return {"tasks":len(subset),"correct":{"action":sum(r["field_correct"]["action"] for r in subset),"direct_object":sum(r["field_correct"]["direct_object"] for r in subset),"reference_entity":sum(r["field_correct"]["reference_entity"] for r in subset),"all_three":sum(r["all_three_fields_correct"] for r in subset)},"classification_counts":{c:sum(r["classification"]==c for r in subset) for c in ("SINGLE_RELATION_EXACT","ACTION_EXTRACTION_FAILURE","DIRECT_OBJECT_EXTRACTION_FAILURE","REFERENCE_ENTITY_EXTRACTION_FAILURE","MULTIPLE_SINGLE_RELATION_FIELDS_FAILED","INVALID_CONTRACT","SERIALIZATION_FAILURE")}}
    energy_complete=len(energy)==len(rows)
    return {"schema":"zth_qwen3_1_7b_single_relation_extraction_aggregate_v1","exploratory_not_confirmatory":True,"candidate":{"model_id":EXPECTED_MODEL_ID,"operative_parameters":EXPECTED_PARAMS,"artifact_sha256":EXPECTED_MODEL_SHA},"task_count":len(rows),"parse_valid":sum(r["raw_parse_valid"] for r in rows),"contract_valid":sum(r["contract_valid"] for r in rows),"fields_correct":{field:sum(r["field_correct"][field] for r in rows) for field in FIELDS},"all_three_fields_correct":sum(r["all_three_fields_correct"] for r in rows),"reference_entity_substituted_for_direct_object":sum(r["reference_entity_substituted_for_direct_object"] for r in rows),"classification_counts":{c:sum(r["classification"]==c for r in rows) for c in ("SINGLE_RELATION_EXACT","ACTION_EXTRACTION_FAILURE","DIRECT_OBJECT_EXTRACTION_FAILURE","REFERENCE_ENTITY_EXTRACTION_FAILURE","MULTIPLE_SINGLE_RELATION_FIELDS_FAILED","INVALID_CONTRACT","SERIALIZATION_FAILURE")},"regimes":{"DIRECT_ENTITY_OBJECT":regime("DIRECT_ENTITY_OBJECT"),"SUBOBJECT_WITH_REFERENCE":regime("SUBOBJECT_WITH_REFERENCE")},"latency_ms":{"median":statistics.median(lat),"mean":statistics.mean(lat),"p95":ordered[min(len(ordered)-1,round((len(ordered)-1)*.95))]},"energy_joules":{"sampled_task_count":len(energy),"complete_for_all_tasks":energy_complete,"mean_per_sampled_action":statistics.mean(energy) if energy else None,"median_per_sampled_action":statistics.median(energy) if energy else None,"sampled_total":sum(energy),"j_per_correct_three_field":sum(energy)/sum(r["all_three_fields_correct"] for r in rows) if energy_complete and sum(r["all_three_fields_correct"] for r in rows) else None},"idle_power":idle,"execution":{"supplier_model_calls":8,"teacher_calls":0,"retries":0,"escalations":0,"adaptations":0}}


def main()->int:
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare",action="store_true"); group.add_argument("--execute",action="store_true"); parser.add_argument("--output-dir",type=Path,required=True); args=parser.parse_args(); (prepare if args.prepare else execute)(args.output_dir); return 0


if __name__=="__main__": raise SystemExit(main())
