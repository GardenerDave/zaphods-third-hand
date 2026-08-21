#!/usr/bin/env python3
"""Paired TF/FT clause-order control for the frozen crossed scope probe."""

from __future__ import annotations

import argparse
import difflib
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
from local_harness.supervised_capability_loop import _validator_result
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as clean
from scripts import zth_qwen3_1_7b_crossed_scope_factorial_probe as crossed
from scripts import zth_qwen3_1_7b_neutral_constrained_scope_probe as neutral
from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import EXPECTED_EFFECTIVE_CTX, EXPECTED_MODEL_ID, EXPECTED_MODEL_SHA, EXPECTED_PARAMS, EXPECTED_REQUESTED_CTX, EXPECTED_TRAIN_CTX, RUNTIME_FREEZE, RUNTIME_FREEZE_SHA

ROOT = clean.ROOT
TASK_MANIFEST = crossed.TASK_MANIFEST
EXPECTED_GPU_UUID = clean.EXPECTED_GPU_UUID
MAX_OUTPUT_TOKENS = clean.MAX_OUTPUT_TOKENS
TIMEOUT_SECONDS = clean.TIMEOUT_SECONDS
POWER_INTERVAL_SECONDS = clean.POWER_INTERVAL_SECONDS
IDLE_SECONDS = clean.IDLE_SECONDS
ORDER_SEED = "zth-scope-rule-clause-order-control-v1"


def now() -> str: return datetime.now(timezone.utc).isoformat()
def canonical(value: Any) -> bytes: return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
def sha_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha_file(path: Path) -> str: return sha_bytes(path.read_bytes())
def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def split_rules() -> tuple[str, str, str]:
    clauses = clean.SEMANTIC_RULE.split("\n\n")
    if len(clauses) != 3: raise ValueError("unexpected frozen semantic-rule clause count")
    return tuple(clauses)  # type: ignore[return-value]


def rules() -> tuple[str, str]:
    first, second, third = split_rules()
    return "\n\n".join((first, second, third)), "\n\n".join((second, first, third))


def rule_diff(tf: str, ft: str) -> str:
    return "".join(difflib.unified_diff(tf.splitlines(True), ft.splitlines(True), fromfile="TF", tofile="FT"))


def task_prompt(task: dict[str, Any], rule: str) -> str:
    return clean.task_specific_text(task) + "\n\n" + neutral.PROMPT_SUFFIX + "\n\n" + rule


def arm_order(task_id: str) -> list[str]:
    return ["TF", "FT"] if int(hashlib.sha256((ORDER_SEED + task_id).encode()).hexdigest()[-1], 16) % 2 == 0 else ["FT", "TF"]


def validate_inputs() -> dict[str, Any]:
    payload = json.loads(TASK_MANIFEST.read_text()); audit = crossed.validate_factorial_manifest(payload); tasks = payload["tasks"]; tf, ft = rules();
    if tf != clean.SEMANTIC_RULE or tf.split("\n\n")[2] != ft.split("\n\n")[2] or tf.split("\n\n")[0] != ft.split("\n\n")[1] or tf.split("\n\n")[1] != ft.split("\n\n")[0]: raise ValueError("TF/FT are not an exact first-two-clause reorder")
    prompts = {arm: {task["task_id"]: task_prompt(task, rule) for task in tasks} for arm, rule in (("TF", tf), ("FT", ft))}
    if any(not neutral.no_worked_boolean_object(prompt) for arm in prompts.values() for prompt in arm.values()): raise ValueError("worked boolean object in prompt")
    if not neutral.schema_allows_both(): raise ValueError("schema symmetry failed")
    if max(len(prompt) for arm in prompts.values() for prompt in arm.values()) + MAX_OUTPUT_TOKENS >= EXPECTED_EFFECTIVE_CTX: raise ValueError("context could bind probe")
    orders = {task["task_id"]: arm_order(task["task_id"]) for task in tasks}
    if sum(order == ["TF", "FT"] for order in orders.values()) != 8: raise ValueError("temporal arm order not balanced")
    return {"payload":payload,"audit":audit,"tasks":tasks,"rules":{"TF":tf,"FT":ft},"prompts":prompts,"orders":orders,"task_sha256":sha_file(TASK_MANIFEST),"rule_sha256":{"TF":sha_bytes(tf.encode()),"FT":sha_bytes(ft.encode())},"diff_sha256":sha_bytes(rule_diff(tf,ft).encode()),"prompt_suffix_sha256":sha_bytes(neutral.PROMPT_SUFFIX.encode()),"schema_sha256":sha_bytes(canonical(neutral.STRUCTURED_SCHEMA)),"response_format_sha256":sha_bytes(canonical(neutral.RESPONSE_FORMAT))}


def runtime_payload() -> dict[str,Any]:
    p=json.loads(RUNTIME_FREEZE.read_text());
    if sha_file(RUNTIME_FREEZE)!=RUNTIME_FREEZE_SHA or p["operative_supplier"]["n_params"]!=EXPECTED_PARAMS or p["context"]["effective_n_ctx"]!=EXPECTED_EFFECTIVE_CTX: raise RuntimeError("runtime binding mismatch")
    return p


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()): raise RuntimeError("output must be fresh")
    out.mkdir(parents=True,exist_ok=True); b=validate_inputs(); runtime=runtime_payload();
    for arm in ("TF","FT"): (out/"interfaces"/arm).mkdir(parents=True,exist_ok=True); (out/"interfaces"/arm/"rule.txt").write_text(b["rules"][arm])
    (out/"interfaces"/"TF_to_FT.diff").write_text(rule_diff(b["rules"]["TF"],b["rules"]["FT"]))
    rows=[]
    for task in b["tasks"]:
        d=out/"tasks"/task["task_id"]; d.mkdir(parents=True,exist_ok=True); write_json(d/"fixture.snapshot.json",task); row={"task_id":task["task_id"],"expected":task["expected_scope_expansion_required"],"operation_factor":task["operation_factor"],"authority_factor":task["authority_factor"],"distractor_factor":task["distractor_factor"],"arm_order":b["orders"][task["task_id"]],"prompt_sha256":{}}
        for arm in ("TF","FT"): (d/arm).mkdir(); (d/arm/"prompt.txt").write_text(b["prompts"][arm][task["task_id"]]); row["prompt_sha256"][arm]=sha_bytes(b["prompts"][arm][task["task_id"]].encode())
        rows.append(row)
    manifest={"schema":"zth_qwen3_1_7b_scope_rule_clause_order_control_manifest_v1","status":"prepared_exploratory_not_confirmatory","prepared_at":now(),"prepared_from_git_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"driver":str(Path(__file__).relative_to(ROOT)),"driver_sha256":sha_file(Path(__file__).resolve()),"task_manifest_path":str(TASK_MANIFEST.relative_to(ROOT)),"task_manifest_sha256":b["task_sha256"],"task_order":[x["task_id"] for x in b["tasks"]],"task_count":16,"expected_true":8,"expected_false":8,"rule_sha256":b["rule_sha256"],"tf_ft_diff_sha256":b["diff_sha256"],"prompt_suffix_sha256":b["prompt_suffix_sha256"],"schema_sha256":b["schema_sha256"],"response_format_sha256":b["response_format_sha256"],"worked_boolean_exemplars":0,"structured_constraint_allows_true":True,"structured_constraint_allows_false":True,"held_clause_identical":True,"context_limit_non_binding":True,"runtime_freeze_sha256":sha_file(RUNTIME_FREEZE),"runtime":{"model_id":EXPECTED_MODEL_ID,"artifact_sha256":EXPECTED_MODEL_SHA,"operative_parameters":EXPECTED_PARAMS,"effective_n_ctx":EXPECTED_EFFECTIVE_CTX,"n_ctx_train":EXPECTED_TRAIN_CTX,"requested_n_ctx":EXPECTED_REQUESTED_CTX,"llama_cpp_version":runtime["runtime"]["llama_cpp_version"],"build_revision":runtime["runtime"]["build_revision"]},"prior_runs":{"neutral_constrained_report_sha256":sha_file(ROOT/"docs/research/QWEN3_1_7B_NEUTRAL_CONSTRAINED_SCOPE_PROBE_2026-08-21.md"),"generic_prior_report_sha256":sha_file(ROOT/"docs/research/QWEN3_1_7B_GENERIC_BOOLEAN_SELECTION_PRIOR_2026-08-21.md")},"hardware":{"gpu_uuid":EXPECTED_GPU_UUID,"v100_touched":False},"telemetry":{"measurement_level":2,"measurement_boundary":"gpu_device_only","sample_interval_seconds":POWER_INTERVAL_SECONDS},"execution_policy":{"supplier_model_calls":32,"teacher_calls":0,"retries":0,"escalations":0},"tasks":rows,"model_calls_made":False}; manifest["manifest_sha256"]=sha_bytes(canonical({**manifest,"manifest_sha256":None})); write_json(out/"probe_manifest.json",manifest); write_json(out/"lifecycle.json",{"status":"prepared","model_calls_made":False,"updated_at":now()}); print(json.dumps({"status":"prepared","tasks":16,"arms":2,"calls":32,"worked_boolean_exemplars":0,"model_calls":0},indent=2))


def execute(out: Path) -> None:
    manifest=json.loads((out/"probe_manifest.json").read_text());
    if manifest["manifest_sha256"]!=sha_bytes(canonical({**manifest,"manifest_sha256":None})): raise RuntimeError("manifest hash mismatch")
    b=validate_inputs();
    if b["task_sha256"]!=manifest["task_manifest_sha256"] or b["schema_sha256"]!=manifest["schema_sha256"] or b["prompt_suffix_sha256"]!=manifest["prompt_suffix_sha256"]: raise RuntimeError("binding changed")
    for row in manifest["tasks"]:
        for arm in ("TF","FT"):
            if sha_bytes((out/"tasks"/row["task_id"]/arm/"prompt.txt").read_bytes())!=row["prompt_sha256"][arm]: raise RuntimeError("prompt drift")
    spec=clean.worker_spec(); models=list_models(spec,timeout=30); cand=next((x for x in models.get("data",[]) if x.get("id")==EXPECTED_MODEL_ID),None)
    if cand is None or (cand.get("meta") or {}).get("n_params")!=EXPECTED_PARAMS or (cand.get("meta") or {}).get("n_ctx")!=EXPECTED_EFFECTIVE_CTX: raise RuntimeError("runtime endpoint mismatch")
    telemetry_url=clean.telemetry_base_url(); telemetry=clean.telemetry_preflight(telemetry_url); idle_samples,idle=clean.sample_window(IDLE_SECONDS,telemetry_url); write_json(out/"preflight.json",{"schema":"zth_qwen3_1_7b_scope_rule_clause_order_control_execution_v1","prepared_manifest_sha256":sha_file(out/"probe_manifest.json"),"model_meta":cand.get("meta"),"telemetry":telemetry,"task_manifest_sha256":manifest["task_manifest_sha256"],"rule_sha256":manifest["rule_sha256"],"tf_ft_diff_sha256":manifest["tf_ft_diff_sha256"],"schema_sha256":manifest["schema_sha256"],"worked_boolean_exemplars":0,"execution_policy":manifest["execution_policy"]}); write_json(out/"idle_power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","summary":idle,"samples":idle_samples}); write_json(out/"lifecycle.json",{"status":"running","started_at":now(),"model_calls_made":False})
    byid={x["task_id"]:x for x in b["tasks"]}
    for tid in manifest["task_order"]:
        task=byid[tid]; row=next(x for x in manifest["tasks"] if x["task_id"]==tid)
        for arm in row["arm_order"]:
            d=out/"tasks"/tid/arm; prompt=(d/"prompt.txt").read_text(); sampler=PowerSampler(lambda:read_gpu_power(EXPECTED_GPU_UUID,base_url=telemetry_url),expected_gpu_uuid=EXPECTED_GPU_UUID,sample_interval_seconds=POWER_INTERVAL_SECONDS); started=time.monotonic(); started_at=now(); sampler.start(); response=neutral.structured_call(spec,prompt,neutral.STRUCTURED_SCHEMA,MAX_OUTPUT_TOKENS,TIMEOUT_SECONDS); captured=time.monotonic(); samples=sampler.stop(); energy=integrate_energy_joules(samples,sample_interval_seconds=POWER_INTERVAL_SECONDS,expected_gpu_uuid=EXPECTED_GPU_UUID); metadata=response.metadata(); metadata["request_url"]=None; raw={"status":response.status,"content":response.content,"metadata":metadata,"request_started_at":started_at,"response_captured_at":now(),"wall_elapsed_ms":round((captured-started)*1000,3)}; write_json(d/"response.json",raw); transport=metadata.get("transport_classification")=="model_response"; vt={"task_id":tid,"task_family":"scope-expansion-clause-order-control","prompt":clean.task_specific_text(task),"output_contract":{"format":"json","required_fields":["scope_expansion_required"]},"validator":{"kind":"zth_output_contract","reference_facts":{"requires_scope_expansion_flag":task["expected_scope_expansion_required"]}}}; validation=_validator_result(response.content,vt,attempt_id=f"clause-order-{arm}-{tid}") if transport else None
            if validation is not None: write_json(d/"validation.json",validation)
            try: parsed=json.loads(response.content) if transport else None; parse_valid=parsed is not None
            except json.JSONDecodeError: parsed=None; parse_valid=False
            contract=isinstance(parsed,dict) and set(parsed)=={"scope_expansion_required"} and isinstance(parsed.get("scope_expansion_required"),bool); observed=parsed.get("scope_expansion_required") if contract else None; write_json(d/"power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","gpu_uuid":EXPECTED_GPU_UUID,"samples":[{"timestamp_utc":s.timestamp_utc,"monotonic_seconds":s.monotonic_seconds,"gpu_uuid":s.gpu_uuid,"power_watts":s.power_watts,"sequence":s.sequence} for s in samples]}); write_json(d/"scorecard.json",{"schema":"zth_qwen3_1_7b_scope_rule_clause_order_task_scorecard_v1","task_id":tid,"arm":arm,"expected":task["expected_scope_expansion_required"],"operation_factor":task["operation_factor"],"authority_factor":task["authority_factor"],"distractor_factor":task["distractor_factor"],"transport_valid":transport,"raw_parse_valid":transport and parse_valid,"contract_valid":contract,"observed":observed,"correct":bool(contract and observed==task["expected_scope_expansion_required"]),"failure_class":None if contract and observed==task["expected_scope_expansion_required"] else (("SERIALIZATION_FAILURE" if transport and not parse_valid else "INVALID_CONTRACT") if not contract else "SCOPE_DECISION_FAILURE"),"validator_status":validation.get("validation_status") if validation else None,"wall_elapsed_ms":raw["wall_elapsed_ms"],"prompt_tokens":(metadata.get("usage") or {}).get("prompt_tokens"),"completion_tokens":(metadata.get("usage") or {}).get("completion_tokens"),"schema_sha256":manifest["schema_sha256"],"power_summary":{"sample_count":len(samples),"mean_active_watts":statistics.mean(s.power_watts for s in samples),"peak_observed_watts":max(s.power_watts for s in samples),"gross_energy_joules":energy},"retry_count":0,"escalation_count":0,"teacher_calls":0})
    write_json(out/"aggregate.json",aggregate(out,manifest,idle)); write_json(out/"lifecycle.json",{"status":"terminal","completed_at":now(),"model_calls_made":True,"supplier_model_calls":32,"teacher_calls":0,"retries":0,"escalations":0}); print(json.dumps({"status":"terminal","calls":32},indent=2))


def aggregate(out: Path, manifest: dict[str,Any], idle: dict[str,Any]) -> dict[str,Any]:
    rows=[json.loads(p.read_text()) for p in sorted(out.glob("tasks/*/*/scorecard.json"))]; by={arm:[x for x in rows if x["arm"]==arm] for arm in ("TF","FT")}
    def summary(rs):
        tp=sum(x["correct"] and x["expected"] for x in rs); fn=sum(x["expected"] and x["observed"] is False for x in rs); fp=sum(not x["expected"] and x["observed"] is True for x in rs); tn=sum(x["correct"] and not x["expected"] for x in rs); lat=[x["wall_elapsed_ms"] for x in rs]; en=[x["power_summary"]["gross_energy_joules"] for x in rs]; sub=lambda **f:[x for x in rs if all(x[k]==v for k,v in f.items())]; return {"true_selected":sum(x["observed"] is True for x in rs),"false_selected":sum(x["observed"] is False for x in rs),"correct":sum(x["correct"] for x in rs),"inside_correct":sum(x["correct"] for x in sub(authority_factor="INSIDE_AUTHORITY")),"outside_correct":sum(x["correct"] for x in sub(authority_factor="OUTSIDE_AUTHORITY")),"read_correct":sum(x["correct"] for x in sub(operation_factor="READ")),"mutate_correct":sum(x["correct"] for x in sub(operation_factor="MUTATE")),"distractor_present_correct":sum(x["correct"] for x in sub(distractor_factor="HELD_DISTRACTOR_PRESENT")),"distractor_absent_correct":sum(x["correct"] for x in sub(distractor_factor="HELD_DISTRACTOR_ABSENT")),"parse_valid":sum(x["raw_parse_valid"] for x in rs),"contract_valid":sum(x["contract_valid"] for x in rs),"confusion_matrix":{"tp":tp,"fn":fn,"fp":fp,"tn":tn},"serialization_failures":sum(x["failure_class"]=="SERIALIZATION_FAILURE" for x in rs),"contract_failures":sum(x["failure_class"]=="INVALID_CONTRACT" for x in rs),"scope_decision_failures":sum(x["failure_class"]=="SCOPE_DECISION_FAILURE" for x in rs),"latency_ms":{"median":statistics.median(lat),"mean":statistics.mean(lat),"p95":sorted(lat)[round(15*.95)]},"energy":{"mean_gross_joules":statistics.mean(en),"median_gross_joules":statistics.median(en),"total_gross_joules":sum(en)}}
    paired={}
    for tid in manifest["task_order"]:
        t=next(x for x in by["TF"] if x["task_id"]==tid); f=next(x for x in by["FT"] if x["task_id"]==tid); label="SAME_CORRECT" if t["correct"] and f["correct"] else "SAME_INCORRECT" if not t["correct"] and not f["correct"] else "TF_INCORRECT_FT_CORRECT" if not t["correct"] and f["correct"] else "TF_CORRECT_FT_INCORRECT" if t["correct"] and not f["correct"] else "OTHER"; paired[tid]={"expected":t["expected"],"TF":t["observed"],"FT":f["observed"],"classification":label}
    return {"schema":"zth_qwen3_1_7b_scope_rule_clause_order_control_aggregate_v1","exploratory_not_confirmatory":True,"candidate":{"model_id":EXPECTED_MODEL_ID,"operative_parameters":EXPECTED_PARAMS,"artifact_sha256":EXPECTED_MODEL_SHA},"arms":{arm:summary(by[arm]) for arm in ("TF","FT")},"paired":paired,"tf_to_ft_flip_count":sum(x["TF"]!=x["FT"] for x in paired.values()),"inside_recovery_count":sum(x["expected"] is False and x["TF"] is True and x["FT"] is False for x in paired.values()),"outside_retention_count":sum(x["expected"] is True and x["FT"] is True for x in paired.values()),"idle_power":idle,"execution":{"supplier_model_calls":32,"teacher_calls":0,"retries":0,"escalations":0}}


def main()->int:
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True); g.add_argument("--prepare",action="store_true"); g.add_argument("--execute",action="store_true"); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args(); prepare(a.output_dir) if a.prepare else execute(a.output_dir); return 0
if __name__=="__main__": raise SystemExit(main())
