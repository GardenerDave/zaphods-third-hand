#!/usr/bin/env python3
"""Fresh minimal action/direct-object extraction probe."""

from __future__ import annotations

import argparse, hashlib, json, statistics, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.icm_call import list_models
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT=base.ROOT
TASKS=ROOT/"docs/research/MINIMAL_ACTION_OBJECT_ATOM_TASKS_2026-08-22.json"
FIELDS=("action","direct_object")
EXPECTED_MODEL_ID=runtime.EXPECTED_MODEL_ID
EXPECTED_MODEL_SHA=runtime.EXPECTED_MODEL_SHA
EXPECTED_PARAMS=runtime.EXPECTED_PARAMS
EXPECTED_CTX=runtime.EXPECTED_EFFECTIVE_CTX
EXPECTED_TRAIN_CTX=runtime.EXPECTED_TRAIN_CTX
EXPECTED_GPU_UUID=runtime.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS=runtime.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS=runtime.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS=runtime.POWER_INTERVAL_SECONDS
IDLE_SECONDS=runtime.IDLE_SECONDS

def now(): return datetime.now(timezone.utc).isoformat()
def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def sha_bytes(v): return hashlib.sha256(v).hexdigest()
def sha_file(p): return sha_bytes(p.read_bytes())
def write_json(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
def norm(v): return " ".join(str(v).casefold().strip().split())
def schema(): return {"type":"object","properties":{f:{"type":"string"} for f in FIELDS},"required":list(FIELDS),"additionalProperties":False}
def response_format(): return {"type":"json_schema","json_schema":{"name":"minimal_action_object_atom","schema":schema()}}
def prompt_for(t): return f"Request clause:\n{t['sentence']}\n\nRequired structured fields describe the request clause.\n\naction:\nthe operation expressed in the request clause.\n\ndirect_object:\nthe thing directly acted upon by that operation.\n\n/no_think"

def validate_model_free():
    payload=json.loads(TASKS.read_text()); tasks=payload["tasks"]
    if len(tasks)!=8 or len({t["task_id"] for t in tasks})!=8: raise RuntimeError("task count/IDs invalid")
    if sum(t["semantic_regime"]=="DIRECT_ENTITY_OBJECT" for t in tasks)!=4 or sum(t["semantic_regime"]=="SUBOBJECT_WITH_REFERENCE" for t in tasks)!=4: raise RuntimeError("regime balance invalid")
    verbs={t["action_verb"] for t in tasks}
    for verb in verbs:
        rows=[t for t in tasks if t["action_verb"]==verb]
        if {t["semantic_regime"] for t in rows}!={"DIRECT_ENTITY_OBJECT","SUBOBJECT_WITH_REFERENCE"}: raise RuntimeError("action predicts regime")
    prompts={t["task_id"]:prompt_for(t) for t in tasks}; text=" ".join(prompts.values()).casefold()
    for forbidden in ("authorization","scope","membership","policy","allowed","routing","supplier","escalation","extract","return","report","record","identify"): 
        if forbidden in text: raise RuntimeError(f"forbidden prompt term: {forbidden}")
    encoded=json.dumps(schema(),sort_keys=True)
    if any(x in encoded for x in ('"enum"','"example"','"examples"','"default"','"const"')): raise RuntimeError("schema cue")
    return {"payload":payload,"tasks":tasks,"prompts":prompts,"schema":schema(),"format":response_format(),"task_sha256":sha_file(TASKS),"schema_sha256":sha_bytes(canonical(schema())),"format_sha256":sha_bytes(canonical(response_format())),"prompt_sha256":{k:sha_bytes(v.encode()) for k,v in prompts.items()}}

def parse_raw(raw):
    try: parsed=json.loads(raw)
    except json.JSONDecodeError as e: return None,False,False,[str(e)]
    valid=isinstance(parsed,dict) and set(parsed)==set(FIELDS) and all(isinstance(parsed.get(f),str) for f in FIELDS)
    return (parsed if valid else None),True,valid,([] if valid else ["exact two-string contract failed"])

def score(parsed,parse_valid,contract_valid,t):
    if not contract_valid or parsed is None: return {"field_correct":{f:False for f in FIELDS},"all_two_fields_correct":False,"mentioned_entity_substituted_for_direct_object":False,"instruction_verb_as_action":False,"classification":"INVALID_CONTRACT" if parse_valid else "SERIALIZATION_FAILURE"}
    fc={f:norm(parsed[f])==norm(t[f"expected_{f}"]) for f in FIELDS}
    instruction=norm(parsed["action"]) in {"extract","return","report","record","identify"}
    substituted=(not fc["direct_object"] and norm(parsed["direct_object"])==norm(t["mentioned_entity"]))
    if instruction: cls="INSTRUCTION_VERB_AS_ACTION"
    elif not fc["action"] and not fc["direct_object"]: cls="BOTH_FIELDS_FAILED"
    elif not fc["action"]: cls="ACTION_EXTRACTION_FAILURE"
    elif not fc["direct_object"]: cls="MENTIONED_ENTITY_SUBSTITUTED_FOR_DIRECT_OBJECT" if substituted else "DIRECT_OBJECT_EXTRACTION_FAILURE"
    else: cls="MINIMAL_ATOM_EXACT"
    return {"field_correct":fc,"all_two_fields_correct":all(fc.values()),"mentioned_entity_substituted_for_direct_object":substituted,"instruction_verb_as_action":instruction,"classification":cls}

def prepare(out):
    if out.exists() and any(out.iterdir()): raise RuntimeError("output must be fresh")
    out.mkdir(parents=True,exist_ok=True); b=validate_model_free(); r=runtime.runtime_payload()
    for t in b["tasks"]:
        d=out/"tasks"/t["task_id"]; d.mkdir(parents=True,exist_ok=True); (d/"prompt.txt").write_text(b["prompts"][t["task_id"]]); write_json(d/"fixture.snapshot.json",t)
    write_json(out/"schema_minimal_action_object.json",b["schema"]); write_json(out/"response_format_minimal_action_object.json",b["format"])
    m={"schema":"zth_qwen3_1_7b_minimal_action_object_atom_manifest_v1","status":"prepared_exploratory_not_confirmatory","prepared_at":now(),"prepared_from_git_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"driver":str(Path(__file__).relative_to(ROOT)),"driver_sha256":sha_file(Path(__file__).resolve()),"task_manifest_sha256":b["task_sha256"],"task_count":8,"direct_entity_object_count":4,"subobject_with_reference_count":4,"task_order":[t["task_id"] for t in b["tasks"]],"schema_sha256":b["schema_sha256"],"response_format_sha256":b["format_sha256"],"prompt_sha256":b["prompt_sha256"],"context_limit_non_binding":True,"runtime_freeze_sha256":sha_file(runtime.RUNTIME_FREEZE),"runtime":{"model_id":EXPECTED_MODEL_ID,"artifact_sha256":EXPECTED_MODEL_SHA,"operative_parameters":EXPECTED_PARAMS,"effective_n_ctx":EXPECTED_CTX,"n_ctx_train":EXPECTED_TRAIN_CTX},"telemetry":{"measurement_level":2,"measurement_boundary":"gpu_device_only","sample_interval_seconds":POWER_INTERVAL_SECONDS},"hardware":{"gpu_uuid":EXPECTED_GPU_UUID,"v100_touched":False},"execution_policy":{"supplier_model_calls":8,"teacher_calls":0,"retries":0,"escalations":0,"adaptation":0},"model_calls_made":False,"runtime_metadata":r["runtime"]}; m["manifest_sha256"]=sha_bytes(canonical({**m,"manifest_sha256":None})); write_json(out/"probe_manifest.json",m); write_json(out/"lifecycle.json",{"status":"prepared","model_calls_made":False,"updated_at":now()}); print(json.dumps({"status":"prepared","tasks":8,"model_calls":0},indent=2))

def execute(out):
    m=json.loads((out/"probe_manifest.json").read_text()); b=validate_model_free()
    if m["manifest_sha256"]!=sha_bytes(canonical({**m,"manifest_sha256":None})) or m["task_manifest_sha256"]!=b["task_sha256"] or m["prompt_sha256"]!=b["prompt_sha256"]: raise RuntimeError("binding mismatch")
    spec=runtime.worker_spec(); models=list_models(spec,timeout=30); c=next((x for x in models.get("data",[]) if x.get("id")==EXPECTED_MODEL_ID),None); meta=(c or {}).get("meta") or {}
    if c is None or meta.get("n_params")!=EXPECTED_PARAMS or meta.get("n_ctx")!=EXPECTED_CTX or meta.get("n_ctx_train")!=EXPECTED_TRAIN_CTX: raise RuntimeError("runtime mismatch")
    tu=base.telemetry_base_url(); telemetry=base.telemetry_preflight(tu); idle_samples,idle=base.sample_window(IDLE_SECONDS,tu); write_json(out/"preflight.json",{"model_meta":meta,"telemetry":telemetry,"prepared_manifest_sha256":sha_file(out/"probe_manifest.json"),"task_manifest_sha256":b["task_sha256"]}); write_json(out/"idle_power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","summary":idle,"samples":idle_samples}); write_json(out/"lifecycle.json",{"status":"running","started_at":now(),"model_calls_made":False})
    rows=[]
    for t in b["tasks"]:
        d=out/"tasks"/t["task_id"]; sampler=PowerSampler(lambda:read_gpu_power(EXPECTED_GPU_UUID,base_url=tu),expected_gpu_uuid=EXPECTED_GPU_UUID,sample_interval_seconds=POWER_INTERVAL_SECONDS); started=time.monotonic(); st=now(); sampler.start(); resp=decomposition.structured_call(spec,(d/"prompt.txt").read_text(),b["format"],MAX_OUTPUT_TOKENS,TIMEOUT_SECONDS); captured=time.monotonic(); samples=sampler.stop(); energy=integrate_energy_joules(samples,sample_interval_seconds=POWER_INTERVAL_SECONDS,expected_gpu_uuid=EXPECTED_GPU_UUID); md=resp.metadata(); md["request_url"]=None; raw={"status":resp.status,"content":resp.content,"metadata":md,"request_started_at":st,"response_captured_at":now(),"wall_elapsed_ms":round((captured-started)*1000,3)}; write_json(d/"response.json",raw); transport=md.get("transport_classification")=="model_response"; parsed,pv,cv,diag=parse_raw(resp.content) if transport else (None,False,False,["transport failure"]); scored=score(parsed,pv,cv,t); write_json(d/"validation.json",{"validation_status":"passed" if transport and cv else "failed","parse_valid":pv,"contract_valid":cv,"diagnostics":diag,"task_id":t["task_id"]}); write_json(d/"power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","gpu_uuid":EXPECTED_GPU_UUID,"samples":[{"timestamp_utc":s.timestamp_utc,"monotonic_seconds":s.monotonic_seconds,"gpu_uuid":s.gpu_uuid,"power_watts":s.power_watts,"sequence":s.sequence} for s in samples]}); card={"schema":"zth_qwen3_1_7b_minimal_action_object_task_scorecard_v1","task_id":t["task_id"],"semantic_regime":t["semantic_regime"],"expected_fields":{"action":t["expected_action"],"direct_object":t["expected_direct_object"]},"mentioned_entity":t["mentioned_entity"],"requested_target":t["requested_target"],"observed_fields":parsed,"transport_valid":transport,"raw_parse_valid":pv,"contract_valid":cv,**scored,"deterministic_binding":norm(parsed["direct_object"])==norm(t["requested_target"]) if cv else None,"expected_binding":t["semantic_regime"]=="DIRECT_ENTITY_OBJECT","wall_elapsed_ms":raw["wall_elapsed_ms"],"power_summary":{"sample_count":len(samples),"mean_active_watts":statistics.mean(s.power_watts for s in samples),"peak_observed_watts":max(s.power_watts for s in samples),"gross_energy_joules":energy}}; write_json(d/"scorecard.json",card); rows.append(card)
    write_json(out/"aggregate.json",aggregate(rows,idle)); write_json(out/"lifecycle.json",{"status":"terminal","completed_at":now(),"model_calls_made":True,"supplier_model_calls":8,"unique_called_tasks":8,"duplicate_called_tasks":0,"teacher_calls":0,"retries":0,"escalations":0}); print(json.dumps({"status":"terminal","tasks":8,"model_calls":8},indent=2))

def aggregate(rows,idle):
    lat=[r["wall_elapsed_ms"] for r in rows]; en=[r["power_summary"]["gross_energy_joules"] for r in rows]; ordered=sorted(lat)
    def reg(name):
        s=[r for r in rows if r["semantic_regime"]==name]; return {"tasks":len(s),"action":sum(r["field_correct"]["action"] for r in s),"direct_object":sum(r["field_correct"]["direct_object"] for r in s),"all_two":sum(r["all_two_fields_correct"] for r in s),"binding_correct":sum(r["deterministic_binding"]==r["expected_binding"] for r in s),"mentioned_substitution":sum(r["mentioned_entity_substituted_for_direct_object"] for r in s),"instruction_verb_as_action":sum(r["instruction_verb_as_action"] for r in s)}
    return {"schema":"zth_qwen3_1_7b_minimal_action_object_aggregate_v1","task_count":8,"parse_valid":sum(r["raw_parse_valid"] for r in rows),"contract_valid":sum(r["contract_valid"] for r in rows),"fields_correct":{"action":sum(r["field_correct"]["action"] for r in rows),"direct_object":sum(r["field_correct"]["direct_object"] for r in rows)},"all_two_fields_correct":sum(r["all_two_fields_correct"] for r in rows),"deterministic_binding_correct":sum(r["deterministic_binding"]==r["expected_binding"] for r in rows),"mentioned_entity_substituted_for_direct_object":sum(r["mentioned_entity_substituted_for_direct_object"] for r in rows),"instruction_verb_as_action":sum(r["instruction_verb_as_action"] for r in rows),"failure_counts":{c:sum(r["classification"]==c for r in rows) for c in ("ACTION_EXTRACTION_FAILURE","DIRECT_OBJECT_EXTRACTION_FAILURE","MENTIONED_ENTITY_SUBSTITUTED_FOR_DIRECT_OBJECT","INSTRUCTION_VERB_AS_ACTION","BOTH_FIELDS_FAILED","INVALID_CONTRACT","SERIALIZATION_FAILURE")},"regimes":{"DIRECT_ENTITY_OBJECT":reg("DIRECT_ENTITY_OBJECT"),"SUBOBJECT_WITH_REFERENCE":reg("SUBOBJECT_WITH_REFERENCE")},"latency_ms":{"median":statistics.median(lat),"mean":statistics.mean(lat),"p95":ordered[round((len(ordered)-1)*.95)]},"energy_joules":{"mean":statistics.mean(en),"median":statistics.median(en),"total":sum(en),"j_per_correct_two_field":sum(en)/sum(r["all_two_fields_correct"] for r in rows) if sum(r["all_two_fields_correct"] for r in rows) else None},"idle_power":idle,"execution":{"supplier_model_calls":8,"teacher_calls":0,"retries":0,"escalations":0,"adaptations":0}}

def main():
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True); g.add_argument("--prepare",action="store_true"); g.add_argument("--execute",action="store_true"); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args(); (prepare if a.prepare else execute)(a.output_dir)
if __name__=="__main__": main()
