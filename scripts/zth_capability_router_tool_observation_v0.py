#!/usr/bin/env python3
"""Bounded read-only repository observation with one deterministic replan."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts import zth_capability_router_v1 as v1
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base

ROOT = base.ROOT
TASKS = ROOT / "docs/research/CAPABILITY_ROUTER_TOOL_OBSERVATION_V0_TASKS_2026-08-22.json"
REGISTRY = ROOT / "docs/research/CAPABILITY_ROUTER_TOOL_REGISTRY_V0_2026-08-22.json"
MAX_REPLANS = 1
TOOL_CAPABILITY = "tool.read_only_repository_observation"
TOOL_SUPPLIER = "python_read_only_repository_observer_v0"
TARGET_RE = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9_./-]*\.(?:json|md|txt))\b")
FORBIDDEN_RUNTIME_FIELDS = {"observation_requirement", "requires_tool_observation", "tool_capability_id", "required_capabilities", "expected_supplier", "expected_route"}


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
        raise RuntimeError("tool slice requires six unique tasks")
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


def build_planner_facts(task: dict[str, Any], triage: dict[str, Any], orchestration: dict[str, Any], observation: dict[str, Any] | None = None) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "schema": "zth_tool_observation_planner_facts_v0",
        "task_id": task["task_id"],
        "request_evidence": {"input_request": task["input_request"], "requested_target": extract_target(task["input_request"])},
        "triage_content": {"task_type": triage["task_type"], "allowed_targets": list(triage["allowed_targets"]), "held_targets": list(triage["held_targets"]), "risk_flags": list(triage["risk_flags"]), "validation_hooks": list(triage["validation_hooks"]), "output_contract": dict(triage["output_contract"])},
        "orchestration_content": {"allowed_targets": list(orchestration["allowed_targets"]), "held_targets": list(orchestration["held_targets"]), "authority_boundaries": list(orchestration["authority_boundaries"]), "review_required": orchestration["review_required"]},
        "environment_facts": copy.deepcopy(task.get("environment_facts", {})),
        "packet_source": {"triage_id": triage["triage_id"], "orchestration_id": orchestration["orchestration_id"]},
        "provenance": {"request": "input_request", "packet": ["vogon_triage_packet.json", "orchestration_packet.json"], "authority": "environment_facts.authority_record"},
    }
    if observation is not None:
        facts["validated_observation"] = copy.deepcopy(observation)
        facts["provenance"]["observation"] = "tool_observation.json"
    return facts


def derive_requirements(facts: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    request = norm(facts["request_evidence"]["input_request"])
    authority = facts["environment_facts"].get("authority_record")
    target = facts["request_evidence"].get("requested_target")
    required: list[str] = []
    derivations: list[dict[str, Any]] = []
    unresolved: list[str] = []

    def add(capability: str, kind: str, fields: list[str], reason: str) -> None:
        if capability not in required:
            required.append(capability)
        derivations.append({"capability_id": capability, "derivation_type": kind, "source_artifacts": ["planner_facts.json"], "source_fields": fields, "reason": reason})

    obs = facts.get("validated_observation")
    if obs is not None and obs.get("status") == "VALID_OBSERVATION":
        policy = "deterministic.observation_exists_policy" if obs.get("exists") else "deterministic.observation_absence_policy"
        add(policy, "DETERMINISTIC_PACKET_RULE", ["validated_observation.exists", "validated_observation.validation_status"], "Validated runtime observation selects the corresponding deterministic post-observation policy.")
        return required, derivations, unresolved
    if isinstance(facts["environment_facts"].get("canonical_operands"), dict):
        operands = facts["environment_facts"]["canonical_operands"]
        if {"target_match", "operation_match"} <= set(operands):
            add("deterministic.boolean_composition", "DETERMINISTIC_PACKET_RULE", ["environment_facts.canonical_operands"], "Canonical operands require no world observation.")
        else:
            unresolved.append("deterministic.boolean_composition")
        return required, derivations, unresolved
    if "service status" in request:
        add("tool.current_service_observation", "ENVIRONMENTAL_REQUIREMENT", ["request_evidence.input_request", "triage_content.task_type"], "The request asks for an unsupported service-state observation.")
        return required, derivations, unresolved
    if target and isinstance(authority, dict) and ("exists" in request or "present" in request) and isinstance(authority.get("allowed_targets"), list):
        add(TOOL_CAPABILITY, "SEMANTIC_INTERPRETATION", ["request_evidence.input_request", "request_evidence.requested_target", "orchestration_content.authority_boundaries"], "The bounded request explicitly asks for current existence state of one named target.")
        return required, derivations, unresolved
    unresolved.append("read-only observation requirement")
    return required, derivations, unresolved


def choose_supplier(capability: str, index: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any] | None, str]:
    candidates = [entry for entry in index.get(capability, []) if entry["status"] == "QUALIFIED_EXPLORATORY"]
    if not candidates:
        return None, "No qualified supplier; fail closed."
    selected = sorted(candidates, key=lambda entry: (entry["supplier_type"], entry["supplier_id"]))[0]
    return selected, f"Selected qualified {selected['supplier_type']} supplier."


def plan_capabilities(facts: dict[str, Any], index: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any], dict[str, Any]]:
    required, derivations, unresolved = derive_requirements(facts)
    records = []
    for capability in required:
        candidates = index.get(capability, [])
        selected, reason = choose_supplier(capability, index)
        records.append({"capability_id": capability, "candidate_suppliers": [{"supplier_id": e["supplier_id"], "supplier_type": e["supplier_type"], "interface_id": e["interface_id"], "status": e["status"]} for e in candidates], "selected_supplier": None if selected is None else {"supplier_id": selected["supplier_id"], "supplier_type": selected["supplier_type"], "interface_id": selected["interface_id"]}, "selection_reason": reason, "coverage_status": "COVERED" if selected else "UNCOVERED"})
    complete = bool(required) and not unresolved and all(item["coverage_status"] == "COVERED" for item in records)
    steps = []
    if complete:
        for item in records:
            cap = item["capability_id"]
            supplier = item["selected_supplier"]
            if cap == TOOL_CAPABILITY:
                req, prod, deps, prov = ["repository_relative_path", "authorized_targets"], ["observation"], [], {"repository_relative_path": "PACKET", "authorized_targets": "PACKET"}
            elif cap in {"deterministic.observation_exists_policy", "deterministic.observation_absence_policy"}:
                req, prod, deps, prov = ["observation"], ["terminal_observation"], [], {"observation": "PRIOR_STEP"}
            elif cap == "deterministic.boolean_composition":
                req, prod, deps, prov = ["canonical_operands"], ["policy_result"], [], {"canonical_operands": "ENVIRONMENT"}
            else:
                req, prod, deps, prov = [], [], [], {}
            steps.append({"step_id": f"step_{cap.replace('.', '_')}", "capability_id": cap, "supplier_id": supplier["supplier_id"], "supplier_type": supplier["supplier_type"], "requires_inputs": req, "produces_outputs": prod, "depends_on": deps, "input_provenance": prov})
    plan = {"schema": "zth_tool_observation_capability_plan_v0", "task_id": facts["task_id"], "derived_required_capabilities": required, "capabilities": records, "unresolved_requirements": unresolved, "overall_coverage": "COMPLETE" if complete else "INCOMPLETE", "execution_steps": steps, "planned_tool_calls": sum(s["supplier_type"] == "TOOL" for s in steps), "planned_model_calls": 0, "planned_deterministic_steps": sum(s["supplier_type"] == "DETERMINISTIC_CODE" for s in steps)}
    derivation = {"schema": "zth_tool_observation_capability_requirement_derivation_v0", "task_id": facts["task_id"], "requirements": derivations, "unresolved": unresolved, "output_required_capabilities": required}
    return plan, derivation


def build_success_contract(facts: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    predicates = []
    required = plan["derived_required_capabilities"]
    if TOOL_CAPABILITY in required:
        predicates.extend([{"predicate": "tool_observation_schema_valid"}, {"predicate": "observation_path_matches_requested_target"}, {"predicate": "observation_authority_valid"}])
    if "deterministic.observation_exists_policy" in required:
        predicates.append({"predicate": "validated_observation_present"})
    if "deterministic.observation_absence_policy" in required:
        predicates.append({"predicate": "validated_observation_absent"})
    if "deterministic.boolean_composition" in required:
        predicates.append({"predicate": "canonical_policy_computed"})
    if plan["overall_coverage"] != "COMPLETE":
        predicates.append({"predicate": "coverage_complete", "value": False})
    return {"schema": "zth_tool_observation_success_contract_v0", "task_id": facts["task_id"], "predicates": predicates, "contains_worked_answer": False}


def validate_tool_request(request: dict[str, Any], *, repo_root: Path = ROOT) -> dict[str, Any]:
    path_text = request.get("repository_relative_path")
    allowed = request.get("authorized_targets")
    result = {"schema": "zth_tool_authority_validation_v0", "status": "DENIED", "repository_relative_path": path_text, "reason": None}
    if not isinstance(path_text, str) or not path_text.strip():
        result["reason"] = "missing repository-relative path"
        return result
    path = Path(path_text)
    if path.is_absolute():
        result["reason"] = "absolute path denied"
        return result
    if ".." in path.parts:
        result["reason"] = "parent traversal denied"
        return result
    if not isinstance(allowed, list) or path_text not in allowed:
        result["reason"] = "target not an exact member of authorized target set"
        return result
    root = repo_root.resolve()
    resolved = (root / path).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        result["reason"] = "resolved path escapes repository root"
        return result
    result.update({"status": "AUTHORIZED", "resolved_path": str(resolved), "authority_source": request.get("authority_source")})
    return result


def observe_repository(request: dict[str, Any], authority: dict[str, Any], *, repo_root: Path = ROOT) -> dict[str, Any]:
    if authority["status"] != "AUTHORIZED":
        return {"schema": "zth_tool_observation_v0", "status": "TOOL_AUTHORITY_DENIED", "repository_relative_path": request.get("repository_relative_path"), "exists": None, "is_file": None, "size_bytes": None, "sha256": None}
    target = repo_root / request["repository_relative_path"]
    exists = target.exists()
    is_file = target.is_file() if exists else False
    digest = None
    size = None
    if is_file:
        size = target.stat().st_size
        h = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        digest = h.hexdigest()
    return {"schema": "zth_tool_observation_v0", "status": "VALID_OBSERVATION", "repository_relative_path": request["repository_relative_path"], "exists": exists, "is_file": is_file, "size_bytes": size, "sha256": digest}


def validate_observation(observation: dict[str, Any], request: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    valid = observation.get("status") == "VALID_OBSERVATION" and authority.get("status") == "AUTHORIZED"
    failures = []
    if observation.get("repository_relative_path") != request.get("repository_relative_path"):
        failures.append("observation path mismatch")
    if not isinstance(observation.get("exists"), bool) or not isinstance(observation.get("is_file"), bool):
        failures.append("observation boolean fields invalid")
    if observation.get("sha256") is not None and (not observation.get("is_file") or not re.fullmatch(r"[0-9a-f]{64}", observation["sha256"])):
        failures.append("observation hash invalid")
    if not observation.get("is_file") and observation.get("sha256") is not None:
        failures.append("non-file hash must be null")
    return {"schema": "zth_tool_result_validation_v0", "status": "VALID" if valid and not failures else "INVALID", "failures": failures}


def execute_deterministic(plan: dict[str, Any], facts: dict[str, Any], observation: dict[str, Any] | None) -> dict[str, Any]:
    cap = plan["derived_required_capabilities"]
    if "deterministic.boolean_composition" in cap:
        operands = facts["environment_facts"]["canonical_operands"]
        return {"terminal_state": "terminal_success", "policy_result": not (operands["target_match"] and operands["operation_match"]), "deterministic_steps": 1}
    if "deterministic.observation_exists_policy" in cap and observation and observation.get("exists") is True:
        return {"terminal_state": "terminal_success", "terminal_observation": "VALID_OBSERVATION_EXISTING", "deterministic_steps": 1}
    if "deterministic.observation_absence_policy" in cap and observation and observation.get("exists") is False:
        return {"terminal_state": "terminal_success", "terminal_observation": "VALID_OBSERVATION_ABSENT", "deterministic_steps": 1}
    return {"terminal_state": "ready_for_review", "deterministic_steps": 1, "failure": "post-observation contract failed"}


def validate_model_free() -> dict[str, Any]:
    tasks = load_tasks()
    index = registry_index()
    prepared = []
    for task in tasks:
        if any(field in json.dumps(task.get("environment_facts", {})) for field in FORBIDDEN_RUNTIME_FIELDS):
            raise RuntimeError(f"forbidden planner/tool hint in {task['task_id']}")
        triage, orchestration = make_packets(task)
        facts = build_planner_facts(task, triage, orchestration)
        plan, derivation = plan_capabilities(facts, index)
        contract = build_success_contract(facts, plan)
        input_rendered = json.dumps({"facts": facts, "contract": contract})
        if any(field in input_rendered for field in FORBIDDEN_RUNTIME_FIELDS):
            raise RuntimeError(f"forbidden field leaked into runtime inputs: {task['task_id']}")
        output_rendered = json.dumps({"plan": plan, "derivation": derivation})
        if any(field in output_rendered for field in FORBIDDEN_RUNTIME_FIELDS - {"required_capabilities"}):
            raise RuntimeError(f"forbidden field leaked into non-requirement outputs: {task['task_id']}")
        prepared.append((task, triage, orchestration, facts, plan, contract, derivation))
    if sum(item[4]["overall_coverage"] == "COMPLETE" for item in prepared) != 5:
        raise RuntimeError("expected five complete plan_0 routes")
    if sum(item[4]["overall_coverage"] == "INCOMPLETE" for item in prepared) != 1:
        raise RuntimeError("expected one incomplete plan_0 route")
    return {"tasks": tasks, "plans": prepared, "task_sha256": sha_file(TASKS), "registry_sha256": sha_file(REGISTRY)}


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = validate_model_free()
    for task, triage, orchestration, facts, plan, contract, derivation in binding["plans"]:
        td = out / "tasks" / task["task_id"]
        td.mkdir(parents=True, exist_ok=True)
        write_json(td / "runtime_task.json", {"schema": "zth_tool_runtime_task_v0", "task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"], "packet_source": facts["packet_source"]})
        write_json(td / "evaluator.json", {key: value for key, value in task.items() if key.startswith("expected_")})
        write_json(td / "vogon_triage_packet.json", triage)
        write_json(td / "orchestration_packet.json", orchestration)
        write_json(td / "planner_facts_0.json", facts)
        write_json(td / "capability_requirement_derivation_0.json", derivation)
        write_json(td / "capability_plan_0.json", plan)
        write_json(td / "success_contract_0.json", contract)
        write_json(td / "replan_delta.json", {"schema": "zth_tool_replan_delta_v0", "observation_consumed": False, "previous_required_capabilities": plan["derived_required_capabilities"], "new_required_capabilities": [], "capabilities_satisfied": [], "capabilities_added": [], "capabilities_removed": [], "reason": "No replan before execution."})
    manifest = {"schema": "zth_tool_observation_manifest_v0", "status": "prepared_exploratory_not_production", "prepared_at": now(), "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "driver": str(Path(__file__).relative_to(ROOT)), "driver_sha256": sha_file(Path(__file__).resolve()), "task_manifest_sha256": binding["task_sha256"], "registry_sha256": binding["registry_sha256"], "task_count": 6, "max_replans": MAX_REPLANS, "planner_hint_input_fields": 0, "runtime_expected_field_reads": 0, "observation_requirement_input_field_present": False, "planned_tool_calls": sum(item[4]["planned_tool_calls"] for item in binding["plans"]), "planned_model_calls": 0, "model_calls_made": False, "tool_calls_made": False, "external_calls": 0, "v100_touched": False}
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls": 0, "tool_calls": 0, "replans": 0, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 6, "planned_tool_calls": manifest["planned_tool_calls"], "model_calls": 0, "tool_calls": 0}, indent=2))


def execute(out: Path) -> None:
    manifest = json.loads((out / "router_manifest.json").read_text())
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("manifest digest mismatch")
    total_tools = total_replans = 0
    for td in sorted((out / "tasks").glob("*")):
        runtime_task = json.loads((td / "runtime_task.json").read_text())
        facts0 = json.loads((td / "planner_facts_0.json").read_text())
        plan0 = json.loads((td / "capability_plan_0.json").read_text())
        contract0 = json.loads((td / "success_contract_0.json").read_text())
        trace = {"schema": "zth_tool_route_trace_v0", "task_id": runtime_task["task_id"], "input_request": runtime_task["input_request"], "packets": ["vogon_triage_packet.json", "orchestration_packet.json"], "planner_facts_0": "planner_facts_0.json", "requirement_derivation_0": "capability_requirement_derivation_0.json", "capability_plan_0": "capability_plan_0.json", "tool_supplier": None, "tool_calls": 0, "terminal_state": None}
        if plan0["overall_coverage"] != "COMPLETE":
            result = {"terminal_state": "ready_for_review", "reason": "incomplete plan_0 coverage", "tool_calls": 0, "replans": 0}
            trace["terminal_state"] = result["terminal_state"]
            write_json(td / "runtime_result.json", result)
            write_json(td / "route_trace.json", trace)
            continue
        tool_step = next((step for step in plan0["execution_steps"] if step["supplier_type"] == "TOOL"), None)
        if tool_step is None:
            result = execute_deterministic(plan0, facts0, None)
            result.update({"tool_calls": 0, "replans": 0})
            trace["terminal_state"] = result["terminal_state"]
            write_json(td / "runtime_result.json", result)
            write_json(td / "route_trace.json", trace)
            continue
        target = facts0["request_evidence"].get("requested_target")
        allowed = facts0["environment_facts"].get("authority_record", {}).get("allowed_targets", [])
        tool_request = {"schema": "zth_tool_request_v0", "capability_id": TOOL_CAPABILITY, "supplier_id": TOOL_SUPPLIER, "repository_relative_path": target, "authorized_targets": allowed, "authority_source": "environment_facts.authority_record.allowed_targets"}
        write_json(td / "tool_request.json", tool_request)
        authority = validate_tool_request(tool_request)
        write_json(td / "tool_authority_validation.json", authority)
        trace["tool_supplier"] = {"supplier_id": TOOL_SUPPLIER, "capability_id": TOOL_CAPABILITY, "selection_evidence": "capability_plan_0.json"}
        if authority["status"] != "AUTHORIZED":
            observation = {"schema": "zth_tool_observation_v0", "status": "TOOL_AUTHORITY_DENIED", "repository_relative_path": target, "exists": None, "is_file": None, "size_bytes": None, "sha256": None}
            write_json(td / "tool_observation.json", observation)
            write_json(td / "tool_result_validation.json", {"schema": "zth_tool_result_validation_v0", "status": "TOOL_AUTHORITY_DENIED", "failures": [authority["reason"]]})
            result = {"terminal_state": "ready_for_review", "reason": "TOOL_AUTHORITY_DENIED", "tool_calls": 0, "replans": 0}
            trace["authority_validation"] = authority
            trace["terminal_state"] = result["terminal_state"]
            write_json(td / "runtime_result.json", result)
            write_json(td / "route_trace.json", trace)
            continue
        total_tools += 1
        observation = observe_repository(tool_request, authority)
        write_json(td / "tool_observation.json", observation)
        validation = validate_observation(observation, tool_request, authority)
        write_json(td / "tool_result_validation.json", validation)
        trace.update({"authority_validation": authority, "tool_request": "tool_request.json", "tool_observation": "tool_observation.json", "tool_observation_status": observation["status"]})
        if validation["status"] != "VALID":
            result = {"terminal_state": "ready_for_review", "reason": "TOOL_INTERFACE_FAILURE", "tool_calls": 1, "replans": 0}
            trace["terminal_state"] = result["terminal_state"]
            write_json(td / "runtime_result.json", result)
            write_json(td / "route_trace.json", trace)
            continue
        total_replans += 1
        facts1 = build_planner_facts({"task_id": runtime_task["task_id"], "input_request": runtime_task["input_request"], "environment_facts": runtime_task["environment_facts"]}, json.loads((td / "vogon_triage_packet.json").read_text()), json.loads((td / "orchestration_packet.json").read_text()), observation)
        plan1, derivation1 = plan_capabilities(facts1, registry_index())
        contract1 = build_success_contract(facts1, plan1)
        write_json(td / "planner_facts_1.json", facts1)
        write_json(td / "capability_requirement_derivation_1.json", derivation1)
        write_json(td / "capability_plan_1.json", plan1)
        write_json(td / "success_contract_1.json", contract1)
        delta = {"schema": "zth_tool_replan_delta_v0", "previous_required_capabilities": plan0["derived_required_capabilities"], "new_required_capabilities": plan1["derived_required_capabilities"], "observation_consumed": True, "capabilities_satisfied": [TOOL_CAPABILITY], "capabilities_added": [cap for cap in plan1["derived_required_capabilities"] if cap not in plan0["derived_required_capabilities"]], "capabilities_removed": [cap for cap in plan0["derived_required_capabilities"] if cap not in plan1["derived_required_capabilities"]], "reason": "Re-derived after validated observation."}
        write_json(td / "replan_delta.json", delta)
        if plan1["derived_required_capabilities"] == plan0["derived_required_capabilities"]:
            result = {"terminal_state": "ready_for_review", "reason": "REPLAN_STALLED", "tool_calls": 1, "replans": 1}
        else:
            result = execute_deterministic(plan1, facts1, observation)
            result.update({"tool_calls": 1, "replans": 1})
        trace.update({"planner_facts_1": "planner_facts_1.json", "requirement_derivation_1": "capability_requirement_derivation_1.json", "capability_plan_1": "capability_plan_1.json", "replan_delta": "replan_delta.json", "terminal_state": result["terminal_state"]})
        write_json(td / "runtime_result.json", result)
        write_json(td / "route_trace.json", trace)
    write_json(out / "lifecycle.json", {"status": "terminal_runtime", "completed_at": now(), "model_calls": 0, "tool_calls": total_tools, "replans": total_replans, "teacher_calls": 0, "retries": 0, "escalations": 0, "planner_hint_input_fields": 0, "runtime_expected_field_reads": 0, "external_calls": 0})
    print(json.dumps({"status": "terminal_runtime", "tool_calls": total_tools, "replans": total_replans, "model_calls": 0}, indent=2))


def closeout(out: Path) -> None:
    rows = []
    for td in sorted((out / "tasks").glob("*")):
        evaluator = json.loads((td / "evaluator.json").read_text())
        result = json.loads((td / "runtime_result.json").read_text())
        plan0 = json.loads((td / "capability_plan_0.json").read_text())
        actual0 = [step["capability_id"] for step in plan0["execution_steps"]]
        expected0 = evaluator.get("expected_plan_0_required_capabilities", evaluator.get("expected_required_capabilities", []))
        plan1 = json.loads((td / "capability_plan_1.json").read_text()) if (td / "capability_plan_1.json").exists() else None
        actual1 = [] if plan1 is None else plan1["derived_required_capabilities"]
        expected1 = evaluator.get("expected_plan_1_required_capabilities", [])
        rows.append({"task_id": td.name, "task_correct": result["terminal_state"] == evaluator["expected_terminal_state"], "runtime_terminal_state": result["terminal_state"], "plan_0_requirements_correct": actual0 == expected0, "plan_1_requirements_correct": actual1 == expected1, "tool_calls": result.get("tool_calls", 0), "replans": result.get("replans", 0), "expected_tool_calls": evaluator["expected_tool_call_count"], "expected_replans": evaluator["expected_replans"]})
        write_json(td / "evaluator_scorecard.json", {"schema": "zth_tool_observation_evaluator_scorecard_v0", **rows[-1]})
    aggregate = {"schema": "zth_tool_observation_aggregate_v0", "tasks_correct": sum(row["task_correct"] for row in rows), "plan_0_requirements_matched": sum(row["plan_0_requirements_correct"] for row in rows), "plan_1_requirements_matched": sum(row["plan_1_requirements_correct"] for row in rows), "authorized_tool_calls_executed": sum(row["tool_calls"] for row in rows), "valid_observations": sum(row["tool_calls"] == 1 and (out / "tasks" / row["task_id"] / "tool_result_validation.json").exists() and json.loads((out / "tasks" / row["task_id"] / "tool_result_validation.json").read_text()).get("status") == "VALID" for row in rows), "observation_dependent_replans": sum(row["replans"] == 1 for row in rows), "replans_capability_set_changed": sum(row["replans"] == 1 and row["plan_1_requirements_correct"] for row in rows), "terminal_successes": sum(row["runtime_terminal_state"] == "terminal_success" for row in rows), "ready_for_review": sum(row["runtime_terminal_state"] == "ready_for_review" for row in rows), "replan_stalled": sum((out / "tasks" / row["task_id"] / "runtime_result.json").exists() and json.loads((out / "tasks" / row["task_id"] / "runtime_result.json").read_text()).get("reason") == "REPLAN_STALLED" for row in rows), "duplicate_tool_calls": sum(row["tool_calls"] > 1 for row in rows), "unnecessary_tool_calls": 0, "model_calls": 0, "external_calls": 0, "planner_hint_input_fields": 0, "runtime_expected_field_reads": 0, "execution": {"teacher_calls": 0, "retries": 0, "escalations": 0}}
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
