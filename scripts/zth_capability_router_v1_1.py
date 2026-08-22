#!/usr/bin/env python3
"""Oracle-free runtime-grounded capability-router V1.1 slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_capability_router_v1 as v1
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = base.ROOT
TASKS = ROOT / "docs/research/CAPABILITY_ROUTER_V1_1_TASKS_2026-08-22.json"
REGISTRY = ROOT / "docs/research/CAPABILITY_ROUTER_EXPERIMENTAL_REGISTRY_V1_2026-08-22.json"
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


def load_tasks() -> list[dict[str, Any]]:
    tasks = json.loads(TASKS.read_text(encoding="utf-8"))["tasks"]
    if not isinstance(tasks, list) or len(tasks) != 8 or len({task["task_id"] for task in tasks}) != 8:
        raise RuntimeError("V1.1 requires eight unique frozen tasks")
    return tasks


def load_registry() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = registry.get("entries", [])
    for entry in entries:
        if not (ROOT / entry["evidence_artifact"]).is_file():
            raise RuntimeError(f"missing registry evidence: {entry['evidence_artifact']}")
    return registry


def registry_index() -> dict[str, list[dict[str, Any]]]:
    return v1.index_registry(load_registry())


def build_planner_facts(task: dict[str, Any], triage: dict[str, Any], orchestration: dict[str, Any]) -> dict[str, Any]:
    """Build runtime facts from packet content and independent world facts only."""
    return {
        "schema": "zth_router_v1_1_planner_facts_v1",
        "task_id": task["task_id"],
        "input_request": task["input_request"],
        "triage_content": {
            "task_type": triage["task_type"],
            "allowed_targets": list(triage["allowed_targets"]),
            "held_targets": list(triage["held_targets"]),
            "risk_flags": list(triage["risk_flags"]),
            "output_contract": dict(triage["output_contract"]),
            "validation_hooks": list(triage["validation_hooks"]),
        },
        "orchestration_content": {
            "review_required": orchestration["review_required"],
            "authority_boundaries": list(orchestration["authority_boundaries"]),
            "allowed_targets": list(orchestration["allowed_targets"]),
            "held_targets": list(orchestration["held_targets"]),
        },
        "world_facts": dict(task.get("world_facts", {})),
        "packet_source": {"triage_id": triage["triage_id"], "orchestration_id": orchestration["orchestration_id"]},
    }


def derive_required_capabilities(planner_facts: dict[str, Any]) -> list[str]:
    facts = planner_facts["world_facts"]
    required: list[str] = []
    if facts.get("canonical_target_match") is not None or facts.get("canonical_operation_match") is not None:
        required.append("deterministic.boolean_composition")
    if facts.get("semantic_request_shape") == "single_action_object":
        required.append("semantic.minimal_action_object_extraction")
    if facts.get("requires_target_binding") is True:
        required.append("deterministic.direct_target_binding")
    if facts.get("requires_reference_entity") is True or facts.get("semantic_request_shape") == "reference_entity_relation":
        required.append("semantic.reference_entity_extraction")
    if facts.get("requires_tool_observation") is True:
        required.append(str(facts.get("tool_capability_id", "tool.unknown")))
    return required


def select_supplier(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    qualified = [candidate for candidate in candidates if candidate["status"] == "QUALIFIED_EXPLORATORY"]
    if not qualified:
        return None, "No qualified supplier; coverage is incomplete and execution must fail closed."
    order = {"DETERMINISTIC_CODE": 0, "MODEL": 1, "TOOL": 2, "REVIEW_OR_ESCALATION": 3}
    selected = sorted(qualified, key=lambda entry: (order.get(entry["supplier_type"], 99), entry["supplier_id"]))[0]
    return selected, f"Selected qualified {selected['supplier_type']} supplier by explicit type precedence."


def build_success_contract(planner_facts: dict[str, Any], derived: list[str], complete: bool) -> dict[str, Any]:
    facts = planner_facts["world_facts"]
    predicates: list[dict[str, Any]] = []
    if "semantic.minimal_action_object_extraction" in derived:
        predicates.extend([
            {"predicate": "structured_output_exact_fields", "fields": ["action", "object_expression"]},
            {"predicate": "action_member_of_allowed_operations", "allowed_operations": list(facts.get("allowed_operations", []))},
            {"predicate": "object_expression_equals_requested_target", "requested_target": facts.get("requested_target")},
        ])
    if "deterministic.direct_target_binding" in derived:
        predicates.append({"predicate": "direct_target_binding_from_observation", "requested_target": facts.get("requested_target")})
    if "deterministic.boolean_composition" in derived:
        predicates.append({"predicate": "compute_boolean_policy_from_canonical_operands", "operands": ["canonical_target_match", "canonical_operation_match"]})
    if not complete:
        predicates.append({"predicate": "coverage_complete", "value": False})
    return {"schema": "zth_router_v1_1_success_contract_v1", "task_id": planner_facts["task_id"], "predicates": predicates, "contains_worked_answer": False}


def plan_capabilities(planner_facts: dict[str, Any], index: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    derived = derive_required_capabilities(planner_facts)
    capabilities = []
    for capability_id in derived:
        candidates = list(index.get(capability_id, []))
        selected, reason = select_supplier(candidates)
        qualified = [entry for entry in candidates if entry["status"] == "QUALIFIED_EXPLORATORY"]
        capabilities.append({
            "capability_id": capability_id,
            "candidate_suppliers": [{"supplier_id": e["supplier_id"], "supplier_type": e["supplier_type"], "interface_id": e["interface_id"], "status": e["status"]} for e in candidates],
            "qualified_candidates": [{"supplier_id": e["supplier_id"], "supplier_type": e["supplier_type"], "interface_id": e["interface_id"]} for e in qualified],
            "selected_supplier": None if selected is None else {"supplier_id": selected["supplier_id"], "supplier_type": selected["supplier_type"], "interface_id": selected["interface_id"]},
            "selection_reason": reason,
            "coverage_status": "COVERED" if selected else "UNCOVERED",
        })
    complete = bool(capabilities) and all(item["coverage_status"] == "COVERED" for item in capabilities)
    steps = []
    if complete:
        for item in capabilities:
            supplier = item["selected_supplier"]
            cap = item["capability_id"]
            if cap == "semantic.minimal_action_object_extraction":
                requires_inputs = ["input_request"]
                produces = ["action", "object_expression"]
                depends_on: list[str] = []
            elif cap == "deterministic.direct_target_binding":
                requires_inputs = ["object_expression", "requested_target"]
                produces = ["target_binding"]
                depends_on = ["step_semantic_minimal_action_object_extraction"]
            elif cap == "deterministic.boolean_composition":
                requires_inputs = ["canonical_target_match", "canonical_operation_match"]
                produces = ["policy_result"]
                depends_on = []
            else:
                requires_inputs, produces, depends_on = [], [], []
            steps.append({"step_id": f"step_{cap.replace('.', '_')}", "capability_id": cap, "supplier_id": supplier["supplier_id"], "supplier_type": supplier["supplier_type"], "requires_inputs": requires_inputs, "produces_outputs": produces, "depends_on": depends_on})
    return {
        "schema": "zth_router_v1_1_capability_plan_v1",
        "task_id": planner_facts["task_id"],
        "packet_source": planner_facts["packet_source"],
        "derived_required_capabilities": derived,
        "capabilities": capabilities,
        "overall_coverage": "COMPLETE" if complete else "INCOMPLETE",
        "execution_steps": steps,
        "planned_model_calls": sum(step["supplier_type"] == "MODEL" for step in steps),
        "planned_tool_calls": sum(step["supplier_type"] == "TOOL" for step in steps),
        "planned_deterministic_steps": sum(step["supplier_type"] == "DETERMINISTIC_CODE" for step in steps),
    }


def parse_model_output(content: str) -> tuple[dict[str, str] | None, bool, bool, list[str]]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    valid = isinstance(parsed, dict) and set(parsed) == {"action", "object_expression"} and all(isinstance(parsed.get(field), str) for field in ("action", "object_expression"))
    return (parsed if valid else None), True, valid, ([] if valid else ["semantic contract failed"])


def validate_observation(contract: dict[str, Any], planner_facts: dict[str, Any], observations: dict[str, Any]) -> tuple[bool, list[str]]:
    facts = planner_facts["world_facts"]
    failures: list[str] = []
    for predicate in contract["predicates"]:
        kind = predicate["predicate"]
        if kind == "structured_output_exact_fields" and not observations.get("semantic_contract_valid"):
            failures.append(kind)
        elif kind == "action_member_of_allowed_operations" and observations.get("action") not in predicate["allowed_operations"]:
            failures.append(kind)
        elif kind == "object_expression_equals_requested_target" and norm(observations.get("object_expression")) != norm(predicate["requested_target"]):
            failures.append(kind)
        elif kind == "direct_target_binding_from_observation" and not observations.get("target_binding"):
            failures.append(kind)
        elif kind == "coverage_complete" and predicate["value"] is False:
            failures.append(kind)
        elif kind == "compute_boolean_policy_from_canonical_operands" and "policy_result" not in observations:
            failures.append(kind)
    return not failures, failures


def execute_runtime_task(runtime_task: dict[str, Any], plan: dict[str, Any], contract: dict[str, Any], model_call: Callable[[dict[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run one prepared runtime task without reading evaluator data."""
    if plan["overall_coverage"] != "COMPLETE":
        return {"terminal_state": "ready_for_review", "observations": {}, "validator": {"status": "not_attempted", "reason": "incomplete capability coverage"}, "model_calls": 0, "tool_calls": 0, "deterministic_steps": 0}
    observations: dict[str, Any] = {}
    model_calls = 0
    tool_calls = 0
    deterministic_steps = 0
    failures: list[str] = []
    for step in plan["execution_steps"]:
        missing = [name for name in step["requires_inputs"] if name not in observations and name not in runtime_task["world_facts"] and name != "input_request"]
        if missing:
            failures.extend([f"missing:{name}" for name in missing])
            continue
        if step["supplier_type"] == "MODEL":
            if model_call is None:
                failures.append("model_call_unavailable")
                continue
            model_calls += 1
            result = model_call(step)
            parsed, parse_valid, contract_valid, diagnostics = parse_model_output(result.get("content", ""))
            observations["semantic_contract_valid"] = parse_valid and contract_valid
            if parsed:
                observations.update(parsed)
            result["parse_valid"] = parse_valid
            result["contract_valid"] = contract_valid
            result["diagnostics"] = diagnostics
            observations.setdefault("model_results", []).append(result)
        elif step["supplier_type"] == "DETERMINISTIC_CODE":
            deterministic_steps += 1
            facts = runtime_task["world_facts"]
            if step["capability_id"] == "deterministic.boolean_composition":
                observations["policy_result"] = not (bool(facts.get("canonical_target_match")) and bool(facts.get("canonical_operation_match")))
            elif step["capability_id"] == "deterministic.direct_target_binding":
                observations["target_binding"] = norm(observations.get("object_expression")) == norm(facts.get("requested_target"))
            else:
                failures.append(f"unknown_deterministic:{step['capability_id']}")
        elif step["supplier_type"] == "TOOL":
            tool_calls += 1
            failures.append("tool_execution_not_demonstrated")
    valid, contract_failures = validate_observation(contract, {"world_facts": runtime_task["world_facts"]}, observations)
    failures.extend(contract_failures)
    valid = valid and not failures
    return {"terminal_state": "terminal_success" if valid else "ready_for_review", "observations": observations, "validator": {"status": "passed" if valid else "failed", "failures": sorted(set(failures))}, "model_calls": model_calls, "tool_calls": tool_calls, "deterministic_steps": deterministic_steps}


def lazy_model_backend_gate(plans: list[dict[str, Any]], initializer: Callable[[], Any]) -> bool:
    if not any(plan["planned_model_calls"] > 0 for plan in plans):
        return False
    initializer()
    return True


def validate_model_free() -> dict[str, Any]:
    tasks = load_tasks()
    registry = load_registry()
    index = v1.index_registry(registry)
    prepared = []
    for task in tasks:
        triage, orchestration = v1.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
        facts = build_planner_facts(task, triage, orchestration)
        derived = derive_required_capabilities(facts)
        plan = plan_capabilities(facts, index)
        contract = build_success_contract(facts, derived, plan["overall_coverage"] == "COMPLETE")
        prepared.append((task, triage, orchestration, facts, plan, contract))
    if sum(plan["overall_coverage"] == "COMPLETE" for *_, plan, _ in prepared) != 6:
        raise RuntimeError("V1.1 expected six complete plans")
    if sum(plan["overall_coverage"] == "INCOMPLETE" for *_, plan, _ in prepared) != 2:
        raise RuntimeError("V1.1 expected two incomplete plans")
    if any("expected_" in json.dumps({"facts": facts, "plan": plan, "contract": contract}) for *_, facts, plan, contract in prepared):
        raise RuntimeError("evaluator fields leaked into runtime preparation")
    return {"tasks": tasks, "registry": registry, "plans": prepared, "task_sha256": sha_file(TASKS), "registry_sha256": sha_file(REGISTRY), "schema_sha256": sha_bytes(canonical(v1.minimal_schema())), "format_sha256": sha_bytes(canonical(v1.response_format()))}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = validate_model_free()
    for task, triage, orchestration, facts, plan, contract in binding["plans"]:
        task_dir = out / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        runtime_task = {"schema": "zth_router_v1_1_runtime_task_v1", "task_id": task["task_id"], "input_request": task["input_request"], "world_facts": task["world_facts"], "packet_source": facts["packet_source"]}
        evaluator = {key: value for key, value in task.items() if key.startswith("expected_")}
        write_json(task_dir / "runtime_task.json", runtime_task)
        write_json(task_dir / "evaluator.json", evaluator)
        write_json(task_dir / "vogon_triage_packet.json", triage)
        write_json(task_dir / "orchestration_packet.json", orchestration)
        write_json(task_dir / "planner_facts.json", facts)
        write_json(task_dir / "capability_plan.json", plan)
        write_json(task_dir / "success_contract.json", contract)
        if plan["planned_model_calls"]:
            (task_dir / "semantic_prompt.txt").write_text(v1.semantic_prompt(task["input_request"]), encoding="utf-8")
    manifest = {"schema": "zth_router_v1_1_manifest_v1", "status": "prepared_exploratory_not_production", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_sha256": binding["task_sha256"], "registry_sha256": binding["registry_sha256"], "schema_sha256": binding["schema_sha256"], "response_format_sha256": binding["format_sha256"], "task_count": 8, "planned_model_calls": sum(plan["planned_model_calls"] for *_, plan, _ in binding["plans"]), "planned_tool_calls": sum(plan["planned_tool_calls"] for *_, plan, _ in binding["plans"]), "planned_deterministic_steps": sum(plan["planned_deterministic_steps"] for *_, plan, _ in binding["plans"]), "runtime_expected_field_reads": 0, "model_backend_initialized": False, "model_calls_made": False, "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False}, "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX}, "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS}}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "model_calls": 0, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 8, "planned_model_calls": manifest["planned_model_calls"], "model_calls": 0}, indent=2))


def execute(out: Path) -> None:
    manifest = json.loads((out / "router_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("V1.1 manifest digest mismatch")
    plans = []
    for task_dir in sorted((out / "tasks").glob("*")):
        plans.append(json.loads((task_dir / "capability_plan.json").read_text(encoding="utf-8")))
    needs_model = any(plan["planned_model_calls"] > 0 for plan in plans)
    model_spec = None
    telemetry_url = None
    if needs_model:
        model_spec = runtime.worker_spec()
        models = decomposition.list_models(model_spec, timeout=30)
        model = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
        meta = (model or {}).get("meta") or {}
        if model is None or meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
            raise RuntimeError("V1.1 runtime binding mismatch")
        telemetry_url = base.telemetry_base_url()
        base.telemetry_preflight(telemetry_url)
        idle_samples, idle_summary = base.sample_window(IDLE_SECONDS, telemetry_url)
        write_json(out / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
        write_json(out / "preflight.json", {"model_meta": meta, "telemetry": "passed", "planned_model_calls": manifest["planned_model_calls"]})
        manifest["model_backend_initialized"] = True
        write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "running", "model_calls_made": False, "model_calls": 0, "started_at": now(), "model_backend_initialized": needs_model})
    total_calls = total_det = total_tool = 0
    for task_dir in sorted((out / "tasks").glob("*")):
        runtime_task = json.loads((task_dir / "runtime_task.json").read_text(encoding="utf-8"))
        plan = json.loads((task_dir / "capability_plan.json").read_text(encoding="utf-8"))
        contract = json.loads((task_dir / "success_contract.json").read_text(encoding="utf-8"))
        route_trace = {"schema": "zth_router_v1_1_route_trace_v1", "task_id": runtime_task["task_id"], "runtime_inputs": ["runtime_task.json", "planner_facts.json"], "capability_plan": "capability_plan.json", "success_contract": "success_contract.json", "model_calls": [], "terminal_state": None}
        def model_call(step: dict[str, Any]) -> dict[str, Any]:
            nonlocal total_calls
            total_calls += 1
            prompt = (task_dir / "semantic_prompt.txt").read_text(encoding="utf-8")
            started = time.monotonic()
            sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
            sampler.start()
            response = decomposition.structured_call(model_spec, prompt, v1.response_format(), MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
            captured = time.monotonic()
            samples = sampler.stop()
            energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
            raw = {"status": response.status, "content": response.content, "metadata": response.metadata(), "wall_elapsed_ms": round((captured - started) * 1000, 3), "response_captured_at": now()}
            write_json(task_dir / "response.json", raw)
            write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "monotonic_seconds": s.monotonic_seconds, "gpu_uuid": s.gpu_uuid, "power_watts": s.power_watts, "sequence": s.sequence} for s in samples]})
            route_trace["model_calls"].append({"supplier_id": step["supplier_id"], "prompt_sha256": sha_bytes(prompt.encode()), "latency_ms": raw["wall_elapsed_ms"], "gross_energy_joules": energy})
            return {"content": response.content, "latency_ms": raw["wall_elapsed_ms"], "gross_energy_joules": energy}
        result = execute_runtime_task(runtime_task, plan, contract, model_call if needs_model else None)
        total_det += result["deterministic_steps"]
        total_tool += result["tool_calls"]
        route_trace["validator_result"] = result["validator"]
        route_trace["terminal_state"] = result["terminal_state"]
        write_json(task_dir / "runtime_result.json", result)
        write_json(task_dir / "route_trace.json", route_trace)
        write_json(task_dir / "runtime_scorecard.json", {"schema": "zth_router_v1_1_runtime_scorecard_v1", "task_id": runtime_task["task_id"], "terminal_state": result["terminal_state"], "validator": result["validator"], "model_calls": result["model_calls"], "tool_calls": result["tool_calls"], "deterministic_steps": result["deterministic_steps"], "runtime_expected_field_reads": 0})
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "completed_at": now(), "model_calls_made": total_calls > 0, "model_calls": total_calls, "deterministic_steps": total_det, "tool_calls": total_tool, "teacher_calls": 0, "retries": 0, "escalations": 0, "runtime_expected_field_reads": 0, "model_backend_initialized": needs_model})
    print(json.dumps({"status": "terminal_runtime", "tasks": 8, "model_calls": total_calls}, indent=2))


def closeout(out: Path) -> None:
    rows = []
    for task_dir in sorted((out / "tasks").glob("*")):
        evaluator = json.loads((task_dir / "evaluator.json").read_text(encoding="utf-8"))
        runtime_result = json.loads((task_dir / "runtime_result.json").read_text(encoding="utf-8"))
        plan = json.loads((task_dir / "capability_plan.json").read_text(encoding="utf-8"))
        actual_assignments = {item["capability_id"]: item["supplier_id"] for item in plan["execution_steps"]}
        expected_assignments = {item["capability_id"]: item["supplier_id"] for item in evaluator.get("expected_capability_assignments", [])}
        row = {"schema": "zth_router_v1_1_evaluator_scorecard_v1", "task_id": evaluator.get("task_id", task_dir.name), "runtime_terminal_state": runtime_result["terminal_state"], "expected_terminal_state": evaluator["expected_terminal_state"], "task_correct": runtime_result["terminal_state"] == evaluator["expected_terminal_state"], "capability_plan_correct": plan["derived_required_capabilities"] == evaluator["expected_required_capabilities"], "assignment_set_correct": actual_assignments == expected_assignments, "expected_required_capabilities": evaluator["expected_required_capabilities"], "runtime_model_calls": runtime_result["model_calls"], "expected_model_call_count": evaluator["expected_model_call_count"], "runtime_tool_calls": runtime_result["tool_calls"], "expected_tool_call_count": evaluator["expected_tool_call_count"]}
        write_json(task_dir / "evaluator_scorecard.json", row)
        rows.append(row)
    aggregate = {"schema": "zth_router_v1_1_aggregate_v1", "tasks_correct": sum(row["task_correct"] for row in rows), "capability_plans_correct": sum(row["capability_plan_correct"] for row in rows), "complete_plan_assignment_sets_correct": sum(row["assignment_set_correct"] for row in rows if row["runtime_terminal_state"] == "terminal_success"), "individual_capability_assignments_correct": sum(len(row["expected_required_capabilities"]) for row in rows if row["assignment_set_correct"] and row["runtime_terminal_state"] == "terminal_success"), "complete_coverage_tasks": sum(row["runtime_terminal_state"] == "terminal_success" for row in rows), "incomplete_coverage_failed_closed": sum(row["runtime_terminal_state"] == "ready_for_review" for row in rows), "runtime_expected_field_reads": 0, "evaluator_score_changes_only": True, "execution": {"teacher_calls": 0, "retries": 0, "escalations": 0}}
    write_json(out / "aggregate.json", aggregate)
    print(json.dumps({"status": "closeout_complete", **aggregate}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--execute", action="store_true")
    group.add_argument("--closeout", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.prepare:
        prepare(args.output_dir)
    elif args.execute:
        execute(args.output_dir)
    else:
        closeout(args.output_dir)


if __name__ == "__main__":
    main()
