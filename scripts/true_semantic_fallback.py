#!/usr/bin/env python3
"""First bounded semantic fallback whose missing fact is operation class."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import deterministic_first_confirmation as confirmation
from scripts import zth_capability_router_tool_observation_v0 as tool
from scripts import zth_deterministic_first_semantic_fallback as fallback
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = runtime.ROOT
RUN = ROOT / ".work/model_size_supplier_floor/true_semantic_fallback/run_20260823T150000Z"
RUNTIME_CASES = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_RUNTIME_CASES_2026-08-23.json"
EVALUATOR_CASES = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_EVALUATOR_CASES_2026-08-23.json"
REGISTRY = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_REGISTRY_V0_2026-08-23.json"
MODEL_CAPABILITY = "semantic.bounded_operation_classification"
MODEL_SUPPLIER = "qwen3_1_7b_bounded_operation_class_candidate_supplier"
MODEL_INTERFACE = "bounded_operation_class_candidate_v0"
MODEL_ID = runtime.EXPECTED_MODEL_ID
MODEL_SHA = runtime.EXPECTED_MODEL_SHA
PARAMS = runtime.EXPECTED_PARAMS
GPU_UUID = runtime.EXPECTED_GPU_UUID
MAX_TOKENS = runtime.MAX_OUTPUT_TOKENS
TIMEOUT = runtime.TIMEOUT_SECONDS
POWER_INTERVAL = runtime.POWER_INTERVAL_SECONDS
TARGET_RE = fallback.TARGET_RE
RISKY_WORDS = {"amend", "amended", "dispatch", "dispatched", "archive", "archived", "delete", "deleted"}
ENUM = {"observe_presence", "inspect", "unresolved"}


def now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_specs() -> list[tuple[str, str, str, str | None]]:
    cases = [
        ("tsf-001", "TRUE_FALLBACK_PRESENCE", "Is docs/research/TRUE_FALLBACK_PRESENCE_AMBER_2026-08-23.md around in this tree?", "observe_presence"),
        ("tsf-002", "TRUE_FALLBACK_PRESENCE", "Do we have docs/research/TRUE_FALLBACK_PRESENCE_BRONZE_2026-08-23.json here?", "observe_presence"),
        ("tsf-003", "TRUE_FALLBACK_PRESENCE", "Tell me if docs/research/TRUE_FALLBACK_PRESENCE_CITRINE_2026-08-23.txt is available.", "observe_presence"),
        ("tsf-004", "TRUE_FALLBACK_INSPECT", "Take a look at docs/research/TRUE_FALLBACK_INSPECT_DAWN_2026-08-23.md.", "inspect"),
        ("tsf-005", "TRUE_FALLBACK_INSPECT", "Give docs/research/TRUE_FALLBACK_INSPECT_EMBER_2026-08-23.json a quick look.", "inspect"),
        ("tsf-006", "TRUE_FALLBACK_INSPECT", "Have a look at docs/research/TRUE_FALLBACK_INSPECT_FROST_2026-08-23.txt.", "inspect"),
        ("tsf-007", "DETERMINISTIC_CONTROL", "Determine whether docs/research/TRUE_FALLBACK_CONTROL_EXISTING_2026-08-23.md exists right now.", "observe_presence"),
        ("tsf-008", "DETERMINISTIC_CONTROL", "Inspect docs/research/TRUE_FALLBACK_CONTROL_INSPECT_2026-08-23.md.", "inspect"),
        ("tsf-009", "FAIL_CLOSED_AMBIGUOUS", "Check and inspect docs/research/TRUE_FALLBACK_AMBIGUOUS_2026-08-23.md.", None),
        ("tsf-010", "FAIL_CLOSED_UNSUPPORTED", "Delete docs/research/TRUE_FALLBACK_UNSUPPORTED_2026-08-23.md.", None),
    ]
    return cases


def runtime_cases() -> list[dict[str, Any]]:
    result = []
    for task_id, regime, request, operation in fixture_specs():
        target = TARGET_RE.findall(request)[0]
        allowed_ops = [operation] if operation else []
        result.append({
            "task_id": task_id,
            "input_request": request,
            "environment_facts": {"authority_record": {"allowed_targets": [target], "allowed_observation_operations": allowed_ops}},
        })
    return result


def evaluator_cases() -> list[dict[str, Any]]:
    expected = [
        ("tsf-001", "TRUE_FALLBACK_PRESENCE", "observe_presence", True, True, True, True),
        ("tsf-002", "TRUE_FALLBACK_PRESENCE", "observe_presence", True, True, True, True),
        ("tsf-003", "TRUE_FALLBACK_PRESENCE", "observe_presence", True, True, True, True),
        ("tsf-004", "TRUE_FALLBACK_INSPECT", "inspect", True, True, False, False),
        ("tsf-005", "TRUE_FALLBACK_INSPECT", "inspect", True, True, False, False),
        ("tsf-006", "TRUE_FALLBACK_INSPECT", "inspect", True, True, False, False),
        ("tsf-007", "DETERMINISTIC_CONTROL", "observe_presence", False, True, True, True),
        ("tsf-008", "DETERMINISTIC_CONTROL", "inspect", False, True, False, False),
        ("tsf-009", "FAIL_CLOSED_AMBIGUOUS", None, False, True, False, False),
        ("tsf-010", "FAIL_CLOSED_UNSUPPORTED", None, False, True, False, False),
    ]
    return [{"task_id": tid, "regime": regime, "expected_semantic_class": op, "expected_model_required": model, "expected_routing_decision_correct": route, "expected_execution_path_complete": complete, "expected_task_terminal_success": terminal} for tid, regime, op, model, route, complete, terminal in expected]


def schema() -> dict[str, Any]:
    return {"type": "object", "properties": {"operation_class_candidate": {"type": "string", "enum": sorted(ENUM)}}, "required": ["operation_class_candidate"], "additionalProperties": False}


def response_format() -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "bounded_operation_class_candidate", "schema": schema()}}


def prompt(request: str) -> str:
    return (f"Request clause:\n{request}\n\n"
            "Classify only the requested operation class.\n"
            "observe_presence means determine whether the named target exists, is present, or is available.\n"
            "inspect means examine or look at the named target.\n"
            "unresolved means the operation class is ambiguous, unsupported, or cannot be determined safely.\n\n"
            "Return only the required structured field. Do not identify the target, choose a tool, decide authorization, or decide whether the task can be completed.\n/no_think")


def parse_response(content: str) -> tuple[str | None, bool, bool, list[str]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    valid = isinstance(value, dict) and set(value) == {"operation_class_candidate"} and isinstance(value.get("operation_class_candidate"), str)
    candidate = value.get("operation_class_candidate") if valid else None
    enum_valid = valid and candidate in ENUM
    return candidate if enum_valid else None, True, enum_valid, [] if enum_valid else ["strict operation-class contract failed"]


def preflight(request: str, authority: dict[str, Any]) -> dict[str, Any]:
    targets = TARGET_RE.findall(request)
    context = fallback.derive_context(request)
    words = set(re.findall(r"[a-z]+", request.casefold()))
    risk_status = "RISKY_OR_UNSUPPORTED" if words & RISKY_WORDS else "SAFE_BOUNDED"
    ambiguity_status = "AMBIGUOUS" if context == "AMBIGUOUS_CONTEXT" or len(targets) != 1 else "UNAMBIGUOUS"
    derivation = fallback.operation_derivation(request)
    if derivation["status"] == "RESOLVED":
        derivation_status = "RESOLVED"
        remaining = [derivation["canonical_operation"]]
    elif ambiguity_status != "UNAMBIGUOUS" or risk_status != "SAFE_BOUNDED" or context in {"UNSUPPORTED_OR_UNKNOWN_CONTEXT", "AMBIGUOUS_CONTEXT"} and derivation["status"] in {"UNSUPPORTED", "AMBIGUOUS"}:
        derivation_status = derivation["status"]
        remaining = []
    else:
        derivation_status = "UNRESOLVED"
        remaining = ["observe_presence", "inspect"]
    eligible = (len(targets) == 1 and ambiguity_status == "UNAMBIGUOUS" and risk_status == "SAFE_BOUNDED" and derivation_status == "UNRESOLVED" and len(remaining) >= 2)
    return {
        "target_status": "EXACTLY_ONE_SAFE_TARGET" if len(targets) == 1 else "TARGET_UNSAFE_OR_AMBIGUOUS",
        "target": targets[0] if len(targets) == 1 else None,
        "target_count": len(targets),
        "risk_status": risk_status,
        "ambiguity_status": ambiguity_status,
        "normalization_context": context,
        "operation_derivation_status": derivation_status,
        "remaining_candidate_operation_classes": remaining,
        "semantic_fallback_eligible": eligible,
        "model_required": eligible,
        "reason": "two bounded operation classes remain semantically plausible" if eligible else derivation.get("reason", "deterministic or fail-closed route"),
        "authority_source": "ENVIRONMENT_AUTHORITY_RECORD",
    }


def plan(task_id: str, pre: dict[str, Any], canonical_operation: str | None = None) -> dict[str, Any]:
    if pre["model_required"] and canonical_operation is None:
        required = [MODEL_CAPABILITY]
        records = [{"capability_id": MODEL_CAPABILITY, "selected_supplier": {"supplier_id": MODEL_SUPPLIER, "supplier_type": "MODEL", "interface_id": MODEL_INTERFACE}, "coverage_status": "COVERED"}]
    else:
        operation = canonical_operation or (pre["remaining_candidate_operation_classes"][0] if len(pre["remaining_candidate_operation_classes"]) == 1 else None)
        required = ["deterministic.operation_resolution", "deterministic.authority_validation"] if operation else []
        if operation == "observe_presence": required.append(tool.TOOL_CAPABILITY)
        if operation == "inspect": required.append("actuator.inspect")
        records = []
        for cap in required:
            if cap == tool.TOOL_CAPABILITY:
                selected = {"supplier_id": tool.TOOL_SUPPLIER, "supplier_type": "TOOL", "interface_id": "repository_relative_metadata_observation_v0"}
            elif cap == "actuator.inspect":
                selected = None
            else:
                selected = {"supplier_id": "python_deterministic_v0", "supplier_type": "DETERMINISTIC_CODE", "interface_id": cap}
            records.append({"capability_id": cap, "selected_supplier": selected, "coverage_status": "COVERED" if selected else "UNCOVERED"})
    complete = bool(required) and all(x["coverage_status"] == "COVERED" for x in records)
    return {"schema": "zth_true_semantic_fallback_capability_plan_v0", "task_id": task_id, "derived_required_capabilities": required, "capabilities": records, "overall_coverage": "COMPLETE" if complete else "INCOMPLETE", "execution_path_complete": complete, "routing_success": bool(canonical_operation in {"observe_presence", "inspect"} or (not pre["model_required"] and not required)), "planned_model_calls": sum(x["selected_supplier"] is not None and x["selected_supplier"]["supplier_type"] == "MODEL" for x in records), "planned_tool_calls": sum(x["selected_supplier"] is not None and x["selected_supplier"]["supplier_type"] == "TOOL" for x in records), "planned_deterministic_steps": sum(x["selected_supplier"] is not None and x["selected_supplier"]["supplier_type"] == "DETERMINISTIC_CODE" for x in records)}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()): raise RuntimeError("fresh true-fallback run required")
    cases, evaluators = runtime_cases(), evaluator_cases()
    assert len(cases) == 10 and len(evaluators) == 10
    by_eval = {x["task_id"]: x for x in evaluators}
    write_json(RUNTIME_CASES, {"schema": "zth_true_semantic_fallback_runtime_cases_v0", "cases": cases})
    write_json(EVALUATOR_CASES, {"schema": "zth_true_semantic_fallback_evaluator_cases_v0", "cases": evaluators})
    write_json(REGISTRY, {"schema": "zth_true_semantic_fallback_registry_v0", "automatic_promotion": False, "entries": [{"capability_id": MODEL_CAPABILITY, "supplier_id": MODEL_SUPPLIER, "supplier_type": "MODEL", "interface_id": MODEL_INTERFACE, "status": "EXPERIMENTAL_CANDIDATE", "evidence_artifact": "docs/research/TRUE_SEMANTIC_FALLBACK_DESIGN_2026-08-23.md", "evidence_scope": "six true-fallback operation-class cases; no target/tool/authority output", "qualification_decision": "no promotion"}, {"capability_id": tool.TOOL_CAPABILITY, "supplier_id": tool.TOOL_SUPPLIER, "supplier_type": "TOOL", "interface_id": "repository_relative_metadata_observation_v0", "status": "QUALIFIED_EXPLORATORY", "evidence_artifact": "docs/research/CAPABILITY_ROUTER_TOOL_OBSERVATION_V0_DESIGN_2026-08-22.md", "evidence_scope": "exact-target read-only repository metadata", "qualification_decision": "preserved prior evidence"}]})
    out.mkdir(parents=True, exist_ok=True)
    planned_models = planned_tools = 0
    for case in cases:
        pre = preflight(case["input_request"], case["environment_facts"]["authority_record"])
        expected = by_eval[case["task_id"]]
        if expected["regime"].startswith("TRUE_FALLBACK"):
            assert pre["semantic_fallback_eligible"] and pre["model_required"] and pre["operation_derivation_status"] == "UNRESOLVED"
            gap = {"known_facts_before_model": ["one_safe_target", "safe_bounded_request", "no_ambiguity", "no_unsupported_operation"], "unknown_decision_critical_fact": "which bounded semantic operation class the request expresses", "remaining_candidate_classes": pre["remaining_candidate_operation_classes"], "why_deterministic_resolution_is_insufficient": "request is outside the frozen deterministic operation grammar", "why_model_is_permitted": "exactly one target is safe and two bounded operation classes remain plausible"}
        else:
            gap = None
        p0 = plan(case["task_id"], pre)
        planned_models += p0["planned_model_calls"]
        planned_tools += p0["planned_tool_calls"]
        td = out / "tasks" / case["task_id"]
        write_json(td / "runtime_task.json", {k: case[k] for k in ("task_id", "input_request", "environment_facts")})
        write_json(td / "preflight.json", pre)
        write_json(td / "capability_plan_0.json", p0)
        write_json(td / "semantic_information_gap.json", gap) if gap else None
        if pre["model_required"]:
            (td / "prompt.txt").write_text(prompt(case["input_request"]), encoding="utf-8")
            write_json(td / "schema.json", schema())
        if any(key.startswith("expected_") for key in case): raise AssertionError("runtime case contains evaluator field")
    manifest = {"schema": "zth_true_semantic_fallback_manifest_v0", "status": "prepared_model_free", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "runtime_cases_sha256": sha_file(RUNTIME_CASES), "evaluator_cases_sha256": sha_file(EVALUATOR_CASES), "registry_sha256": sha_file(REGISTRY), "task_count": 10, "true_fallback_opportunities": 6, "planned_model_calls": planned_models, "stage_0_planned_tool_calls": planned_tools, "conditional_post_model_tool_calls": 3, "model_calls_made": 0, "tool_calls_made": 0, "teacher_calls_made": 0, "30b_calls_made": 0, "external_calls_made": 0, "retries": 0, "runtime_expected_field_reads": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0, "qualification_change": False, "model_id": MODEL_ID, "model_sha256": MODEL_SHA, "operative_parameters": PARAMS, "gpu_uuid": GPU_UUID, "driver_sha256": sha_file(Path(__file__))}
    manifest["manifest_sha256"] = hashlib.sha256(canonical({**manifest, "manifest_sha256": None})).hexdigest()
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls": 0, "tool_calls": 0, "teacher_calls": 0, "retries": 0})


def preflight_model(out: Path):
    spec = runtime.worker_spec()
    models = decomposition.list_models(spec, timeout=30)
    candidate = next((x for x in models.get("data", []) if x.get("id") == MODEL_ID), None)
    meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != PARAMS: raise RuntimeError("model binding mismatch")
    telemetry_url = runtime.telemetry_base_url()
    telemetry = runtime.telemetry_preflight(telemetry_url)
    write_json(out / "model_preflight.json", {"model_meta": meta, "telemetry": telemetry, "model_id": MODEL_ID, "gpu_uuid": GPU_UUID})
    return spec, telemetry_url


def execute(out: Path) -> None:
    manifest = read_json(out / "router_manifest.json")
    spec, telemetry_url = preflight_model(out) if manifest["planned_model_calls"] else (None, None)
    model_calls = tool_calls = 0
    for td in sorted((out / "tasks").glob("*")):
        rt = read_json(td / "runtime_task.json"); pre = read_json(td / "preflight.json"); p0 = read_json(td / "capability_plan_0.json")
        trace = {"schema": "zth_true_semantic_fallback_trace_v0", "task_id": rt["task_id"], "runtime_expected_field_reads": 0, "model_calls": [], "tool_calls": []}
        canonical_operation = None; candidate = None; parse_valid = contract_valid = False
        if pre["model_required"]:
            p = td / "prompt.txt"; s = td / "schema.json"
            write_json(td / "call_started.json", {"task_id": rt["task_id"], "started_at": now(), "prompt_sha256": sha_file(p), "schema_sha256": sha_file(s), "supplier_id": MODEL_SUPPLIER, "model_id": MODEL_ID})
            sampler = PowerSampler(lambda: read_gpu_power(GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=GPU_UUID, sample_interval_seconds=POWER_INTERVAL); started = time.monotonic(); sampler.start(); response = decomposition.structured_call(spec, p.read_text(encoding="utf-8"), response_format(), MAX_TOKENS, TIMEOUT); elapsed = time.monotonic() - started; samples = sampler.stop(); energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL, expected_gpu_uuid=GPU_UUID)
            metadata = response.metadata(); metadata["request_url"] = None
            write_json(td / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "wall_elapsed_ms": round(elapsed * 1000, 3), "gross_energy_joules": energy})
            write_json(td / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": GPU_UUID, "samples": [{"timestamp_utc": x.timestamp_utc, "power_watts": x.power_watts, "gpu_uuid": x.gpu_uuid, "sequence": x.sequence} for x in samples]})
            candidate, parse_valid, contract_valid, diagnostics = parse_response(response.content); model_calls += 1; trace["model_calls"].append({"parse_valid": parse_valid, "contract_valid": contract_valid})
            write_json(td / "candidate_validation.json", {"candidate": candidate, "parse_valid": parse_valid, "contract_valid": contract_valid, "enum_valid": candidate in ENUM if candidate else False, "admissible": candidate in pre["remaining_candidate_operation_classes"] if candidate else False, "diagnostics": diagnostics})
            if not contract_valid or candidate is None or candidate == "unresolved" or candidate not in pre["remaining_candidate_operation_classes"]:
                result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "SEMANTIC_CLASSIFICATION_UNRESOLVED_OR_INVALID", "model_calls": 1, "tool_calls": 0}
                write_json(td / "runtime_result.json", result); trace["terminal_state"] = result["terminal_state"]; write_json(td / "route_trace.json", trace); continue
            canonical_operation = candidate
            write_json(td / "operation_derivation_1.json", {"schema": "zth_true_semantic_fallback_operation_derivation_v0", "status": "RESOLVED", "derivation_type": "PRIOR_MODEL_STEP_DETERMINISTIC_VALIDATION", "canonical_operation": canonical_operation, "source_fields": ["preflight", "prior_model.operation_class_candidate"], "model_output_granted_authority": False})
        else:
            canonical_operation = pre["operation_derivation_status"] == "RESOLVED" and fallback.operation_derivation(rt["input_request"]).get("canonical_operation") or None
        if canonical_operation is None:
            result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "NO_ROUTABLE_OPERATION", "model_calls": model_calls and int(pre["model_required"]), "tool_calls": 0}
            write_json(td / "runtime_result.json", result); trace["terminal_state"] = result["terminal_state"]; write_json(td / "route_trace.json", trace); continue
        p1 = plan(rt["task_id"], pre, canonical_operation); write_json(td / "capability_plan_1.json", p1)
        authority = rt["environment_facts"]["authority_record"]
        if canonical_operation == "observe_presence" and p1["overall_coverage"] == "COMPLETE":
            auth, request, tool_auth, observation, count = confirmation.execute_read_only_observation(canonical_operation, pre["target"], authority)
            write_json(td / "execution_authority_validation.json", auth); write_json(td / "tool_request.json", request)
            if tool_auth is not None: write_json(td / "tool_authority_validation.json", tool_auth)
            if auth["status"] != "AUTHORIZED":
                result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": auth["status"], "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 0}; write_json(td / "runtime_result.json", result); continue
            tool_calls += count; write_json(td / "tool_observation.json", observation); validation = tool.validate_observation(observation, request, tool_auth); write_json(td / "tool_result_validation.json", validation)
            state = {"operation_resolved": True, "operation_authorized": auth["operation_authorized"], "target_bound": auth["target_authorized"], "coverage_complete": p1["overall_coverage"] == "COMPLETE", "observation_valid": validation["status"] == "VALID"}
            evaluation = confirmation.evaluate_contract(state); write_json(td / "success_contract_evaluation.json", evaluation)
            result = {"routing_success": True, "execution_path_complete": evaluation["passed"], "task_terminal_success": evaluation["passed"], "terminal_state": "terminal_success" if evaluation["passed"] else "ready_for_review", "reason": "SUCCESS_CONTRACT_EVALUATED", "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 1}
        elif canonical_operation == "inspect":
            result = {"routing_success": True, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "NO_QUALIFIED_EXECUTION_SUPPLIER", "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 0}
        else:
            result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "NO_ROUTABLE_OPERATION", "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 0}
        write_json(td / "runtime_result.json", result); trace["terminal_state"] = result["terminal_state"]; write_json(td / "route_trace.json", trace)
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "model_calls": model_calls, "tool_calls": tool_calls, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "retries": 0, "runtime_expected_field_reads": 0, "model_output_granted_authority": 0})


def closeout(out: Path) -> None:
    evaluators = {x["task_id"]: x for x in read_json(EVALUATOR_CASES)["cases"]}; rows=[]; lat=[]; energy=[]
    for td in sorted((out / "tasks").glob("*")):
        ev = evaluators[td.name]; pre = read_json(td / "preflight.json"); result = read_json(td / "runtime_result.json"); response = read_json(td / "response.json") if (td / "response.json").exists() else None; candidate = None
        if (td / "candidate_validation.json").exists(): candidate = read_json(td / "candidate_validation.json").get("candidate")
        if response: lat.append(response.get("wall_elapsed_ms")); energy.append(response.get("gross_energy_joules"))
        row = {"task_id": td.name, "regime": ev["regime"], "model_required": ev["expected_model_required"], "preflight_eligible": pre["semantic_fallback_eligible"], "model_calls": result.get("model_calls", 0), "parse_valid": None if not response else read_json(td / "candidate_validation.json").get("parse_valid"), "contract_valid": None if not response else read_json(td / "candidate_validation.json").get("contract_valid"), "observed_operation_class": candidate, "semantic_classification_correct": (candidate == ev["expected_semantic_class"]) if ev["expected_model_required"] else None, "routing_decision_correct": result["routing_success"] == ev["expected_routing_decision_correct"], "execution_path_complete": result["execution_path_complete"], "execution_path_complete_correct": result["execution_path_complete"] == ev["expected_execution_path_complete"], "task_terminal_success": result["task_terminal_success"], "task_terminal_success_correct": result["task_terminal_success"] == ev["expected_task_terminal_success"], "terminal_state": result["terminal_state"], "tool_calls": result.get("tool_calls", 0)}
        write_json(td / "evaluator_scorecard.json", row); rows.append(row)
    model_rows = [x for x in rows if x["model_required"]]; true_rows = [x for x in model_rows if x["regime"] == "TRUE_FALLBACK_PRESENCE" or x["regime"] == "TRUE_FALLBACK_INSPECT"]; presence = [x for x in model_rows if x["regime"] == "TRUE_FALLBACK_PRESENCE"]; inspect = [x for x in model_rows if x["regime"] == "TRUE_FALLBACK_INSPECT"]
    semantic_correct = sum(x["semantic_classification_correct"] for x in model_rows)
    aggregate = {"schema": "zth_true_semantic_fallback_aggregate_v0", "task_count": len(rows), "true_semantic_fallback_opportunities": len(model_rows), "model_calls_planned": 6, "model_calls_made": sum(x["model_calls"] for x in rows), "deterministic_controls_model_calls": sum(x["model_calls"] for x in rows if x["regime"] == "DETERMINISTIC_CONTROL"), "fail_closed_controls_model_calls": sum(x["model_calls"] for x in rows if x["regime"].startswith("FAIL_CLOSED")), "parse_valid_calls": sum(x["parse_valid"] is True for x in model_rows), "contract_valid_calls": sum(x["contract_valid"] is True for x in model_rows), "operation_class_candidate_accepted": sum(x["observed_operation_class"] in ENUM - {"unresolved"} for x in model_rows), "semantic_classification_correct": semantic_correct, "semantic_classification_applicable": len(model_rows), "semantic_classification_correct_presence": sum(x["semantic_classification_correct"] for x in presence), "semantic_classification_correct_inspect": sum(x["semantic_classification_correct"] for x in inspect), "model_unresolved_outputs": sum(x["observed_operation_class"] in {None, "unresolved"} for x in model_rows), "incorrect_semantic_classifications": sum(x["observed_operation_class"] not in {None, ev["expected_semantic_class"]} for x, ev in [(x, evaluators[x["task_id"]]) for x in model_rows]), "execution_coverage_complete": sum(x["execution_path_complete"] for x in rows), "execution_coverage_incomplete": sum(not x["execution_path_complete"] for x in rows), "presence_observations_executed": sum(x["regime"] == "TRUE_FALLBACK_PRESENCE" and x["tool_calls"] == 1 for x in rows), "valid_observations": sum((td / "tool_result_validation.json").exists() for td in (out / "tasks").glob("*")), "inspect_cases_correctly_no_actuator_gated": sum(x["regime"] == "TRUE_FALLBACK_INSPECT" and x["semantic_classification_correct"] and x["terminal_state"] == "ready_for_review" for x in rows), "routing_decisions_correct": sum(x["routing_decision_correct"] for x in rows), "execution_paths_complete": sum(x["execution_path_complete"] for x in rows), "task_terminal_success": sum(x["task_terminal_success"] for x in rows), "runtime_evaluator_influence": 0, "MODEL_OUTPUT_GRANTED_AUTHORITY": 0, "retries": 0, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "qualification_change": False, "model_latency_ms": {"mean": statistics.mean(lat) if lat else None, "median": statistics.median(lat) if lat else None, "p95": sorted(lat)[min(len(lat)-1, round((len(lat)-1)*0.95))] if lat else None}, "model_energy_joules": {"total": sum(energy), "mean": statistics.mean(energy) if energy else None, "median": statistics.median(energy) if energy else None}, "rows": rows}
    true_demo = semantic_correct > 0 and sum(x["routing_decision_correct"] for x in true_rows) > 0
    aggregate.update({"TRUE_SEMANTIC_FALLBACK_DEMONSTRATED": true_demo, "DECISION_CRITICAL_MODEL_SEMANTIC_CONTRIBUTION_DEMONSTRATED": true_demo, "MODEL_OUTPUT_TO_CAPABILITY_PLAN_TRANSITION_DEMONSTRATED": true_demo, "MULTI_CLASS_BOUNDED_SEMANTIC_FALLBACK_DEMONSTRATED": sum(x["semantic_classification_correct"] for x in presence) > 0 and sum(x["semantic_classification_correct"] for x in inspect) > 0, "MODEL_OUTPUT_GRANTED_AUTHORITY": 0, "next_decision": "TEST_SEMANTIC_OPERATION_CLASSIFICATION_SUPPLIER_FLOOR" if true_demo and semantic_correct == len(model_rows) else ("DIAGNOSE_GENUINE_SEMANTIC_OPERATION_CLASSIFICATION_FAILURES" if true_demo else "RECONSIDER_BOUNDED_SEMANTIC_OPERATION_INTERFACE")})
    matrix = {"schema": "zth_true_semantic_fallback_matrix_v0", "execution_driver_sha256": read_json(out / "router_manifest.json")["driver_sha256"], "closeout_driver_sha256": sha_file(Path(__file__)), "aggregate": aggregate, "rows": rows}
    write_json(out / "aggregate.json", aggregate); write_json(out / "matrix.json", matrix); write_json(out / "lifecycle.json", {"status": "closeout_complete", "model_calls": aggregate["model_calls_made"], "tool_calls": sum(x["tool_calls"] for x in rows), "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "retries": 0, "runtime_expected_field_reads": 0}); write_json(ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_MATRIX_2026-08-23.json", matrix)
    report = f"""# True semantic fallback closeout

This fresh experiment used the enum-only `{MODEL_INTERFACE}` interface. The
target was extracted deterministically; the model classified only operation
class. Historical artifacts were not replayed or rescored.

## Results

- true fallback opportunities: {aggregate['true_semantic_fallback_opportunities']}
- model calls planned/made: {aggregate['model_calls_planned']}/{aggregate['model_calls_made']}
- semantic classifications correct: {aggregate['semantic_classification_correct']}/{aggregate['semantic_classification_applicable']}
- presence classifications correct: {aggregate['semantic_classification_correct_presence']}/3
- inspect classifications correct: {aggregate['semantic_classification_correct_inspect']}/3
- deterministic-control model calls: {aggregate['deterministic_controls_model_calls']}
- fail-closed-control model calls: {aggregate['fail_closed_controls_model_calls']}
- presence observations executed: {aggregate['presence_observations_executed']}
- inspect cases correctly no-actuator gated: {aggregate['inspect_cases_correctly_no_actuator_gated']}
- routing decisions correct: {aggregate['routing_decisions_correct']}/{aggregate['task_count']}
- execution paths complete: {aggregate['execution_paths_complete']}/{aggregate['task_count']}
- task terminal successes: {aggregate['task_terminal_success']}/{aggregate['task_count']}
- model output granted authority: 0

`TRUE_SEMANTIC_FALLBACK_DEMONSTRATED={str(true_demo).lower()}`. The model was
eligible only when deterministic preflight found one safe target, no ambiguity
or risk, unresolved operation derivation, and both `observe_presence` and
`inspect` remained plausible. Correct inspect classifications were review-gated
because no inspect actuator is qualified; that is correct routing, not a model
failure.

Resource totals: model latency mean/median/p95
`{aggregate['model_latency_ms']['mean']}/{aggregate['model_latency_ms']['median']}/{aggregate['model_latency_ms']['p95']} ms`; gross GPU energy total/mean/median
`{aggregate['model_energy_joules']['total']}/{aggregate['model_energy_joules']['mean']}/{aggregate['model_energy_joules']['median']} J`.

No retries, teacher, 30B, external, destructive, or qualification actions
occurred. See the [matrix](TRUE_SEMANTIC_FALLBACK_MATRIX_2026-08-23.json) and
per-task run artifacts for eligibility proofs, semantic gaps, raw responses,
candidate validation, authority, coverage, and hashes.

`NEXT_DECISION={aggregate['next_decision']}`.
"""
    (ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_2026-08-23.md").write_text(report, encoding="utf-8")
    print(json.dumps(aggregate, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); group.add_argument("--closeout", action="store_true"); parser.add_argument("--output-dir", type=Path, default=RUN); args = parser.parse_args()
    if args.prepare: prepare(args.output_dir)
    elif args.execute: execute(args.output_dir)
    else: closeout(args.output_dir)


if __name__ == "__main__":
    main()
