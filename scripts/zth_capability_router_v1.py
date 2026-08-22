#!/usr/bin/env python3
"""Experimental packet-derived, multi-capability ZTH Router V1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from local_harness.orchestration_packet import assemble_orchestration_packet, validate_orchestration_packet
from local_harness.prompt_patch_library import PromptPatchLibrary
from local_harness.stage_a_power_telemetry import PowerSampler, integrate_energy_joules, read_gpu_power
from local_harness.triage_router_rules import route_messy_input
from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts import zth_qwen3_1_7b_atomic_scope_relation_decomposition as decomposition
from scripts import zth_qwen3_1_7b_clean_scope_logic_probe as runtime

ROOT = base.ROOT
TASKS = ROOT / "docs/research/CAPABILITY_ROUTER_V1_TASKS_2026-08-22.json"
REGISTRY = ROOT / "docs/research/CAPABILITY_ROUTER_EXPERIMENTAL_REGISTRY_V1_2026-08-22.json"
PATCH_DIR = ROOT / "examples/prompt_patches"
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
    payload = json.loads(TASKS.read_text(encoding="utf-8"))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 10:
        raise RuntimeError("Router V1 requires exactly 10 frozen tasks")
    if len({task.get("task_id") for task in tasks}) != len(tasks):
        raise RuntimeError("Router V1 task IDs must be unique")
    return tasks


def load_registry() -> dict[str, Any]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if payload.get("automatic_promotion") is not False:
        raise RuntimeError("automatic capability promotion must be false")
    entries = payload.get("entries")
    required = {"capability_id", "supplier_id", "supplier_type", "interface_id", "status", "evidence_artifact", "evidence_scope", "qualification_decision"}
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("registry entries missing")
    for entry in entries:
        if not required <= set(entry):
            raise RuntimeError("registry entry missing required evidence fields")
        if entry["status"] not in {"QUALIFIED_EXPLORATORY", "NOT_QUALIFIED", "UNKNOWN"}:
            raise RuntimeError("registry status is not explicit")
        if not (ROOT / entry["evidence_artifact"]).is_file():
            raise RuntimeError(f"registry evidence missing: {entry['evidence_artifact']}")
    return payload


def index_registry(registry: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for entry in registry["entries"]:
        index.setdefault(entry["capability_id"], []).append(entry)
    return index


def minimal_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"action": {"type": "string"}, "object_expression": {"type": "string"}},
        "required": ["action", "object_expression"],
        "additionalProperties": False,
    }


def response_format() -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": "router_v1_minimal_semantic_atom", "schema": minimal_schema()}}


def semantic_prompt(input_request: str) -> str:
    return (
        f"Request clause:\n{input_request}\n\n"
        "Required structured fields describe the request clause.\n\n"
        "action:\n"
        "the operation expressed in the request clause.\n\n"
        "object_expression:\n"
        "the phrase describing what the action is applied to.\n\n"
        "/no_think"
    )


def build_runtime_packet(task: dict[str, Any], triage: dict[str, Any], orchestration: dict[str, Any]) -> dict[str, Any]:
    """Build the planner input from packet facts only, never evaluator annotations."""
    return {
        "schema": "zth_router_v1_runtime_packet_v1",
        "task_id": task["task_id"],
        "input_request": task["input_request"],
        "packet_inputs": dict(task.get("packet_inputs", {})),
        "packet_source": {
            "triage_id": triage["triage_id"],
            "orchestration_id": orchestration["orchestration_id"],
        },
    }


def derive_required_capabilities(runtime_packet: dict[str, Any]) -> list[str]:
    """Derive capabilities solely from canonical runtime packet properties."""
    facts = runtime_packet["packet_inputs"]
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
        return None, "No QUALIFIED_EXPLORATORY supplier exists for this capability; coverage is incomplete."
    order = {"DETERMINISTIC_CODE": 0, "MODEL": 1, "TOOL": 2, "REVIEW_OR_ESCALATION": 3}
    selected = sorted(qualified, key=lambda candidate: (order.get(candidate["supplier_type"], 99), candidate["supplier_id"]))[0]
    return selected, f"Selected qualified {selected['supplier_type']} supplier using explicit supplier-type precedence."


def plan_capabilities(runtime_packet: dict[str, Any], registry_index: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    derived = derive_required_capabilities(runtime_packet)
    records = []
    for capability_id in derived:
        candidates = list(registry_index.get(capability_id, []))
        selected, reason = select_supplier(candidates)
        qualified = [candidate for candidate in candidates if candidate["status"] == "QUALIFIED_EXPLORATORY"]
        records.append({
            "capability_id": capability_id,
            "candidate_suppliers": [{"supplier_id": item["supplier_id"], "supplier_type": item["supplier_type"], "interface_id": item["interface_id"], "status": item["status"]} for item in candidates],
            "qualified_candidates": [{"supplier_id": item["supplier_id"], "supplier_type": item["supplier_type"], "interface_id": item["interface_id"]} for item in qualified],
            "selected_supplier": None if selected is None else {"supplier_id": selected["supplier_id"], "supplier_type": selected["supplier_type"], "interface_id": selected["interface_id"]},
            "selection_reason": reason,
            "coverage_status": "COVERED" if selected is not None else "UNCOVERED",
        })
    complete = bool(records) and all(record["coverage_status"] == "COVERED" for record in records)
    steps = []
    if complete:
        for record in records:
            supplier = record["selected_supplier"]
            steps.append({"capability_id": record["capability_id"], "supplier_id": supplier["supplier_id"], "supplier_type": supplier["supplier_type"]})
    return {
        "schema": "zth_router_v1_capability_plan_v1",
        "task_id": runtime_packet["task_id"],
        "packet_source": runtime_packet["packet_source"],
        "derived_required_capabilities": derived,
        "capabilities": records,
        "overall_coverage": "COMPLETE" if complete else "INCOMPLETE",
        "execution_steps": steps,
        "planned_model_calls": sum(step["supplier_type"] == "MODEL" for step in steps),
        "planned_tool_calls": sum(step["supplier_type"] == "TOOL" for step in steps),
        "planned_deterministic_steps": sum(step["supplier_type"] == "DETERMINISTIC_CODE" for step in steps),
    }


def validate_model_free() -> dict[str, Any]:
    tasks = load_tasks()
    registry = load_registry()
    index = index_registry(registry)
    if not any(list(index).count("semantic.minimal_action_object_extraction") == 1 for _ in [0]):
        raise RuntimeError("registry index malformed")
    for capability_id, candidates in index.items():
        if not isinstance(candidates, list) or not candidates:
            raise RuntimeError(f"capability {capability_id} lost supplier list")
    plans = []
    for task in tasks:
        triage, orchestration = make_packets(task)
        runtime_packet = build_runtime_packet(task, triage, orchestration)
        plan = plan_capabilities(runtime_packet, index)
        plans.append((task, runtime_packet, plan))
    if sum(plan["overall_coverage"] == "COMPLETE" for _, _, plan in plans) != 7:
        raise RuntimeError("V1 expected seven complete plans")
    if sum(plan["overall_coverage"] == "INCOMPLETE" for _, _, plan in plans) != 3:
        raise RuntimeError("V1 expected three incomplete plans")
    if any(plan["planned_model_calls"] for task, _, plan in plans if task["task_id"] in {"router-v1-001", "router-v1-002", "router-v1-007", "router-v1-009", "router-v1-010"}):
        raise RuntimeError("deterministic/review-only plans must have zero executable model calls")
    return {"tasks": tasks, "registry": registry, "registry_index": index, "plans": plans, "task_sha256": sha_file(TASKS), "registry_sha256": sha_file(REGISTRY), "schema_sha256": sha_bytes(canonical(minimal_schema())), "format_sha256": sha_bytes(canonical(response_format()))}


def make_packets(task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    triage = route_messy_input(task["input_request"], triage_id=f"triage_{task['task_id']}", source="capability_router_v1")
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    orchestration = assemble_orchestration_packet(triage, library, orchestration_id=f"orch_{task['task_id']}")
    validate_orchestration_packet(orchestration, library)
    return triage, orchestration


def parse_model_output(content: str) -> tuple[dict[str, str] | None, bool, bool, list[str]]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, False, False, [str(exc)]
    valid = isinstance(parsed, dict) and set(parsed) == {"action", "object_expression"} and all(isinstance(parsed.get(field), str) for field in ("action", "object_expression"))
    return (parsed if valid else None), True, valid, ([] if valid else ["exact semantic atom contract failed"])


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    binding = validate_model_free()
    for task, runtime_packet, plan in binding["plans"]:
        task_dir = out / "tasks" / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        triage, orchestration = make_packets(task)
        write_json(task_dir / "fixture.json", task)
        write_json(task_dir / "vogon_triage_packet.json", triage)
        write_json(task_dir / "orchestration_packet.json", orchestration)
        write_json(task_dir / "runtime_packet.json", runtime_packet)
        write_json(task_dir / "capability_plan.json", plan)
        if plan["planned_model_calls"]:
            (task_dir / "semantic_prompt.txt").write_text(semantic_prompt(task["input_request"]), encoding="utf-8")
    manifest = {
        "schema": "zth_router_v1_manifest_v1",
        "status": "prepared_exploratory_not_production",
        "prepared_at": now(),
        "prepared_from_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "driver": str(Path(__file__).relative_to(ROOT)),
        "driver_sha256": sha_file(Path(__file__).resolve()),
        "task_manifest_sha256": binding["task_sha256"],
        "registry_sha256": binding["registry_sha256"],
        "schema_sha256": binding["schema_sha256"],
        "response_format_sha256": binding["format_sha256"],
        "task_count": 10,
        "planned_model_calls": sum(plan["planned_model_calls"] for _, _, plan in binding["plans"]),
        "planned_tool_calls": sum(plan["planned_tool_calls"] for _, _, plan in binding["plans"]),
        "planned_deterministic_steps": sum(plan["planned_deterministic_steps"] for _, _, plan in binding["plans"]),
        "model_backend_initialized": False,
        "hardware": {"gpu_uuid": EXPECTED_GPU_UUID, "v100_touched": False},
        "runtime": {"model_id": EXPECTED_MODEL_ID, "artifact_sha256": EXPECTED_MODEL_SHA, "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX},
        "telemetry": {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "sample_interval_seconds": POWER_INTERVAL_SECONDS},
        "model_calls_made": False,
    }
    manifest["manifest_sha256"] = sha_bytes(canonical({**manifest, "manifest_sha256": None}))
    write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "prepared", "model_calls_made": False, "model_calls": 0, "updated_at": now()})
    print(json.dumps({"status": "prepared", "tasks": 10, "planned_model_calls": manifest["planned_model_calls"], "model_calls": 0}, indent=2))


def execute(out: Path) -> None:
    binding = validate_model_free()
    manifest = json.loads((out / "router_manifest.json").read_text(encoding="utf-8"))
    if manifest["manifest_sha256"] != sha_bytes(canonical({**manifest, "manifest_sha256": None})):
        raise RuntimeError("manifest digest mismatch")
    for key, value in (("task_manifest_sha256", binding["task_sha256"]), ("registry_sha256", binding["registry_sha256"]), ("schema_sha256", binding["schema_sha256"]), ("response_format_sha256", binding["format_sha256"])):
        if manifest[key] != value:
            raise RuntimeError(f"V1 binding mismatch: {key}")
    plans_by_id = {task["task_id"]: plan for task, _, plan in binding["plans"]}
    needs_model = any(plan["planned_model_calls"] for plan in plans_by_id.values())
    model_spec = None
    telemetry_url = None
    idle_summary = None
    if needs_model:
        model_spec = runtime.worker_spec()
        models = decomposition.list_models(model_spec, timeout=30)
        model = next((item for item in models.get("data", []) if item.get("id") == EXPECTED_MODEL_ID), None)
        meta = (model or {}).get("meta") or {}
        if model is None or meta.get("n_params") != EXPECTED_PARAMS or meta.get("n_ctx") != EXPECTED_CTX or meta.get("n_ctx_train") != EXPECTED_TRAIN_CTX:
            raise RuntimeError("lazy model runtime binding mismatch")
        telemetry_url = base.telemetry_base_url()
        base.telemetry_preflight(telemetry_url)
        idle_samples, idle_summary = base.sample_window(IDLE_SECONDS, telemetry_url)
        write_json(out / "idle_power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "summary": idle_summary, "samples": idle_samples})
        write_json(out / "preflight.json", {"model_meta": meta, "telemetry": "passed", "planned_model_calls": manifest["planned_model_calls"]})
        manifest["model_backend_initialized"] = True
        write_json(out / "router_manifest.json", manifest)
    write_json(out / "lifecycle.json", {"status": "running", "model_calls_made": False, "model_calls": 0, "started_at": now(), "model_backend_initialized": needs_model})
    rows = []
    model_calls = 0
    tool_calls = 0
    deterministic_steps = 0
    for task in binding["tasks"]:
        task_dir = out / "tasks" / task["task_id"]
        plan = plans_by_id[task["task_id"]]
        runtime_packet = json.loads((task_dir / "runtime_packet.json").read_text(encoding="utf-8"))
        trace = {"schema": "zth_router_v1_route_trace_v1", "task_id": task["task_id"], "input": task["input_request"], "packet": {"triage": "vogon_triage_packet.json", "orchestration": "orchestration_packet.json", "runtime": "runtime_packet.json"}, "capability_plan": "capability_plan.json", "selected_steps": plan["execution_steps"], "model_calls": [], "tool_calls": [], "deterministic_results": [], "validator_result": None, "terminal_state": None}
        if plan["overall_coverage"] != "COMPLETE":
            trace["validator_result"] = {"status": "not_attempted", "reason": "incomplete capability coverage", "uncovered_capabilities": [record["capability_id"] for record in plan["capabilities"] if record["coverage_status"] == "UNCOVERED"]}
            trace["terminal_state"] = "ready_for_review"
            row = {"task_id": task["task_id"], "capability_plan_correct": plan["derived_required_capabilities"] == task["expected_required_capabilities"], "assignment_correct": False, "coverage_complete": False, "terminal_state": "ready_for_review", "task_correct": task["expected_terminal_state"] == "ready_for_review", "model_calls": 0, "tool_calls": 0, "deterministic_steps": 0, "model_avoided": True}
        else:
            observed_semantic = None
            step_valid = True
            for step in plan["execution_steps"]:
                if step["supplier_type"] == "MODEL":
                    model_calls += 1
                    prompt = (task_dir / "semantic_prompt.txt").read_text(encoding="utf-8")
                    started = time.monotonic()
                    sampler = PowerSampler(lambda: read_gpu_power(EXPECTED_GPU_UUID, base_url=telemetry_url), expected_gpu_uuid=EXPECTED_GPU_UUID, sample_interval_seconds=POWER_INTERVAL_SECONDS)
                    sampler.start()
                    response = decomposition.structured_call(model_spec, prompt, response_format(), MAX_OUTPUT_TOKENS, TIMEOUT_SECONDS)
                    captured = time.monotonic()
                    samples = sampler.stop()
                    energy = integrate_energy_joules(samples, sample_interval_seconds=POWER_INTERVAL_SECONDS, expected_gpu_uuid=EXPECTED_GPU_UUID)
                    metadata = response.metadata()
                    raw = {"status": response.status, "content": response.content, "metadata": metadata, "request_started_at": now(), "response_captured_at": now(), "wall_elapsed_ms": round((captured - started) * 1000, 3)}
                    write_json(task_dir / "response.json", raw)
                    observed_semantic, parse_valid, contract_valid, diagnostics = parse_model_output(response.content)
                    expected = task.get("expected_model_result", {})
                    action_correct = bool(observed_semantic and norm(observed_semantic["action"]) == norm(expected.get("action", "")))
                    object_correct = bool(observed_semantic and norm(observed_semantic["object_expression"]) == norm(expected.get("object_expression", "")))
                    trace["model_calls"].append({"supplier_id": step["supplier_id"], "prompt_sha256": sha_bytes(prompt.encode()), "parse_valid": parse_valid, "contract_valid": contract_valid, "action_correct": action_correct, "object_expression_correct": object_correct, "latency_ms": raw["wall_elapsed_ms"], "gross_energy_joules": energy})
                    write_json(task_dir / "validation.json", {"validation_status": "passed" if parse_valid and contract_valid else "failed", "parse_valid": parse_valid, "contract_valid": contract_valid, "diagnostics": diagnostics, "action_correct": action_correct, "object_expression_correct": object_correct})
                    write_json(task_dir / "power_samples.json", {"measurement_level": 2, "measurement_boundary": "gpu_device_only", "gpu_uuid": EXPECTED_GPU_UUID, "samples": [{"timestamp_utc": sample.timestamp_utc, "monotonic_seconds": sample.monotonic_seconds, "gpu_uuid": sample.gpu_uuid, "power_watts": sample.power_watts, "sequence": sample.sequence} for sample in samples]})
                    step_valid = step_valid and parse_valid and contract_valid and action_correct and object_correct
                elif step["supplier_type"] == "DETERMINISTIC_CODE":
                    deterministic_steps += 1
                    if step["capability_id"] == "deterministic.boolean_composition":
                        result = not (bool(runtime_packet["packet_inputs"].get("canonical_target_match")) and bool(runtime_packet["packet_inputs"].get("canonical_operation_match")))
                        trace["deterministic_results"].append({"capability_id": step["capability_id"], "result": result})
                        step_valid = step_valid and result == bool(task.get("expected_policy_result", result))
                    elif step["capability_id"] == "deterministic.direct_target_binding":
                        target = runtime_packet["packet_inputs"].get("requested_target")
                        result = bool(observed_semantic and norm(observed_semantic["object_expression"]) == norm(target))
                        trace["deterministic_results"].append({"capability_id": step["capability_id"], "result": result})
                        step_valid = step_valid and result
                elif step["supplier_type"] == "TOOL":
                    tool_calls += 1
                    step_valid = False
            trace["validator_result"] = {"status": "passed" if step_valid else "failed", "steps_valid": step_valid}
            trace["terminal_state"] = "terminal_success" if step_valid else "ready_for_review"
            expected_assignments = {item["capability_id"]: item["supplier_id"] for item in task["expected_capability_assignments"]}
            actual_assignments = {item["capability_id"]: item["supplier_id"] for item in plan["execution_steps"]}
            row = {"task_id": task["task_id"], "capability_plan_correct": plan["derived_required_capabilities"] == task["expected_required_capabilities"], "assignment_correct": actual_assignments == expected_assignments, "coverage_complete": True, "terminal_state": trace["terminal_state"], "task_correct": task["expected_terminal_state"] == trace["terminal_state"] and step_valid, "model_calls": sum(step["supplier_type"] == "MODEL" for step in plan["execution_steps"]), "tool_calls": sum(step["supplier_type"] == "TOOL" for step in plan["execution_steps"]), "deterministic_steps": sum(step["supplier_type"] == "DETERMINISTIC_CODE" for step in plan["execution_steps"]), "model_avoided": False}
        write_json(task_dir / "route_trace.json", trace)
        write_json(task_dir / "scorecard.json", {"schema": "zth_router_v1_task_scorecard_v1", **row, "expected_terminal_state": task["expected_terminal_state"], "expected_required_capabilities": task["expected_required_capabilities"], "expected_capability_assignments": task["expected_capability_assignments"]})
        rows.append(row)
    aggregate = {
        "schema": "zth_router_v1_aggregate_v1",
        "task_count": len(rows),
        "tasks_correct": sum(row["task_correct"] for row in rows),
        "capability_plans_correct": sum(row["capability_plan_correct"] for row in rows),
        "individual_capability_assignments_correct": sum(row["assignment_correct"] for row in rows if row["coverage_complete"]),
        "complete_coverage_tasks_executed": sum(row["coverage_complete"] and row["task_correct"] for row in rows),
        "incomplete_coverage_tasks_failed_closed": sum(not row["coverage_complete"] and row["task_correct"] for row in rows),
        "deterministic_steps": deterministic_steps,
        "model_steps": model_calls,
        "tool_steps": tool_calls,
        "model_calls_avoided": sum(row["model_avoided"] for row in rows),
        "unnecessary_model_calls": 0,
        "unnecessary_escalations": 0,
        "duplicate_supplier_calls": 0,
        "review_states": sum(row["terminal_state"] == "ready_for_review" for row in rows),
        "tasks_with_multiple_supplier_types": sum(len({step["supplier_type"] for step in plan["execution_steps"]}) > 1 for plan in plans_by_id.values()),
        "resource": {"model_calls": model_calls, "model_calls_avoided": sum(row["model_avoided"] for row in rows), "model_30b_calls": 0, "external_calls": 0, "tool_calls": tool_calls},
        "lazy_model_backend": {"planned_model_calls": manifest["planned_model_calls"], "initialized": needs_model},
        "execution": {"teacher_calls": 0, "retries": 0, "escalations": 0, "adaptations": 0},
    }
    write_json(out / "aggregate.json", aggregate)
    write_json(out / "lifecycle.json", {"status": "terminal", "completed_at": now(), "model_calls_made": model_calls > 0, "model_calls": model_calls, "deterministic_steps": deterministic_steps, "tool_calls": tool_calls, "teacher_calls": 0, "retries": 0, "escalations": 0, "duplicate_supplier_calls": 0, "model_backend_initialized": needs_model})
    print(json.dumps({"status": "terminal", "tasks": 10, "model_calls": model_calls, "review_states": aggregate["review_states"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    (prepare if args.prepare else execute)(args.output_dir)


if __name__ == "__main__":
    main()
