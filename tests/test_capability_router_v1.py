from __future__ import annotations

from scripts.zth_capability_router_v1 import (
    derive_required_capabilities,
    eligible_suppliers_for_capability,
    index_registry,
    load_registry,
    load_tasks,
    lazy_model_backend_gate,
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
    assert plan["capability_eligibility"][0]["eligibility_status"] == "ELIGIBLE"
    assert len(plan["capabilities"][0]["candidate_suppliers"]) == 2
    assert plan["capabilities"][0]["selected_supplier"]["supplier_type"] == "DETERMINISTIC_CODE"
    assert plan["capabilities"][0]["eligibility_reason"] == "At least one QUALIFIED_EXPLORATORY supplier exists in the registry."


def test_eligible_suppliers_are_projected_from_eligibility_evidence_only():
    record = {
        "candidate_suppliers": [
            {"supplier_id": "eligible", "supplier_type": "MODEL", "interface_id": "i1", "status": "QUALIFIED_EXPLORATORY"},
            {"supplier_id": "ineligible", "supplier_type": "TOOL", "interface_id": "i2", "status": "NOT_QUALIFIED"},
        ]
    }
    projected = eligible_suppliers_for_capability(record)
    assert [item["supplier_id"] for item in projected] == ["eligible"]
    assert projected[0]["status"] == "QUALIFIED_EXPLORATORY"


def test_ineligible_supplier_cannot_reach_selection(monkeypatch):
    registry = load_registry()
    index = index_registry(registry)
    index["deterministic.direct_target_binding"] = [
        {
            "capability_id": "deterministic.direct_target_binding",
            "supplier_id": "qualified_model",
            "supplier_type": "MODEL",
            "interface_id": "synthetic_model",
            "status": "QUALIFIED_EXPLORATORY",
        },
        {
            "capability_id": "deterministic.direct_target_binding",
            "supplier_id": "blocked_tool",
            "supplier_type": "TOOL",
            "interface_id": "synthetic_tool",
            "status": "NOT_QUALIFIED",
        },
    ]
    runtime_packet = {
        "task_id": "synthetic",
        "packet_inputs": {"requires_target_binding": True},
        "packet_source": {"triage_id": "t", "orchestration_id": "o"},
    }

    def guarded_select(candidates):
        assert all(candidate["status"] == "QUALIFIED_EXPLORATORY" for candidate in candidates)
        return candidates[0], "guarded"

    monkeypatch.setattr("scripts.zth_capability_router_v1.select_supplier", guarded_select)
    plan = plan_capabilities(runtime_packet, index)
    assert plan["capabilities"][0]["selected_supplier"]["supplier_id"] == "qualified_model"


def test_mixed_candidates_expose_both_in_eligibility_and_only_eligible_reach_selection(monkeypatch):
    registry = load_registry()
    index = index_registry(registry)
    index["deterministic.direct_target_binding"] = [
        {
            "capability_id": "deterministic.direct_target_binding",
            "supplier_id": "qualified_model",
            "supplier_type": "MODEL",
            "interface_id": "synthetic_model",
            "status": "QUALIFIED_EXPLORATORY",
        },
        {
            "capability_id": "deterministic.direct_target_binding",
            "supplier_id": "blocked_tool",
            "supplier_type": "TOOL",
            "interface_id": "synthetic_tool",
            "status": "NOT_QUALIFIED",
        },
    ]
    runtime_packet = {
        "task_id": "synthetic",
        "packet_inputs": {"requires_target_binding": True},
        "packet_source": {"triage_id": "t", "orchestration_id": "o"},
    }
    seen = {}

    def guarded_select(candidates):
        seen["supplier_ids"] = [candidate["supplier_id"] for candidate in candidates]
        return candidates[0], "guarded"

    monkeypatch.setattr("scripts.zth_capability_router_v1.select_supplier", guarded_select)
    plan = plan_capabilities(runtime_packet, index)
    eligibility = plan["capability_eligibility"][0]
    assert {item["supplier_id"] for item in eligibility["candidate_suppliers"]} == {"qualified_model", "blocked_tool"}
    assert {item["supplier_id"] for item in eligibility["qualified_candidates"]} == {"qualified_model"}
    assert seen["supplier_ids"] == ["qualified_model"]
    assert plan["capabilities"][0]["selected_supplier"]["supplier_id"] == "qualified_model"


def test_incomplete_coverage_has_no_executable_model_steps():
    binding = validate_model_free()
    task, runtime_packet, plan = next(item for item in binding["plans"] if item[0]["task_id"] == "router-v1-009")
    assert plan["overall_coverage"] == "INCOMPLETE"
    assert plan["planned_model_calls"] == 0
    assert plan["execution_steps"] == []
    assert any(item["eligibility_status"] == "INELIGIBLE" for item in plan["capability_eligibility"])
    assert any("No QUALIFIED_EXPLORATORY supplier exists" in item["eligibility_reason"] for item in plan["capability_eligibility"])


def test_no_eligible_suppliers_produces_no_execution_step_and_explicit_reason(monkeypatch):
    registry = load_registry()
    index = index_registry(registry)
    index["deterministic.direct_target_binding"] = [
        {
            "capability_id": "deterministic.direct_target_binding",
            "supplier_id": "blocked_tool",
            "supplier_type": "TOOL",
            "interface_id": "synthetic_tool",
            "status": "NOT_QUALIFIED",
        }
    ]
    runtime_packet = {
        "task_id": "synthetic",
        "packet_inputs": {"requires_target_binding": True},
        "packet_source": {"triage_id": "t", "orchestration_id": "o"},
    }
    called = False

    def fail_if_called(candidates):
        nonlocal called
        called = True
        raise AssertionError("selection should not run without eligible suppliers")

    monkeypatch.setattr("scripts.zth_capability_router_v1.select_supplier", fail_if_called)
    plan = plan_capabilities(runtime_packet, index)
    assert called is False
    assert plan["overall_coverage"] == "INCOMPLETE"
    assert plan["execution_steps"] == []
    assert plan["capabilities"][0]["selected_supplier"] is None
    assert plan["capabilities"][0]["coverage_status"] == "UNCOVERED"
    assert plan["capabilities"][0]["selection_reason"] == "No eligible suppliers were admitted by capability eligibility."


def test_all_deterministic_and_review_workloads_are_lazy_model_free():
    binding = validate_model_free()
    selected = {"router-v1-001", "router-v1-002", "router-v1-007", "router-v1-009", "router-v1-010"}
    assert all(plan["planned_model_calls"] == 0 for task, _, plan in binding["plans"] if task["task_id"] in selected)
    assert len(load_tasks()) == 10


def test_lazy_backend_gate_does_not_touch_unavailable_endpoint_for_no_model_plans():
    binding = validate_model_free()
    no_model_plans = [plan for task, _, plan in binding["plans"] if task["task_id"] in {"router-v1-001", "router-v1-002", "router-v1-007", "router-v1-009", "router-v1-010"}]
    def unavailable_endpoint():
        raise AssertionError("unavailable model endpoint was touched")
    assert lazy_model_backend_gate(no_model_plans, unavailable_endpoint) is False
