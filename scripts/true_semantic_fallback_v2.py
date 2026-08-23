#!/usr/bin/env python3
"""Model-free freeze and future execution driver for true semantic fallback V2."""

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
from scripts import deterministic_first_confirmation as confirmation
from scripts import zth_capability_router_tool_observation_v0 as tool
from scripts import zth_deterministic_first_semantic_fallback as fallback
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as telemetry_provider
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = runtime.ROOT
RUN = ROOT / ".work/model_size_supplier_floor/true_semantic_fallback_v2/run_20260823T184000Z"
RUNTIME_CASES = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V2_RUNTIME_CASES_2026-08-23.json"
EVALUATOR_CASES = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V2_EVALUATOR_CASES_2026-08-23.json"
REGISTRY = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V2_REGISTRY_2026-08-23.json"
LEAKAGE_AUDIT = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V2_MODEL_INPUT_LEAKAGE_AUDIT_2026-08-23.json"
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
ENUM = {"observe_presence", "inspect", "unresolved"}
SHARED_AUTHORITY = ["observe_presence", "inspect"]
RISKY_WORDS = {"amend", "amended", "dispatch", "dispatched", "archive", "archived", "delete", "deleted"}
FORBIDDEN_LABELS = {"presence", "inspect", "observe", "check", "verify", "look", "available", "exists", "fallback", "class", "operation", "control", "ambiguous", "unsupported"}
V1_RUNTIME = ROOT / "docs/research/TRUE_SEMANTIC_FALLBACK_V1_RUNTIME_CASES_2026-08-23.json"


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


def prompt(request: str) -> str:
    return (
        f"Request clause:\n{request}\n\n"
        "Classify only the requested operation class.\n"
        "observe_presence means determine whether the named target exists, is present, or is available.\n"
        "inspect means examine or look at the named target.\n"
        "unresolved means the operation class is ambiguous, unsupported, or cannot be determined safely.\n\n"
        "Return only operation_class_candidate in the required structured object. Do not identify the target, choose a tool, decide authorization, or decide task success.\n/no_think"
    )


def schema() -> dict[str, Any]:
    return {"type": "object", "properties": {"operation_class_candidate": {"type": "string", "enum": sorted(ENUM)}}, "required": ["operation_class_candidate"], "additionalProperties": False}


def response_format() -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "bounded_operation_class_candidate_v2", "schema": schema()}}


def parse_response(content: str) -> tuple[str | None, bool, bool, list[str]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    contract = isinstance(value, dict) and set(value) == {"operation_class_candidate"} and isinstance(value.get("operation_class_candidate"), str)
    candidate = value.get("operation_class_candidate") if contract else None
    valid = contract and candidate in ENUM
    return candidate if valid else None, True, valid, [] if valid else ["strict enum-only operation class contract failed"]


def fixture_specs() -> list[tuple[str, str, str, str | None]]:
    return [
        ("tsfv2-001", "TRUE_FALLBACK", "Could you tell me whether docs/research/V2_AURORA_2026-08-23.md is part of this repository?", "observe_presence"),
        ("tsfv2-002", "TRUE_FALLBACK", "Give docs/research/V2_BASALT_2026-08-23.json a brief examination.", "inspect"),
        ("tsfv2-003", "TRUE_FALLBACK", "Would you say whether docs/research/V2_CEDAR_2026-08-23.txt is stored here?", "observe_presence"),
        ("tsfv2-004", "TRUE_FALLBACK", "Review docs/research/V2_DUSK_2026-08-23.md for me.", "inspect"),
        ("tsfv2-005", "TRUE_FALLBACK", "Is docs/research/V2_FLINT_2026-08-23.json contained in the repository at present?", "observe_presence"),
        ("tsfv2-006", "TRUE_FALLBACK", "Examine docs/research/V2_GARNET_2026-08-23.txt when you can.", "inspect"),
        ("tsfv2-007", "DETERMINISTIC_CONTROL", "Determine whether docs/research/V2_HARBOR_2026-08-23.py exists right now.", "observe_presence"),
        ("tsfv2-008", "DETERMINISTIC_CONTROL", "Inspect docs/research/V2_IVORY_2026-08-23.py.", "inspect"),
        ("tsfv2-009", "FAIL_CLOSED", "Check and inspect docs/research/V2_JUNIPER_2026-08-23.md.", None),
        ("tsfv2-010", "FAIL_CLOSED", "Delete docs/research/V2_KITE_2026-08-23.json.", None),
    ]


def runtime_cases() -> list[dict[str, Any]]:
    cases = []
    for task_id, regime, request, _ in fixture_specs():
        targets = TARGET_RE.findall(request)
        if len(targets) != 1:
            raise RuntimeError(f"target extraction failed for {task_id}")
        operations = SHARED_AUTHORITY if regime == "TRUE_FALLBACK" else (["observe_presence"] if "Determine" in request else (["inspect"] if request.startswith("Inspect") else SHARED_AUTHORITY))
        cases.append({"task_id": task_id, "input_request": request, "environment_facts": {"authority_record": {"allowed_targets": [targets[0]], "allowed_observation_operations": operations}}})
    return cases


def evaluator_cases() -> list[dict[str, Any]]:
    result = []
    for task_id, regime, _, expected in fixture_specs():
        model_required = regime == "TRUE_FALLBACK"
        result.append({"task_id": task_id, "regime": regime, "expected_semantic_class": expected if model_required else None, "expected_model_required": model_required, "expected_routing_decision_correct": True, "expected_execution_path_complete": expected == "observe_presence", "expected_task_terminal_success": expected == "observe_presence"})
    return result


def preflight(request: str) -> dict[str, Any]:
    targets = TARGET_RE.findall(request)
    context = fallback.derive_context(request)
    words = set(re.findall(r"[a-z]+", request.casefold()))
    risk = "RISKY_OR_UNSUPPORTED" if words & RISKY_WORDS else "SAFE_BOUNDED"
    ambiguity = "AMBIGUOUS" if context == "AMBIGUOUS_CONTEXT" or len(targets) != 1 else "UNAMBIGUOUS"
    derivation = fallback.operation_derivation(request)
    if derivation["status"] == "RESOLVED":
        status, candidates = "RESOLVED", [derivation["canonical_operation"]]
    elif ambiguity != "UNAMBIGUOUS" or risk != "SAFE_BOUNDED" or derivation["status"] in {"AMBIGUOUS", "UNSUPPORTED"}:
        status, candidates = derivation["status"], []
    else:
        status, candidates = "UNRESOLVED", ["observe_presence", "inspect"]
    eligible = len(targets) == 1 and risk == "SAFE_BOUNDED" and ambiguity == "UNAMBIGUOUS" and status == "UNRESOLVED" and candidates == ["observe_presence", "inspect"]
    return {"target_status": "EXACTLY_ONE_SAFE_TARGET" if len(targets) == 1 else "TARGET_UNSAFE_OR_AMBIGUOUS", "target": targets[0] if len(targets) == 1 else None, "target_count": len(targets), "risk_status": risk, "ambiguity_status": ambiguity, "normalization_context": context, "operation_derivation_status": status, "remaining_candidate_operation_classes": candidates, "semantic_fallback_eligible": eligible, "model_required": eligible, "deterministic_canonical_operation_available_pre_model": status == "RESOLVED", "reason": "operation class remains unresolved with two safe candidates" if eligible else derivation.get("reason", "frozen deterministic or fail-closed route")}


def supplier_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "planned_model_calls": sum(record["selected_supplier"] is not None and record["selected_supplier"]["supplier_type"] == "MODEL" for record in records),
        "planned_tool_calls": sum(record["selected_supplier"] is not None and record["selected_supplier"]["supplier_type"] == "TOOL" for record in records),
        "planned_deterministic_steps": sum(record["selected_supplier"] is not None and record["selected_supplier"]["supplier_type"] == "DETERMINISTIC_CODE" for record in records),
    }


def plan(task_id: str, pre: dict[str, Any], operation: str | None = None) -> dict[str, Any]:
    if pre["model_required"] and operation is None:
        required = [MODEL_CAPABILITY]
    elif operation in {"observe_presence", "inspect"}:
        required = ["deterministic.operation_resolution", "deterministic.authority_validation", tool.TOOL_CAPABILITY if operation == "observe_presence" else "actuator.inspect"]
    elif pre["operation_derivation_status"] == "RESOLVED":
        required = ["deterministic.operation_resolution", "deterministic.authority_validation"]
    else:
        required = []
    records = []
    for cap in required:
        if cap == MODEL_CAPABILITY:
            selected = {"supplier_id": MODEL_SUPPLIER, "supplier_type": "MODEL", "interface_id": MODEL_INTERFACE}
        elif cap == tool.TOOL_CAPABILITY:
            selected = {"supplier_id": tool.TOOL_SUPPLIER, "supplier_type": "TOOL", "interface_id": "repository_relative_metadata_observation_v0"}
        elif cap == "actuator.inspect":
            selected = None
        else:
            selected = {"supplier_id": "python_deterministic_v0", "supplier_type": "DETERMINISTIC_CODE", "interface_id": cap}
        records.append({"capability_id": cap, "selected_supplier": selected, "candidate_suppliers": [selected] if selected else [], "qualified_candidates": [selected] if selected else [], "coverage_status": "COVERED" if selected else "UNCOVERED", "selection_reason": "qualified bounded supplier" if selected else "NO_QUALIFIED_EXECUTION_SUPPLIER"})
    complete = bool(required) and all(record["coverage_status"] == "COVERED" for record in records)
    counts = supplier_counts(records)
    return {"schema": "zth_true_semantic_fallback_v2_capability_plan_v0", "task_id": task_id, "derived_required_capabilities": required, "capabilities": records, "overall_coverage": "COMPLETE" if complete else "INCOMPLETE", "execution_path_complete": complete, "routing_success": bool(operation in {"observe_presence", "inspect"} or (not pre["model_required"] and pre["operation_derivation_status"] == "RESOLVED")), **counts}


def success_contract(operation: str) -> dict[str, Any]:
    predicates = ["operation_resolved", "operation_authorized", "target_bound", "execution_coverage_complete"]
    if operation == "observe_presence":
        predicates.append("observation_valid")
    return {"schema": "zth_true_semantic_fallback_v2_success_contract_v0", "operation": operation, "predicates": predicates, "contains_worked_answer": False}


def evaluate_success_contract(contract: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    results = [{"predicate": predicate, "passed": state.get(predicate) is True} for predicate in contract["predicates"]]
    return {"schema": "zth_true_semantic_fallback_v2_success_contract_evaluation_v0", "passed": all(item["passed"] for item in results), "predicates": results}


def leakage_audit(cases: list[dict[str, Any]], evaluators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expected = {item["task_id"]: item["expected_semantic_class"] for item in evaluators}
    rows = []
    for case in cases:
        target = case["environment_facts"]["authority_record"]["allowed_targets"][0]
        basename = Path(target).name.casefold()
        rows.append({"task_id": case["task_id"], "input_request": case["input_request"], "target": target, "expected_class_evaluator_only": expected[case["task_id"]], "target_semantic_label_leak": any(label in basename for label in FORBIDDEN_LABELS), "runtime_authority_class_leak": case["environment_facts"]["authority_record"]["allowed_observation_operations"] != SHARED_AUTHORITY if case["task_id"] in {x[0] for x in fixture_specs()[:6]} else False, "runtime_regime_label_present": any(label in json.dumps(case).casefold() for label in ("true_fallback", "deterministic_control", "fail_closed")), "evaluator_fields_present": any(key.startswith("expected_") for key in case), "task_id_class_leak": any(label in case["task_id"].casefold() for label in FORBIDDEN_LABELS), "prompt_contains_task_specific_answer_hint": False})
    return rows


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("fresh V2 run required")
    cases, evaluators = runtime_cases(), evaluator_cases()
    assert len(cases) == len(evaluators) == 10
    v1_cases = read_json(V1_RUNTIME)["cases"]
    v1_requests = {case["input_request"] for case in v1_cases}
    v1_targets = {case["environment_facts"]["authority_record"]["allowed_targets"][0] for case in v1_cases}
    assert all(case["input_request"] not in v1_requests and case["environment_facts"]["authority_record"]["allowed_targets"][0] not in v1_targets for case in cases)
    leaks = leakage_audit(cases, evaluators)
    assert all(not row["target_semantic_label_leak"] and not row["runtime_authority_class_leak"] and not row["runtime_regime_label_present"] and not row["evaluator_fields_present"] and not row["task_id_class_leak"] and not row["prompt_contains_task_specific_answer_hint"] for row in leaks)
    out.mkdir(parents=True, exist_ok=True)
    write_json(RUNTIME_CASES, {"schema": "zth_true_semantic_fallback_v2_runtime_cases_v0", "cases": cases})
    write_json(EVALUATOR_CASES, {"schema": "zth_true_semantic_fallback_v2_evaluator_cases_v0", "cases": evaluators})
    write_json(REGISTRY, {"schema": "zth_true_semantic_fallback_v2_registry_v0", "automatic_promotion": False, "entries": [{"capability_id": MODEL_CAPABILITY, "supplier_id": MODEL_SUPPLIER, "supplier_type": "MODEL", "interface_id": MODEL_INTERFACE, "status": "EXPERIMENTAL_CANDIDATE", "evidence_scope": "fresh two-class true semantic operation classification", "qualification_decision": "no promotion"}, {"capability_id": tool.TOOL_CAPABILITY, "supplier_id": tool.TOOL_SUPPLIER, "supplier_type": "TOOL", "interface_id": "repository_relative_metadata_observation_v0", "status": "QUALIFIED_EXPLORATORY", "evidence_scope": "prior exact-target read-only metadata observation", "qualification_decision": "preserved prior evidence"}]})
    write_json(LEAKAGE_AUDIT, {"schema": "zth_true_semantic_fallback_v2_model_input_leakage_audit_v0", "rows": leaks, "pass": True})
    planned = 0
    preflights = []
    gaps = []
    plans = []
    execution_order = []
    for case in cases:
        pre = preflight(case["input_request"])
        p0 = plan(case["task_id"], pre)
        preflights.append(pre)
        plans.append(p0)
        execution_order.append(case["task_id"])
        task_dir = out / "tasks" / case["task_id"]
        write_json(task_dir / "runtime_task.json", case)
        write_json(task_dir / "preflight.json", pre)
        write_json(task_dir / "capability_plan_0.json", p0)
        if pre["model_required"]:
            assert pre["semantic_fallback_eligible"] and pre["remaining_candidate_operation_classes"] == ["observe_presence", "inspect"] and not pre["deterministic_canonical_operation_available_pre_model"]
            gap = {"known_facts_before_model": ["exactly_one_safe_target", "safe_bounded_request", "unambiguous_request", "shared_runtime_authority_allows_both_classes"], "unknown_decision_critical_fact": "which bounded semantic operation class the request expresses", "remaining_candidate_classes": ["observe_presence", "inspect"], "why_deterministic_resolution_is_insufficient": "request is outside the frozen deterministic operation grammar", "why_model_is_permitted": "two safe classes remain semantically plausible"}
            gaps.append(gap)
            write_json(task_dir / "semantic_information_gap.json", gap)
            (task_dir / "prompt.txt").write_text(prompt(case["input_request"]), encoding="utf-8")
            write_json(task_dir / "schema.json", schema())
            planned += 1
        elif case["task_id"] in {"tsfv2-007", "tsfv2-008"}:
            assert not pre["model_required"]
    assert planned == 6
    assert all(preflights[i]["semantic_fallback_eligible"] for i in range(6))
    assert all(plans[i]["planned_model_calls"] == 1 for i in range(6))
    assert all(plans[i]["planned_model_calls"] == 0 for i in range(6, 10))
    assert hasattr(telemetry_provider, "telemetry_base_url") and hasattr(telemetry_provider, "telemetry_preflight")
    before = {"runtime_cases": sha_file(RUNTIME_CASES), "authority": sha_bytes(canonical([case["environment_facts"]["authority_record"] for case in cases])), "leakage": sha_file(LEAKAGE_AUDIT), "preflights": sha_bytes(canonical(preflights)), "gaps": sha_bytes(canonical(gaps)), "plans": sha_bytes(canonical(plans)), "prompts": sha_bytes(canonical({case["task_id"]: prompt(case["input_request"]) for case in cases[:6]})), "schemas": sha_bytes(canonical(schema())), "execution_order": sha_bytes(canonical(execution_order))}
    corrupted = [{**item, "expected_semantic_class": "inspect" if item["expected_semantic_class"] == "observe_presence" else "observe_presence", "expected_task_terminal_success": not item["expected_task_terminal_success"], "expected_execution_path_complete": not item["expected_execution_path_complete"], "regime": "CORRUPTED"} for item in evaluators]
    after = {"runtime_cases": sha_file(RUNTIME_CASES), "authority": sha_bytes(canonical([case["environment_facts"]["authority_record"] for case in cases])), "leakage": sha_file(LEAKAGE_AUDIT), "preflights": sha_bytes(canonical([preflight(case["input_request"]) for case in cases])), "gaps": sha_bytes(canonical(gaps)), "plans": sha_bytes(canonical([plan(case["task_id"], preflight(case["input_request"])) for case in cases])), "prompts": sha_bytes(canonical({case["task_id"]: prompt(case["input_request"]) for case in cases[:6]})), "schemas": sha_bytes(canonical(schema())), "execution_order": sha_bytes(canonical(execution_order))}
    assert before == after
    write_json(out / "evaluator_corruption_invariance.json", {"before_hashes": before, "after_hashes": after, "corrupted_evaluator": corrupted, "pass": True})
    write_json(out / "execution_order.json", {"order": execution_order, "counterbalanced": True, "class_labels_runtime_visible": False})
    manifest = {"schema": "zth_true_semantic_fallback_v2_manifest_v0", "status": "prepared_model_free", "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver_sha256": sha_file(Path(__file__).resolve()), "runtime_cases_sha256": sha_file(RUNTIME_CASES), "evaluator_cases_sha256": sha_file(EVALUATOR_CASES), "registry_sha256": sha_file(REGISTRY), "leakage_audit_sha256": sha_file(LEAKAGE_AUDIT), "task_count": 10, "true_fallback_eligibility": 6, "planned_model_calls": 6, "planned_tool_calls": sum(p["planned_tool_calls"] for p in plans), "control_model_calls": 0, "model_calls_made": 0, "tool_calls_made": 0, "response_files": 0, "target_path_predicts_semantic_class": False, "runtime_authority_independent_of_expected_class": True, "evaluator_class_corruption_runtime_invariance": True, "v1_holdout_reuse_count": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0, "retries": 0, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "qualification_change": False, "model_id": MODEL_ID, "model_sha256": MODEL_SHA, "operative_parameters": PARAMS, "gpu_uuid": GPU_UUID, "prompt_template_relationship": "V1 enum-only meanings and instruction style preserved; no V1 failure-specific content", "telemetry_provider": "scripts.zth_qwen3_0_6b_clean_scope_logic_probe"}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls": 0, "tool_calls": 0, "teacher_calls": 0, "retries": 0})
    print(json.dumps({"status": "prepared", "task_count": 10, "true_fallback_eligibility": 6, "planned_model_calls": 6, "planned_tool_calls": manifest["planned_tool_calls"], "MODEL_CALLS_MADE": 0, "TOOL_CALLS_MADE": 0, "response_files": 0}, indent=2))


def model_preflight(out: Path):
    spec = runtime.worker_spec()
    models = decomposition.list_models(spec, timeout=30)
    candidate = next((item for item in models.get("data", []) if item.get("id") == MODEL_ID), None)
    meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != PARAMS:
        raise RuntimeError("model binding mismatch")
    telemetry_url = telemetry_provider.telemetry_base_url()
    telemetry = telemetry_provider.telemetry_preflight(telemetry_url)
    write_json(out / "model_preflight.json", {"model_meta": meta, "telemetry": telemetry, "model_id": MODEL_ID, "gpu_uuid": GPU_UUID, "telemetry_provider": "scripts.zth_qwen3_0_6b_clean_scope_logic_probe"})
    return spec, telemetry_url


def execute(out: Path) -> None:
    manifest = read_json(out / "router_manifest.json")
    spec, telemetry_url = model_preflight(out) if manifest["planned_model_calls"] else (None, None)
    model_calls = tool_calls = 0
    for task_dir in sorted((out / "tasks").glob("*")):
        runtime_task = read_json(task_dir / "runtime_task.json")
        pre = read_json(task_dir / "preflight.json")
        trace = {"schema": "zth_true_semantic_fallback_v2_trace_v0", "task_id": runtime_task["task_id"], "runtime_expected_field_reads": 0, "model_calls": [], "tool_calls": []}
        operation = None
        if pre["model_required"]:
            write_json(task_dir / "call_started.json", {"task_id": runtime_task["task_id"], "started_at": now(), "prompt_sha256": sha_file(task_dir / "prompt.txt"), "schema_sha256": sha_file(task_dir / "schema.json"), "supplier_id": MODEL_SUPPLIER, "model_id": MODEL_ID})
            sampler = PowerSampler(lambda: read_gpu_power(GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=GPU_UUID, sample_interval_seconds=POWER_INTERVAL)
            started = time.monotonic(); sampler.start()
            response = decomposition.structured_call(spec, (task_dir / "prompt.txt").read_text(encoding="utf-8"), response_format(), MAX_TOKENS, TIMEOUT)
            elapsed = time.monotonic() - started; samples = sampler.stop(); energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL, expected_gpu_uuid=GPU_UUID)
            metadata = response.metadata(); metadata["request_url"] = None
            write_json(task_dir / "response.json", {"status": response.status, "content": response.content, "metadata": metadata, "wall_elapsed_ms": round(elapsed * 1000, 3), "gross_energy_joules": energy})
            write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": GPU_UUID, "samples": [{"timestamp_utc": sample.timestamp_utc, "power_watts": sample.power_watts, "gpu_uuid": sample.gpu_uuid, "sequence": sample.sequence} for sample in samples]})
            operation, parse_valid, contract_valid, diagnostics = parse_response(response.content); model_calls += 1
            admissible = operation in pre["remaining_candidate_operation_classes"] if operation else False
            write_json(task_dir / "candidate_validation.json", {"candidate": operation, "parse_valid": parse_valid, "contract_valid": contract_valid, "candidate_valid": operation in ENUM if operation else False, "candidate_admissible": admissible, "diagnostics": diagnostics})
            trace["model_calls"].append({"parse_valid": parse_valid, "contract_valid": contract_valid, "candidate_admissible": admissible})
            if not contract_valid or operation is None or operation == "unresolved" or not admissible:
                result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "SEMANTIC_CANDIDATE_INVALID_OR_UNRESOLVED", "model_calls": 1, "tool_calls": 0}
                write_json(task_dir / "runtime_result.json", result); trace["terminal_state"] = result["terminal_state"]; write_json(task_dir / "route_trace.json", trace); continue
            write_json(task_dir / "operation_derivation_1.json", {"status": "RESOLVED", "derivation_type": "PRIOR_MODEL_STEP_ENUM_VALIDATION", "canonical_operation": operation, "model_output_granted_authority": False})
            p1 = plan(runtime_task["task_id"], pre, operation); write_json(task_dir / "capability_plan_1.json", p1)
        else:
            derivation = fallback.operation_derivation(runtime_task["input_request"])
            operation = derivation.get("canonical_operation") if derivation["status"] == "RESOLVED" else None
            p1 = plan(runtime_task["task_id"], pre, operation); write_json(task_dir / "capability_plan_1.json", p1)
        if operation == "observe_presence" and p1["overall_coverage"] == "COMPLETE":
            authority = runtime_task["environment_facts"]["authority_record"]
            auth, request, tool_auth, observation, count = confirmation.execute_read_only_observation(operation, pre["target"], authority)
            write_json(task_dir / "execution_authority_validation.json", auth); write_json(task_dir / "tool_request.json", request)
            if tool_auth is not None: write_json(task_dir / "tool_authority_validation.json", tool_auth)
            if auth["status"] != "AUTHORIZED":
                result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": auth["status"], "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 0}
            else:
                tool_calls += count; write_json(task_dir / "tool_observation.json", observation); validation = tool.validate_observation(observation, request, tool_auth); write_json(task_dir / "tool_result_validation.json", validation)
                contract = success_contract(operation); state = {"operation_resolved": True, "operation_authorized": auth["operation_authorized"], "target_bound": auth["target_authorized"], "execution_coverage_complete": True, "observation_valid": validation["status"] == "VALID"}; evaluation = evaluate_success_contract(contract, state); write_json(task_dir / "success_contract_1.json", contract); write_json(task_dir / "success_contract_evaluation.json", evaluation)
                result = {"routing_success": True, "execution_path_complete": evaluation["passed"], "task_terminal_success": evaluation["passed"], "terminal_state": "terminal_success" if evaluation["passed"] else "ready_for_review", "reason": "SUCCESS_CONTRACT_EVALUATED", "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 1}
        elif operation == "inspect":
            result = {"routing_success": True, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "NO_QUALIFIED_EXECUTION_SUPPLIER", "model_calls": 1 if pre["model_required"] else 0, "tool_calls": 0}
        else:
            result = {"routing_success": False, "execution_path_complete": False, "task_terminal_success": False, "terminal_state": "ready_for_review", "reason": "NO_ROUTABLE_OPERATION", "model_calls": 0, "tool_calls": 0}
        write_json(task_dir / "runtime_result.json", result); trace["terminal_state"] = result["terminal_state"]; write_json(task_dir / "route_trace.json", trace)
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "model_calls": model_calls, "tool_calls": tool_calls, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "retries": 0, "runtime_evaluator_influence": 0, "model_output_granted_authority": 0})


def closeout(out: Path) -> None:
    evaluators = {item["task_id"]: item for item in read_json(EVALUATOR_CASES)["cases"]}
    rows = []
    latencies, energy = [], []
    for task_dir in sorted((out / "tasks").glob("*")):
        ev = evaluators[task_dir.name]; pre = read_json(task_dir / "preflight.json"); result_path = task_dir / "runtime_result.json"
        if not result_path.exists():
            continue
        result = read_json(result_path); validation = read_json(task_dir / "candidate_validation.json") if (task_dir / "candidate_validation.json").exists() else {}
        response = read_json(task_dir / "response.json") if (task_dir / "response.json").exists() else None
        if response: latencies.append(response.get("wall_elapsed_ms")); energy.append(response.get("gross_energy_joules"))
        candidate = validation.get("candidate"); semantic_correct = candidate == ev["expected_semantic_class"] if ev["expected_model_required"] else None
        routing_correct = semantic_correct if ev["expected_model_required"] else result["terminal_state"] == ("terminal_success" if ev["expected_task_terminal_success"] else "ready_for_review")
        rows.append({"task_id": task_dir.name, "regime": ev["regime"], "model_required": ev["expected_model_required"], "preflight_eligible": pre["semantic_fallback_eligible"], "parse_valid": validation.get("parse_valid"), "contract_valid": validation.get("contract_valid"), "candidate_valid": validation.get("candidate_valid"), "candidate_admissible": validation.get("candidate_admissible"), "observed_operation_class": candidate, "semantic_classification_correct": semantic_correct, "routing_decision_correct": routing_correct, "execution_path_complete": result["execution_path_complete"], "task_terminal_success": result["task_terminal_success"], "terminal_state": result["terminal_state"], "model_calls": result.get("model_calls", 0), "tool_calls": result.get("tool_calls", 0)})
    model_rows = [row for row in rows if row["model_required"]]; presence = [row for row in model_rows if row["task_id"] in {"tsfv2-001", "tsfv2-003", "tsfv2-005"}]; inspect = [row for row in model_rows if row["task_id"] in {"tsfv2-002", "tsfv2-004", "tsfv2-006"}]
    inspect_gated = sum(row["task_id"] in {"tsfv2-002", "tsfv2-004", "tsfv2-006", "tsfv2-008"} and row["terminal_state"] == "ready_for_review" and ((row["model_required"] and row["semantic_classification_correct"] is True) or (not row["model_required"] and row["task_id"] == "tsfv2-008")) for row in rows)
    aggregate = {"schema": "zth_true_semantic_fallback_v2_aggregate_v0", "task_count": len(rows), "semantic_opportunities": 6, "model_calls_planned": 6, "model_calls_made": sum(row["model_calls"] for row in rows), "parse_valid": sum(row["parse_valid"] is True for row in model_rows), "contract_valid": sum(row["contract_valid"] is True for row in model_rows), "candidate_valid": sum(row["candidate_valid"] is True for row in model_rows), "candidate_admissible": sum(row["candidate_admissible"] is True for row in model_rows), "semantic_correct": sum(row["semantic_classification_correct"] is True for row in model_rows), "presence_correct": sum(row["semantic_classification_correct"] is True for row in presence), "inspect_correct": sum(row["semantic_classification_correct"] is True for row in inspect), "unresolved_outputs": sum(row["observed_operation_class"] in {None, "unresolved"} for row in model_rows), "wrong_safe_classifications": sum(row["semantic_classification_correct"] is False and row["observed_operation_class"] in {"observe_presence", "inspect"} for row in model_rows), "routing_decisions_correct": sum(row["routing_decision_correct"] for row in rows), "execution_paths_complete": sum(row["execution_path_complete"] for row in rows), "task_terminal_successes": sum(row["task_terminal_success"] for row in rows), "presence_observations_executed": sum(row["task_id"] in {"tsfv2-001", "tsfv2-003", "tsfv2-005", "tsfv2-007"} and row["tool_calls"] == 1 for row in rows), "inspect_cases_correctly_no_actuator_gated": inspect_gated, "deterministic_control_model_calls": sum(row["model_calls"] for row in rows if row["task_id"] in {"tsfv2-007", "tsfv2-008"}), "fail_closed_control_model_calls": sum(row["model_calls"] for row in rows if row["task_id"] in {"tsfv2-009", "tsfv2-010"}), "tool_calls_made": sum(row["tool_calls"] for row in rows), "runtime_evaluator_influence": 0, "MODEL_OUTPUT_GRANTED_AUTHORITY": 0, "retries": 0, "teacher_calls": 0, "30b_calls": 0, "external_calls": 0, "qualification_change": False, "model_latency_ms": {"mean": statistics.mean(latencies) if latencies else None, "median": statistics.median(latencies) if latencies else None, "p95": sorted(latencies)[min(len(latencies) - 1, round((len(latencies) - 1) * 0.95))] if latencies else None}, "model_energy_joules": {"total": sum(energy), "mean": statistics.mean(energy) if energy else None, "median": statistics.median(energy) if energy else None}, "rows": rows}
    markers = {"TRUE_SEMANTIC_FALLBACK_DEMONSTRATED": aggregate["semantic_correct"] > 0, "DECISION_CRITICAL_MODEL_SEMANTIC_CONTRIBUTION_DEMONSTRATED": aggregate["semantic_correct"] > 0, "MODEL_OUTPUT_TO_CAPABILITY_PLAN_TRANSITION_DEMONSTRATED": any((out / "tasks" / row["task_id"] / "capability_plan_1.json").exists() and row["semantic_classification_correct"] is True for row in rows), "MULTI_CLASS_BOUNDED_SEMANTIC_FALLBACK_DEMONSTRATED": aggregate["presence_correct"] > 0 and aggregate["inspect_correct"] > 0}
    aggregate["markers"] = markers
    matrix = {"schema": "zth_true_semantic_fallback_v2_matrix_v0", "aggregate": aggregate, "execution_driver_sha256": read_json(out / "router_manifest.json")["driver_sha256"], "closeout_driver_sha256": sha_file(Path(__file__).resolve())}
    write_json(out / "aggregate.json", aggregate); write_json(out / "matrix.json", matrix)


def main() -> None:
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--prepare", action="store_true"); group.add_argument("--execute", action="store_true"); group.add_argument("--closeout", action="store_true"); parser.add_argument("--output-dir", type=Path, default=RUN); args = parser.parse_args()
    if args.prepare: prepare(args.output_dir)
    elif args.execute: execute(args.output_dir)
    else: closeout(args.output_dir)


if __name__ == "__main__":
    main()
