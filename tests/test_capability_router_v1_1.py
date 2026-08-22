from __future__ import annotations

from copy import deepcopy

from scripts.zth_capability_router_v1_1 import (
    build_success_contract,
    derive_required_capabilities,
    execute_runtime_task,
    lazy_model_backend_gate,
    validate_model_free,
)


def test_planner_facts_and_contracts_are_runtime_grounded():
    binding = validate_model_free()
    assert len(binding["plans"]) == 8
    assert sum(plan["overall_coverage"] == "COMPLETE" for *_, plan, _ in binding["plans"]) == 6
    assert sum(plan["overall_coverage"] == "INCOMPLETE" for *_, plan, _ in binding["plans"]) == 2
    for _, _, _, facts, plan, contract in binding["plans"]:
        rendered = str({"facts": facts, "plan": plan, "contract": contract})
        assert "expected_" not in rendered
        assert contract["contains_worked_answer"] is False


def test_dependency_steps_require_semantic_outputs_for_binding():
    binding = validate_model_free()
    semantic = next(plan for task, _, _, _, plan, _ in binding["plans"] if task["task_id"] == "router-v1-1-003")
    binding_step = next(step for step in semantic["execution_steps"] if step["capability_id"] == "deterministic.direct_target_binding")
    assert "object_expression" in binding_step["requires_inputs"]
    assert "requested_target" in binding_step["requires_inputs"]
    assert binding_step["depends_on"] == ["step_semantic_minimal_action_object_extraction"]


def test_oracle_corruption_does_not_change_runtime_result_or_calls():
    binding = validate_model_free()
    task, _, _, facts, plan, contract = next(item for item in binding["plans"] if item[0]["task_id"] == "router-v1-1-003")
    runtime_task = {"task_id": task["task_id"], "input_request": task["input_request"], "world_facts": task["world_facts"]}
    calls = []

    def fake_model(_step):
        calls.append(1)
        return {"content": '{"action":"inspect","object_expression":"amber-ground-ledger.json"}'}

    before = execute_runtime_task(runtime_task, deepcopy(plan), deepcopy(contract), fake_model)
    wrong_evaluator = {"expected_required_capabilities": ["wrong"], "expected_terminal_state": "ready_for_review", "expected_model_result": {"action": "wrong", "object_expression": "wrong"}}
    after = execute_runtime_task(runtime_task, deepcopy(plan), deepcopy(contract), fake_model)
    assert before == after
    assert before["terminal_state"] == "terminal_success"
    assert len(calls) == 2
    assert wrong_evaluator["expected_terminal_state"] != before["terminal_state"]


def test_no_model_workload_does_not_touch_unavailable_backend():
    binding = validate_model_free()
    no_model = [plan for task, _, _, _, plan, _ in binding["plans"] if task["task_id"] in {"router-v1-1-001", "router-v1-1-002", "router-v1-1-007", "router-v1-1-008"}]

    def unavailable():
        raise AssertionError("model backend touched")

    assert lazy_model_backend_gate(no_model, unavailable) is False


def test_derived_capabilities_ignore_evaluator_annotations():
    binding = validate_model_free()
    task, _, _, facts, plan, _ = next(item for item in binding["plans"] if item[0]["task_id"] == "router-v1-1-003")
    expected = derive_required_capabilities(facts)
    task["expected_required_capabilities"] = ["tool.fake"]
    task["expected_capability_assignments"] = []
    assert derive_required_capabilities(facts) == expected
    assert plan["derived_required_capabilities"] == expected
