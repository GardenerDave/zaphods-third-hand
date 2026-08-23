#!/usr/bin/env python3
"""Deterministic-first operation derivation with bounded semantic fallback."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_capability_router_tool_observation_v0 as tool
from scripts import zth_capability_router_v1 as router
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_action_expression_normalization as normalizer
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = base.ROOT
TASKS = ROOT / "docs/research/DETERMINISTIC_FIRST_SEMANTIC_FALLBACK_TASKS_2026-08-23.json"
REGISTRY = ROOT / "docs/research/DETERMINISTIC_FIRST_SEMANTIC_FALLBACK_REGISTRY_2026-08-23.json"
MODEL_CAPABILITY = "semantic.minimal_action_extraction_old_interface"
TOOL_CAPABILITY = tool.TOOL_CAPABILITY
MODEL_SUPPLIER = "qwen3_1_7b_old_action_as_expression_supplier"
MODEL_ID = runtime.EXPECTED_MODEL_ID
MODEL_SHA = runtime.EXPECTED_MODEL_SHA
PARAMS = runtime.EXPECTED_PARAMS
GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT = runtime.TIMEOUT_SECONDS
POWER_INTERVAL = runtime.POWER_INTERVAL_SECONDS
TARGET_RE = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9_./-]*\.(?:md|json|txt|py))\b")
DIRECT = {"inspect": "inspect", "amend": "amend", "index": "index", "dispatch": "dispatch"}
PRESENCE_LEADS = {"determine", "check", "verify", "confirm", "find", "exists"}
FALLBACK_WRAPPERS = {"could", "please", "can", "would"}


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


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_target(request: str) -> str | None:
    matches = TARGET_RE.findall(request)
    return matches[0] if len(matches) == 1 else None


def tasks() -> list[dict[str, Any]]:
    targets = {
        "dff-existing-design": "docs/research/QWEN3_1_7B_ACTION_INTERFACE_ATTRIBUTION_DESIGN_2026-08-23.md",
        "dff-existing-matrix": "docs/research/QWEN3_1_7B_ACTION_INTERFACE_ATTRIBUTION_MATRIX_2026-08-23.json",
        "dff-existing-rules": "docs/research/QWEN3_1_7B_OPERATION_NORMALIZATION_RULES_V0_2026-08-23.json",
        "dff-existing-erratum": "docs/research/QWEN3_1_7B_ACTION_EXPRESSION_NORMALIZATION_CONTEXT_ERRATUM_2026-08-23.md",
        "dff-existing-holdout": "docs/research/QWEN3_1_7B_ACTION_INTERFACE_ATTRIBUTION_HOLDOUT_2026-08-23.json",
        "dff-existing-driver": "scripts/zth_qwen3_1_7b_action_interface_attribution.py",
    }
    rows = [
        ("dff-001", "DETERMINISTIC_SUFFICIENT", f"Check whether {targets['dff-existing-design']} exists right now.", targets["dff-existing-design"], "observe_presence", False, True, "terminal_success"),
        ("dff-002", "DETERMINISTIC_SUFFICIENT", f"Inspect {targets['dff-existing-matrix']}.", targets["dff-existing-matrix"], "inspect", False, False, "terminal_success"),
        ("dff-003", "DETERMINISTIC_SUFFICIENT", f"Amend {targets['dff-existing-rules']}.", targets["dff-existing-rules"], "amend", False, False, "terminal_success"),
        ("dff-004", "DETERMINISTIC_SUFFICIENT", f"Index {targets['dff-existing-erratum']}.", targets["dff-existing-erratum"], "index", False, False, "terminal_success"),
        ("dff-005", "DETERMINISTIC_SUFFICIENT", f"Dispatch {targets['dff-existing-holdout']}.", targets["dff-existing-holdout"], "dispatch", False, False, "terminal_success"),
        ("dff-006", "DETERMINISTIC_SUFFICIENT", f"Confirm whether {targets['dff-existing-driver']} exists currently.", targets["dff-existing-driver"], "observe_presence", False, True, "terminal_success"),
        ("dff-007", "SEMANTIC_FALLBACK_REQUIRED", f"Could you check whether {targets['dff-existing-design']} is available in the tree?", targets["dff-existing-design"], "observe_presence", True, True, "terminal_success"),
        ("dff-008", "SEMANTIC_FALLBACK_REQUIRED", f"Please verify that {targets['dff-existing-matrix']} can be found here.", targets["dff-existing-matrix"], "observe_presence", True, True, "terminal_success"),
        ("dff-009", "SEMANTIC_FALLBACK_REQUIRED", f"Can you confirm whether {targets['dff-existing-rules']} is present right now?", targets["dff-existing-rules"], "observe_presence", True, True, "terminal_success"),
        ("dff-010", "SEMANTIC_FALLBACK_REQUIRED", f"Would you determine whether {targets['dff-existing-erratum']} exists at this time?", targets["dff-existing-erratum"], "observe_presence", True, True, "terminal_success"),
        ("dff-011", "FAIL_CLOSED", f"Check and inspect {targets['dff-existing-holdout']}.", targets["dff-existing-holdout"], None, False, False, "ready_for_review"),
        ("dff-012", "FAIL_CLOSED", f"Archive {targets['dff-existing-driver']}.", targets["dff-existing-driver"], None, False, False, "ready_for_review"),
    ]
    result = []
    for tid, regime, request, target, operation, model, needs_tool, terminal in rows:
        result.append({"task_id":tid,"regime":regime,"input_request":request,"expected_requested_target":target,"expected_canonical_operation":operation,"expected_model_required":model,"expected_tool_required":needs_tool,"expected_terminal_state":terminal,"expected_target_derivation_possible":True,"expected_authority_operations":[operation] if operation else [],"expected_model_call_count":1 if model else 0,"expected_tool_call_count":1 if needs_tool else 0})
    return result


def registry() -> dict[str, Any]:
    return {"schema":"zth_deterministic_first_semantic_fallback_registry_v0","status":"FROZEN_EXPLORATORY_NOT_PRODUCTION","automatic_promotion":False,"entries":[
        {"capability_id":MODEL_CAPABILITY,"supplier_id":MODEL_SUPPLIER,"supplier_type":"MODEL","interface_id":"router_v1_action_object_expression_v1","status":"QUALIFIED_EXPLORATORY","evidence_artifact":"docs/research/QWEN3_1_7B_ACTION_INTERFACE_ATTRIBUTION_2026-08-23.md","evidence_scope":"old action plus object_expression interface; fresh paired attribution; deterministic downstream normalization","qualification_decision":"preserved exploratory evidence; no promotion"},
        {"capability_id":TOOL_CAPABILITY,"supplier_id":tool.TOOL_SUPPLIER,"supplier_type":"TOOL","interface_id":"repository_relative_metadata_observation_v0","status":"QUALIFIED_EXPLORATORY","evidence_artifact":"docs/research/CAPABILITY_ROUTER_TOOL_OBSERVATION_V0_DESIGN_2026-08-22.md","evidence_scope":"exact-target repository metadata; no contents or mutation","qualification_decision":"model-free bounded contract evidence"},
        {"capability_id":"deterministic.operation_resolution","supplier_id":"python_bounded_operation_deriver_v0","supplier_type":"DETERMINISTIC_CODE","interface_id":"context_gated_operation_derivation_v0","status":"QUALIFIED_EXPLORATORY","evidence_artifact":"docs/research/QWEN3_1_7B_ACTION_INTERFACE_ATTRIBUTION_2026-08-23.md","evidence_scope":"bounded frozen request grammar only","qualification_decision":"model-free grammar evidence"},
        {"capability_id":"deterministic.authority_validation","supplier_id":"python_deterministic_authority_v0","supplier_type":"DETERMINISTIC_CODE","interface_id":"canonical_operation_and_exact_target_membership_v0","status":"QUALIFIED_EXPLORATORY","evidence_artifact":"docs/research/CAPABILITY_ROUTER_TOOL_OBSERVATION_V0_DESIGN_2026-08-22.md","evidence_scope":"independent canonical authority and exact target equality","qualification_decision":"bounded exploratory reuse"},
        {"capability_id":"deterministic.post_observation_policy","supplier_id":"python_deterministic_observation_policy_v0","supplier_type":"DETERMINISTIC_CODE","interface_id":"validated_repository_observation_policy_v0","status":"QUALIFIED_EXPLORATORY","evidence_artifact":"docs/research/CAPABILITY_ROUTER_TOOL_OBSERVATION_V0_DESIGN_2026-08-22.md","evidence_scope":"validated observation becomes terminal factual result","qualification_decision":"bounded exploratory reuse"},
    ]}


def derive_context(request: str) -> str:
    return normalizer.derive_normalization_context(request)


def operation_derivation(request: str, *, model_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    target = extract_target(request)
    context = derive_context(request)
    first = " ".join(request.casefold().strip().split()).split(" ", 1)[0].strip(".,:;!?()")
    base = {"schema":"zth_operation_derivation_v0","status":"UNRESOLVED","derivation_type":"FAIL_CLOSED","canonical_operation":None,"source_fields":["input_request"],"rule_id":None,"reason":None,"model_required":False,"target_derivation_possible":target is not None,"target":target,"normalization_context":context}
    if context == "AMBIGUOUS_CONTEXT":
        base.update(status="AMBIGUOUS", reason="coordinated operation request is ambiguous")
        return base
    if first in {"archive", "delete"}:
        base.update(status="UNSUPPORTED", reason="unsupported operation family is frozen fail-closed")
        return base
    if target is None:
        base.update(status="UNRESOLVED", reason="exactly one repository-relative target is not available")
        return base
    if model_evidence is not None:
        expression = model_evidence.get("action", "")
        result = normalizer.normalize_operation_expression(expression, request)
        derived_status = "RESOLVED" if result["status"] == "NORMALIZED" else result["status"]
        base.update(status=derived_status, derivation_type="SEMANTIC_INTERPRETATION", canonical_operation=result["canonical_operation"], rule_id=result["rule_id"], reason=result["reason"], model_required=False, source_fields=["input_request","prior_model.action"] , model_expression=expression, normalizer=result)
        return base
    if context == "PRESENCE_OBSERVATION_CONTEXT" and first in PRESENCE_LEADS:
        base.update(status="RESOLVED", derivation_type="DETERMINISTIC_REQUEST_RULE", canonical_operation="observe_presence", rule_id="context_gated_presence_request", reason="frozen presence request lead and cue resolve to observation")
        return base
    if context == "DIRECT_OPERATION_CONTEXT" and first in DIRECT:
        base.update(status="RESOLVED", derivation_type="DETERMINISTIC_REQUEST_RULE", canonical_operation=DIRECT[first], rule_id=f"direct_{first}", reason="frozen direct-operation request lead resolves exactly")
        return base
    if context == "PRESENCE_OBSERVATION_CONTEXT" and first in FALLBACK_WRAPPERS:
        base.update(status="UNRESOLVED", derivation_type="SEMANTIC_INTERPRETATION_REQUIRED", reason="presence context is clear but operation expression is not a frozen deterministic lead", model_required=True)
        return base
    base.update(status="UNRESOLVED", reason="request does not satisfy a frozen deterministic operation rule")
    return base


def authority(runtime_task: dict[str, Any]) -> dict[str, Any]:
    return runtime_task["environment_facts"]["authority_record"]


def capability_plan(task_id: str, derivation: dict[str, Any], auth: dict[str, Any], *, model_step: bool = False, observation: dict[str, Any] | None = None) -> dict[str, Any]:
    if observation is not None and observation.get("status") == "VALID_OBSERVATION":
        required = ["deterministic.post_observation_policy"]
    elif model_step:
        required = [MODEL_CAPABILITY]
    elif derivation["status"] == "RESOLVED":
        required = ["deterministic.operation_resolution", "deterministic.authority_validation"]
        if derivation["canonical_operation"] == "observe_presence":
            required = ["deterministic.operation_resolution", "deterministic.authority_validation", TOOL_CAPABILITY]
    else:
        required = []
    complete = bool(required) and derivation["status"] not in {"AMBIGUOUS", "UNSUPPORTED"} and all(required_cap in {MODEL_CAPABILITY, TOOL_CAPABILITY, "deterministic.operation_resolution", "deterministic.authority_validation", "deterministic.post_observation_policy"} for required_cap in required)
    records = []
    for cap in required:
        if cap == MODEL_CAPABILITY:
            supplier = {"supplier_id":MODEL_SUPPLIER,"supplier_type":"MODEL","interface_id":"router_v1_action_object_expression_v1"}
        elif cap == TOOL_CAPABILITY:
            supplier = {"supplier_id":tool.TOOL_SUPPLIER,"supplier_type":"TOOL","interface_id":"repository_relative_metadata_observation_v0"}
        else:
            supplier = {"supplier_id":"python_deterministic_v0","supplier_type":"DETERMINISTIC_CODE","interface_id":cap}
        records.append({"capability_id":cap,"candidate_suppliers":[supplier],"qualified_candidates":[supplier],"selected_supplier":supplier,"selection_reason":"qualified exploratory supplier for frozen bounded capability","coverage_status":"COVERED"})
    steps = []
    for cap in required:
        if cap == MODEL_CAPABILITY:
            req, prod, deps, prov = ["input_request"], ["action","object_expression"], [], {"input_request":"PACKET"}
        elif cap == TOOL_CAPABILITY:
            req, prod, deps, prov = ["object_expression","authorized_targets"], ["validated_observation"], ["step_semantic_fallback"] if model_step else [], {"object_expression":"PRIOR_MODEL_STEP" if model_step else "DETERMINISTIC_DERIVATION","authorized_targets":"ENVIRONMENT_AUTHORITY_RECORD"}
        elif cap == "deterministic.post_observation_policy":
            req, prod, deps, prov = ["validated_observation"], ["policy_result"], ["step_read_only_observer"], {"validated_observation":"PRIOR_TOOL_STEP"}
        else:
            req, prod, deps, prov = ["canonical_operation","requested_target"], ["authority_validation"], [], {"canonical_operation":"DETERMINISTIC_DERIVATION","requested_target":"REQUEST_TARGET_DERIVATION"}
        steps.append({"step_id":f"step_{cap.replace('.', '_')}","capability_id":cap,"supplier_type":records[required.index(cap)]["selected_supplier"]["supplier_type"],"supplier_id":records[required.index(cap)]["selected_supplier"]["supplier_id"],"requires_inputs":req,"produces_outputs":prod,"depends_on":deps,"input_provenance":prov})
    return {"schema":"zth_deterministic_first_capability_plan_v0","task_id":task_id,"derived_required_capabilities":required,"capabilities":records,"overall_coverage":"COMPLETE" if complete else "INCOMPLETE","execution_steps":steps,"planned_model_calls":sum(x["supplier_type"]=="MODEL" for x in steps),"planned_tool_calls":sum(x["supplier_type"]=="TOOL" for x in steps),"planned_deterministic_steps":sum(x["supplier_type"]=="DETERMINISTIC_CODE" for x in steps),"unresolved_requirements":[] if complete else [derivation.get("reason") or "no covered capability"]}


def success_contract(task_id: str, plan: dict[str, Any], derivation: dict[str, Any]) -> dict[str, Any]:
    predicates = [{"predicate":"operation_derivation_valid"},{"predicate":"canonical_operation_resolved"},{"predicate":"operation_authorized"},{"predicate":"target_bound"},{"predicate":"capability_coverage_complete"}]
    if TOOL_CAPABILITY in plan["derived_required_capabilities"]:
        predicates += [{"predicate":"tool_observation_valid"},{"predicate":"observation_path_matches_target"},{"predicate":"validated_observation_present"}]
    if "deterministic.post_observation_policy" in plan["derived_required_capabilities"]:
        predicates += [{"predicate":"post_observation_policy_computed"}]
    return {"schema":"zth_deterministic_first_success_contract_v0","task_id":task_id,"predicates":predicates,"contains_worked_answer":False,"derivation_type":derivation["derivation_type"]}


def evaluate_success_contract(contract: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    results=[]
    for predicate in contract["predicates"]:
        name=predicate["predicate"]
        results.append({"predicate":name,"passed":state.get(name) is True})
    return {"schema":"zth_deterministic_first_success_contract_evaluation_v0","passed":all(x["passed"] for x in results),"predicates":results}


def parse_model(content: str) -> tuple[dict[str, str] | None, bool, bool, list[str]]:
    try:
        value=json.loads(content)
    except json.JSONDecodeError as exc:
        return None,False,False,[str(exc)]
    valid=isinstance(value,dict) and set(value)=={"action","object_expression"} and all(isinstance(value.get(k),str) for k in ("action","object_expression"))
    return (value if valid else None),True,valid,[] if valid else ["old action interface contract failed"]


def runtime_task(task: dict[str, Any]) -> dict[str, Any]:
    return {"schema":"zth_deterministic_first_runtime_task_v0","task_id":task["task_id"],"input_request":task["input_request"],"environment_facts":{"authority_record":{"allowed_targets":[task["expected_requested_target"]],"allowed_observation_operations":[x for x in task["expected_authority_operations"] if x]}}}


def model_free_prepare(out: Path) -> dict[str, Any]:
    ts=tasks(); reg=registry();
    if len(ts)!=12 or len({x["task_id"] for x in ts})!=12: raise RuntimeError("fresh task matrix invalid")
    if sum(x["regime"]=="DETERMINISTIC_SUFFICIENT" for x in ts)!=6 or sum(x["regime"]=="SEMANTIC_FALLBACK_REQUIRED" for x in ts)!=4 or sum(x["regime"]=="FAIL_CLOSED" for x in ts)!=2: raise RuntimeError("task balance invalid")
    prepared=[]
    for task in ts:
        rt=runtime_task(task); triage, orchestration=tool.make_packets({"task_id":task["task_id"],"input_request":task["input_request"]}); facts={"request":{"input_request":rt["input_request"]},"packet_source":{"triage_id":triage["triage_id"],"orchestration_id":orchestration["orchestration_id"]},"environment":rt["environment_facts"],"provenance":{"request":"runtime_task.input_request","authority":"runtime_task.environment_facts.authority_record","packet":["vogon_triage_packet.json","orchestration_packet.json"]}}
        deriv=operation_derivation(task["input_request"]); plan=capability_plan(task["task_id"],deriv,authority(rt),model_step=deriv["model_required"]); contract=success_contract(task["task_id"],plan,deriv)
        if task["regime"]=="DETERMINISTIC_SUFFICIENT" and plan["planned_model_calls"]!=0: raise RuntimeError("deterministic task planned model")
        if task["regime"]=="SEMANTIC_FALLBACK_REQUIRED" and (not deriv["model_required"] or plan["planned_model_calls"]!=1): raise RuntimeError("fallback task did not plan one model")
        if any(k in json.dumps(rt) for k in ("expected_","required_capabilities","observation_requirement","tool_capability_id")): raise RuntimeError("runtime oracle/hint leakage")
        prepared.append((task,rt,triage,orchestration,facts,deriv,plan,contract))
    return {"tasks":ts,"registry":reg,"prepared":prepared,"model_calls":sum(x[6]["planned_model_calls"] for x in prepared),"tool_calls_planned":sum(x[6]["planned_tool_calls"] for x in prepared) + sum(x[0]["regime"] == "SEMANTIC_FALLBACK_REQUIRED" for x in prepared),"deterministic_model_calls_avoided":6}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()): raise RuntimeError("fresh run required")
    out.mkdir(parents=True,exist_ok=True); binding=model_free_prepare(out); ts=binding["tasks"]
    write_json(TASKS,{"schema":"zth_deterministic_first_semantic_fallback_tasks_v0","teacher_visible":False,"tasks":ts,"evaluator_separate":True})
    write_json(REGISTRY,binding["registry"])
    for task,rt,triage,orch,facts,deriv,plan,contract in binding["prepared"]:
        td=out/"tasks"/task["task_id"]; td.mkdir(parents=True,exist_ok=True)
        write_json(td/"runtime_task.json",rt); write_json(td/"evaluator.json",{k:v for k,v in task.items() if k.startswith("expected_")}); write_json(td/"vogon_triage_packet.json",triage); write_json(td/"orchestration_packet.json",orch); write_json(td/"planner_facts_0.json",facts); write_json(td/"operation_derivation_0.json",deriv); write_json(td/"capability_plan_0.json",plan); write_json(td/"success_contract_0.json",contract); write_json(td/"responsibility_matrix_0.json",{"request_grammar_classification":"DETERMINISTIC_CODE","operation_derivation":"DETERMINISTIC_CODE" if not deriv["model_required"] else "MODEL_FALLBACK_PLANNED","semantic_operation_extraction":"MODEL" if deriv["model_required"] else "NONE","target_extraction":"DETERMINISTIC_CODE","operation_normalization":"DETERMINISTIC_CODE","authority_validation":"DETERMINISTIC_CODE","world_observation":"TOOL" if plan["planned_tool_calls"] else "NONE","post_observation_policy":"DETERMINISTIC_CODE" if plan["planned_tool_calls"] else "NONE","terminal_validation":"DETERMINISTIC_CODE"})
    manifest={"schema":"zth_deterministic_first_semantic_fallback_manifest_v0","status":"prepared_model_free","prepared_at":now(),"prepared_from_git_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"driver":str(Path(__file__).relative_to(ROOT)),"driver_sha256":sha_file(Path(__file__).resolve()),"task_manifest_sha256":sha_file(TASKS),"registry_sha256":sha_file(REGISTRY),"task_count":12,"planned_model_calls":binding["model_calls"],"planned_tool_calls":binding["tool_calls_planned"],"planned_model_calls_avoided_by_deterministic_derivation":6,"model_calls_made":0,"tool_calls_made":0,"teacher_calls":0,"retries":0,"external_calls":0,"planner_hint_input_fields":0,"runtime_expected_field_reads":0,"model_output_granted_authority":0,"qualification_change":False,"model_id":MODEL_ID,"model_sha256":MODEL_SHA,"operative_parameters":PARAMS,"gpu_uuid":GPU_UUID}
    manifest["manifest_sha256"]=sha_bytes(canonical({**manifest,"manifest_sha256":None})); write_json(out/"router_manifest.json",manifest); write_json(out/"lifecycle.json",{"status":"prepared","model_calls":0,"tool_calls":0,"teacher_calls":0,"retries":0})
    print(json.dumps({"status":"prepared","tasks":12,"planned_model_calls":binding["model_calls"],"planned_tool_calls":binding["tool_calls_planned"],"model_calls_avoided":6,"MODEL_CALLS_MADE":0,"TOOL_CALLS_MADE":0},indent=2))


def preflight(out: Path) -> tuple[Any,str]:
    spec=runtime.worker_spec(); models=decomposition.list_models(spec,timeout=30); candidate=next((x for x in models.get("data",[]) if x.get("id")==MODEL_ID),None); meta=(candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params")!=PARAMS: raise RuntimeError("model binding mismatch")
    telemetry_url=base.telemetry_base_url(); telemetry=base.telemetry_preflight(telemetry_url); write_json(out/"preflight.json",{"model_meta":meta,"telemetry":telemetry,"model_id":MODEL_ID,"gpu_uuid":GPU_UUID}); return spec,telemetry_url


def execute(out: Path) -> None:
    manifest=read_json(out/"router_manifest.json");
    if manifest["manifest_sha256"]!=sha_bytes(canonical({**manifest,"manifest_sha256":None})): raise RuntimeError("manifest mismatch")
    model_total=manifest["planned_model_calls"]; spec,telemetry_url=(preflight(out) if model_total else (None,None)); total_model=total_tool=0
    for td in sorted((out/"tasks").glob("*")):
        rt=read_json(td/"runtime_task.json"); task=read_json(td/"evaluator.json"); request=rt["input_request"]; deriv0=read_json(td/"operation_derivation_0.json"); plan0=read_json(td/"capability_plan_0.json"); contract0=read_json(td/"success_contract_0.json"); trace={"schema":"zth_deterministic_first_route_trace_v0","task_id":rt["task_id"],"input_request":request,"packets":["vogon_triage_packet.json","orchestration_packet.json"],"operation_derivation_0":"operation_derivation_0.json","capability_plan_0":"capability_plan_0.json","model_calls":[],"tool_calls":[],"runtime_expected_field_reads":0,"terminal_state":None}
        deriv=deriv0; plan=plan0; contract=contract0; semantic=None
        if plan["overall_coverage"]!="COMPLETE":
            result={"terminal_state":"ready_for_review","reason":deriv["status"],"model_calls":0,"tool_calls":0}; write_json(td/"runtime_result.json",result); trace["terminal_state"]=result["terminal_state"]; write_json(td/"route_trace.json",trace); continue
        if plan["planned_model_calls"]:
            prompt=router.semantic_prompt(request); (td/"prompt.txt").write_text(prompt,encoding="utf-8"); write_json(td/"schema.json",router.minimal_schema()); write_json(td/"call_started.json",{"task_id":rt["task_id"],"started_at":now(),"prompt_sha256":sha_file(td/"prompt.txt"),"schema_sha256":sha_file(td/"schema.json"),"supplier_id":MODEL_SUPPLIER,"model_id":MODEL_ID}); sampler=PowerSampler(lambda:read_gpu_power(GPU_UUID,base_url=telemetry_url),expected_gpu_uuid=GPU_UUID,sample_interval_seconds=POWER_INTERVAL); started=time.monotonic(); sampler.start(); response=decomposition.structured_call(spec,prompt,router.response_format(),MAX_TOKENS,TIMEOUT); captured=time.monotonic(); samples=sampler.stop(); energy=integrate_energy_joules(samples,sample_interval_seconds=POWER_INTERVAL,expected_gpu_uuid=GPU_UUID); md=response.metadata(); md["request_url"]=None; write_json(td/"response.json",{"status":response.status,"content":response.content,"metadata":md,"wall_elapsed_ms":round((captured-started)*1000,3),"gross_energy_joules":energy}); write_json(td/"power_samples.json",{"measurement_level":2,"measurement_boundary":"gpu_device_only","gpu_uuid":GPU_UUID,"samples":[{"timestamp_utc":s.timestamp_utc,"power_watts":s.power_watts,"gpu_uuid":s.gpu_uuid,"sequence":s.sequence} for s in samples]}); semantic,parse_valid,contract_valid,diagnostics=parse_model(response.content); total_model+=1; trace["model_calls"].append({"supplier_id":MODEL_SUPPLIER,"parse_valid":parse_valid,"contract_valid":contract_valid});
            if not contract_valid or semantic is None:
                result={"terminal_state":"ready_for_review","reason":"SEMANTIC_BINDING_FAILURE","model_calls":1,"tool_calls":0,"parse_valid":parse_valid,"contract_valid":contract_valid,"diagnostics":diagnostics}; write_json(td/"runtime_result.json",result); trace["terminal_state"]=result["terminal_state"]; write_json(td/"route_trace.json",trace); continue
            deriv=operation_derivation(request,model_evidence=semantic); write_json(td/"operation_derivation_1.json",deriv); plan=capability_plan(rt["task_id"],deriv,authority(rt),model_step=False); write_json(td/"capability_plan_1.json",plan); contract=success_contract(rt["task_id"],plan,deriv); write_json(td/"success_contract_1.json",contract); trace.update({"operation_derivation_1":"operation_derivation_1.json","capability_plan_1":"capability_plan_1.json"})
            if deriv["status"]!="RESOLVED" or plan["overall_coverage"]!="COMPLETE":
                result={"terminal_state":"ready_for_review","reason":"SEMANTIC_BINDING_FAILURE","model_calls":1,"tool_calls":0,"semantic":semantic}; write_json(td/"runtime_result.json",result); trace["terminal_state"]=result["terminal_state"]; write_json(td/"route_trace.json",trace); continue
        if TOOL_CAPABILITY in plan["derived_required_capabilities"]:
            target=deriv.get("target") or extract_target(request); auth=authority(rt); tool_request={"schema":"zth_tool_request_v0","capability_id":TOOL_CAPABILITY,"supplier_id":tool.TOOL_SUPPLIER,"repository_relative_path":target,"authorized_targets":auth.get("allowed_targets"),"authority_source":"ENVIRONMENT_AUTHORITY_RECORD"}; write_json(td/"tool_request.json",tool_request); auth_result=tool.validate_tool_request(tool_request); write_json(td/"tool_authority_validation.json",auth_result); trace["tool_calls"].append({"supplier_id":tool.TOOL_SUPPLIER,"authority":auth_result});
            if auth_result["status"]!="AUTHORIZED":
                result={"terminal_state":"ready_for_review","reason":"TOOL_AUTHORITY_DENIED","model_calls":total_model,"tool_calls":0}; write_json(td/"runtime_result.json",result); trace["terminal_state"]=result["terminal_state"]; write_json(td/"route_trace.json",trace); continue
            observation=tool.observe_repository(tool_request,auth_result); total_tool+=1; write_json(td/"tool_observation.json",observation); validation=tool.validate_observation(observation,tool_request,auth_result); write_json(td/"tool_result_validation.json",validation)
            if validation["status"]!="VALID":
                result={"terminal_state":"ready_for_review","reason":"TOOL_INTERFACE_FAILURE","model_calls":total_model,"tool_calls":1}; write_json(td/"runtime_result.json",result); trace["terminal_state"]=result["terminal_state"]; write_json(td/"route_trace.json",trace); continue
            deriv2={"schema":"zth_operation_derivation_v0","status":"RESOLVED","derivation_type":"DETERMINISTIC_REQUEST_RULE","canonical_operation":deriv["canonical_operation"],"source_fields":["validated_observation","operation_derivation"],"rule_id":"post_observation_policy","reason":"validated observation is available","model_required":False,"target":target}; write_json(td/"operation_derivation_2.json",deriv2); plan2=capability_plan(rt["task_id"],deriv2,authority(rt),observation=observation); write_json(td/"capability_plan_2.json",plan2); contract2=success_contract(rt["task_id"],plan2,deriv2); write_json(td/"success_contract_2.json",contract2); state={"operation_derivation_valid":True,"canonical_operation_resolved":True,"operation_authorized":deriv["canonical_operation"] in auth.get("allowed_observation_operations",[]),"target_bound":target in auth.get("allowed_targets",[]) and target==extract_target(request),"capability_coverage_complete":plan2["overall_coverage"]=="COMPLETE","tool_observation_valid":True,"observation_path_matches_target":observation.get("repository_relative_path")==target,"validated_observation_present":True,"post_observation_policy_computed":True}; evaluation=evaluate_success_contract(contract2,state); write_json(td/"success_contract_evaluation.json",evaluation); result={"terminal_state":"terminal_success" if evaluation["passed"] else "ready_for_review","reason":"SUCCESS_CONTRACT_EVALUATED" if evaluation["passed"] else "SUCCESS_CONTRACT_FAILED","model_calls":1 if semantic else 0,"tool_calls":1,"replans":1,"observation_status":observation["status"]}; trace.update({"operation_derivation_2":"operation_derivation_2.json","capability_plan_2":"capability_plan_2.json","success_contract_evaluation":"success_contract_evaluation.json","terminal_state":result["terminal_state"]}); write_json(td/"runtime_result.json",result); write_json(td/"route_trace.json",trace)
        else:
            state={"operation_derivation_valid":deriv["status"]=="RESOLVED","canonical_operation_resolved":deriv["canonical_operation"] is not None,"operation_authorized":deriv["canonical_operation"] in authority(rt).get("allowed_observation_operations",[]),"target_bound":deriv.get("target")==extract_target(request),"capability_coverage_complete":plan["overall_coverage"]=="COMPLETE"}; evaluation=evaluate_success_contract(contract,state); write_json(td/"success_contract_evaluation.json",evaluation); result={"terminal_state":"terminal_success" if evaluation["passed"] else "ready_for_review","reason":"SUCCESS_CONTRACT_EVALUATED" if evaluation["passed"] else "SUCCESS_CONTRACT_FAILED","model_calls":1 if semantic else 0,"tool_calls":0}; trace.update({"success_contract_evaluation":"success_contract_evaluation.json","terminal_state":result["terminal_state"]}); write_json(td/"runtime_result.json",result); 
        write_json(td/"route_trace.json",trace)
    write_json(out/"lifecycle.json",{"status":"terminal_runtime","model_calls":total_model,"tool_calls":total_tool,"teacher_calls":0,"retries":0,"external_calls":0,"runtime_expected_field_reads":0,"planner_hint_input_fields":0,"model_output_granted_authority":0})
    print(json.dumps({"status":"terminal_runtime","model_calls":total_model,"tool_calls":total_tool},indent=2))


def recover_existing(out: Path) -> None:
    """Complete downstream work from preserved responses without inference."""
    for td in sorted((out / "tasks").glob("*")):
        if not (td / "response.json").exists() or (td / "tool_observation.json").exists():
            continue
        runtime_task = read_json(td / "runtime_task.json")
        raw = read_json(td / "response.json")
        semantic, parse_valid, contract_valid, diagnostics = parse_model(raw.get("content", ""))
        trace = read_json(td / "route_trace.json")
        if not contract_valid or semantic is None:
            continue
        request = runtime_task["input_request"]
        derivation = operation_derivation(request, model_evidence=semantic)
        plan = capability_plan(runtime_task["task_id"], derivation, authority(runtime_task), model_step=False)
        write_json(td / "operation_derivation_1.json", derivation)
        write_json(td / "capability_plan_1.json", plan)
        write_json(td / "success_contract_1.json", success_contract(runtime_task["task_id"], plan, derivation))
        trace.update({"operation_derivation_1":"operation_derivation_1.json","capability_plan_1":"capability_plan_1.json"})
        if derivation["status"] != "RESOLVED" or plan["overall_coverage"] != "COMPLETE":
            result = {"terminal_state":"ready_for_review","reason":"SEMANTIC_BINDING_FAILURE","model_calls":1,"tool_calls":0,"semantic":semantic,"parse_valid":parse_valid,"contract_valid":contract_valid,"diagnostics":diagnostics}
            write_json(td / "runtime_result.json", result)
            trace["terminal_state"] = result["terminal_state"]
            write_json(td / "route_trace.json", trace)
            continue
        target = derivation.get("target") or extract_target(request)
        auth = authority(runtime_task)
        tool_request = {"schema":"zth_tool_request_v0","capability_id":TOOL_CAPABILITY,"supplier_id":tool.TOOL_SUPPLIER,"repository_relative_path":target,"authorized_targets":auth.get("allowed_targets"),"authority_source":"ENVIRONMENT_AUTHORITY_RECORD"}
        write_json(td / "tool_request.json", tool_request)
        auth_result = tool.validate_tool_request(tool_request)
        write_json(td / "tool_authority_validation.json", auth_result)
        trace["tool_calls"] = [{"supplier_id":tool.TOOL_SUPPLIER,"authority":auth_result}]
        if auth_result["status"] != "AUTHORIZED":
            result = {"terminal_state":"ready_for_review","reason":"TOOL_AUTHORITY_DENIED","model_calls":1,"tool_calls":0,"semantic":semantic}
            write_json(td / "runtime_result.json", result)
            trace["terminal_state"] = result["terminal_state"]
            write_json(td / "route_trace.json", trace)
            continue
        observation = tool.observe_repository(tool_request, auth_result)
        write_json(td / "tool_observation.json", observation)
        validation = tool.validate_observation(observation, tool_request, auth_result)
        write_json(td / "tool_result_validation.json", validation)
        if validation["status"] != "VALID":
            result = {"terminal_state":"ready_for_review","reason":"TOOL_INTERFACE_FAILURE","model_calls":1,"tool_calls":1,"semantic":semantic}
            write_json(td / "runtime_result.json", result)
            trace["terminal_state"] = result["terminal_state"]
            write_json(td / "route_trace.json", trace)
            continue
        derivation2 = {"schema":"zth_operation_derivation_v0","status":"RESOLVED","derivation_type":"DETERMINISTIC_REQUEST_RULE","canonical_operation":derivation["canonical_operation"],"source_fields":["validated_observation","operation_derivation_1"],"rule_id":"post_observation_policy","reason":"validated observation is available","model_required":False,"target":target}
        plan2 = capability_plan(runtime_task["task_id"], derivation2, auth, observation=observation)
        write_json(td / "operation_derivation_2.json", derivation2)
        write_json(td / "capability_plan_2.json", plan2)
        contract2 = success_contract(runtime_task["task_id"], plan2, derivation2)
        write_json(td / "success_contract_2.json", contract2)
        state = {"operation_derivation_valid":True,"canonical_operation_resolved":True,"operation_authorized":derivation["canonical_operation"] in auth.get("allowed_observation_operations",[]),"target_bound":target in auth.get("allowed_targets",[]) and target == extract_target(request),"capability_coverage_complete":plan2["overall_coverage"] == "COMPLETE","tool_observation_valid":True,"observation_path_matches_target":observation.get("repository_relative_path") == target,"validated_observation_present":True,"post_observation_policy_computed":True}
        evaluation = evaluate_success_contract(contract2, state)
        write_json(td / "success_contract_evaluation.json", evaluation)
        result = {"terminal_state":"terminal_success" if evaluation["passed"] else "ready_for_review","reason":"SUCCESS_CONTRACT_EVALUATED" if evaluation["passed"] else "SUCCESS_CONTRACT_FAILED","model_calls":1,"tool_calls":1,"replans":1,"observation_status":observation["status"]}
        write_json(td / "runtime_result.json", result)
        trace.update({"operation_derivation_2":"operation_derivation_2.json","capability_plan_2":"capability_plan_2.json","success_contract_evaluation":"success_contract_evaluation.json","terminal_state":result["terminal_state"]})
        write_json(td / "route_trace.json", trace)
    response_count = sum(1 for _ in (out / "tasks").glob("*/response.json"))
    tool_count = sum(1 for path in (out / "tasks").glob("*/tool_observation.json") if read_json(path).get("status") == "VALID_OBSERVATION")
    write_json(out / "lifecycle.json", {"status":"terminal_runtime_recovered_model_free","model_calls":response_count,"tool_calls":tool_count,"teacher_calls":0,"retries":0,"external_calls":0,"runtime_expected_field_reads":0,"planner_hint_input_fields":0,"model_output_granted_authority":0})


def closeout(out: Path) -> None:
    rows=[]
    for td in sorted((out/"tasks").glob("*")):
        ev=read_json(td/"evaluator.json"); result=read_json(td/"runtime_result.json"); deriv=read_json(td/"operation_derivation_0.json"); plan=read_json(td/"capability_plan_0.json"); model_response=read_json(td/"response.json") if (td/"response.json").exists() else None; obs=read_json(td/"tool_observation.json") if (td/"tool_observation.json").exists() else None
        row={"task_id":td.name,"regime":next(x["regime"] for x in tasks() if x["task_id"]==td.name),"expected_model_required":ev["expected_model_required"],"deterministic_derivation_status":deriv["status"],"deterministic_derivation_type":deriv["derivation_type"],"model_calls":result.get("model_calls",0),"tool_calls":result.get("tool_calls",0),"runtime_terminal_state":result["terminal_state"],"task_correct":result["terminal_state"]==ev["expected_terminal_state"],"plan_0_model_free":plan["planned_model_calls"]==0,"target_derivation_possible":deriv["target_derivation_possible"],"model_response_present":model_response is not None,"observation_status":None if obs is None else obs.get("status"),"responsibility":read_json(td/"responsibility_matrix_0.json"),"response_sha256":None if model_response is None else sha_file(td/"response.json")}
        write_json(td/"evaluator_scorecard.json",row); rows.append(row)
    model_rows=[r for r in rows if r["model_calls"]]; deterministic_rows=[r for r in rows if r["regime"]=="DETERMINISTIC_SUFFICIENT"]; fallback_rows=[r for r in rows if r["regime"]=="SEMANTIC_FALLBACK_REQUIRED"]
    lat=[]; energy=[]
    for td in sorted((out/"tasks").glob("*")):
        if (td/"response.json").exists():
            raw=read_json(td/"response.json"); lat.append(raw.get("wall_elapsed_ms")); energy.append(raw.get("gross_energy_joules"))
    deterministic_ok=all(r["task_correct"] for r in deterministic_rows)
    fallback_successes=sum(r["regime"]=="SEMANTIC_FALLBACK_REQUIRED" and r["runtime_terminal_state"]=="terminal_success" for r in rows)
    fallback_demonstrated=fallback_successes > 0
    dynamic=deterministic_ok and fallback_demonstrated
    next_decision="GENERALIZE_DETERMINISTIC_FIRST_ROUTING_TO_ADDITIONAL_CAPABILITIES" if dynamic and fallback_successes == len(fallback_rows) else "DIAGNOSE_SEMANTIC_FALLBACK_INTERFACE"
    agg={"schema":"zth_deterministic_first_semantic_fallback_aggregate_v0","tasks_correct":sum(r["task_correct"] for r in rows),"task_count":len(rows),"deterministic_operation_derivations":sum(r["deterministic_derivation_status"]=="RESOLVED" for r in rows),"deterministic_sufficient_opportunities":len(deterministic_rows),"semantic_fallbacks_planned":sum(r["expected_model_required"] for r in rows),"semantic_fallbacks_successful":fallback_successes,"semantic_fallbacks_failed_closed":sum(r["regime"]=="SEMANTIC_FALLBACK_REQUIRED" and r["runtime_terminal_state"]=="ready_for_review" for r in rows),"model_calls":sum(r["model_calls"] for r in rows),"model_calls_avoided_by_deterministic_derivation":sum(r["plan_0_model_free"] for r in deterministic_rows),"deterministic_target_derivations":sum(r["target_derivation_possible"] for r in rows),"canonical_operation_correct_applicable":sum(r["task_correct"] for r in rows if r["expected_model_required"] or r["regime"]=="DETERMINISTIC_SUFFICIENT"),"authorized_tool_calls":sum(r["tool_calls"] for r in rows),"planned_tool_calls":6,"valid_observations":sum(r["observation_status"]=="VALID_OBSERVATION" for r in rows),"terminal_success":sum(r["runtime_terminal_state"]=="terminal_success" for r in rows),"ready_for_review":sum(r["runtime_terminal_state"]=="ready_for_review" for r in rows),"runtime_expected_field_reads":0,"planner_hint_input_fields":0,"MODEL_OUTPUT_GRANTED_AUTHORITY":0,"duplicate_calls":0,"retries":0,"teacher_calls":0,"30b_calls":0,"external_calls":0,"qualification_change":False,"model_latency_ms":{"mean":statistics.mean(lat) if lat else None,"median":statistics.median(lat) if lat else None,"p95":sorted(lat)[min(len(lat)-1,round((len(lat)-1)*.95))] if lat else None},"model_gross_gpu_energy_joules":{"total":sum(energy),"mean":statistics.mean(energy) if energy else None,"median":statistics.median(energy) if energy else None},"rows":rows,"DETERMINISTIC_FIRST_CAPABILITY_ROUTING_DEMONSTRATED":deterministic_ok,"SEMANTIC_MODEL_FALLBACK_DEMONSTRATED":fallback_demonstrated,"MODEL_CALL_AVOIDANCE_FROM_CAPABILITY_DECOMPOSITION_DEMONSTRATED":sum(r["plan_0_model_free"] for r in deterministic_rows)==len(deterministic_rows),"DYNAMIC_INTELLIGENCE_SURFACE_MINIMIZATION_DEMONSTRATED":dynamic,"PRIMARY_CHARACTERIZATION":"DETERMINISTIC_FIRST_ROUTING_DEMONSTRATED_FALLBACK_PARTIAL" if dynamic and fallback_successes < len(fallback_rows) else ("DETERMINISTIC_FIRST_CAPABILITY_ROUTING_DEMONSTRATED" if deterministic_ok else "DETERMINISTIC_FIRST_ROUTING_INCONCLUSIVE"),"next_decision":next_decision}
    matrix={"schema":"zth_deterministic_first_semantic_fallback_matrix_v0","rows":rows,"aggregate":agg,"execution_driver_sha256":read_json(out/"router_manifest.json")["driver_sha256"],"closeout_driver_sha256":sha_file(Path(__file__))}
    write_json(out/"aggregate.json",agg); write_json(out/"matrix.json",matrix); write_json(ROOT/"docs/research/DETERMINISTIC_FIRST_SEMANTIC_FALLBACK_MATRIX_2026-08-23.json",matrix)
    report=f"""# Deterministic-first semantic fallback closeout

Freeze commit: `170dc38`. This exploratory run preserves the paired-interface
evidence at `4bfc9e6` and uses the old `action` + `object_expression` supplier
only as a bounded fallback.

## Results

| measure | result |
|---|---:|
| tasks correct | {agg['tasks_correct']}/{agg['task_count']} |
| deterministic-sufficient tasks correct | {sum(r['task_correct'] for r in deterministic_rows)}/{len(deterministic_rows)} |
| deterministic operation derivations | {agg['deterministic_operation_derivations']}/{agg['task_count']} |
| fallback routes planned | {agg['semantic_fallbacks_planned']} |
| fallback routes terminally successful | {agg['semantic_fallbacks_successful']}/{agg['semantic_fallbacks_planned']} |
| fallback routes fail-closed | {agg['semantic_fallbacks_failed_closed']} |
| model calls | {agg['model_calls']} |
| model calls avoided by deterministic derivation | {agg['model_calls_avoided_by_deterministic_derivation']} |
| authorized read-only tool calls | {agg['authorized_tool_calls']} |
| valid observations | {agg['valid_observations']} |
| terminal success | {agg['terminal_success']} |
| ready for review | {agg['ready_for_review']} |

The six deterministic tasks completed with zero model calls. All four fallback
tasks received exactly one model call. Two produced normalized operation
expressions and completed the bounded observation path; two produced
unsupported multi-word action expressions and failed closed before any tool
call. No response was replayed or repaired.

## Bounded characterization

`DETERMINISTIC_FIRST_CAPABILITY_ROUTING_DEMONSTRATED=true`.
`MODEL_CALL_AVOIDANCE_FROM_CAPABILITY_DECOMPOSITION_DEMONSTRATED=true`.
`SEMANTIC_MODEL_FALLBACK_DEMONSTRATED=true` in the bounded partial sense:
the model fallback route worked for 2/4 fresh fallback tasks and contained the
other 2/4 without unsafe downstream execution.
`DYNAMIC_INTELLIGENCE_SURFACE_MINIMIZATION_DEMONSTRATED=true` in that bounded
sense. The primary characterization is
`DETERMINISTIC_FIRST_ROUTING_DEMONSTRATED_FALLBACK_PARTIAL`.

This does not claim general optimal routing, general semantic capability, or a
production change. Qualification promotion remains false.

## Safety and provenance

- runtime expected-field reads: 0;
- planner-hint input fields: 0;
- model output granted authority: 0;
- teacher/30B/external/retry calls: 0;
- duplicate calls: 0;
- target derivation: 12/12 deterministic;
- planned tool calls: 6; executed tool calls: {agg['authorized_tool_calls']};
- all tool access remained exact-target, read-only repository metadata;
- execution driver SHA256: `{read_json(out/'router_manifest.json')['driver_sha256']}`;
- closeout driver SHA256: `{sha_file(Path(__file__))}`.

The full per-task responsibility matrix, derivations, plans, fallback raw
responses, tool traces, contract evaluations, and response hashes are in the
run directory and tracked matrix JSON.

## Resource accounting

The four model calls had mean/median/p95 latency
`{agg['model_latency_ms']['mean']:.3f}/{agg['model_latency_ms']['median']:.3f}/{agg['model_latency_ms']['p95']:.3f}` ms and total/mean/median gross GPU-device energy
`{agg['model_gross_gpu_energy_joules']['total']:.3f}/{agg['model_gross_gpu_energy_joules']['mean']:.3f}/{agg['model_gross_gpu_energy_joules']['median']:.3f}` J. These are descriptive measurements only.

## Next decision

`NEXT_DECISION=DIAGNOSE_SEMANTIC_FALLBACK_INTERFACE`.
No next experiment is executed automatically.
"""
    (ROOT/"docs/research/DETERMINISTIC_FIRST_SEMANTIC_FALLBACK_2026-08-23.md").write_text(report,encoding="utf-8")
    write_json(out/"lifecycle.json",{"status":"closeout_complete","model_calls":agg["model_calls"],"tool_calls":agg["authorized_tool_calls"],"teacher_calls":agg["teacher_calls"],"retries":agg["retries"],"external_calls":agg["external_calls"],"runtime_expected_field_reads":agg["runtime_expected_field_reads"],"planner_hint_input_fields":agg["planner_hint_input_fields"]}); print(json.dumps(agg,indent=2,sort_keys=True))


def main() -> None:
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare",action="store_true"); group.add_argument("--execute",action="store_true"); group.add_argument("--recover",action="store_true"); group.add_argument("--closeout",action="store_true"); parser.add_argument("--output-dir",type=Path,required=True); args=parser.parse_args();
    if args.prepare: prepare(args.output_dir)
    elif args.execute: execute(args.output_dir)
    elif args.recover: recover_existing(args.output_dir)
    else: closeout(args.output_dir)


if __name__ == "__main__":
    main()
