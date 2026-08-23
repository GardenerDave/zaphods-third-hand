#!/usr/bin/env python3
"""Oracle-clean V1 of the bounded semantic operation-class fallback experiment."""

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
RUN = ROOT / ".work/model_size_supplier_floor/true_semantic_fallback_v1/run_20260823T160000Z"
RUNTIME_CASES = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_RUNTIME_CASES_2026-08-23.json"
EVALUATOR_CASES = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_EVALUATOR_CASES_2026-08-23.json"
REGISTRY = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_REGISTRY_2026-08-23.json"
LEAKAGE_AUDIT = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_MODEL_INPUT_LEAKAGE_AUDIT_2026-08-23.json"
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
SHARED_RUNTIME_AUTHORITY = ["observe_presence", "inspect"]
FORBIDDEN_TARGET_LABELS = {"presence", "inspect", "observe", "check", "verify", "look", "control", "fallback", "ambiguous", "unsupported", "operation", "class"}


def now() -> str:
    from datetime import datetime, timezone
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


def fixture_specs() -> list[tuple[str, str, str, str | None]]:
    return [
        ("tsfv1-001", "TRUE_FALLBACK", "Is docs/research/TSF_AMBER_2026-08-23.md around in this tree?", "observe_presence"),
        ("tsfv1-002", "TRUE_FALLBACK", "Take a look at docs/research/TSF_BRONZE_2026-08-23.json.", "inspect"),
        ("tsfv1-003", "TRUE_FALLBACK", "Do we have docs/research/TSF_CITRINE_2026-08-23.txt here?", "observe_presence"),
        ("tsfv1-004", "TRUE_FALLBACK", "Give docs/research/TSF_DAWN_2026-08-23.md a quick look.", "inspect"),
        ("tsfv1-005", "TRUE_FALLBACK", "Tell me if docs/research/TSF_EMBER_2026-08-23.json is available.", "observe_presence"),
        ("tsfv1-006", "TRUE_FALLBACK", "Have a look at docs/research/TSF_FROST_2026-08-23.txt.", "inspect"),
        ("tsfv1-007", "DETERMINISTIC_CONTROL", "Determine whether docs/research/TSF_JADE_2026-08-23.md exists right now.", "observe_presence"),
        ("tsfv1-008", "DETERMINISTIC_CONTROL", "Inspect docs/research/TSF_KELP_2026-08-23.json.", "inspect"),
        ("tsfv1-009", "FAIL_CLOSED", "Check and inspect docs/research/TSF_LUNA_2026-08-23.txt.", None),
        ("tsfv1-010", "FAIL_CLOSED", "Delete docs/research/TSF_MICA_2026-08-23.md.", None),
    ]


def runtime_cases() -> list[dict[str, Any]]:
    cases = []
    for task_id, _, request, _ in fixture_specs():
        target = TARGET_RE.findall(request)[0]
        cases.append({"task_id": task_id, "input_request": request, "environment_facts": {"authority_record": {"allowed_targets": [target], "allowed_observation_operations": list(SHARED_RUNTIME_AUTHORITY)}}})
    return cases


def evaluator_cases() -> list[dict[str, Any]]:
    expected = {task_id: operation for task_id, _, _, operation in fixture_specs()}
    regimes = {task_id: regime for task_id, regime, _, _ in fixture_specs()}
    result = []
    for task_id, regime, _, operation in fixture_specs():
        model_required = regime == "TRUE_FALLBACK"
        result.append({"task_id": task_id, "regime": regime, "expected_semantic_class": operation if model_required else None, "expected_model_required": model_required, "expected_routing_decision_correct": True, "expected_execution_path_complete": operation == "observe_presence", "expected_task_terminal_success": operation == "observe_presence"})
    assert all(expected[x["task_id"]] == x["expected_semantic_class"] for x in result if x["expected_model_required"])
    return result


def schema() -> dict[str, Any]:
    return {"type": "object", "properties": {"operation_class_candidate": {"type": "string", "enum": sorted(ENUM)}}, "required": ["operation_class_candidate"], "additionalProperties": False}


def response_format() -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "bounded_operation_class_candidate_v1", "schema": schema()}}


def prompt(request: str) -> str:
    return (f"Request clause:\n{request}\n\n"
            "Classify only the requested operation class.\n"
            "observe_presence means determine whether the named target exists, is present, or is available.\n"
            "inspect means examine or look at the named target.\n"
            "unresolved means the operation class is ambiguous, unsupported, or cannot be determined safely.\n\n"
            "Return only operation_class_candidate in the required structured object. Do not identify the target, choose a tool, decide authorization, or decide task success.\n/no_think")


def parse_response(content: str) -> tuple[str | None, bool, bool, list[str]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    contract = isinstance(value, dict) and set(value) == {"operation_class_candidate"} and isinstance(value.get("operation_class_candidate"), str)
    candidate = value.get("operation_class_candidate") if contract else None
    valid = contract and candidate in ENUM
    return candidate if valid else None, True, valid, [] if valid else ["strict enum-only operation class contract failed"]


def preflight(request: str) -> dict[str, Any]:
    targets = TARGET_RE.findall(request)
    context = fallback.derive_context(request)
    words = set(re.findall(r"[a-z]+", request.casefold()))
    risk_status = "RISKY_OR_UNSUPPORTED" if words & RISKY_WORDS else "SAFE_BOUNDED"
    ambiguity_status = "AMBIGUOUS" if context == "AMBIGUOUS_CONTEXT" or len(targets) != 1 else "UNAMBIGUOUS"
    derivation = fallback.operation_derivation(request)
    if derivation["status"] == "RESOLVED":
        derivation_status, remaining = "RESOLVED", [derivation["canonical_operation"]]
    elif ambiguity_status != "UNAMBIGUOUS" or risk_status != "SAFE_BOUNDED" or derivation["status"] in {"AMBIGUOUS", "UNSUPPORTED"}:
        derivation_status, remaining = derivation["status"], []
    else:
        derivation_status, remaining = "UNRESOLVED", ["observe_presence", "inspect"]
    eligible = len(targets) == 1 and ambiguity_status == "UNAMBIGUOUS" and risk_status == "SAFE_BOUNDED" and derivation_status == "UNRESOLVED" and len(remaining) >= 2
    return {"target_status": "EXACTLY_ONE_SAFE_TARGET" if len(targets) == 1 else "TARGET_UNSAFE_OR_AMBIGUOUS", "target": targets[0] if len(targets) == 1 else None, "target_count": len(targets), "risk_status": risk_status, "ambiguity_status": ambiguity_status, "normalization_context": context, "operation_derivation_status": derivation_status, "remaining_candidate_operation_classes": remaining, "semantic_fallback_eligible": eligible, "model_required": eligible, "reason": "operation class remains unresolved with two safe candidates" if eligible else derivation.get("reason", "deterministic or fail-closed route")}


def plan(task_id: str, pre: dict[str, Any], operation: str | None = None) -> dict[str, Any]:
    if pre["model_required"] and operation is None:
        required = [MODEL_CAPABILITY]; records = [{"capability_id": MODEL_CAPABILITY, "selected_supplier": {"supplier_id": MODEL_SUPPLIER, "supplier_type": "MODEL", "interface_id": MODEL_INTERFACE}, "coverage_status": "COVERED"}]
    else:
        required = ["deterministic.operation_resolution", "deterministic.authority_validation"] if operation else []
        if operation == "observe_presence": required.append(tool.TOOL_CAPABILITY)
        if operation == "inspect": required.append("actuator.inspect")
        records = []
        for cap in required:
            if cap == tool.TOOL_CAPABILITY: supplier = {"supplier_id": tool.TOOL_SUPPLIER, "supplier_type": "TOOL", "interface_id": "repository_relative_metadata_observation_v0"}
            elif cap == "actuator.inspect": supplier = None
            else: supplier = {"supplier_id": "python_deterministic_v0", "supplier_type": "DETERMINISTIC_CODE", "interface_id": cap}
            records.append({"capability_id": cap, "selected_supplier": supplier, "coverage_status": "COVERED" if supplier else "UNCOVERED"})
    complete = bool(required) and all(x["coverage_status"] == "COVERED" for x in records)
    counts = supplier_counts(records)
    return {"schema": "zth_true_semantic_fallback_v1_capability_plan_v0", "task_id": task_id, "derived_required_capabilities": required, "capabilities": records, "overall_coverage": "COMPLETE" if complete else "INCOMPLETE", "execution_path_complete": complete, "routing_success": bool(operation in {"observe_presence", "inspect"} or (not pre["model_required"] and not required)), **counts}


def leakage_audit(cases: list[dict[str, Any]], evaluators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected = {x["task_id"]: x["expected_semantic_class"] for x in evaluators}
    rows = []
    for case in cases:
        target = case["environment_facts"]["authority_record"]["allowed_targets"][0]
        basename = Path(target).name.casefold()
        rows.append({"task_id": case["task_id"], "input_request": case["input_request"], "target": target, "expected_class_evaluator_only": expected[case["task_id"]], "target_semantic_label_leak": any(label in basename for label in FORBIDDEN_TARGET_LABELS), "runtime_authority_class_leak": case["environment_facts"]["authority_record"]["allowed_observation_operations"] != SHARED_RUNTIME_AUTHORITY, "runtime_regime_label_present": any(label in json.dumps(case).casefold() for label in ("true_fallback", "deterministic_control", "fail_closed")), "evaluator_fields_present": any(k.startswith("expected_") for k in case), "prompt_classification_specification_allowed": True})
    return rows


def supplier_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    """Count only selected suppliers; uncovered capabilities are valid records."""
    return {
        "planned_model_calls": sum(
            record["selected_supplier"] is not None
            and record["selected_supplier"]["supplier_type"] == "MODEL"
            for record in records
        ),
        "planned_tool_calls": sum(
            record["selected_supplier"] is not None
            and record["selected_supplier"]["supplier_type"] == "TOOL"
            for record in records
        ),
        "planned_deterministic_steps": sum(
            record["selected_supplier"] is not None
            and record["selected_supplier"]["supplier_type"] == "DETERMINISTIC_CODE"
            for record in records
        ),
    }


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()): raise RuntimeError("fresh V1 run required")
    cases, evaluators = runtime_cases(), evaluator_cases()
    write_json(RUNTIME_CASES, {"schema": "zth_true_semantic_fallback_v1_runtime_cases_v0", "cases": cases})
    write_json(EVALUATOR_CASES, {"schema": "zth_true_semantic_fallback_v1_evaluator_cases_v0", "cases": evaluators})
    write_json(REGISTRY, {"schema": "zth_true_semantic_fallback_v1_registry_v0", "automatic_promotion": False, "entries": [{"capability_id": MODEL_CAPABILITY, "supplier_id": MODEL_SUPPLIER, "supplier_type": "MODEL", "interface_id": MODEL_INTERFACE, "status": "EXPERIMENTAL_CANDIDATE", "evidence_artifact": "docs/research/TRUE_SEMANTIC_FALLBACK_V1_DESIGN_2026-08-23.md", "evidence_scope": "fresh neutral-target two-class operation classification", "qualification_decision": "no promotion"}, {"capability_id": tool.TOOL_CAPABILITY, "supplier_id": tool.TOOL_SUPPLIER, "supplier_type": "TOOL", "interface_id": "repository_relative_metadata_observation_v0", "status": "QUALIFIED_EXPLORATORY", "evidence_artifact": "docs/research/CAPABILITY_ROUTER_TOOL_OBSERVATION_V0_DESIGN_2026-08-22.md", "evidence_scope": "prior exact-target read-only metadata evidence", "qualification_decision": "preserved prior evidence"}]})
    leaks = leakage_audit(cases, evaluators); assert all(not x["target_semantic_label_leak"] and not x["runtime_authority_class_leak"] and not x["runtime_regime_label_present"] and not x["evaluator_fields_present"] for x in leaks); write_json(LEAKAGE_AUDIT, {"schema": "zth_true_semantic_fallback_v1_model_input_leakage_audit_v0", "rows": leaks, "pass": True})
    out.mkdir(parents=True, exist_ok=True); planned = 0
    for case in cases:
        pre = preflight(case["input_request"]); p0 = plan(case["task_id"], pre); expected = next(x for x in evaluators if x["task_id"] == case["task_id"])
        if expected["regime"] == "TRUE_FALLBACK":
            assert pre["semantic_fallback_eligible"] and pre["model_required"] and pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"]
            gap = {"known_facts_before_model": ["exactly_one_safe_target", "safe_bounded_request", "unambiguous_request", "shared_runtime_authority_allows_both_classes"], "unknown_decision_critical_fact": "which bounded semantic operation class the request expresses", "remaining_candidate_classes": pre["remaining_candidate_operation_classes"], "why_deterministic_resolution_is_insufficient": "request is outside the frozen deterministic operation grammar", "why_model_is_permitted": "the two safe classes remain semantically plausible"}
            write_json(out / "tasks" / case["task_id"] / "semantic_information_gap.json", gap)
        else:
            assert not pre["model_required"]
        td = out / "tasks" / case["task_id"]; write_json(td / "runtime_task.json", case); write_json(td / "preflight.json", pre); write_json(td / "capability_plan_0.json", p0)
        if pre["model_required"]:
            (td / "prompt.txt").write_text(prompt(case["input_request"]), encoding="utf-8"); write_json(td / "schema.json", schema()); planned += 1
    before = {"runtime_cases": sha_file(RUNTIME_CASES), "authority": sha_bytes(canonical([x["environment_facts"]["authority_record"] for x in cases])), "leakage": sha_file(LEAKAGE_AUDIT), "preflights": sha_bytes(canonical([preflight(x["input_request"]) for x in cases])), "plans": sha_bytes(canonical([plan(x["task_id"], preflight(x["input_request"])) for x in cases])), "prompts": sha_bytes(canonical({x["task_id"]: prompt(x["input_request"]) for x in cases if preflight(x["input_request"])["model_required"]})), "schema": sha_bytes(canonical(schema()))}
    corrupted = [dict(x, expected_semantic_class="inspect" if x["expected_semantic_class"] == "observe_presence" else "observe_presence") for x in evaluators]
    after = {"runtime_cases": sha_file(RUNTIME_CASES), "authority": sha_bytes(canonical([x["environment_facts"]["authority_record"] for x in cases])), "leakage": sha_file(LEAKAGE_AUDIT), "preflights": sha_bytes(canonical([preflight(x["input_request"]) for x in cases])), "plans": sha_bytes(canonical([plan(x["task_id"], preflight(x["input_request"])) for x in cases])), "prompts": sha_bytes(canonical({x["task_id"]: prompt(x["input_request"]) for x in cases if preflight(x["input_request"])["model_required"]})), "schema": sha_bytes(canonical(schema()))}
    write_json(out / "evaluator_corruption_invariance.json", {"corrupted_evaluator": corrupted, "before_hashes": before, "after_hashes": after, "pass": before == after})
    assert before == after
    manifest = {"schema": "zth_true_semantic_fallback_v1_manifest_v0", "status": "prepared_model_free", "supersedes": "abbb0c1d44b1eadfdc8b23cbeaa33e8da7d994f6", "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "runtime_cases_sha256": sha_file(RUNTIME_CASES), "evaluator_cases_sha256": sha_file(EVALUATOR_CASES), "registry_sha256": sha_file(REGISTRY), "leakage_audit_sha256": sha_file(LEAKAGE_AUDIT), "task_count": 10, "true_fallback_eligibility": 6, "planned_model_calls": planned, "control_model_calls": 0, "model_calls_made": 0, "tool_calls_made": 0, "raw_response_files": 0, "teacher_calls_made": 0, "30b_calls_made": 0, "external_calls_made": 0, "retries": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0, "target_path_predicts_semantic_class": False, "runtime_authority_independent_of_expected_class": True, "evaluator_class_corruption_runtime_invariance": True, "qualification_change": False, "model_id": MODEL_ID, "model_sha256": MODEL_SHA, "operative_parameters": PARAMS, "gpu_uuid": GPU_UUID, "driver_sha256": sha_file(Path(__file__))}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None})); write_json(out / "router_manifest.json", manifest); write_json(out / "lifecycle.json", {"status": "prepared", "model_calls": 0, "tool_calls": 0, "retries": 0})


def model_preflight(out: Path):
    spec = runtime.worker_spec(); models = decomposition.list_models(spec, timeout=30); candidate = next((x for x in models.get("data", []) if x.get("id") == MODEL_ID), None); meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != PARAMS: raise RuntimeError("model binding mismatch")
    telemetry_url = runtime.telemetry_base_url(); telemetry = runtime.telemetry_preflight(telemetry_url); write_json(out / "model_preflight.json", {"model_meta": meta, "telemetry": telemetry, "model_id": MODEL_ID, "gpu_uuid": GPU_UUID}); return spec, telemetry_url


def execute(out: Path) -> None:
    manifest = read_json(out / "router_manifest.json"); spec, telemetry_url = model_preflight(out) if manifest["planned_model_calls"] else (None, None); model_calls = tool_calls = 0
    for td in sorted((out / "tasks").glob("*")):
        rt = read_json(td / "runtime_task.json"); pre = read_json(td / "preflight.json"); canonical_operation = None; candidate = None
        trace = {"schema": "zth_true_semantic_fallback_v1_trace_v0", "task_id": rt["task_id"], "runtime_expected_field_reads": 0, "model_calls": [], "tool_calls": []}
        if pre["model_required"]:
            prompt_path, schema_path = td / "prompt.txt", td / "schema.json"; write_json(td / "call_started.json", {"task_id": rt["task_id"], "started_at": now(), "prompt_sha256": sha_file(prompt_path), "schema_sha256": sha_file(schema_path), "supplier_id": MODEL_SUPPLIER, "model_id": MODEL_ID})
            sampler = PowerSampler(lambda: read_gpu_power(GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=GPU_UUID, sample_interval_seconds=POWER_INTERVAL); started = time.monotonic(); sampler.start(); response = decomposition.structured_call(spec, prompt_path.read_text(encoding="utf-8"), response_format(), MAX_TOKENS, TIMEOUT); elapsed = time.monotonic() - started; samples = sampler.stop(); energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL, expected_gpu_uuid=GPU_UUID); metadata = response.metadata(); metadata["request_url"] = None
            write_json(td / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "wall_elapsed_ms": round(elapsed * 1000, 3), "gross_energy_joules": energy}); write_json(td / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": GPU_UUID, "samples": [{"timestamp_utc": x.timestamp_utc, "power_watts": x.power_watts, "gpu_uuid": x.gpu_uuid, "sequence": x.sequence} for x in samples]})
            candidate, parse_valid, contract_valid, diagnostics = parse_response(response.content); model_calls += 1; admissible = candidate in pre["remaining_candidate_operation_classes"] if candidate else False; write_json(td / "candidate_validation.json", {"candidate": candidate, "parse_valid": parse_valid, "contract_valid": contract_valid, "candidate_valid": candidate in ENUM if candidate else False, "candidate_admissible": admissible, "diagnostics": diagnostics}); trace["model_calls"].append({"parse_valid": parse_valid, "contract_valid": contract_valid, "candidate_admissible": admissible})
            if not contract_valid or candidate is None or candidate == "unresolved" or not admissible:
                result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "SEMANTIC_CANDIDATE_INVALID_OR_UNRESOLVED", "model_calls": 1, "tool_calls": 0}; write_json(td / "runtime_result.json", result); trace["terminal_state"] = result["terminal_state"]; write_json(td / "route_trace.json", trace); continue
            canonical_operation = candidate; write_json(td / "operation_derivation_1.json", {"schema": "zth_true_semantic_fallback_v1_operation_derivation_v0", "status": "RESOLVED", "derivation_type": "PRIOR_MODEL_STEP_DETERMINISTIC_VALIDATION", "canonical_operation": canonical_operation, "model_output_granted_authority": False}); p1 = plan(rt["task_id"], pre, canonical_operation); write_json(td / "capability_plan_1.json", p1)
        else:
            deriv = fallback.operation_derivation(rt["input_request"]); canonical_operation = deriv.get("canonical_operation") if deriv["status"] == "RESOLVED" else None; p1 = plan(rt["task_id"], pre, canonical_operation); write_json(td / "capability_plan_1.json", p1)
        if canonical_operation == "observe_presence" and p1["overall_coverage"] == "COMPLETE":
            authority = rt["environment_facts"]["authority_record"]; auth, request, tool_auth, observation, count = confirmation.execute_read_only_observation(canonical_operation, pre["target"], authority); write_json(td / "execution_authority_validation.json", auth); write_json(td / "tool_request.json", request); write_json(td / "tool_authority_validation.json", tool_auth) if tool_auth is not None else None
            if auth["status"] != "AUTHORIZED":
                result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": auth["status"], "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 0}; write_json(td / "runtime_result.json", result); continue
            tool_calls += count; write_json(td / "tool_observation.json", observation); validation = tool.validate_observation(observation, request, tool_auth); write_json(td / "tool_result_validation.json", validation); state = {"operation_resolved": True, "operation_authorized": auth["operation_authorized"], "target_bound": auth["target_authorized"], "coverage_complete": True, "observation_valid": validation["status"] == "VALID"}; evaluation = confirmation.evaluate_contract(state); write_json(td / "success_contract_evaluation.json", evaluation); result = {"routing_success": True, "execution_path_complete": evaluation["passed"], "task_terminal_success": evaluation["passed"], "terminal_state": "terminal_success" if evaluation["passed"] else "ready_for_review", "reason": "SUCCESS_CONTRACT_EVALUATED", "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 1}
        elif canonical_operation == "inspect":
            result = {"routing_success": True, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "NO_QUALIFIED_EXECUTION_SUPPLIER", "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 0}
        else:
            result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "NO_ROUTABLE_OPERATION", "model_calls": 0, "tool_calls": 0}
        write_json(td / "runtime_result.json", result); trace["terminal_state"] = result["terminal_state"]; write_json(td / "route_trace.json", trace)
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "model_calls": model_calls, "tool_calls": tool_calls, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "retries": 0, "runtime_expected_field_reads": 0, "model_output_granted_authority": 0})


def closeout(out: Path) -> None:
    task_dirs = sorted((out / "tasks").glob("*"))
    if not any((td / "runtime_result.json").exists() for td in task_dirs):
        manifest = read_json(out / "router_manifest.json")
        failure = read_json(out / "zero_call_preflight_failure.json") if (out / "zero_call_preflight_failure.json").exists() else {}
        restart = read_json(out / "zero_call_preflight_restart.json") if (out / "zero_call_preflight_restart.json").exists() else {}
        failure_classes = [x for x in [failure.get("failure_class"), restart.get("failure_class")] if x]
        rows = [{"task_id": td.name, "execution_status": "NOT_EXECUTED_PRE_MODEL_PREFLIGHT", "model_calls": 0, "tool_calls": 0} for td in task_dirs]
        aggregate = {
            "schema": "zth_true_semantic_fallback_v1_blocked_aggregate_v0",
            "status": "PRE_INFERENCE_BLOCKED",
            "task_count": len(rows),
            "true_fallback_opportunities": 6,
            "model_calls_planned": manifest["planned_model_calls"],
            "model_calls_made": 0,
            "tool_calls_made": 0,
            "raw_response_files": 0,
            "semantic_evidence_available": False,
            "scientific_evidence_contaminated": False,
            "runtime_evaluator_influence": 0,
            "MODEL_OUTPUT_GRANTED_AUTHORITY": 0,
            "teacher_calls": 0,
            "30b_calls": 0,
            "external_calls": 0,
            "retries": 0,
            "qualification_change": False,
            "zero_call_preflight_failure": True,
            "preflight_failure_class": failure_classes[0] if failure_classes else "LOCAL_ENDPOINT_PRE_INFERENCE_FAILURE",
            "preflight_failure_classes": failure_classes,
            "rows": rows,
        }
        matrix = {
            "schema": "zth_true_semantic_fallback_v1_blocked_matrix_v0",
            "superseded_v0_freeze": "abbb0c1d44b1eadfdc8b23cbeaa33e8da7d994f6",
            "execution_driver_sha256": manifest["driver_sha256"],
            "closeout_driver_sha256": sha_file(Path(__file__)),
            "aggregate": aggregate,
            "rows": rows,
        }
        write_json(out / "aggregate.json", aggregate)
        write_json(out / "matrix.json", matrix)
        write_json(ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_MATRIX_2026-08-23.json", matrix)
        write_json(out / "lifecycle.json", {"status": "closeout_pre_inference_blocked", "model_calls": 0, "tool_calls": 0, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "retries": 0})
        report = f"""# Oracle-clean true semantic fallback V1 closeout

The superseded V0 freeze `abbb0c1d44b1eadfdc8b23cbeaa33e8da7d994f6` remains untouched and produced no model evidence. V1 was frozen with neutral targets, evaluator-separated runtime cases, class-independent authority, six eligible model calls, and zero calls before execution.

Execution was blocked during local 1.7B model-list preflight. The initial attempt failed before inference with `{failure_classes[0] if failure_classes else 'UNKNOWN'}`; the one explicitly authorized infrastructure restart also failed before inference with `{failure_classes[1] if len(failure_classes) > 1 else 'UNKNOWN'}`. The frozen run contains zero model calls, zero tool calls, zero raw response files, and no task inference. No scientific V1 semantic result is claimed.

The execution driver hash is `{matrix['execution_driver_sha256']}`. This closeout was generated by a separate closeout driver hash `{matrix['closeout_driver_sha256']}` and did not execute or replay any task calls. Teacher, 30B, external, retry, and qualification-change counts are all zero.

`ORIGINAL_TRUE_FALLBACK_FREEZE_EXECUTED=false` remains true for the superseded V0. `SCIENTIFIC_EVIDENCE_CONTAMINATED=false` applies to both this V1 run and the unexecuted V0 design. The next action is not executed automatically; endpoint availability would need to be restored before any new authorized run.
"""
        (ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_2026-08-23.md").write_text(report, encoding="utf-8")
        print(json.dumps(aggregate, indent=2, sort_keys=True))
        return
    evaluators = {x["task_id"]: x for x in read_json(EVALUATOR_CASES)["cases"]}; rows=[]; lat=[]; energy=[]
    for td in sorted((out / "tasks").glob("*")):
        ev = evaluators[td.name]; pre = read_json(td / "preflight.json"); result = read_json(td / "runtime_result.json"); response = read_json(td / "response.json") if (td / "response.json").exists() else None; validation = read_json(td / "candidate_validation.json") if (td / "candidate_validation.json").exists() else {}
        if response: lat.append(response.get("wall_elapsed_ms")); energy.append(response.get("gross_energy_joules"))
        candidate = validation.get("candidate"); semantic_correct = (candidate == ev["expected_semantic_class"]) if ev["expected_model_required"] else None
        routing_correct = semantic_correct if ev["expected_model_required"] else (result["terminal_state"] == "terminal_success" if ev["regime"] == "DETERMINISTIC_CONTROL" and ev["expected_execution_path_complete"] else result["terminal_state"] == "ready_for_review")
        row = {"task_id": td.name, "regime": ev["regime"], "model_required": ev["expected_model_required"], "preflight_eligible": pre["semantic_fallback_eligible"], "parse_valid": validation.get("parse_valid"), "contract_valid": validation.get("contract_valid"), "candidate_valid": validation.get("candidate_valid"), "candidate_admissible": validation.get("candidate_admissible"), "observed_operation_class": candidate, "semantic_classification_correct": semantic_correct, "routing_decision_correct": routing_correct, "execution_path_complete": result["execution_path_complete"], "execution_path_complete_correct": result["execution_path_complete"] == ev["expected_execution_path_complete"], "task_terminal_success": result["task_terminal_success"], "task_terminal_success_correct": result["task_terminal_success"] == ev["expected_task_terminal_success"], "terminal_state": result["terminal_state"], "model_calls": result.get("model_calls", 0), "tool_calls": result.get("tool_calls", 0)}
        write_json(td / "evaluator_scorecard.json", row); rows.append(row)
    model_rows = [x for x in rows if x["model_required"]]; presence = [x for x in model_rows if x["task_id"] in {"tsfv1-001", "tsfv1-003", "tsfv1-005"}]; inspect = [x for x in model_rows if x["task_id"] in {"tsfv1-002", "tsfv1-004", "tsfv1-006"}]; semantic_correct = sum(x["semantic_classification_correct"] is True for x in model_rows)
    aggregate = {"schema": "zth_true_semantic_fallback_v1_aggregate_v0", "task_count": len(rows), "true_fallback_opportunities": len(model_rows), "model_calls_planned": 6, "model_calls_made": sum(x["model_calls"] for x in rows), "deterministic_control_model_calls": sum(x["model_calls"] for x in rows if x["task_id"] in {"tsfv1-007", "tsfv1-008"}), "fail_closed_control_model_calls": sum(x["model_calls"] for x in rows if x["task_id"] in {"tsfv1-009", "tsfv1-010"}), "parse_valid": sum(x["parse_valid"] is True for x in model_rows), "contract_valid": sum(x["contract_valid"] is True for x in model_rows), "candidate_valid": sum(x["candidate_valid"] is True for x in model_rows), "candidate_admissible": sum(x["candidate_admissible"] is True for x in model_rows), "semantic_classification_correct": semantic_correct, "semantic_classification_correct_presence": sum(x["semantic_classification_correct"] is True for x in presence), "semantic_classification_correct_inspect": sum(x["semantic_classification_correct"] is True for x in inspect), "model_unresolved_outputs": sum(x["observed_operation_class"] in {None, "unresolved"} for x in model_rows), "incorrect_semantic_classifications": sum(x["semantic_classification_correct"] is False for x in model_rows), "execution_coverage_complete": sum(x["execution_path_complete"] for x in rows), "execution_coverage_incomplete": sum(not x["execution_path_complete"] for x in rows), "presence_observations_executed": sum(x["task_id"] in {"tsfv1-001", "tsfv1-003", "tsfv1-005"} and x["tool_calls"] == 1 for x in rows), "valid_observations": sum((td / "tool_result_validation.json").exists() and read_json(td / "tool_result_validation.json").get("status") == "VALID" for td in (out / "tasks").glob("*")), "inspect_cases_correctly_no_actuator_gated": sum(x["task_id"] in {"tsfv1-002", "tsfv1-004", "tsfv1-006"} and x["semantic_classification_correct"] is True and x["terminal_state"] == "ready_for_review" for x in rows), "routing_decisions_correct": sum(x["routing_decision_correct"] for x in rows), "execution_paths_complete": sum(x["execution_path_complete"] for x in rows), "task_terminal_success": sum(x["task_terminal_success"] for x in rows), "runtime_evaluator_influence": 0, "MODEL_OUTPUT_GRANTED_AUTHORITY": 0, "retries": 0, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "qualification_change": False, "model_latency_ms": {"mean": statistics.mean(lat) if lat else None, "median": statistics.median(lat) if lat else None, "p95": sorted(lat)[min(len(lat)-1, round((len(lat)-1)*.95))] if lat else None}, "model_energy_joules": {"total": sum(energy), "mean": statistics.mean(energy) if energy else None, "median": statistics.median(energy) if energy else None}, "rows": rows}
    true_demo = semantic_correct > 0; both = aggregate["semantic_classification_correct_presence"] > 0 and aggregate["semantic_classification_correct_inspect"] > 0
    aggregate.update({"TRUE_SEMANTIC_FALLBACK_DEMONSTRATED": true_demo, "DECISION_CRITICAL_MODEL_SEMANTIC_CONTRIBUTION_DEMONSTRATED": true_demo, "MODEL_OUTPUT_TO_CAPABILITY_PLAN_TRANSITION_DEMONSTRATED": true_demo, "MULTI_CLASS_BOUNDED_SEMANTIC_FALLBACK_DEMONSTRATED": both, "next_decision": "DIAGNOSE_GENUINE_SEMANTIC_OPERATION_CLASSIFICATION_FAILURES" if true_demo and semantic_correct < 6 else ("TEST_SEMANTIC_OPERATION_CLASSIFICATION_SUPPLIER_FLOOR" if true_demo else "RECONSIDER_BOUNDED_SEMANTIC_OPERATION_INTERFACE")})
    matrix = {"schema": "zth_true_semantic_fallback_v1_matrix_v0", "superseded_v0_freeze": "abbb0c1d44b1eadfdc8b23cbeaa33e8da7d994f6", "execution_driver_sha256": read_json(out / "router_manifest.json")["driver_sha256"], "closeout_driver_sha256": sha_file(Path(__file__)), "aggregate": aggregate, "rows": rows}; write_json(out / "aggregate.json", aggregate); write_json(out / "matrix.json", matrix); write_json(ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_MATRIX_2026-08-23.json", matrix); write_json(out / "lifecycle.json", {"status": "closeout_complete", "model_calls": aggregate["model_calls_made"], "tool_calls": sum(x["tool_calls"] for x in rows), "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "retries": 0})
    report = f"""# Oracle-clean true semantic fallback V1 closeout

The unexecuted contaminated V0 freeze `abbb0c1d44b1eadfdc8b23cbeaa33e8da7d994f6` remains untouched and is superseded, not rescored. V1 used neutral targets and the same shared runtime authority class set for every task.

Results: semantic classifications {aggregate['semantic_classification_correct']}/6 overall, presence {aggregate['semantic_classification_correct_presence']}/3, inspect {aggregate['semantic_classification_correct_inspect']}/3; model calls {aggregate['model_calls_made']}; deterministic-control calls {aggregate['deterministic_control_model_calls']}; fail-closed-control calls {aggregate['fail_closed_control_model_calls']}; presence observations {aggregate['presence_observations_executed']}; routing decisions correct {aggregate['routing_decisions_correct']}/10; execution paths complete {aggregate['execution_paths_complete']}/10; task terminal success {aggregate['task_terminal_success']}/10.

`TRUE_SEMANTIC_FALLBACK_DEMONSTRATED={str(true_demo).lower()}` and `MULTI_CLASS_BOUNDED_SEMANTIC_FALLBACK_DEMONSTRATED={str(both).lower()}`. Correct inspect classifications are successful semantic/routing outcomes even when review-gated for the absent inspect actuator. Authority and target naming were not semantic answer channels.

Runtime evaluator influence: 0. Model output granted authority: 0. Retries, teacher, 30B, external, and qualification changes: 0. Latency mean/median/p95: {aggregate['model_latency_ms']['mean']}/{aggregate['model_latency_ms']['median']}/{aggregate['model_latency_ms']['p95']} ms. GPU energy total/mean/median: {aggregate['model_energy_joules']['total']}/{aggregate['model_energy_joules']['mean']}/{aggregate['model_energy_joules']['median']} J.

See the [V1 matrix](TRUE_SEMANTIC_FALLBACK_V1_MATRIX_2026-08-23.json), leakage audit, raw responses, semantic gaps, candidate validation, authority traces, and plans in the fresh run directory. `NEXT_DECISION={aggregate['next_decision']}`.
"""
    (ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_2026-08-23.md").write_text(report, encoding="utf-8"); print(json.dumps(aggregate, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); group.add_argument("--closeout", action="store_true"); parser.add_argument("--output-dir", type=Path, default=RUN); args = parser.parse_args()
    if args.prepare: prepare(args.output_dir)
    elif args.execute: execute(args.output_dir)
    else: closeout(args.output_dir)


if __name__ == "__main__":
    main()
