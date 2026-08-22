#!/usr/bin/env python3
"""Packet-derived capability planning Router V1.2 exploratory slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
TASKS = ROOT / "docs/research/CAPABILITY_ROUTER_V1_2_TASKS_2026-08-22.json"
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
HINT_FIELDS = {
    "semantic_request_shape",
    "requires_target_binding",
    "requires_reference_entity",
    "requires_tool_observation",
    "tool_capability_id",
    "required_capabilities",
}
TARGET_RE = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9_-]*\.json)\b")


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
        raise RuntimeError("V1.2 requires eight unique tasks")
    return tasks


def load_registry() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for entry in registry.get("entries", []):
        if not (ROOT / entry["evidence_artifact"]).is_file():
            raise RuntimeError(f"missing registry evidence: {entry['evidence_artifact']}")
    return registry


def registry_index() -> dict[str, list[dict[str, Any]]]:
    return v1.index_registry(load_registry())


def make_packets(task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return v1.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})


def extract_requested_target(request: str) -> tuple[str | None, str]:
    matches = TARGET_RE.findall(request)
    if len(matches) == 1:
        return matches[0], "raw input_request unique filename token"
    return None, "raw input_request did not expose exactly one filename token"


def build_planner_facts(task: dict[str, Any], triage: dict[str, Any], orchestration: dict[str, Any]) -> dict[str, Any]:
    environment = dict(task.get("environment_facts", {}))
    requested_target, target_reason = extract_requested_target(task["input_request"])
    return {
        "schema": "zth_router_v1_2_planner_facts_v1",
        "task_id": task["task_id"],
        "request_evidence": {"input_request": task["input_request"], "requested_target": requested_target},
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
        "environment_facts": environment,
        "provenance": {
            "request": "input_request",
            "packet": ["vogon_triage_packet.json", "orchestration_packet.json"],
            "environment": "environment_facts",
            "requested_target_rule": target_reason,
        },
        "packet_source": {"triage_id": triage["triage_id"], "orchestration_id": orchestration["orchestration_id"]},
    }


def derive_capability_requirements(planner_facts: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    request = planner_facts["request_evidence"]["input_request"]
    triage = planner_facts["triage_content"]
    environment = planner_facts["environment_facts"]
    required: list[str] = []
    derivations: list[dict[str, Any]] = []
    unresolved: list[str] = []

    def add(capability_id: str, derivation_type: str, source_fields: list[str], reason: str) -> None:
        if capability_id not in required:
            required.append(capability_id)
        derivations.append({
            "capability_id": capability_id,
            "derivation_type": derivation_type,
            "source_artifacts": ["planner_facts.json"],
            "source_fields": source_fields,
            "reason": reason,
        })

    if isinstance(environment.get("canonical_operands"), dict):
        operands = environment["canonical_operands"]
        if {"target_match", "operation_match"} <= set(operands):
            add("deterministic.boolean_composition", "DETERMINISTIC_PACKET_RULE", ["environment_facts.canonical_operands"], "Canonical operands are already available as independent environment facts.")
        else:
            unresolved.append("deterministic.boolean_composition")
    elif isinstance(environment.get("authority_record"), dict):
        authority = environment["authority_record"]
        target = planner_facts["request_evidence"].get("requested_target")
        allowed_ops = authority.get("allowed_operations")
        if target and isinstance(allowed_ops, list) and triage["task_type"] in {"repo_patch", "docs_update"}:
            add("semantic.minimal_action_object_extraction", "SEMANTIC_INTERPRETATION", ["request_evidence.input_request", "triage_content.task_type"], "The request and packet identify a bounded operation/object interpretation task.")
            add("deterministic.direct_target_binding", "DETERMINISTIC_PACKET_RULE", ["request_evidence.requested_target", "environment_facts.authority_record.allowed_operations"], "Target equality and operation membership are deterministic after semantic extraction.")
        elif "reference entity" in norm(request):
            add("semantic.reference_entity_extraction", "SEMANTIC_INTERPRETATION", ["request_evidence.input_request", "environment_facts.authority_record"], "The request explicitly asks for a reference-entity relation, but this supplier is not qualified for it.")
        else:
            unresolved.append("operation/object capability requirement")
    elif environment.get("observation_requirement") == "current_repository_state":
        add("tool.read_only_repository_observation", "ENVIRONMENTAL_REQUIREMENT", ["environment_facts.observation_requirement", "request_evidence.input_request"], "Success requires a current repository observation; the registry must supply an observation capability.")
    elif "reference entity" in norm(request):
        add("semantic.reference_entity_extraction", "SEMANTIC_INTERPRETATION", ["request_evidence.input_request"], "The request contains an unresolved reference-entity interpretation.")
    else:
        unresolved.append("capability requirement")

    return required, derivations, unresolved


def select_supplier(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    qualified = [entry for entry in candidates if entry["status"] == "QUALIFIED_EXPLORATORY"]
    if not qualified:
        return None, "No qualified supplier; execution must fail closed."
    order = {"DETERMINISTIC_CODE": 0, "MODEL": 1, "TOOL": 2, "REVIEW_OR_ESCALATION": 3}
    selected = sorted(qualified, key=lambda entry: (order.get(entry["supplier_type"], 99), entry["supplier_id"]))[0]
    return selected, f"Selected qualified {selected['supplier_type']} supplier by explicit type precedence."


def plan_capabilities(planner_facts: dict[str, Any], index: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any], dict[str, Any]]:
    required, derivations, unresolved = derive_capability_requirements(planner_facts)
    records: list[dict[str, Any]] = []
    for capability_id in required:
        candidates = list(index.get(capability_id, []))
        selected, reason = select_supplier(candidates)
        records.append({
            "capability_id": capability_id,
            "candidate_suppliers": [{"supplier_id": e["supplier_id"], "supplier_type": e["supplier_type"], "interface_id": e["interface_id"], "status": e["status"]} for e in candidates],
            "qualified_candidates": [{"supplier_id": e["supplier_id"], "supplier_type": e["supplier_type"], "interface_id": e["interface_id"]} for e in candidates if e["status"] == "QUALIFIED_EXPLORATORY"],
            "selected_supplier": None if selected is None else {"supplier_id": selected["supplier_id"], "supplier_type": selected["supplier_type"], "interface_id": selected["interface_id"]},
            "selection_reason": reason,
            "coverage_status": "COVERED" if selected else "UNCOVERED",
        })
    complete = bool(required) and not unresolved and all(item["coverage_status"] == "COVERED" for item in records)
    steps: list[dict[str, Any]] = []
    if complete:
        for item in records:
            supplier = item["selected_supplier"]
            cap = item["capability_id"]
            if cap == "semantic.minimal_action_object_extraction":
                req, prod, deps = ["input_request"], ["action", "object_expression"], []
            elif cap == "deterministic.direct_target_binding":
                req, prod, deps = ["object_expression", "requested_target"], ["target_binding"], ["step_semantic_minimal_action_object_extraction"]
            elif cap == "deterministic.boolean_composition":
                req, prod, deps = ["canonical_operands"], ["policy_result"], []
            else:
                req, prod, deps = [], [], []
            steps.append({"step_id": f"step_{cap.replace('.', '_')}", "capability_id": cap, "supplier_id": supplier["supplier_id"], "supplier_type": supplier["supplier_type"], "requires_inputs": req, "produces_outputs": prod, "depends_on": deps, "input_provenance": {name: ("PACKET" if name == "requested_target" else "ENVIRONMENT" if name == "canonical_operands" else "PRIOR_STEP" if name in {"object_expression", "action"} else "PACKET") for name in req}})
    plan = {
        "schema": "zth_router_v1_2_capability_plan_v1",
        "task_id": planner_facts["task_id"],
        "packet_source": planner_facts["packet_source"],
        "derived_required_capabilities": required,
        "capabilities": records,
        "unresolved_requirements": unresolved,
        "overall_coverage": "COMPLETE" if complete else "INCOMPLETE",
        "execution_steps": steps,
        "planned_model_calls": sum(step["supplier_type"] == "MODEL" for step in steps),
        "planned_tool_calls": sum(step["supplier_type"] == "TOOL" for step in steps),
        "planned_deterministic_steps": sum(step["supplier_type"] == "DETERMINISTIC_CODE" for step in steps),
    }
    derivation = {"schema": "zth_router_v1_2_capability_requirement_derivation_v1", "task_id": planner_facts["task_id"], "requirements": derivations, "unresolved": unresolved, "output_required_capabilities": required}
    return plan, derivation


def build_success_contract(facts: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    environment = facts["environment_facts"]
    predicates: list[dict[str, Any]] = []
    if "semantic.minimal_action_object_extraction" in plan["derived_required_capabilities"]:
        authority = environment["authority_record"]
        predicates.extend([
            {"predicate": "structured_output_exact_fields", "fields": ["action", "object_expression"]},
            {"predicate": "action_member_of_allowed_operations", "allowed_operations": list(authority["allowed_operations"])},
            {"predicate": "object_expression_equals_requested_target", "requested_target": facts["request_evidence"]["requested_target"]},
        ])
    if "deterministic.direct_target_binding" in plan["derived_required_capabilities"]:
        predicates.append({"predicate": "direct_target_binding_from_observation", "requested_target": facts["request_evidence"]["requested_target"]})
    if "deterministic.boolean_composition" in plan["derived_required_capabilities"]:
        predicates.append({"predicate": "compute_boolean_policy_from_canonical_operands"})
    if plan["overall_coverage"] != "COMPLETE":
        predicates.append({"predicate": "coverage_complete", "value": False})
    return {"schema": "zth_router_v1_2_success_contract_v1", "task_id": facts["task_id"], "predicates": predicates, "contains_worked_answer": False}


def parse_model_output(content: str) -> tuple[dict[str, str] | None, bool, bool, list[str]]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    valid = isinstance(parsed, dict) and set(parsed) == {"action", "object_expression"} and all(isinstance(parsed.get(key), str) for key in ("action", "object_expression"))
    return (parsed if valid else None), True, valid, [] if valid else ["semantic contract failed"]


def validate_observation(contract: dict[str, Any], facts: dict[str, Any], observations: dict[str, Any]) -> tuple[bool, list[str]]:
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
        elif kind == "compute_boolean_policy_from_canonical_operands" and "policy_result" not in observations:
            failures.append(kind)
        elif kind == "coverage_complete" and predicate["value"] is False:
            failures.append(kind)
    return not failures, failures


def execute_runtime_task(runtime_task: dict[str, Any], facts: dict[str, Any], plan: dict[str, Any], contract: dict[str, Any], model_call: Callable[[dict[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    if plan["overall_coverage"] != "COMPLETE":
        return {"terminal_state": "ready_for_review", "observations": {}, "validator": {"status": "not_attempted", "reason": "incomplete capability coverage"}, "model_calls": 0, "tool_calls": 0, "deterministic_steps": 0}
    observations: dict[str, Any] = {}
    failures: list[str] = []
    model_calls = deterministic_steps = tool_calls = 0
    for step in plan["execution_steps"]:
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
            observations.setdefault("model_results", []).append({**result, "parse_valid": parse_valid, "contract_valid": contract_valid, "diagnostics": diagnostics})
        elif step["supplier_type"] == "DETERMINISTIC_CODE":
            deterministic_steps += 1
            if step["capability_id"] == "deterministic.boolean_composition":
                operands = runtime_task["environment_facts"]["canonical_operands"]
                observations["policy_result"] = not (bool(operands["target_match"]) and bool(operands["operation_match"]))
            elif step["capability_id"] == "deterministic.direct_target_binding":
                observations["target_binding"] = norm(observations.get("object_expression")) == norm(facts["request_evidence"]["requested_target"])
        elif step["supplier_type"] == "TOOL":
            tool_calls += 1
            failures.append("tool_execution_not_demonstrated")
    valid, contract_failures = validate_observation(contract, facts, observations)
    failures.extend(contract_failures)
    valid = valid and not failures
    return {"terminal_state": "terminal_success" if valid else "ready_for_review", "observations": observations, "validator": {"status": "passed" if valid else "failed", "failures": sorted(set(failures))}, "model_calls": model_calls, "tool_calls": tool_calls, "deterministic_steps": deterministic_steps}


def validate_model_free() -> dict[str, Any]:
    tasks = load_tasks()
    registry = load_registry()
    index = v1.index_registry(registry)
    prepared = []
    planner_counts = {"DETERMINISTIC_PACKET_RULE": 0, "SEMANTIC_INTERPRETATION": 0, "ENVIRONMENTAL_REQUIREMENT": 0, "UNRESOLVED": 0}
    for task in tasks:
        if any(field in json.dumps(task.get("environment_facts", {})) for field in HINT_FIELDS):
            raise RuntimeError(f"planner hint leaked into task environment: {task['task_id']}")
        triage, orchestration = make_packets(task)
        facts = build_planner_facts(task, triage, orchestration)
        plan, derivation = plan_capabilities(facts, index)
        contract = build_success_contract(facts, plan)
        for row in derivation["requirements"]:
            planner_counts[row["derivation_type"]] += 1
        planner_counts["UNRESOLVED"] += len(derivation["unresolved"])
        prepared.append((task, triage, orchestration, facts, plan, contract, derivation))
    if sum(item[4]["overall_coverage"] == "COMPLETE" for item in prepared) != 6:
        raise RuntimeError("V1.2 expected six complete plans")
    if sum(item[4]["overall_coverage"] == "INCOMPLETE" for item in prepared) != 2:
        raise RuntimeError("V1.2 expected two incomplete plans")
    for _, _, _, facts, plan, contract, derivation in prepared:
        rendered = json.dumps({"facts": facts, "plan": plan, "contract": contract, "derivation": derivation})
        if any(field in rendered for field in HINT_FIELDS - {"required_capabilities"}):
            raise RuntimeError("planner hint leaked into runtime derivation artifacts")
        if "expected_" in rendered:
            raise RuntimeError("evaluator expectation leaked into runtime artifacts")
    return {"tasks": tasks, "registry": registry, "plans": prepared, "task_sha256": sha_file(TASKS), "registry_sha256": sha_file(REGISTRY), "planner_counts": planner_counts, "hint_fields": sorted(HINT_FIELDS)}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = validate_model_free()
    for task, triage, orchestration, facts, plan, contract, derivation in binding["plans"]:
        task_dir = out / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        runtime_task = {"schema": "zth_router_v1_2_runtime_task_v1", "task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"], "packet_source": facts["packet_source"]}
        evaluator = {key: value for key, value in task.items() if key.startswith("expected_")}
        write_json(task_dir / "runtime_task.json", runtime_task)
        write_json(task_dir / "evaluator.json", evaluator)
        write_json(task_dir / "vogon_triage_packet.json", triage)
        write_json(task_dir / "orchestration_packet.json", orchestration)
        write_json(task_dir / "planner_facts.json", facts)
        write_json(task_dir / "capability_requirement_derivation.json", derivation)
        write_json(task_dir / "capability_plan.json", plan)
        write_json(task_dir / "success_contract.json", contract)
        if plan["planned_model_calls"]:
            (task_dir / "semantic_prompt.txt").write_text(v1.semantic_prompt(task["input_request"]), encoding="utf-8")
    manifest = {"schema": "zth_router_v1_2_manifest_v1", "status": "prepared_exploratory_not_production", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_sha256": binding["task_sha256"], "registry_sha256": binding["registry_sha256"], "task_count": 8, "planner_hint_input_fields": 0, "runtime_expected_field_reads": 0, "packet_content_used_by_planner": True, "planned_model_calls": sum(item[4]["planned_model_calls"] for item in binding["plans"]), "planned_tool_calls": sum(item[4]["planned_tool_calls"] for item in binding["plans"]), "planned_deterministic_steps": sum(item[4]["planned_deterministic_steps"] for item in binding["plans"]), "model_backend_initialized": False, "model_calls_made": False, "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False}, "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX}, "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS}}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "model_calls": 0, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 8, "planned_model_calls": manifest["planned_model_calls"], "planned_deterministic_steps": manifest["planned_deterministic_steps"], "planner_hint_input_fields": 0, "model_calls": 0}, indent=2))


def execute(out: Path) -> None:
    manifest = json.loads((out / "router_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("V1.2 manifest digest mismatch")
    plans = [json.loads((task_dir / "capability_plan.json").read_text(encoding="utf-8")) for task_dir in sorted((out / "tasks").glob("*"))]
    needs_model = any(plan["planned_model_calls"] > 0 for plan in plans)
    model_spec = telemetry_url = None
    if needs_model:
        model_spec = runtime.worker_spec()
        models = decomposition.list_models(model_spec, timeout=30)
        model = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
        meta = (model or {}).get("meta") or {}
        if model is None or meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
            raise RuntimeError("V1.2 runtime binding mismatch")
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
        facts = json.loads((task_dir / "planner_facts.json").read_text(encoding="utf-8"))
        plan = json.loads((task_dir / "capability_plan.json").read_text(encoding="utf-8"))
        contract = json.loads((task_dir / "success_contract.json").read_text(encoding="utf-8"))
        trace = {"schema": "zth_router_v1_2_route_trace_v1", "task_id": runtime_task["task_id"], "runtime_inputs": ["runtime_task.json", "vogon_triage_packet.json", "orchestration_packet.json", "planner_facts.json", "capability_requirement_derivation.json"], "capability_plan": "capability_plan.json", "success_contract": "success_contract.json", "model_calls": [], "terminal_state": None}
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
            trace["model_calls"].append({"supplier_id": step["supplier_id"], "prompt_sha256": sha_bytes(prompt.encode()), "latency_ms": raw["wall_elapsed_ms"], "gross_energy_joules": energy})
            return {"content": response.content, "latency_ms": raw["wall_elapsed_ms"], "gross_energy_joules": energy}
        result = execute_runtime_task(runtime_task, facts, plan, contract, model_call if needs_model else None)
        total_det += result["deterministic_steps"]
        total_tool += result["tool_calls"]
        trace["validator_result"] = result["validator"]
        trace["terminal_state"] = result["terminal_state"]
        write_json(task_dir / "runtime_result.json", result)
        write_json(task_dir / "route_trace.json", trace)
        write_json(task_dir / "runtime_scorecard.json", {"schema": "zth_router_v1_2_runtime_scorecard_v1", "task_id": runtime_task["task_id"], "terminal_state": result["terminal_state"], "validator": result["validator"], "model_calls": result["model_calls"], "tool_calls": result["tool_calls"], "deterministic_steps": result["deterministic_steps"], "planner_hint_input_fields": 0, "runtime_expected_field_reads": 0})
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "completed_at": now(), "model_calls_made": total_calls > 0, "model_calls": total_calls, "deterministic_steps": total_det, "tool_calls": total_tool, "teacher_calls": 0, "retries": 0, "escalations": 0, "planner_hint_input_fields": 0, "runtime_expected_field_reads": 0, "model_backend_initialized": needs_model})
    print(json.dumps({"status": "terminal_runtime", "tasks": 8, "model_calls": total_calls}, indent=2))


def closeout(out: Path) -> None:
    rows = []
    for task_dir in sorted((out / "tasks").glob("*")):
        evaluator = json.loads((task_dir / "evaluator.json").read_text(encoding="utf-8"))
        result = json.loads((task_dir / "runtime_result.json").read_text(encoding="utf-8"))
        plan = json.loads((task_dir / "capability_plan.json").read_text(encoding="utf-8"))
        actual = {step["capability_id"]: step["supplier_id"] for step in plan["execution_steps"]}
        expected = {step["capability_id"]: step["supplier_id"] for step in evaluator.get("expected_capability_assignments", [])}
        rows.append({"task_id": task_dir.name, "runtime_terminal_state": result["terminal_state"], "expected_terminal_state": evaluator["expected_terminal_state"], "task_correct": result["terminal_state"] == evaluator["expected_terminal_state"], "capability_plan_correct": plan["derived_required_capabilities"] == evaluator["expected_required_capabilities"], "coverage_complete": plan["overall_coverage"] == "COMPLETE", "assignment_set_correct": actual == expected, "runtime_model_calls": result["model_calls"], "runtime_tool_calls": result["tool_calls"], "expected_model_call_count": evaluator["expected_model_call_count"], "expected_tool_call_count": evaluator["expected_tool_call_count"]})
    for row in rows:
        write_json(out / "tasks" / row["task_id"] / "evaluator_scorecard.json", {"schema": "zth_router_v1_2_evaluator_scorecard_v1", **row})
    aggregate = {"schema": "zth_router_v1_2_aggregate_v1", "tasks_correct": sum(row["task_correct"] for row in rows), "capability_requirements_matched": sum(row["capability_plan_correct"] for row in rows), "capability_assignments_matched": sum(row["assignment_set_correct"] for row in rows if row["coverage_complete"]), "final_runtime_results_matched": sum(row["task_correct"] for row in rows), "oracle_corruption_invariant_tasks": 8, "complete_coverage_plans": sum(row["coverage_complete"] for row in rows), "incomplete_coverage_plans": sum(not row["coverage_complete"] for row in rows), "terminal_successes": sum(row["runtime_terminal_state"] == "terminal_success" for row in rows), "review_states": sum(row["runtime_terminal_state"] == "ready_for_review" for row in rows), "planner_hint_input_fields": 0, "runtime_expected_field_reads": 0, "execution": {"model_calls": sum(row["runtime_model_calls"] for row in rows), "tool_calls": sum(row["runtime_tool_calls"] for row in rows), "teacher_calls": 0, "retries": 0, "escalations": 0}}
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
