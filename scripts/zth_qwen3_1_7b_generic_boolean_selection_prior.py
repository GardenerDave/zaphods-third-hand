#!/usr/bin/env python3
"""Generic value-neutral boolean calibration with rule-order control."""

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
from local_harness.icm_spec import OPENAI_CHAT, SYSTEM_PROMPT, WorkerResponse, classify_worker_response, completion_url
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from local_harness.supervised_capability_loop import _validator_result
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as clean
from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import EXPECTED_EFFECTIVE_CTX, EXPECTED_MODEL_ID, EXPECTED_MODEL_SHA, EXPECTED_PARAMS, EXPECTED_REQUESTED_CTX, EXPECTED_TRAIN_CTX, RUNTIME_FREEZE, RUNTIME_FREEZE_SHA

ROOT = clean.ROOT
TASK_MANIFEST = ROOT / "docs/research/GENERIC_BOOLEAN_SELECTION_PRIOR_PROBE_TASKS_2026-08-21.json"
EXPECTED_GPU_UUID = clean.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = clean.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = clean.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = clean.POWER_INTERVAL_SECONDS
IDLE_SECONDS = clean.IDLE_SECONDS
ORDER_SEED = "zth-generic-boolean-order-v1"
TF_RULE = "decision_flag is true when the marker code is KAPPA-7.\n\ndecision_flag is false when the marker code is LAMBDA-4."
FT_RULE = "decision_flag is false when the marker code is LAMBDA-4.\n\ndecision_flag is true when the marker code is KAPPA-7."
PROMPT_SUFFIX = "Return the structured response using the supplied output schema.\n\nDetermine decision_flag from the marker fact and the rule.\n\nDo not provide reasoning or explanation.\n/no_think"
STRUCTURED_SCHEMA = {"type":"object","properties":{"decision_flag":{"type":"boolean"}},"required":["decision_flag"],"additionalProperties":False}
RESPONSE_FORMAT = {"type":"json_schema","json_schema":{"name":"decision_flag_object","schema":STRUCTURED_SCHEMA}}
FORBIDDEN_TERMS = ("scope", "authority", "permission", "approval", "review", "risk", "safe", "unsafe", "allowed", "held", "required", "forbidden", "mutation", "read", "write")


def now() -> str: return datetime.now(timezone.utc).isoformat()
def canonical(value: Any) -> bytes: return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
def sha_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha_file(path: Path) -> str: return sha_bytes(path.read_bytes())
def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rule_diff() -> str:
    return "".join(difflib.unified_diff(TF_RULE.splitlines(True), FT_RULE.splitlines(True), fromfile="TF", tofile="FT"))


def task_text(task: dict[str, Any]) -> str:
    return f"Marker code: {task['marker_code']}."


def prompt_for(task: dict[str, Any], rule: str) -> str:
    return task_text(task) + "\n\n" + rule + "\n\n" + PROMPT_SUFFIX


def schema_allows_both() -> bool:
    encoded = json.dumps(STRUCTURED_SCHEMA, sort_keys=True)
    return STRUCTURED_SCHEMA["type"] == "object" and STRUCTURED_SCHEMA["properties"] == {"decision_flag":{"type":"boolean"}} and STRUCTURED_SCHEMA["required"] == ["decision_flag"] and STRUCTURED_SCHEMA["additionalProperties"] is False and not any(key in encoded for key in ("default", "const", "example", "examples", "enum"))


def audit_text(text: str) -> list[str]:
    lowered = text.casefold()
    findings = [term for term in FORBIDDEN_TERMS if term in lowered]
    if '{"decision_flag": true}' in lowered or '{"decision_flag": false}' in lowered:
        findings.append("worked_boolean_object")
    return findings


def validate_inputs() -> dict[str, Any]:
    payload = json.loads(TASK_MANIFEST.read_text(encoding="utf-8")); tasks = payload["tasks"]
    if payload["schema"] != "zth_generic_boolean_selection_prior_task_set_v1" or len(tasks) != 16 or len({x["task_id"] for x in tasks}) != 16:
        raise ValueError("generic boolean task manifest invalid")
    if sum(x["marker_code"] == "KAPPA-7" for x in tasks) != 8 or sum(x["marker_code"] == "LAMBDA-4" for x in tasks) != 8:
        raise ValueError("marker balance invalid")
    if sum(x["expected"] for x in tasks) != 8 or any(x["expected"] != payload["marker_mapping"][x["marker_code"]] for x in tasks):
        raise ValueError("expected balance/mapping invalid")
    texts = [task_text(x) for x in tasks]
    if any(audit_text(t) for t in texts): raise ValueError("task terminology leakage")
    if audit_text(PROMPT_SUFFIX): raise ValueError("prompt terminology leakage")
    if any(term in TF_RULE.casefold() or term in FT_RULE.casefold() for term in FORBIDDEN_TERMS): raise ValueError("rule terminology leakage")
    if not schema_allows_both(): raise ValueError("schema does not allow both values")
    tf = [prompt_for(x, TF_RULE) for x in tasks]; ft = [prompt_for(x, FT_RULE) for x in tasks]
    if max(max(map(len, tf)), max(map(len, ft))) + MAX_OUTPUT_TOKENS >= EXPECTED_EFFECTIVE_CTX: raise ValueError("context could bind calibration")
    return {"payload":payload,"tasks":tasks,"tf_prompts":tf,"ft_prompts":ft,"task_sha256":sha_file(TASK_MANIFEST),"tf_rule_sha256":sha_bytes(TF_RULE.encode()),"ft_rule_sha256":sha_bytes(FT_RULE.encode()),"rule_diff_sha256":sha_bytes(rule_diff().encode()),"prompt_suffix_sha256":sha_bytes(PROMPT_SUFFIX.encode()),"schema_sha256":sha_bytes(canonical(STRUCTURED_SCHEMA)),"response_format_sha256":sha_bytes(canonical(RESPONSE_FORMAT)),"max_prompt_chars":max(max(map(len, tf)),max(map(len, ft))),"scope_terminology_findings":0}


def runtime_payload() -> dict[str, Any]:
    p=json.loads(RUNTIME_FREEZE.read_text());
    if sha_file(RUNTIME_FREEZE)!=RUNTIME_FREEZE_SHA or p["operative_supplier"]["n_params"]!=EXPECTED_PARAMS or p["context"]["effective_n_ctx"]!=EXPECTED_EFFECTIVE_CTX: raise RuntimeError("runtime binding mismatch")
    return p


def arm_order(task_id: str) -> list[str]:
    return ["TF","FT"] if int(hashlib.sha256((ORDER_SEED+task_id).encode()).hexdigest()[-1],16)%2==0 else ["FT","TF"]


def structured_call(spec: Any, prompt: str, max_tokens: int, timeout: int) -> WorkerResponse:
    if spec.api != OPENAI_CHAT: raise RuntimeError("generic calibration requires OpenAI chat endpoint")
    payload={"model":spec.model,"messages":[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":0.2,"stream":False,"response_format":RESPONSE_FORMAT}
    url=completion_url(spec); prov={"prompt_sha256":sha_bytes(prompt.encode()),"api":spec.api,"model":spec.model,"max_tokens":max_tokens,"temperature":0.2,"response_format_sha256":sha_bytes(canonical(RESPONSE_FORMAT)),"endpoint_alias":"JARVIS_LOCAL"}; req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer dummy"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: result=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors="replace"); return WorkerResponse(status="http_error",content=f"[HTTP error {e.code}]\n{body}",request_url=url,model=spec.model,configured_model=spec.configured_model,finish_reason=None,usage=None,timings=None,raw_response=None,error=body,request_provenance=prov)
    except Exception as e: return WorkerResponse(status="request_error",content=f"[request error]\n{e}",request_url=url,model=spec.model,configured_model=spec.configured_model,finish_reason=None,usage=None,timings=None,raw_response=None,error=str(e),request_provenance=prov)
    try:
        c=result["choices"][0]; content=c.get("message",{}).get("content") or ""; return WorkerResponse(status="ok" if content else "empty_content",content=content,request_url=url,model=result.get("model",spec.model),configured_model=spec.configured_model,finish_reason=c.get("finish_reason"),usage=result.get("usage"),timings=result.get("timings"),raw_response=result,request_provenance=prov)
    except Exception as e: return WorkerResponse(status="request_error",content=f"[response error]\n{e}",request_url=url,model=spec.model,configured_model=spec.configured_model,finish_reason=None,usage=None,timings=None,raw_response=result,error=str(e),request_provenance=prov)


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()): raise RuntimeError("output must be fresh")
    out.mkdir(parents=True,exist_ok=True); b=validate_inputs(); runtime=runtime_payload(); write_json(out/"structured_schema.json",STRUCTURED_SCHEMA); write_json(out/"response_format.json",RESPONSE_FORMAT)
    rows=[]
    for task,tf,ft in zip(b["tasks"],b["tf_prompts"],b["ft_prompts"]):
        d=out/"tasks"/task["task_id"]; d.mkdir(parents=True,exist_ok=True); write_json(d/"fixture.snapshot.json",task); (d/"TF").mkdir(); (d/"FT").mkdir(); (d/"TF"/"prompt.txt").write_text(tf); (d/"FT"/"prompt.txt").write_text(ft); rows.append({"task_id":task["task_id"],"marker_code":task["marker_code"],"expected":task["expected"],"arm_order":arm_order(task["task_id"]),"prompt_sha256":{"TF":sha_bytes(tf.encode()),"FT":sha_bytes(ft.encode())}})
    manifest={"schema":"zth_qwen3_1_7b_generic_boolean_selection_prior_manifest_v1","status":"prepared_exploratory_not_confirmatory","prepared_at":now(),"prepared_from_git_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"driver":str(Path(__file__).relative_to(ROOT)),"driver_sha256":sha_file(Path(__file__).resolve()),"task_manifest_path":str(TASK_MANIFEST.relative_to(ROOT)),"task_manifest_sha256":b["task_sha256"],"task_order":[x["task_id"] for x in b["tasks"]],"task_count":16,"marker_counts":{"KAPPA-7":8,"LAMBDA-4":8},"expected_counts":{"true":8,"false":8},"tf_rule_sha256":b["tf_rule_sha256"],"ft_rule_sha256":b["ft_rule_sha256"],"tf_ft_diff_sha256":b["rule_diff_sha256"],"prompt_suffix_sha256":b["prompt_suffix_sha256"],"schema_sha256":b["schema_sha256"],"response_format_sha256":b["response_format_sha256"],"scope_terminology_findings":0,"worked_boolean_exemplars":0,"structured_constraint_allows_true":True,"structured_constraint_allows_false":True,"runtime_freeze_sha256":sha_file(RUNTIME_FREEZE),"runtime":{"model_id":EXPECTED_MODEL_ID,"artifact_sha256":EXPECTED_MODEL_SHA,"operative_parameters":EXPECTED_PARAMS,"effective_n_ctx":EXPECTED_EFFECTIVE_CTX,"n_ctx_train":EXPECTED_TRAIN_CTX,"requested_n_ctx":EXPECTED_REQUESTED_CTX,"context_limit_non_binding":True,"llama_cpp_version":runtime["runtime"]["llama_cpp_version"],"build_revision":runtime["runtime"]["build_revision"]},"hardware":{"gpu_uuid":EXPECTED_GPU_UUID,"v100_touched":False},"telemetry":{"measurement_level":2,"measurement_boundary":"gpu_device_only","sample_interval_seconds":POWER_INTERVAL_SECONDS},"execution_policy":{"supplier_model_calls":32,"teacher_calls":0,"retries":0,"escalations":0},"tasks":rows,"model_calls_made":False}; manifest["manifest_sha256"]=sha_bytes(canonical({**manifest,"manifest_sha256":None})); write_json(out/"probe_manifest.json",manifest); write_json(out/"lifecycle.json",{"status":"prepared","model_calls_made":False,"updated_at":now()}); print(json.dumps({"status":"prepared","tasks":16,"arms":2,"calls":32,"scope_terminology_findings":0,"model_calls":0},indent=2))


def execute(out: Path) -> None:
    manifest=json.loads((out/"probe_manifest.json").read_text());
    if manifest["manifest_sha256"]!=sha_bytes(canonical({**manifest,"manifest_sha256":None})): raise RuntimeError("manifest hash mismatch")
    b=validate_inputs();
    if b["task_sha256"]!=manifest["task_manifest_sha256"] or manifest["scope_terminology_findings"]!=0 or manifest["worked_boolean_exemplars"]!=0: raise RuntimeError("frozen calibration binding changed")
    for row in manifest["tasks"]:
        for arm in ("TF","FT"):
            if sha_bytes((out/"tasks"/row["task_id"]/arm/"prompt.txt").read_bytes())!=row["prompt_sha256"][arm]: raise RuntimeError("prompt drift")
    spec=clean.worker_spec(); models=list_models(spec,timeout=30); cand=next((x for x in models.get("data",[]) if x.get("id")==EXPECTED_MODEL_ID),None)
    if cand is None or (cand.get("meta") or {}).get("n_params")!=EXPECTED_PARAMS or (cand.get("meta") or {}).get("n_ctx")!=EXPECTED_EFFECTIVE_CTX: raise RuntimeError("runtime endpoint mismatch")
    telemetry_url=clean.telemetry_base_url(); telemetry=clean.telemetry_preflight(telemetry_url); idle_samples,idle=clean.sample_window(IDLE_SECONDS,telemetry_url); write_json(out/"preflight.json",{"schema":"zth_qwen3_1_7b_generic_boolean_selection_prior_execution_v1","prepared_manifest_sha256":sha_file(out/"probe_manifest.json"),"model_meta":cand.get("meta"),"telemetry":telemetry,"task_manifest_sha256":manifest["task_manifest_sha256"],"tf_rule_sha256":manifest["tf_rule_sha256"],"ft_rule_sha256":manifest["ft_rule_sha256"],"schema_sha256":manifest["schema_sha256"],"scope_terminology_findings":0,"worked_boolean_exemplars":0,"execution_policy":manifest["execution_policy"]}); write_json(out/"idle_power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","summary":idle,"samples":idle_samples}); write_json(out/"lifecycle.json",{"status":"running","started_at":now(),"model_calls_made":False})
    byid={x["task_id"]:x for x in b["tasks"]}
    for tid in manifest["task_order"]:
        task=byid[tid]; row=next(x for x in manifest["tasks"] if x["task_id"]==tid)
        for arm in row["arm_order"]:
            d=out/"tasks"/tid/arm; prompt=(d/"prompt.txt").read_text(); sampler=PowerSampler(lambda:read_gpu_power(EXPECTED_GPU_UUID,base_url=telemetry_url),expected_gpu_uuid=EXPECTED_GPU_UUID,sample_interval_seconds=POWER_INTERVAL_SECONDS); started=time.monotonic(); started_at=now(); sampler.start(); response=structured_call(spec,prompt,MAX_OUTPUT_TOKENS,TIMEOUT_SECONDS); captured=time.monotonic(); samples=sampler.stop(); energy=integrate_energy_joules(samples,sample_interval_seconds=POWER_INTERVAL_SECONDS,expected_gpu_uuid=EXPECTED_GPU_UUID); metadata=response.metadata(); metadata["request_url"]=None; raw={"status":response.status,"content":response.content,"metadata":metadata,"request_started_at":started_at,"response_captured_at":now(),"wall_elapsed_ms":round((captured-started)*1000,3)}; write_json(d/"response.json",raw); transport=metadata.get("transport_classification")=="model_response"; vt={"task_id":tid,"task_family":"generic-boolean-selection-prior","prompt":task_text(task),"output_contract":{"format":"json","required_fields":["decision_flag"]},"validator":{"kind":"zth_output_contract","reference_facts":{"expected_decision_flag":task["expected"]}}}; validation=_validator_result(response.content,vt,attempt_id=f"generic-{arm}-{tid}") if transport else None;
            if validation is not None: write_json(d/"validation.json",validation)
            try:
                parsed=json.loads(response.content) if transport else None
                parse_valid=parsed is not None
            except json.JSONDecodeError:
                parsed=None
                parse_valid=False
            contract=isinstance(parsed,dict) and set(parsed)=={"decision_flag"} and isinstance(parsed.get("decision_flag"),bool); observed=parsed.get("decision_flag") if contract else None; write_json(d/"power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","gpu_uuid":EXPECTED_GPU_UUID,"samples":[{"timestamp_utc":s.timestamp_utc,"monotonic_seconds":s.monotonic_seconds,"gpu_uuid":s.gpu_uuid,"power_watts":s.power_watts,"sequence":s.sequence} for s in samples]}); write_json(d/"scorecard.json",{"schema":"zth_qwen3_1_7b_generic_boolean_task_scorecard_v1","task_id":tid,"arm":arm,"marker_code":task["marker_code"],"expected":task["expected"],"transport_valid":transport,"raw_parse_valid":transport and parse_valid,"contract_valid":contract,"observed":observed,"correct":bool(contract and observed==task["expected"]),"failure_class":None if contract and observed==task["expected"] else (("SERIALIZATION_FAILURE" if transport and not parse_valid else "INVALID_CONTRACT") if not contract else "DECISION_FAILURE"),"validator_status":validation.get("validation_status") if validation else None,"wall_elapsed_ms":raw["wall_elapsed_ms"],"prompt_tokens":(metadata.get("usage") or {}).get("prompt_tokens"),"completion_tokens":(metadata.get("usage") or {}).get("completion_tokens"),"power_summary":{"sample_count":len(samples),"mean_active_watts":statistics.mean(s.power_watts for s in samples),"peak_observed_watts":max(s.power_watts for s in samples),"gross_energy_joules":energy},"schema_sha256":manifest["schema_sha256"],"retry_count":0,"escalation_count":0,"teacher_calls":0})
    write_json(out/"aggregate.json",aggregate(out,manifest,idle)); write_json(out/"lifecycle.json",{"status":"terminal","completed_at":now(),"model_calls_made":True,"supplier_model_calls":32,"teacher_calls":0,"retries":0,"escalations":0}); print(json.dumps({"status":"terminal","calls":32},indent=2))


def aggregate(out: Path, manifest: dict[str,Any], idle: dict[str,Any]) -> dict[str,Any]:
    rows=[json.loads(p.read_text()) for p in sorted(out.glob("tasks/*/*/scorecard.json"))]; by={"TF":[x for x in rows if x["arm"]=="TF"],"FT":[x for x in rows if x["arm"]=="FT"]}
    def summary(rs):
        tp=sum(x["correct"] and x["expected"] for x in rs); fn=sum(x["expected"] and x["observed"] is False for x in rs); fp=sum(not x["expected"] and x["observed"] is True for x in rs); tn=sum(x["correct"] and not x["expected"] for x in rs); lat=[x["wall_elapsed_ms"] for x in rs]; en=[x["power_summary"]["gross_energy_joules"] for x in rs]; return {"true_selected":sum(x["observed"] is True for x in rs),"false_selected":sum(x["observed"] is False for x in rs),"correct":sum(x["correct"] for x in rs),"kappa_correct":sum(x["correct"] for x in rs if x["marker_code"]=="KAPPA-7"),"lambda_correct":sum(x["correct"] for x in rs if x["marker_code"]=="LAMBDA-4"),"parse_valid":sum(x["raw_parse_valid"] for x in rs),"contract_valid":sum(x["contract_valid"] for x in rs),"confusion_matrix":{"tp":tp,"fn":fn,"fp":fp,"tn":tn},"serialization_failures":sum(x["failure_class"]=="SERIALIZATION_FAILURE" for x in rs),"contract_failures":sum(x["failure_class"]=="INVALID_CONTRACT" for x in rs),"decision_failures":sum(x["failure_class"]=="DECISION_FAILURE" for x in rs),"latency_ms":{"median":statistics.median(lat),"mean":statistics.mean(lat),"p95":sorted(lat)[round(15*.95)],"energy":{"mean":statistics.mean(en),"median":statistics.median(en),"total":sum(en)}}}
    per={arm:summary(by[arm]) for arm in ("TF","FT")}; paired={}
    for tid in manifest["task_order"]:
        t=next(x for x in rows if x["task_id"]==tid and x["arm"]=="TF"); f=next(x for x in rows if x["task_id"]==tid and x["arm"]=="FT"); label="SAME_CORRECT" if t["correct"] and f["correct"] else "SAME_INCORRECT" if not t["correct"] and not f["correct"] else "FLIPPED_WITH_ORDER" if t["observed"]!=f["observed"] else "OTHER"; paired[tid]={"expected":t["expected"],"TF":t["observed"],"FT":f["observed"],"classification":label}
    return {"schema":"zth_qwen3_1_7b_generic_boolean_selection_prior_aggregate_v1","exploratory_not_confirmatory":True,"candidate":{"model_id":EXPECTED_MODEL_ID,"operative_parameters":EXPECTED_PARAMS,"artifact_sha256":EXPECTED_MODEL_SHA},"arms":per,"paired":paired,"tf_to_ft_flip_count":sum(x["classification"]=="FLIPPED_WITH_ORDER" for x in paired.values()),"idle_power":idle,"execution":{"supplier_model_calls":32,"teacher_calls":0,"retries":0,"escalations":0}}


def main()->int:
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True); g.add_argument("--prepare",action="store_true"); g.add_argument("--execute",action="store_true"); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args(); prepare(a.output_dir) if a.prepare else execute(a.output_dir); return 0
if __name__=="__main__": raise SystemExit(main())
