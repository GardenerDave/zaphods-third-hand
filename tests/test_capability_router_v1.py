from __future__ import annotations

from scripts.zth_capability_router_v1 import (
    derive_required_capabilities,
    index_registry,
    load_registry,
    load_tasks,
    plan_capabilities,
    validate_model_free,
)


def test_v1_plans_from_packet_facts_not_expectations():
    binding = validate_model_free()
    task, runtime_packet, plan = next(item for item in binding["plans"] if item[0]["task_id"] == "router-v1-003")
    original = list(plan["derived_required_capabilities"])
    task["expected_required_capabilities"] = ["tool.fake_expectation_only"]
    task["expected_capability_assignments"] = []
    assert derive_required_capabilities(runtime_packet) == original
    assert plan_capabilities(runtime_packet, binding["registry_index"])["derived_required_capabilities"] == original


def test_registry_preserves_multiple_suppliers_and_prefers_deterministic():
    registry = load_registry()
    index = index_registry(registry)
    synthetic = list(index["deterministic.direct_target_binding"]) + [{
        "capability_id": "deterministic.direct_target_binding",
        "supplier_id": "synthetic_model",
        "supplier_type": "MODEL",
        "interface_id": "synthetic",
        "status": "QUALIFIED_EXPLORATORY",
    }]
    index["deterministic.direct_target_binding"] = synthetic
    runtime_packet = {"task_id": "synthetic", "packet_inputs": {"requires_target_binding": True}, "packet_source": {"triage_id": "t", "orchestration_id": "o"}}
    plan = plan_capabilities(runtime_packet, index)
    assert len(plan["capabilities"][0]["candidate_suppliers"]) == 2
    assert plan["capabilities"][0]["selected_supplier"]["supplier_type"] == "DETERMINISTIC_CODE"


def test_incomplete_coverage_has_no_executable_model_steps():
    binding = validate_model_free()
    task, runtime_packet, plan = next(item for item in binding["plans"] if item[0]["task_id"] == "router-v1-009")
    assert plan["overall_coverage"] == "INCOMPLETE"
    assert plan["planned_model_calls"] == 0
    assert plan["execution_steps"] == []


def test_all_deterministic_and_review_workloads_are_lazy_model_free():
    binding = validate_model_free()
    selected = {"router-v1-001", "router-v1-002", "router-v1-007", "router-v1-009", "router-v1-010"}
    assert all(plan["planned_model_calls"] == 0 for task, _, plan in binding["plans"] if task["task_id"] in selected)
    assert len(load_tasks()) == 10
