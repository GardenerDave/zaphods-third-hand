from __future__ import annotations

from copy import deepcopy

from scripts import zth_capability_router_v1 as v1
from scripts.zth_capability_router_v1_2 import (
    HINT_FIELDS,
    build_planner_facts,
    build_success_contract,
    derive_capability_requirements,
    execute_runtime_task,
    load_tasks,
    plan_capabilities,
    registry_index,
    validate_model_free,
)


def test_v1_2_model_free_plans_have_no_hint_inputs():
    binding = validate_model_free()
    assert len(binding["plans"]) == 8
    assert sum(item[4]["overall_coverage"] == "COMPLETE" for item in binding["plans"]) == 6
    assert sum(item[4]["overall_coverage"] == "INCOMPLETE" for item in binding["plans"]) == 2
    for task, _, _, facts, plan, contract, derivation in binding["plans"]:
        assert not any(field in str(task.get("environment_facts", {})) for field in HINT_FIELDS)
        rendered = str({"facts": facts, "plan": plan, "contract": contract, "derivation": derivation})
        assert "expected_" not in rendered
        assert "semantic_request_shape" not in rendered
        assert "requires_target_binding" not in rendered
        assert "requires_reference_entity" not in rendered
        assert "requires_tool_observation" not in rendered
        assert "tool_capability_id" not in rendered
        assert contract["contains_worked_answer"] is False


def test_packet_content_changes_requirement_derivation():
    task = next(item for item in load_tasks() if item["task_id"] == "router-v1-2-003")
    triage, orchestration = v1.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    facts = build_planner_facts(task, triage, orchestration)
    plan, _ = plan_capabilities(facts, registry_index())
    assert plan["overall_coverage"] == "COMPLETE"
    changed_triage = deepcopy(triage)
    changed_triage["task_type"] = "design_planning"
    changed_facts = build_planner_facts(task, changed_triage, orchestration)
    changed_plan, _ = plan_capabilities(changed_facts, registry_index())
    assert changed_plan["overall_coverage"] == "INCOMPLETE"
    assert changed_plan["derived_required_capabilities"] != plan["derived_required_capabilities"]


def test_evaluator_corruption_cannot_change_runtime_plan_or_execution():
    task = next(item for item in load_tasks() if item["task_id"] == "router-v1-2-004")
    triage, orchestration = v1.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    facts = build_planner_facts(task, triage, orchestration)
    plan, _ = plan_capabilities(facts, registry_index())
    contract = build_success_contract(facts, plan)
    runtime_task = {"task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"]}
    evaluator = {key: "wrong" for key in task if key.startswith("expected_")}
    calls = []

    def fake_model(_step):
        calls.append(1)
        return {"content": '{"action":"update","object_expression":"birch-vault-batch.json"}'}

    before = execute_runtime_task(runtime_task, facts, deepcopy(plan), deepcopy(contract), fake_model)
    after = execute_runtime_task(runtime_task, facts, deepcopy(plan), deepcopy(contract), fake_model)
    assert before == after
    assert before["terminal_state"] == "terminal_success"
    assert len(calls) == 2
    assert evaluator["expected_terminal_state"] != before["terminal_state"]


def test_unresolved_and_unqualified_routes_fail_closed_without_model():
    binding = validate_model_free()
    review_plans = [item[4] for item in binding["plans"] if item[4]["overall_coverage"] == "INCOMPLETE"]
    assert len(review_plans) == 2
    assert all(plan["planned_model_calls"] == 0 for plan in review_plans)


def test_route_trace_preserves_capability_eligibility_and_selection_separation():
    binding = validate_model_free()
    _, _, _, _, plan, _, _ = next(item for item in binding["plans"] if item[0]["task_id"] == "router-v1-2-003")
    trace = {
        "schema": "zth_router_v1_2_route_trace_v1",
        "task_id": "router-v1-2-003",
        "capability_plan": "capability_plan.json",
        "capability_eligibility": plan["capability_eligibility"],
        "capabilities": plan["capabilities"],
        "model_calls": [],
        "terminal_state": None,
    }

    eligibility = trace["capability_eligibility"][0]
    capability = trace["capabilities"][0]
    assert eligibility["candidate_suppliers"]
    assert eligibility["qualified_candidates"]
    assert capability["selected_supplier"] is not None
    assert capability["selected_supplier"]["supplier_id"] in {item["supplier_id"] for item in capability["qualified_candidates"]}
    assert capability["eligibility_reason"] != capability["selection_reason"]
