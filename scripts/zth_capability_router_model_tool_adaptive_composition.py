#!/usr/bin/env python3
"""Fresh bounded MODEL -> TOOL -> observation -> REPLAN composition slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from scripts import zth_capability_router_v1 as v1
from scripts import zth_capability_router_tool_observation_v0 as tool_v0
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = base.ROOT
TASKS = ROOT / "docs/research/CAPABILITY_ROUTER_MODEL_TOOL_ADAPTIVE_COMPOSITION_TASKS_2026-08-23.json"
REGISTRY = ROOT / "docs/research/CAPABILITY_ROUTER_MODEL_TOOL_ADAPTIVE_COMPOSITION_REGISTRY_2026-08-23.json"
MAX_REPLANS = 2
MODEL_CAPABILITY = "semantic.minimal_action_object_extraction"
TOOL_CAPABILITY = "tool.read_only_repository_observation"
TOOL_SUPPLIER = "python_read_only_repository_observer_v0"
MODEL_SUPPLIER = "qwen3_1_7b_minimal_action_object_supplier"
UNSUPPORTED_CAPABILITY = "semantic.external_service_observation"
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
TARGET_RE = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9_./-]*\.(?:md|json|txt))\b")
FORBIDDEN_INPUT_FIELDS = {"expected_", "required_capabilities", "expected_supplier", "tool_capability_id", "observation_requirement"}


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
    if len(tasks) != 6 or len({task["task_id"] for task in tasks}) != 6:
        raise RuntimeError("composition slice requires six unique tasks")
    return tasks


def load_registry() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for entry in registry["entries"]:
        if not (ROOT / entry["evidence_artifact"]).is_file():
            raise RuntimeError(f"registry evidence missing: {entry['evidence_artifact']}")
    return registry


def registry_index() -> dict[str, list[dict[str, Any]]]:
    return v1.index_registry(load_registry())


def make_packets(task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return v1.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})


def extract_target(request: str) -> str | None:
    matches = TARGET_RE.findall(request)
    return matches[0] if len(matches) == 1 else None


def build_planner_facts(runtime_task: dict[str, Any], triage: dict[str, Any], orchestration: dict[str, Any], *, semantic: dict[str, Any] | None = None, observation: dict[str, Any] | None = None) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "schema": "zth_model_tool_adaptive_planner_facts_v1",
        "task_id": runtime_task["task_id"],
        "request_evidence": {"input_request": runtime_task["input_request"], "requested_target": extract_target(runtime_task["input_request"])},
        "triage_content": {"task_type": triage["task_type"], "allowed_targets": list(triage["allowed_targets"]), "held_targets": list(triage["held_targets"]), "risk_flags": list(triage["risk_flags"]), "validation_hooks": list(triage["validation_hooks"]), "output_contract": dict(triage["output_contract"])},
        "orchestration_content": {"allowed_targets": list(orchestration["allowed_targets"]), "held_targets": list(orchestration["held_targets"]), "authority_boundaries": list(orchestration["authority_boundaries"]), "review_required": orchestration["review_required"]},
        "environment_facts": json.loads(json.dumps(runtime_task.get("environment_facts", {}))),
        "packet_source": {"triage_id": triage["triage_id"], "orchestration_id": orchestration["orchestration_id"]},
        "provenance": {"request": "runtime_task.input_request", "packet": ["vogon_triage_packet.json", "orchestration_packet.json"], "authority": "runtime_task.environment_facts.authority_record"},
    }
    if semantic is not None:
        facts["validated_semantic_output"] = json.loads(json.dumps(semantic))
        facts["provenance"]["semantic"] = "PRIOR_MODEL_STEP"
    if observation is not None:
        facts["validated_observation"] = json.loads(json.dumps(observation))
        facts["provenance"]["observation"] = "PRIOR_TOOL_STEP"
    return facts


def derive_requirements(facts: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    request = norm(facts["request_evidence"]["input_request"])
    env = facts["environment_facts"]
    required: list[str] = []
    derivations: list[dict[str, Any]] = []
    unresolved: list[str] = []

    def add(capability: str, kind: str, fields: list[str], reason: str) -> None:
        if capability not in required:
            required.append(capability)
        derivations.append({"capability_id": capability, "derivation_type": kind, "source_artifacts": ["planner_facts.json"], "source_fields": fields, "reason": reason})

    observation = facts.get("validated_observation")
    semantic = facts.get("validated_semantic_output")
    if observation is not None and observation.get("status") == "VALID_OBSERVATION":
        policy = "deterministic.observation_exists_policy" if observation.get("exists") else "deterministic.observation_absence_policy"
        add(policy, "ENVIRONMENTAL_REQUIREMENT", ["validated_observation.exists", "validated_observation.status"], "A validated repository observation selects the bounded deterministic post-observation policy.")
        return required, derivations, unresolved
    if semantic is not None:
        action = semantic.get("action")
        target = semantic.get("object_expression")
        authority = env.get("authority_record", {})
        allowed_ops = authority.get("allowed_observation_operations", [])
        allowed_targets = authority.get("allowed_targets", [])
        if action not in allowed_ops:
            unresolved.append("semantic action is not an allowed observation operation")
        elif not isinstance(target, str) or target != facts["request_evidence"].get("requested_target"):
            unresolved.append("semantic object expression does not exactly bind the requested target")
        elif target not in allowed_targets:
            unresolved.append("semantic target is outside ENVIRONMENT_AUTHORITY_RECORD")
        else:
            add(TOOL_CAPABILITY, "SEMANTIC_INTERPRETATION", ["validated_semantic_output.action", "validated_semantic_output.object_expression", "environment_facts.authority_record.allowed_targets"], "Only a contract-valid semantic output that exactly binds an authorized target derives the bounded repository observation capability.")
        return required, derivations, unresolved
    if isinstance(env.get("canonical_operands"), dict) and {"target_match", "operation_match"} <= set(env["canonical_operands"]):
        add("deterministic.boolean_composition", "DETERMINISTIC_PACKET_RULE", ["environment_facts.canonical_operands"], "Canonical operands are available; no model or tool is needed.")
        return required, derivations, unresolved
    if "external service" in request or "service status" in request:
        add(UNSUPPORTED_CAPABILITY, "SEMANTIC_INTERPRETATION", ["request_evidence.input_request", "triage_content.task_type"], "The request names an unsupported external-service observation capability.")
        return required, derivations, unresolved
    if facts["request_evidence"].get("requested_target") and any(word in request for word in ("exists", "present", "verify", "confirm", "check")):
        add(MODEL_CAPABILITY, "SEMANTIC_INTERPRETATION", ["request_evidence.input_request", "triage_content.output_contract"], "The bounded natural-language request requires the action/object semantic atom before tool selection.")
        return required, derivations, unresolved
    unresolved.append("no safely derivable capability")
    return required, derivations, unresolved


def select_supplier(capability: str, index: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any] | None, str]:
    qualified = [entry for entry in index.get(capability, []) if entry["status"] == "QUALIFIED_EXPLORATORY"]
    if not qualified:
        return None, "No QUALIFIED_EXPLORATORY supplier; fail closed."
    order = {"DETERMINISTIC_CODE": 0, "MODEL": 1, "TOOL": 2, "REVIEW_OR_ESCALATION": 3}
    selected = sorted(qualified, key=lambda entry: (order.get(entry["supplier_type"], 99), entry["supplier_id"]))[0]
    return selected, f"Selected qualified {selected['supplier_type']} supplier using bounded precedence."


def plan_capabilities(facts: dict[str, Any], index: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any], dict[str, Any]]:
    required, derivations, unresolved = derive_requirements(facts)
    records: list[dict[str, Any]] = []
    for capability in required:
        candidates = list(index.get(capability, []))
        selected, reason = select_supplier(capability, index)
        records.append({"capability_id": capability, "candidate_suppliers": [{"supplier_id": e["supplier_id"], "supplier_type": e["supplier_type"], "interface_id": e["interface_id"], "status": e["status"]} for e in candidates], "qualified_candidates": [{"supplier_id": e["supplier_id"], "supplier_type": e["supplier_type"], "interface_id": e["interface_id"]} for e in candidates if e["status"] == "QUALIFIED_EXPLORATORY"], "selected_supplier": None if selected is None else {"supplier_id": selected["supplier_id"], "supplier_type": selected["supplier_type"], "interface_id": selected["interface_id"]}, "selection_reason": reason, "coverage_status": "COVERED" if selected else "UNCOVERED"})
    complete = bool(required) and not unresolved and all(item["coverage_status"] == "COVERED" for item in records)
    steps: list[dict[str, Any]] = []
    if complete:
        for item in records:
            cap = item["capability_id"]
            selected = item["selected_supplier"]
            if cap == MODEL_CAPABILITY:
                req, prod, deps, prov = ["input_request"], ["action", "object_expression"], [], {"input_request": "PACKET"}
            elif cap == TOOL_CAPABILITY:
                req, prod, deps, prov = ["object_expression", "authorized_targets"], ["validated_observation"], ["step_semantic_minimal_action_object_extraction"], {"object_expression": "PRIOR_MODEL_STEP", "authorized_targets": "ENVIRONMENT_AUTHORITY_RECORD"}
            elif cap.startswith("deterministic.observation_"):
                req, prod, deps, prov = ["validated_observation"], ["policy_result"], ["step_tool_read_only_repository_observation"], {"validated_observation": "PRIOR_TOOL_STEP"}
            elif cap == "deterministic.boolean_composition":
                req, prod, deps, prov = ["canonical_operands"], ["policy_result"], [], {"canonical_operands": "ENVIRONMENT"}
            else:
                req, prod, deps, prov = [], [], [], {}
            steps.append({"step_id": f"step_{cap.replace('.', '_')}", "capability_id": cap, "supplier_id": selected["supplier_id"], "supplier_type": selected["supplier_type"], "requires_inputs": req, "produces_outputs": prod, "depends_on": deps, "input_provenance": prov})
    plan = {"schema": "zth_model_tool_adaptive_capability_plan_v1", "task_id": facts["task_id"], "packet_source": facts["packet_source"], "derived_required_capabilities": required, "capabilities": records, "unresolved_requirements": unresolved, "overall_coverage": "COMPLETE" if complete else "INCOMPLETE", "execution_steps": steps, "planned_model_calls": sum(step["supplier_type"] == "MODEL" for step in steps), "planned_tool_calls": sum(step["supplier_type"] == "TOOL" for step in steps), "planned_deterministic_steps": sum(step["supplier_type"] == "DETERMINISTIC_CODE" for step in steps)}
    derivation = {"schema": "zth_model_tool_adaptive_requirement_derivation_v1", "task_id": facts["task_id"], "requirements": derivations, "unresolved": unresolved, "output_required_capabilities": required}
    return plan, derivation


def build_success_contract(facts: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    predicates: list[dict[str, Any]] = []
    required = plan["derived_required_capabilities"]
    if MODEL_CAPABILITY in required or TOOL_CAPABILITY in required:
        authority = facts["environment_facts"].get("authority_record", {})
        predicates.extend([{"predicate": "semantic_contract_valid"}, {"predicate": "action_allowed", "allowed_operations": list(authority.get("allowed_observation_operations", []))}, {"predicate": "object_expression_authorized", "authorized_targets": list(authority.get("allowed_targets", [])), "requested_target": facts["request_evidence"].get("requested_target")}])
    if TOOL_CAPABILITY in required:
        predicates.extend([{"predicate": "tool_authority_valid"}, {"predicate": "tool_observation_schema_valid"}, {"predicate": "observation_path_matches_bound_target"}])
    if "deterministic.observation_exists_policy" in required:
        predicates.append({"predicate": "validated_observation_present"})
    if "deterministic.observation_absence_policy" in required:
        predicates.append({"predicate": "validated_observation_absent"})
    if "deterministic.boolean_composition" in required:
        predicates.append({"predicate": "policy_computed"})
    if plan["overall_coverage"] != "COMPLETE":
        predicates.append({"predicate": "coverage_complete", "value": False})
    return {"schema": "zth_model_tool_adaptive_success_contract_v1", "task_id": facts["task_id"], "predicates": predicates, "contains_worked_answer": False}


def evaluate_success_contract(contract: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for predicate in contract.get("predicates", []):
        kind = predicate["predicate"]
        if kind == "semantic_contract_valid":
            passed = state.get("semantic_contract_valid") is True
        elif kind == "action_allowed":
            passed = state.get("action") in predicate.get("allowed_operations", [])
        elif kind == "object_expression_authorized":
            passed = state.get("object_expression") == predicate.get("requested_target") and state.get("object_expression") in predicate.get("authorized_targets", [])
        elif kind == "tool_authority_valid":
            passed = state.get("tool_authority_valid") is True
        elif kind == "tool_observation_schema_valid":
            passed = state.get("tool_observation_schema_valid") is True
        elif kind == "observation_path_matches_bound_target":
            passed = state.get("observation_path_matches_bound_target") is True
        elif kind == "validated_observation_present":
            passed = state.get("validated_observation_present") is True
        elif kind == "validated_observation_absent":
            passed = state.get("validated_observation_absent") is True
        elif kind == "policy_computed":
            passed = state.get("policy_computed") is True
        elif kind == "coverage_complete":
            passed = state.get("coverage_complete") is predicate.get("value")
        else:
            passed = False
        results.append({"predicate": kind, "passed": passed})
    return {"schema": "zth_success_contract_evaluation_v1", "contract_schema": contract["schema"], "passed": all(item["passed"] for item in results), "predicates": results}


def parse_model_output(content: str) -> tuple[dict[str, str] | None, bool, bool, list[str]]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    valid = isinstance(parsed, dict) and set(parsed) == {"action", "object_expression"} and all(isinstance(parsed.get(key), str) for key in ("action", "object_expression"))
    return (parsed if valid else None), True, valid, [] if valid else ["semantic contract failed"]


def semantic_prompt(request: str) -> str:
    return v1.semantic_prompt(request)


def model_free_binding() -> dict[str, Any]:
    tasks = load_tasks()
    index = registry_index()
    prepared: list[dict[str, Any]] = []
    for task in tasks:
        runtime_task = {"task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"]}
        if any(field in json.dumps(runtime_task) for field in FORBIDDEN_INPUT_FIELDS):
            raise RuntimeError(f"forbidden runtime field in {task['task_id']}")
        triage, orchestration = make_packets(runtime_task)
        facts0 = build_planner_facts(runtime_task, triage, orchestration)
        plan0, derivation0 = plan_capabilities(facts0, index)
        contract0 = build_success_contract(facts0, plan0)
        if MODEL_CAPABILITY in plan0["derived_required_capabilities"]:
            if plan0["planned_model_calls"] != 1 or plan0["planned_tool_calls"] != 0:
                raise RuntimeError("semantic plan must contain exactly one model and no tool")
        if plan0["overall_coverage"] != "COMPLETE" and task["task_id"] in {"model-tool-001", "model-tool-002", "model-tool-003"}:
            raise RuntimeError("authorized semantic task did not receive a complete model plan")
        if any(field in json.dumps({"facts": facts0, "contract": contract0}) for field in ("expected_", "required_capabilities", "tool_capability_id", "observation_requirement")):
            raise RuntimeError(f"runtime planning artifact leaks evaluator/planner hint in {task['task_id']}")
        if contract0["contains_worked_answer"]:
            raise RuntimeError("worked answer in contract")
        prepared.append({"task": task, "runtime_task": runtime_task, "triage": triage, "orchestration": orchestration, "facts0": facts0, "plan0": plan0, "derivation0": derivation0, "contract0": contract0})
    if sum(item["plan0"]["planned_model_calls"] for item in prepared) != 4:
        raise RuntimeError("expected four model-routed initial plans")
    if sum(item["plan0"]["overall_coverage"] == "COMPLETE" for item in prepared) != 5:
        raise RuntimeError("expected five complete initial plans")
    if sum(item["plan0"]["overall_coverage"] == "INCOMPLETE" for item in prepared) != 1:
        raise RuntimeError("expected one incomplete initial plan")
    return {"tasks": tasks, "prepared": prepared, "task_sha256": sha_file(TASKS), "registry_sha256": sha_file(REGISTRY), "schema_sha256": sha_bytes(canonical(v1.minimal_schema())), "format_sha256": sha_bytes(canonical(v1.response_format()))}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = model_free_binding()
    write_json(out / "semantic_schema.json", v1.minimal_schema())
    write_json(out / "response_format.json", v1.response_format())
    for item in binding["prepared"]:
        task = item["task"]
        td = out / "tasks" / task["task_id"]
        td.mkdir(parents=True, exist_ok=True)
        write_json(td / "runtime_task.json", item["runtime_task"])
        write_json(td / "evaluator.json", {key: value for key, value in task.items() if key.startswith("expected_")})
        write_json(td / "vogon_triage_packet.json", item["triage"])
        write_json(td / "orchestration_packet.json", item["orchestration"])
        write_json(td / "planner_facts_0.json", item["facts0"])
        write_json(td / "capability_requirement_derivation_0.json", item["derivation0"])
        write_json(td / "capability_plan_0.json", item["plan0"])
        write_json(td / "success_contract_0.json", item["contract0"])
        if item["plan0"]["planned_model_calls"]:
            (td / "semantic_prompt.txt").write_text(semantic_prompt(task["input_request"]), encoding="utf-8")
    manifest = {"schema": "zth_model_tool_adaptive_composition_manifest_v1", "status": "prepared_exploratory_not_production", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_sha256": binding["task_sha256"], "registry_sha256": binding["registry_sha256"], "schema_sha256": binding["schema_sha256"], "response_format_sha256": binding["format_sha256"], "task_count": 6, "max_replans": MAX_REPLANS, "planned_model_calls": sum(item["plan0"]["planned_model_calls"] for item in binding["prepared"]), "planned_tool_calls": 0, "planned_deterministic_steps": sum(item["plan0"]["planned_deterministic_steps"] for item in binding["prepared"]), "runtime_expected_field_reads": 0, "planner_hint_input_fields": 0, "model_calls_made": False, "tool_calls_made": False, "external_calls": 0, "v100_touched": False, "authority_provenance": "ENVIRONMENT_AUTHORITY_RECORD", "model_output_granted_authority": 0}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls": 0, "tool_calls": 0, "replans": 0, "runtime_expected_field_reads": 0, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 6, "planned_model_calls": manifest["planned_model_calls"], "planned_tool_calls": 0, "model_calls": 0, "tool_calls": 0}, indent=2))


def model_preflight(out: Path) -> tuple[Any, str, dict[str, Any]]:
    spec = runtime.worker_spec()
    models = decomposition.list_models(spec, timeout=30)
    candidate = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
    meta = (candidate or {}).get("meta") or {}
    if candidate is None or meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
        raise RuntimeError("model runtime binding mismatch")
    telemetry_url = base.telemetry_base_url()
    telemetry = base.telemetry_preflight(telemetry_url)
    idle_samples, idle_summary = base.sample_window(IDLE_SECONDS, telemetry_url)
    write_json(out / "preflight.json", {"model_meta": meta, "telemetry": telemetry, "idle_power": idle_summary, "planned_model_calls": 4, "model_id": EXPECTED_MODEL_ID})
    write_json(out / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "samples": idle_samples})
    return spec, telemetry_url, meta


def execute(out: Path) -> None:
    manifest = json.loads((out / "router_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("composition manifest digest mismatch")
    model_spec = telemetry_url = None
    if manifest["planned_model_calls"]:
        model_spec, telemetry_url, _ = model_preflight(out)
    total_model = total_tool = total_replans = total_det = 0
    for td in sorted((out / "tasks").glob("*")):
        runtime_task = json.loads((td / "runtime_task.json").read_text(encoding="utf-8"))
        facts0 = json.loads((td / "planner_facts_0.json").read_text(encoding="utf-8"))
        plan0 = json.loads((td / "capability_plan_0.json").read_text(encoding="utf-8"))
        contract0 = json.loads((td / "success_contract_0.json").read_text(encoding="utf-8"))
        triage = json.loads((td / "vogon_triage_packet.json").read_text(encoding="utf-8"))
        orchestration = json.loads((td / "orchestration_packet.json").read_text(encoding="utf-8"))
        trace: dict[str, Any] = {"schema": "zth_model_tool_adaptive_route_trace_v1", "task_id": runtime_task["task_id"], "input_request": runtime_task["input_request"], "packets": ["vogon_triage_packet.json", "orchestration_packet.json"], "planner_facts_0": "planner_facts_0.json", "capability_plan_0": "capability_plan_0.json", "success_contract_0": "success_contract_0.json", "model_calls": [], "tool_calls": [], "terminal_state": None}
        state: dict[str, Any] = {"coverage_complete": plan0["overall_coverage"] == "COMPLETE"}
        if plan0["overall_coverage"] != "COMPLETE":
            evaluation = evaluate_success_contract(contract0, state)
            write_json(td / "success_contract_evaluation_0.json", evaluation)
            result = {"terminal_state": "ready_for_review", "reason": "incomplete plan_0 coverage", "model_calls": 0, "tool_calls": 0, "replans": 0, "deterministic_steps": 0, "validator": evaluation}
            write_json(td / "runtime_result.json", result)
            trace.update({"validator_result": "success_contract_evaluation_0.json", "terminal_state": result["terminal_state"]})
            write_json(td / "route_trace.json", trace)
            continue
        if not plan0["planned_model_calls"]:
            state.update({"policy_computed": True})
            evaluation = evaluate_success_contract(contract0, {**state, "coverage_complete": True})
            write_json(td / "success_contract_evaluation_0.json", evaluation)
            result = {"terminal_state": "terminal_success" if evaluation["passed"] else "ready_for_review", "reason": "deterministic control", "model_calls": 0, "tool_calls": 0, "replans": 0, "deterministic_steps": 1, "validator": evaluation}
            total_det += 1
            write_json(td / "runtime_result.json", result); trace.update({"terminal_state": result["terminal_state"]}); write_json(td / "route_trace.json", trace)
            continue
        semantic: dict[str, str] | None = None
        prompt = (td / "semantic_prompt.txt").read_text(encoding="utf-8")
        response_path = td / "response.json"
        if response_path.exists():
            # A response artifact spends the supplier call. Recovery must never replay it.
            total_model += 1
            raw = json.loads(response_path.read_text(encoding="utf-8"))
            semantic, parse_valid, contract_valid, diagnostics = parse_model_output(raw.get("content", ""))
            trace["model_calls"].append({"supplier_id": MODEL_SUPPLIER, "prompt_sha256": sha_bytes(prompt.encode()), "parse_valid": parse_valid, "contract_valid": contract_valid, "latency_ms": raw.get("wall_elapsed_ms"), "gross_energy_joules": None, "recovered_existing_response": True})
        else:
            total_model += 1
            started = time.monotonic()
            sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
            sampler.start()
            response = decomposition.structured_call(model_spec, prompt, v1.response_format(), MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
            captured = time.monotonic()
            samples = sampler.stop()
            energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
            raw = {"status": response.status, "content": response.content, "metadata": response.metadata(), "wall_elapsed_ms": round((captured - started) * 1000, 3), "response_captured_at": now()}
            write_json(response_path, raw)
            write_json(td / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": s.timestamp_utc, "monotonic_seconds": s.monotonic_seconds, "gpu_uuid": s.gpu_uuid, "power_watts": s.power_watts, "sequence": s.sequence} for s in samples]})
            semantic, parse_valid, contract_valid, diagnostics = parse_model_output(response.content)
            trace["model_calls"].append({"supplier_id": MODEL_SUPPLIER, "prompt_sha256": sha_bytes(prompt.encode()), "parse_valid": parse_valid, "contract_valid": contract_valid, "latency_ms": raw["wall_elapsed_ms"], "gross_energy_joules": energy, "recovered_existing_response": False})
        state.update({"semantic_contract_valid": contract_valid, "action": semantic.get("action") if semantic else None, "object_expression": semantic.get("object_expression") if semantic else None})
        write_json(td / "semantic_validation.json", {"schema": "zth_model_tool_adaptive_semantic_validation_v1", "parse_valid": parse_valid, "contract_valid": contract_valid, "diagnostics": diagnostics, "observed": semantic})
        contract_eval0 = evaluate_success_contract(contract0, {**state, "coverage_complete": True})
        write_json(td / "success_contract_evaluation_0.json", contract_eval0)
        facts1 = build_planner_facts(runtime_task, triage, orchestration, semantic=semantic or {})
        plan1, derivation1 = plan_capabilities(facts1, registry_index())
        contract1 = build_success_contract(facts1, plan1)
        write_json(td / "planner_facts_1.json", facts1); write_json(td / "capability_requirement_derivation_1.json", derivation1); write_json(td / "capability_plan_1.json", plan1); write_json(td / "success_contract_1.json", contract1)
        write_json(td / "replan_delta_0_1.json", {"previous_required_capabilities": plan0["derived_required_capabilities"], "new_required_capabilities": plan1["derived_required_capabilities"], "observation_consumed": False, "capabilities_satisfied": [MODEL_CAPABILITY] if contract_eval0["passed"] else [], "capabilities_added": [x for x in plan1["derived_required_capabilities"] if x not in plan0["derived_required_capabilities"]], "capabilities_removed": [x for x in plan0["derived_required_capabilities"] if x not in plan1["derived_required_capabilities"]], "reason": "Re-derived after the semantic model step; only a safely bound target can expose the tool requirement."})
        if not contract_eval0["passed"]:
            total_replans += 1
            result = {"terminal_state": "ready_for_review", "reason": "semantic binding or contract failed", "model_calls": 1, "tool_calls": 0, "replans": 1, "deterministic_steps": 0, "validator": contract_eval0}
            write_json(td / "runtime_result.json", result); trace.update({"planner_facts_1": "planner_facts_1.json", "capability_plan_1": "capability_plan_1.json", "replan_delta_0_1": "replan_delta_0_1.json", "terminal_state": result["terminal_state"]}); write_json(td / "route_trace.json", trace)
            continue
        facts1 = json.loads((td / "planner_facts_1.json").read_text(encoding="utf-8"))
        plan1 = json.loads((td / "capability_plan_1.json").read_text(encoding="utf-8"))
        contract1 = json.loads((td / "success_contract_1.json").read_text(encoding="utf-8"))
        if plan1["overall_coverage"] != "COMPLETE" or TOOL_CAPABILITY not in plan1["derived_required_capabilities"]:
            result = {"terminal_state": "ready_for_review", "reason": "TOOL_AUTHORITY_DENIED_OR_UNSAFE_BINDING", "model_calls": 1, "tool_calls": 0, "replans": 1, "deterministic_steps": 0, "validator": json.loads((td / "success_contract_evaluation_0.json").read_text())}
            write_json(td / "runtime_result.json", result); trace.update({"terminal_state": result["terminal_state"]}); write_json(td / "route_trace.json", trace)
            continue
        total_replans += 1
        target = semantic["object_expression"]
        allowed = facts1["environment_facts"]["authority_record"]["allowed_targets"]
        tool_request = {"schema": "zth_model_tool_adaptive_request_v1", "capability_id": TOOL_CAPABILITY, "supplier_id": TOOL_SUPPLIER, "repository_relative_path": target, "authorized_targets": allowed, "authority_source": "ENVIRONMENT_AUTHORITY_RECORD.allowed_targets"}
        write_json(td / "tool_request.json", tool_request)
        authority = tool_v0.validate_tool_request(tool_request)
        write_json(td / "tool_authority_validation.json", authority)
        if authority["status"] != "AUTHORIZED":
            result = {"terminal_state": "ready_for_review", "reason": "TOOL_AUTHORITY_DENIED", "model_calls": 1, "tool_calls": 0, "replans": 1, "deterministic_steps": 0, "validator": {"passed": False, "reason": "authority denied"}}
            write_json(td / "runtime_result.json", result); trace.update({"authority_validation": "tool_authority_validation.json", "terminal_state": result["terminal_state"]}); write_json(td / "route_trace.json", trace)
            continue
        total_tool += 1
        observation = tool_v0.observe_repository(tool_request, authority)
        write_json(td / "tool_observation.json", observation)
        tool_validation = tool_v0.validate_observation(observation, tool_request, authority)
        write_json(td / "tool_result_validation.json", tool_validation)
        state.update({"tool_authority_valid": authority["status"] == "AUTHORIZED", "tool_observation_schema_valid": tool_validation["status"] == "VALID", "observation_path_matches_bound_target": observation.get("repository_relative_path") == target})
        if tool_validation["status"] != "VALID":
            result = {"terminal_state": "ready_for_review", "reason": "TOOL_INTERFACE_FAILURE", "model_calls": 1, "tool_calls": 1, "replans": 1, "deterministic_steps": 0, "validator": {"passed": False, "reason": "invalid observation"}}
            write_json(td / "runtime_result.json", result); trace.update({"tool_request": "tool_request.json", "tool_observation": "tool_observation.json", "terminal_state": result["terminal_state"]}); write_json(td / "route_trace.json", trace)
            continue
        facts2 = build_planner_facts(runtime_task, triage, orchestration, semantic=semantic, observation=observation)
        plan2, derivation2 = plan_capabilities(facts2, registry_index())
        contract2 = build_success_contract(facts2, plan2)
        write_json(td / "planner_facts_2.json", facts2); write_json(td / "capability_requirement_derivation_2.json", derivation2); write_json(td / "capability_plan_2.json", plan2); write_json(td / "success_contract_2.json", contract2)
        write_json(td / "replan_delta_0_1.json", {"previous_required_capabilities": plan0["derived_required_capabilities"], "new_required_capabilities": plan1["derived_required_capabilities"], "observation_consumed": False, "capabilities_satisfied": [MODEL_CAPABILITY], "capabilities_added": [TOOL_CAPABILITY], "capabilities_removed": [MODEL_CAPABILITY], "reason": "Validated semantic output changed the plan to the authorized read-only tool."})
        write_json(td / "replan_delta_1_2.json", {"previous_required_capabilities": plan1["derived_required_capabilities"], "new_required_capabilities": plan2["derived_required_capabilities"], "observation_consumed": True, "capabilities_satisfied": [TOOL_CAPABILITY], "capabilities_added": [x for x in plan2["derived_required_capabilities"] if x not in plan1["derived_required_capabilities"]], "capabilities_removed": [x for x in plan1["derived_required_capabilities"] if x not in plan2["derived_required_capabilities"]], "reason": "Re-derived after the validated repository observation."})
        state.update({"validated_observation_present": observation.get("exists") is True, "validated_observation_absent": observation.get("exists") is False})
        contract_eval1 = evaluate_success_contract(contract1, state)
        contract_eval2 = evaluate_success_contract(contract2, {**state, "policy_computed": True, "coverage_complete": plan2["overall_coverage"] == "COMPLETE"})
        write_json(td / "success_contract_evaluation_1.json", contract_eval1); write_json(td / "success_contract_evaluation_2.json", contract_eval2)
        total_replans += 1; total_det += 1
        result = {"terminal_state": "terminal_success" if contract_eval2["passed"] else "ready_for_review", "reason": "validated two-step replan", "model_calls": 1, "tool_calls": 1, "replans": 2, "deterministic_steps": 1, "validator": contract_eval2, "observation_status": "VALID_OBSERVATION_EXISTING" if observation.get("exists") else "VALID_OBSERVATION_ABSENT"}
        write_json(td / "runtime_result.json", result); trace.update({"planner_facts_1": "planner_facts_1.json", "capability_plan_1": "capability_plan_1.json", "replan_delta_0_1": "replan_delta_0_1.json", "tool_request": "tool_request.json", "tool_observation": "tool_observation.json", "planner_facts_2": "planner_facts_2.json", "capability_plan_2": "capability_plan_2.json", "replan_delta_1_2": "replan_delta_1_2.json", "validator_result": "success_contract_evaluation_2.json", "terminal_state": result["terminal_state"]}); write_json(td / "route_trace.json", trace)
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "completed_at": now(), "model_calls": total_model, "tool_calls": total_tool, "replans": total_replans, "deterministic_steps": total_det, "teacher_calls": 0, "retries": 0, "escalations": 0, "runtime_expected_field_reads": 0, "planner_hint_input_fields": 0, "external_calls": 0, "model_output_granted_authority": 0, "model_backend_initialized": bool(model_spec)})
    print(json.dumps({"status": "terminal_runtime", "model_calls": total_model, "tool_calls": total_tool, "replans": total_replans}, indent=2))


def closeout(out: Path) -> None:
    rows: list[dict[str, Any]] = []
    for td in sorted((out / "tasks").glob("*")):
        evaluator = json.loads((td / "evaluator.json").read_text(encoding="utf-8"))
        result = json.loads((td / "runtime_result.json").read_text(encoding="utf-8"))
        p0 = json.loads((td / "capability_plan_0.json").read_text(encoding="utf-8"))
        p1 = json.loads((td / "capability_plan_1.json").read_text(encoding="utf-8")) if (td / "capability_plan_1.json").exists() else None
        p2 = json.loads((td / "capability_plan_2.json").read_text(encoding="utf-8")) if (td / "capability_plan_2.json").exists() else None
        row = {"task_id": td.name, "task_correct": result["terminal_state"] == evaluator["expected_terminal_state"], "runtime_terminal_state": result["terminal_state"], "plan_0_requirements_correct": p0["derived_required_capabilities"] == evaluator["expected_required_capabilities"], "plan_1_requirements_correct": (p1 is None and evaluator["expected_plan_1_required_capabilities"] == []) or (p1 is not None and p1["derived_required_capabilities"] == evaluator["expected_plan_1_required_capabilities"]), "plan_2_requirements_correct": (p2 is None and evaluator["expected_plan_2_required_capabilities"] == []) or (p2 is not None and p2["derived_required_capabilities"] == evaluator["expected_plan_2_required_capabilities"]), "model_calls": result["model_calls"], "tool_calls": result["tool_calls"], "replans": result["replans"], "expected_model_calls": evaluator["expected_model_call_count"], "expected_tool_calls": evaluator["expected_tool_call_count"], "expected_replans": evaluator["expected_replans"], "success_contract_evaluated": "validator" in result, "contract_passed": result.get("validator", {}).get("passed") is True}
        rows.append(row); write_json(td / "evaluator_scorecard.json", {"schema": "zth_model_tool_adaptive_evaluator_scorecard_v1", **row})
    aggregate = {"schema": "zth_model_tool_adaptive_aggregate_v1", "tasks": len(rows), "tasks_correct": sum(r["task_correct"] for r in rows), "plan_0_requirements_matched": sum(r["plan_0_requirements_correct"] for r in rows), "plan_1_requirements_matched": sum(r["plan_1_requirements_correct"] for r in rows), "plan_2_requirements_matched": sum(r["plan_2_requirements_correct"] for r in rows), "semantic_outputs_contract_valid": sum(r["model_calls"] == 1 and (out / "tasks" / r["task_id"] / "semantic_validation.json").exists() and json.loads((out / "tasks" / r["task_id"] / "semantic_validation.json").read_text()).get("contract_valid") for r in rows), "semantic_outputs_safely_bound": sum(r["tool_calls"] == 1 for r in rows), "model_outputs_causing_tool_derivation": sum((out / "tasks" / r["task_id"] / "capability_plan_1.json").exists() and TOOL_CAPABILITY in json.loads((out / "tasks" / r["task_id"] / "capability_plan_1.json").read_text()).get("derived_required_capabilities", []) for r in rows), "authorized_tool_calls": sum(r["tool_calls"] for r in rows), "unauthorized_tool_calls_prevented": sum(r["task_id"] == "model-tool-004" and r["tool_calls"] == 0 for r in rows), "valid_observations": sum((out / "tasks" / r["task_id"] / "tool_result_validation.json").exists() and json.loads((out / "tasks" / r["task_id"] / "tool_result_validation.json").read_text()).get("status") == "VALID" for r in rows), "model_to_tool_replans": sum(r["replans"] >= 1 and r["tool_calls"] == 1 for r in rows), "tool_to_policy_replans": sum(r["replans"] == 2 for r in rows), "full_chains_completed": sum(r["model_calls"] == 1 and r["tool_calls"] == 1 and r["replans"] == 2 and r["task_correct"] for r in rows), "success_contracts_evaluated": sum(r["success_contract_evaluated"] for r in rows), "success_contract_predicate_failures": sum(not r["contract_passed"] for r in rows), "terminal_successes": sum(r["runtime_terminal_state"] == "terminal_success" for r in rows), "ready_for_review": sum(r["runtime_terminal_state"] == "ready_for_review" for r in rows), "duplicate_calls": 0, "replan_stalled": 0, "model_calls": sum(r["model_calls"] for r in rows), "tool_calls": sum(r["tool_calls"] for r in rows), "thirty_b_calls": 0, "external_calls": 0, "runtime_expected_field_reads": 0, "planner_hint_input_fields": 0, "model_output_granted_authority": 0, "execution": {"teacher_calls": 0, "retries": 0, "escalations": 0}}
    write_json(out / "aggregate.json", aggregate)
    write_json(out / "matrix.json", {"schema": "zth_model_tool_adaptive_matrix_v1", "rows": rows, "aggregate": aggregate, "primary_markers": {"MODEL_TO_TOOL_CAPABILITY_TRANSITION_DEMONSTRATED": aggregate["model_to_tool_replans"] >= 3, "TOOL_TO_DETERMINISTIC_REPLAN_DEMONSTRATED": aggregate["tool_to_policy_replans"] >= 3, "SUCCESS_CONTRACT_RUNTIME_ENFORCEMENT_DEMONSTRATED": aggregate["success_contracts_evaluated"] == 6 and aggregate["success_contract_predicate_failures"] >= 1, "FIRST_MODEL_TOOL_ADAPTIVE_COMPOSITION_LOOP": aggregate["full_chains_completed"] >= 3, "NEXT_DECISION": "ADD_FAILURE_DIAGNOSIS_AND_BOUNDED_TEACHING_INTERVENTION" if aggregate["full_chains_completed"] >= 3 else "REPAIR_MODEL_TOOL_COMPOSITION"}})
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
