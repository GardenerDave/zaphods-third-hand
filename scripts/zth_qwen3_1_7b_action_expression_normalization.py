#!/usr/bin/env python3
"""Bounded action-expression -> deterministic canonical-operation experiment."""

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

from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = base.ROOT
RULES = ROOT / "docs/research/QWEN3_1_7B_OPERATION_NORMALIZATION_RULES_V0_2026-08-23.json"
HISTORICAL_TASKS = ROOT / "docs/research/CAPABILITY_ROUTER_FAILURE_TEACHING_HOLDOUT_V0_TASKS_2026-08-23.json"
HISTORICAL_RUN = ROOT / ".work/model_size_supplier_floor/capability_router_failure_teaching_v0/stage_b/run_20260823T070000Z"
FRESH_TASKS = ROOT / "docs/research/QWEN3_1_7B_ACTION_EXPRESSION_NORMALIZATION_HOLDOUT_2026-08-23.json"
RUN = ROOT / ".work/model_size_supplier_floor/qwen3_1_7b_action_expression_normalization/run_20260823T090000Z"
MODEL_ID = runtime.EXPECTED_MODEL_ID
MODEL_SHA = runtime.EXPECTED_MODEL_SHA
PARAMS = runtime.EXPECTED_PARAMS
GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT = runtime.TIMEOUT_SECONDS
POWER_INTERVAL = runtime.POWER_INTERVAL_SECONDS

SCHEMA = {
    "type": "object",
    "properties": {"action_expression": {"type": "string"}, "object_expression": {"type": "string"}},
    "required": ["action_expression", "object_expression"],
    "additionalProperties": False,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_rules() -> dict[str, Any]:
    rules = read_json(RULES)
    if rules.get("fuzzy_matching") is not False or rules.get("model_output_grants_authority") is not False:
        raise RuntimeError("unsafe normalization rule configuration")
    return rules


def derive_normalization_context(request: Any) -> str:
    """Apply the frozen bounded request grammar; never infer arbitrary intent."""
    if not isinstance(request, str):
        return "UNSUPPORTED_OR_UNKNOWN_CONTEXT"
    text = " ".join(request.casefold().strip().split())
    if not text:
        return "UNSUPPORTED_OR_UNKNOWN_CONTEXT"
    if " and " in text or " or " in text:
        return "AMBIGUOUS_CONTEXT"
    first = text.split(" ", 1)[0].strip(".,:;!?()")
    if first in {"archive", "delete"}:
        return "UNSUPPORTED_OR_UNKNOWN_CONTEXT"
    if first in {"inspect", "amend", "index", "dispatch"}:
        return "DIRECT_OPERATION_CONTEXT"
    presence_cues = ("whether", "exists", "present", "can be found", "right now", "currently")
    # Polite/request wrappers are context cues only. They do not resolve the
    # operation; the deterministic-first planner still sends them to the
    # bounded semantic fallback because their leading operation is not one of
    # the frozen canonical request forms.
    if first in {"determine", "check", "verify", "confirm", "find", "exists", "could", "please", "can", "would"} and any(cue in text for cue in presence_cues):
        return "PRESENCE_OBSERVATION_CONTEXT"
    return "UNSUPPORTED_OR_UNKNOWN_CONTEXT"


def normalize_operation_expression(expression: Any, request_context: str | None = None) -> dict[str, Any]:
    raw = expression if isinstance(expression, str) else ""
    key = raw.strip().casefold()
    rules = load_rules()
    if not key:
        return {"status": "UNRESOLVED", "action_expression": raw, "canonical_operation": None, "rule_id": None, "reason": "empty expression"}
    context = derive_normalization_context(request_context)
    if context == "AMBIGUOUS_CONTEXT" or key in {x.casefold() for x in rules["ambiguous_exact_expressions"]}:
        return {"status": "AMBIGUOUS", "action_expression": raw, "canonical_operation": None, "rule_id": None, "reason": "expression names multiple operations"}
    for rule in rules["rules"]:
        if key in {x.casefold() for x in rule["expressions"]}:
            presence_rule = rule["canonical_operation"] == "observe_presence"
            if presence_rule and context != "PRESENCE_OBSERVATION_CONTEXT":
                return {"status": "UNRESOLVED", "action_expression": raw, "canonical_operation": None, "rule_id": None, "reason": "presence expression is outside the frozen presence context"}
            if not presence_rule and context != "DIRECT_OPERATION_CONTEXT":
                return {"status": "UNRESOLVED", "action_expression": raw, "canonical_operation": None, "rule_id": None, "reason": "direct operation is outside the frozen direct-operation context"}
            return {"status": "NORMALIZED", "action_expression": raw, "canonical_operation": rule["canonical_operation"], "rule_id": rule["rule_id"], "reason": rule["semantic_rationale"]}
    return {"status": "UNRESOLVED", "action_expression": raw, "canonical_operation": None, "rule_id": None, "reason": "no exact frozen rule or unknown request context"}


def semantic_prompt(request: str) -> str:
    return (
        f"Request clause:\n{request}\n\n"
        "Required structured fields describe the request clause.\n\n"
        "action_expression:\n"
        "the smallest text span or semantic expression that identifies the requested operation or requested state-oriented intent.\n\n"
        "object_expression:\n"
        "the phrase describing what the action or state-oriented intent concerns.\n\n"
        "/no_think"
    )


def response_format() -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "router_action_expression_atom", "schema": SCHEMA}}


def frozen_holdout() -> list[dict[str, Any]]:
    return [
        {"task_id":"norm-holdout-001","regime":"PRESENCE_OBSERVATION","input_request":"Determine whether docs/normalization-presence-alpha.txt exists in the current tree.","requested_target":"docs/normalization-presence-alpha.txt","expected_surface_expression":"determine","expected_canonical_operation":"observe_presence","expected_status":"NORMALIZED","allowed_canonical_operations":["observe_presence"]},
        {"task_id":"norm-holdout-002","regime":"PRESENCE_OBSERVATION","input_request":"Check if docs/normalization-presence-beta.txt is present right now.","requested_target":"docs/normalization-presence-beta.txt","expected_surface_expression":"check","expected_canonical_operation":"observe_presence","expected_status":"NORMALIZED","allowed_canonical_operations":["observe_presence"]},
        {"task_id":"norm-holdout-003","regime":"PRESENCE_OBSERVATION","input_request":"Verify that docs/normalization-presence-gamma.txt can be found in the repository.","requested_target":"docs/normalization-presence-gamma.txt","expected_surface_expression":"verify","expected_canonical_operation":"observe_presence","expected_status":"NORMALIZED","allowed_canonical_operations":["observe_presence"]},
        {"task_id":"norm-holdout-004","regime":"PRESENCE_OBSERVATION","input_request":"Confirm whether docs/normalization-presence-delta.txt exists at this time.","requested_target":"docs/normalization-presence-delta.txt","expected_surface_expression":"confirm","expected_canonical_operation":"observe_presence","expected_status":"NORMALIZED","allowed_canonical_operations":["observe_presence"]},
        {"task_id":"norm-holdout-005","regime":"DIRECT_INSPECT","input_request":"Inspect docs/normalization-control-epsilon.md.","requested_target":"docs/normalization-control-epsilon.md","expected_surface_expression":"inspect","expected_canonical_operation":"inspect","expected_status":"NORMALIZED","allowed_canonical_operations":["inspect"]},
        {"task_id":"norm-holdout-006","regime":"DIRECT_AMEND","input_request":"Amend docs/normalization-control-zeta.md.","requested_target":"docs/normalization-control-zeta.md","expected_surface_expression":"amend","expected_canonical_operation":"amend","expected_status":"NORMALIZED","allowed_canonical_operations":["amend"]},
        {"task_id":"norm-holdout-007","regime":"DIRECT_INDEX","input_request":"Index docs/normalization-control-eta.md.","requested_target":"docs/normalization-control-eta.md","expected_surface_expression":"index","expected_canonical_operation":"index","expected_status":"NORMALIZED","allowed_canonical_operations":["index"]},
        {"task_id":"norm-holdout-008","regime":"DIRECT_DISPATCH","input_request":"Dispatch docs/normalization-control-theta.md.","requested_target":"docs/normalization-control-theta.md","expected_surface_expression":"dispatch","expected_canonical_operation":"dispatch","expected_status":"NORMALIZED","allowed_canonical_operations":["dispatch"]},
        {"task_id":"norm-holdout-009","regime":"AMBIGUOUS","input_request":"Check and inspect docs/normalization-ambiguous-iota.md.","requested_target":"docs/normalization-ambiguous-iota.md","expected_surface_expression":None,"expected_canonical_operation":None,"expected_status":"AMBIGUOUS","allowed_canonical_operations":[]},
        {"task_id":"norm-holdout-010","regime":"AMBIGUOUS","input_request":"Verify or confirm docs/normalization-ambiguous-kappa.md.","requested_target":"docs/normalization-ambiguous-kappa.md","expected_surface_expression":None,"expected_canonical_operation":None,"expected_status":"AMBIGUOUS","allowed_canonical_operations":[]},
        {"task_id":"norm-holdout-011","regime":"UNSUPPORTED","input_request":"Archive docs/normalization-unsupported-lambda.md.","requested_target":"docs/normalization-unsupported-lambda.md","expected_surface_expression":"archive","expected_canonical_operation":None,"expected_status":"UNRESOLVED","allowed_canonical_operations":[]},
        {"task_id":"norm-holdout-012","regime":"UNSUPPORTED","input_request":"Delete docs/normalization-unsupported-mu.md.","requested_target":"docs/normalization-unsupported-mu.md","expected_surface_expression":"delete","expected_canonical_operation":None,"expected_status":"UNRESOLVED","allowed_canonical_operations":[]}
    ]


def historical_projection() -> dict[str, Any]:
    old_tasks = {t["task_id"]: t for t in read_json(HISTORICAL_TASKS)["tasks"]}
    rows = []
    for row in read_json(HISTORICAL_RUN / "matrix.json")["rows"]:
        task = old_tasks[row["task_id"]]
        expected_canonical = "observe_presence" if task["regime"] == "OPERATION_VS_STATE_PREDICATE" else task["expected_action"].casefold()
        norm = normalize_operation_expression(row["baseline"]["observed"]["action"], task["input_request"])
        rows.append({"task_id": row["task_id"], "request": task["input_request"], "expected_historical_surface_action": task["expected_action"], "observed_historical_action": row["baseline"]["observed"]["action"], "proposed_action_expression": row["baseline"]["observed"]["action"], "normalized": norm, "expected_canonical_operation": expected_canonical, "canonical_operation_correct": norm["status"] == "NORMALIZED" and norm["canonical_operation"] == expected_canonical, "object_expression": row["baseline"]["observed"]["object_expression"], "object_expression_exact": row["baseline"]["object_expression_exact"], "would_downstream_binding_succeed": bool(norm["status"] == "NORMALIZED" and norm["canonical_operation"] == expected_canonical and row["baseline"]["object_expression_exact"]), "classification": "LEXICAL_ONLY_VARIATION" if row["baseline"]["observed"]["action"].casefold() == task["expected_action"].casefold() and row["baseline"]["action_exact"] is False else ("SEMANTICALLY_EQUIVALENT_OPERATION" if norm["status"] == "NORMALIZED" and norm["canonical_operation"] == expected_canonical else "SEMANTICALLY_WRONG_OPERATION")})
    patched_rows = []
    for row in read_json(HISTORICAL_RUN / "matrix.json")["rows"]:
        task = old_tasks[row["task_id"]]
        expected_canonical = "observe_presence" if task["regime"] == "OPERATION_VS_STATE_PREDICATE" else task["expected_action"].casefold()
        norm = normalize_operation_expression(row["patched"]["observed"]["action"], task["input_request"])
        patched_rows.append({"task_id": row["task_id"], "observed_action": row["patched"]["observed"]["action"], "normalized": norm, "expected_canonical_operation": expected_canonical, "canonical_operation_correct": norm["status"] == "NORMALIZED" and norm["canonical_operation"] == expected_canonical})
    return {"schema":"zth_action_expression_historical_projection_v0","historical_scores_unchanged":True,"baseline_rows":rows,"baseline_canonical_correct":sum(x["canonical_operation_correct"] for x in rows),"patched_rows":patched_rows,"patched_canonical_correct":sum(x["canonical_operation_correct"] for x in patched_rows),"source_run":str(HISTORICAL_RUN.relative_to(ROOT))}


def invariants() -> dict[str, Any]:
    checks = []
    def check(name: str, passed: bool, reason: str) -> None:
        checks.append({"check": name, "passed": passed, "reason": reason})
    presence_request = "Determine whether docs/example.txt exists right now."
    inspect_request = "Inspect docs/example.txt."
    unknown_request = "Ask about docs/example.txt."
    check("presence context", all(normalize_operation_expression(x, presence_request)["status"] == "NORMALIZED" for x in ("determine","check","verify","confirm","find","exists")), "presence expressions normalize only in presence context")
    check("direct context", all(normalize_operation_expression(x, inspect_request)["status"] == "NORMALIZED" for x in ("inspect",)), "direct operation normalizes in direct context")
    check("case variation", normalize_operation_expression("AmEnD", "Amend docs/example.txt.")["canonical_operation"] == "amend", "case-folding is explicit")
    check("outside presence gated", all(normalize_operation_expression(x, inspect_request)["status"] == "UNRESOLVED" for x in ("find","exists")), "state/presence expressions do not generalize outside presence context")
    check("unknown context unresolved", normalize_operation_expression("inspect", unknown_request)["status"] == "UNRESOLVED", "unknown context fails closed")
    check("unknown unresolved", normalize_operation_expression("archive", unknown_request)["status"] == "UNRESOLVED", "unknown expression has no fallback")
    check("multi-operation ambiguous", normalize_operation_expression("check", "Check and inspect docs/example.txt.")["status"] == "AMBIGUOUS", "multiple operation request fails closed")
    check("empty unresolved", normalize_operation_expression("")["status"] == "UNRESOLVED", "empty expression fails closed")
    check("direct operations distinct", all(normalize_operation_expression(x)["canonical_operation"] != "observe_presence" for x in ("inspect","amend","index","dispatch")), "direct operations do not collapse to presence")
    check("authority independent", all("allowed" not in normalize_operation_expression(x, presence_request) for x in ("check","inspect")), "normalizer emits only normalization status and never authority")
    return {"schema":"zth_operation_normalizer_invariants_v0","checks":checks,"pass":all(x["passed"] for x in checks),"model_calls":0,"teacher_calls":0,"tool_calls":0}


def prepare_stage_a(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("stage A output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    projection = historical_projection()
    checks = invariants()
    if not checks["pass"] or projection["baseline_canonical_correct"] != 8:
        raise RuntimeError("model-free normalization freeze failed")
    write_json(out / "historical_projection.json", projection)
    write_json(out / "normalizer_invariants.json", checks)
    manifest = {"schema":"zth_action_expression_normalization_stage_a_manifest_v0","status":"prepared_model_free","prepared_at":now(),"prepared_from_git_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"rules_sha256":digest_file(RULES),"historical_projection_sha256":digest_file(out / "historical_projection.json"),"invariants_sha256":digest_file(out / "normalizer_invariants.json"),"historical_raw_responses_modified":False,"model_calls_made":0,"teacher_calls_made":0,"tool_calls_made":0,"qualification_change":False}
    manifest["manifest_sha256"] = digest_bytes(canonical({**manifest,"manifest_sha256":None}))
    write_json(out / "stage_a_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status":"prepared","model_calls":0,"teacher_calls":0,"tool_calls":0})


def prepare_stage_b(out: Path) -> None:
    stage_a = out.parent.parent / "stage_a" if out.parent.name == "run_20260823T090000Z" else RUN.parent / "stage_a"
    if not (stage_a / "stage_a_manifest.json").exists():
        stage_a = RUN.parent / "stage_a"
    if not read_json(stage_a / "normalizer_invariants.json")["pass"]:
        raise RuntimeError("stage A invariants not passing")
    tasks = frozen_holdout()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("stage B output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    write_json(FRESH_TASKS, {"schema":"zth_action_expression_normalization_holdout_v0","teacher_visible":False,"tasks":tasks,"evaluator_separate":True})
    write_json(out / "schema.json", SCHEMA)
    for task in tasks:
        td = out / "tasks" / task["task_id"]
        td.mkdir(parents=True, exist_ok=True)
        (td / "prompt.txt").write_text(semantic_prompt(task["input_request"]), encoding="utf-8")
        write_json(td / "runtime_task.json", {"task_id":task["task_id"],"input_request":task["input_request"],"requested_target":task["requested_target"],"authority_record":{"allowed_canonical_operations":task["allowed_canonical_operations"],"allowed_targets":[task["requested_target"]]}})
        write_json(td / "evaluator.json", task)
    manifest = {"schema":"zth_action_expression_normalization_stage_b_manifest_v0","status":"prepared_frozen_holdout","prepared_at":now(),"prepared_from_git_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"stage_a_manifest_sha256":digest_file(stage_a / "stage_a_manifest.json"),"rules_sha256":digest_file(RULES),"holdout_sha256":digest_file(FRESH_TASKS),"schema_sha256":digest_file(out / "schema.json"),"task_order":[x["task_id"] for x in tasks],"task_count":12,"planned_model_calls":12,"model_calls_made":0,"teacher_calls_made":0,"tool_calls_made":0,"retries":0,"external_calls":0,"model_output_granted_authority":0,"qualification_change":False,"prompt_hashes":{x["task_id"]:digest_file(out / "tasks" / x["task_id"] / "prompt.txt") for x in tasks}}
    manifest["manifest_sha256"] = digest_bytes(canonical({**manifest,"manifest_sha256":None}))
    write_json(out / "manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status":"prepared","model_calls":0,"teacher_calls":0,"tool_calls":0,"retries":0})


def preflight(out: Path) -> tuple[Any,str]:
    spec = runtime.worker_spec()
    models = decomposition.list_models(spec, timeout=30)
    candidate = next((x for x in models.get("data",[]) if x.get("id") == MODEL_ID), None)
    meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != PARAMS:
        raise RuntimeError("model binding mismatch")
    telemetry_url = base.telemetry_base_url()
    telemetry = base.telemetry_preflight(telemetry_url)
    write_json(out / "preflight.json", {"model_meta":meta,"telemetry":telemetry,"model_id":MODEL_ID,"gpu_uuid":GPU_UUID})
    return spec, telemetry_url


def parse_output(content: str) -> tuple[dict[str,str]|None,bool,bool,list[str]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return None,False,False,[str(exc)]
    valid = isinstance(value,dict) and set(value)=={"action_expression","object_expression"} and all(isinstance(value.get(k),str) for k in ("action_expression","object_expression"))
    return (value if valid else None),True,valid,[] if valid else ["two-string action-expression contract failed"]


def execute(out: Path) -> None:
    manifest = read_json(out / "manifest.json")
    if manifest["manifest_sha256"] != digest_bytes(canonical({**manifest,"manifest_sha256":None})):
        raise RuntimeError("manifest hash mismatch")
    spec, telemetry_url = preflight(out)
    for task_id in manifest["task_order"]:
        td = out / "tasks" / task_id
        if (td / "response.json").exists():
            raise RuntimeError(f"refusing replay {task_id}")
        prompt = (td / "prompt.txt").read_text(encoding="utf-8")
        write_json(td / "call_started.json", {"task_id":task_id,"started_at":now(),"prompt_sha256":digest_file(td / "prompt.txt"),"schema_sha256":digest_file(out / "schema.json"),"supplier_id":"qwen3_1_7b_action_expression_supplier","model_id":MODEL_ID})
        started = time.monotonic()
        sampler = PowerSampler(lambda: read_gpu_power(GPU_UUID,base_url=telemetry_url),expected_gpu_uuid=GPU_UUID,sample_interval_seconds=POWER_INTERVAL)
        sampler.start()
        response = decomposition.structured_call(spec,prompt,response_format(),MAX_TOKENS,TIMEOUT)
        captured = time.monotonic()
        samples = sampler.stop()
        energy = integrate_energy_joules(samples,sample_interval_seconds=POWER_INTERVAL,expected_gpu_uuid=GPU_UUID)
        metadata = response.metadata()
        metadata["request_url"] = None
        write_json(td / "response.json", {"status":response.status,"content":response.content,"metadata":metadata,"wall_elapsed_ms":round((captured-started)*1000,3),"gross_energy_joules":energy})
        write_json(td / "power_samples.json", {"measurement_level":2,"measurement_boundary":"gpu_device_only","gpu_uuid":GPU_UUID,"samples":[{"timestamp_utc":s.timestamp_utc,"power_watts":s.power_watts,"gpu_uuid":s.gpu_uuid,"sequence":s.sequence} for s in samples]})
    write_json(out / "lifecycle.json", {"status":"execution_complete","model_calls":12,"teacher_calls":0,"tool_calls":0,"retries":0})


def closeout(out: Path) -> None:
    tasks = {x["task_id"]:x for x in read_json(FRESH_TASKS)["tasks"]}
    rows=[]
    for task_id,task in tasks.items():
        raw=read_json(out / "tasks" / task_id / "response.json")
        observed,parse_valid,contract_valid,diagnostics=parse_output(raw.get("content",""))
        norm=normalize_operation_expression(observed.get("action_expression") if observed else "",task["input_request"])
        object_exact=bool(contract_valid and observed and " ".join(observed["object_expression"].casefold().split()) == task["requested_target"].casefold())
        canonical_correct=bool(task["expected_canonical_operation"] is not None and norm["status"] == "NORMALIZED" and norm["canonical_operation"] == task["expected_canonical_operation"])
        normalization_decision_correct=bool(norm["status"] == task["expected_status"] and norm["canonical_operation"] == task["expected_canonical_operation"])
        authority_broadening=bool(norm["status"] == "NORMALIZED" and norm["canonical_operation"] not in task["allowed_canonical_operations"] and object_exact)
        row={"task_id":task_id,"regime":task["regime"],"request":task["input_request"],"observed":observed,"parse_valid":parse_valid,"contract_valid":contract_valid,"action_expression_usable":bool(contract_valid and observed and observed["action_expression"].strip()),"object_expression_exact":object_exact,"normalizer":norm,"canonical_operation_correct":canonical_correct,"normalization_decision_correct":normalization_decision_correct,"safe_target_binding":bool(object_exact and norm["status"]=="NORMALIZED" and norm["canonical_operation"] in task["allowed_canonical_operations"]),"surface_action_exact":bool(contract_valid and task.get("expected_surface_expression") and observed and observed["action_expression"].casefold()==task["expected_surface_expression"].casefold()),"failed_closed":bool(task["regime"] in {"AMBIGUOUS","UNSUPPORTED"} and norm["status"] in {"AMBIGUOUS","UNRESOLVED"}),"authority_broadening":authority_broadening,"latency_ms":raw.get("wall_elapsed_ms"),"gross_energy_joules":raw.get("gross_energy_joules"),"diagnostics":diagnostics}
        rows.append(row)
        write_json(out / "tasks" / task_id / "scorecard.json",row)
    def subset(regime=None): return [r for r in rows if regime is None or r["regime"]==regime]
    def metrics(values):
        lat=[x["latency_ms"] for x in values]; energy=[x["gross_energy_joules"] for x in values]
        applicable=sum(tasks[x["task_id"]]["expected_canonical_operation"] is not None for x in values)
        return {"tasks":len(values),"parse_valid":sum(x["parse_valid"] for x in values),"contract_valid":sum(x["contract_valid"] for x in values),"action_expression_usable":sum(x["action_expression_usable"] for x in values),"object_expression_exact":sum(x["object_expression_exact"] for x in values),"normalized":sum(x["normalizer"]["status"]=="NORMALIZED" for x in values),"unresolved":sum(x["normalizer"]["status"]=="UNRESOLVED" for x in values),"ambiguous":sum(x["normalizer"]["status"]=="AMBIGUOUS" for x in values),"canonical_operation_correct":sum(x["canonical_operation_correct"] for x in values),"canonical_operation_applicable":applicable,"normalization_decision_correct":sum(x["normalization_decision_correct"] for x in values),"safe_target_binding":sum(x["safe_target_binding"] for x in values),"surface_action_exact":sum(x["surface_action_exact"] for x in values),"failed_closed":sum(x["failed_closed"] for x in values),"authority_broadening":sum(x["authority_broadening"] for x in values),"latency_ms":{"mean":statistics.mean(lat),"median":statistics.median(lat),"p95":sorted(lat)[min(len(lat)-1,round((len(lat)-1)*.95))]},"energy_joules":{"mean":statistics.mean(energy),"median":statistics.median(energy),"total":sum(energy)}}
    m=metrics(rows); by={reg:metrics(subset(reg)) for reg in sorted({x["regime"] for x in rows})}
    success = m["canonical_operation_correct"] == 8 and m["canonical_operation_applicable"] == 8 and m["normalization_decision_correct"] == 12 and by["PRESENCE_OBSERVATION"]["canonical_operation_correct"] == 4 and all(by[k]["canonical_operation_correct"] == 1 for k in ("DIRECT_AMEND","DIRECT_DISPATCH","DIRECT_INDEX","DIRECT_INSPECT")) and by["AMBIGUOUS"]["failed_closed"] == 2 and by["UNSUPPORTED"]["failed_closed"] == 2 and m["authority_broadening"] == 0
    aggregate={"schema":"zth_action_expression_normalization_aggregate_v0","overall":m,"by_regime":by,"canonical_operation_accuracy":"%d/%d applicable"%(m["canonical_operation_correct"],m["canonical_operation_applicable"]),"normalization_decision_accuracy":"%d/%d"%(m["normalization_decision_correct"],len(rows)),"authority_broadening_events":m["authority_broadening"],"MODEL_OUTPUT_GRANTED_AUTHORITY":0,"model_calls":12,"teacher_calls":0,"tool_calls":0,"retries":0,"external_calls":0,"qualification_change":False,"action_expression_interface_demonstrated":m["action_expression_usable"]==12,"deterministic_operation_normalization_demonstrated":success,"action_field_role_overload_resolved_in_experimental_interface":success,"intelligence_surface_reduced":success,"primary_characterization":"ACTION_EXPRESSION_NORMALIZATION_BOUNDARY_DEMONSTRATED" if success else "ACTION_EXPRESSION_NORMALIZATION_BOUNDARY_PARTIAL","next_decision":"SUPERVISED_REVIEW_OF_ACTION_EXPRESSION_INTERFACE" if success else ("REFINE_OR_REJECT_OPERATION_NORMALIZATION_ONTOLOGY" if m["authority_broadening"] else "DIAGNOSE_ACTION_EXPRESSION_SUPPLIER_FLOOR")}
    write_json(out / "aggregate.json",aggregate); write_json(out / "matrix.json",{"schema":"zth_action_expression_normalization_matrix_v0","rows":rows,"aggregate":aggregate})
    write_json(out / "lifecycle.json", {"status":"closeout_complete","model_calls":12,"teacher_calls":0,"tool_calls":0,"retries":0,"qualification_change":False})
    print(json.dumps(aggregate,indent=2,sort_keys=True))


def main():
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True); g.add_argument("--prepare-stage-a",action="store_true"); g.add_argument("--prepare-stage-b",action="store_true"); g.add_argument("--execute",action="store_true"); g.add_argument("--closeout",action="store_true"); p.add_argument("--output-dir",type=Path,default=RUN); args=p.parse_args()
    if args.prepare_stage_a: prepare_stage_a(args.output_dir)
    elif args.prepare_stage_b: prepare_stage_b(args.output_dir)
    elif args.execute: execute(args.output_dir)
    else: closeout(args.output_dir)


if __name__ == "__main__":
    main()
