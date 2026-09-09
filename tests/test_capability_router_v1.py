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


def synthetic_packet() -> dict:
    return {
        "task_id": "synthetic",
        "packet_inputs": {"semantic_request_shape": "single_action_object"},
        "packet_source": {"triage_id": "t", "orchestration_id": "o"},
    }


def synthetic_model_index(status: str = "QUALIFIED_EXPLORATORY", *, worker_binding_ref: str | None = "router") -> dict:
    entry = {
        "capability_id": "semantic.minimal_action_object_extraction",
        "supplier_id": "router_supplier",
        "supplier_type": "MODEL",
        "interface_id": "minimal_action_object_v0",
        "status": status,
    }
    if worker_binding_ref is not None:
        entry["worker_binding_ref"] = worker_binding_ref
    return {
        "semantic.minimal_action_object_extraction": [
            entry
        ]
    }


def fleet_snapshot(*, binding_status: str = "VERIFIED", availability: str = "AVAILABLE", failure_class: str = "binding_verified", advertised_models: list[str] | None = None) -> dict:
    advertised_models = advertised_models or ["Qwen_Qwen3-1.7B-Q4_K_M.gguf"]
    return {
        "schema": "zth_local_fleet_snapshot_v1",
        "generated_at": "2026-09-08T00:00:01+00:00",
        "workers": [
            {
                "worker": "router",
                "configured_base_url": "http://127.0.0.1:8081/v1",
                "expected_model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
                "binding_status": binding_status,
                "availability": availability,
                "advertised_models": advertised_models,
                "failure_class": failure_class,
                "checked_at": "2026-09-08T00:00:00+00:00",
                "freshness": {"state": "fresh", "age_seconds": 1.0, "stale": False},
                "evidence": {
                    "preflight": {
                        "schema": "zth_worker_binding_preflight_v1",
                        "worker": "router",
                        "configured_base_url": "http://127.0.0.1:8081/v1",
                        "expected_model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
                        "endpoint_status": "ok" if advertised_models else "error",
                        "advertised_models": advertised_models,
                        "binding_status": binding_status,
                        "failure_class": failure_class,
                        "reason": "fixture",
                        "checked_at": "2026-09-08T00:00:00+00:00",
                        "evidence": {"models_url": "http://127.0.0.1:8081/v1/models", "http_status": 200, "response_sha256": "0" * 64},
                    }
                },
            }
        ],
    }


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


def test_route_trace_preserves_capability_eligibility_and_selection_separation():
    binding = validate_model_free()
    task, runtime_packet, plan = next(item for item in binding["plans"] if item[0]["task_id"] == "router-v1-003")
    trace = {
        "schema": "zth_router_v1_route_trace_v1",
        "task_id": task["task_id"],
        "capability_plan": "capability_plan.json",
        "capability_eligibility": plan["capability_eligibility"],
        "capabilities": plan["capabilities"],
        "selected_steps": plan["execution_steps"],
        "model_calls": [],
        "tool_calls": [],
        "deterministic_results": [],
        "validator_result": None,
        "terminal_state": None,
    }

    eligibility = trace["capability_eligibility"][0]
    capability = trace["capabilities"][0]
    assert eligibility["candidate_suppliers"]
    assert eligibility["qualified_candidates"]
    assert capability["selected_supplier"] is not None
    assert capability["selected_supplier"]["supplier_id"] in {item["supplier_id"] for item in capability["qualified_candidates"]}
    assert capability["eligibility_reason"] != capability["selection_reason"]
    assert trace["selected_steps"][0]["supplier_id"] == capability["selected_supplier"]["supplier_id"]


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


def test_capable_live_worker_is_executable_with_supplied_fleet_snapshot():
    plan = plan_capabilities(synthetic_packet(), synthetic_model_index(), fleet_snapshot=fleet_snapshot())
    capability = plan["capabilities"][0]
    assert plan["overall_coverage"] == "COMPLETE"
    assert plan["overall_execution_status"] == "EXECUTABLE"
    assert plan["execution_steps"][0]["supplier_id"] == "router_supplier"
    assert capability["availability_constraints"][0]["availability_status"] == "AVAILABLE"
    assert capability["selected_supplier_availability"]["worker"] == "router"
    assert capability["selected_supplier_availability"]["mapping_source"] == "explicit_worker_binding_ref"
    assert capability["selected_supplier_availability"]["advertised_models"] == ["Qwen_Qwen3-1.7B-Q4_K_M.gguf"]


def test_capable_offline_worker_remains_capability_eligible_but_not_executable():
    snapshot = fleet_snapshot(binding_status="UNVERIFIED", availability="UNAVAILABLE", failure_class="connection_refused", advertised_models=[])
    plan = plan_capabilities(synthetic_packet(), synthetic_model_index(), fleet_snapshot=snapshot)
    capability = plan["capabilities"][0]
    assert plan["capability_eligibility"][0]["eligibility_status"] == "ELIGIBLE"
    assert plan["capability_eligibility"][0]["qualified_candidates"][0]["supplier_id"] == "router_supplier"
    assert plan["capability_eligibility"][0]["qualified_candidates"][0]["worker_binding_ref"] == "router"
    assert plan["overall_coverage"] == "COMPLETE"
    assert plan["overall_execution_status"] == "BLOCKED_BY_AVAILABILITY"
    assert plan["execution_steps"] == []
    assert capability["coverage_status"] == "COVERED"
    assert capability["availability_constraints"][0]["availability_status"] == "UNAVAILABLE"
    assert capability["availability_constraints"][0]["failure_class"] == "connection_refused"


def test_live_but_capability_ineligible_worker_does_not_become_eligible():
    plan = plan_capabilities(synthetic_packet(), synthetic_model_index("NOT_QUALIFIED"), fleet_snapshot=fleet_snapshot())
    assert plan["capability_eligibility"][0]["eligibility_status"] == "INELIGIBLE"
    assert plan["overall_coverage"] == "INCOMPLETE"
    assert plan["overall_execution_status"] == "INCOMPLETE_CAPABILITY"
    assert plan["execution_steps"] == []


def test_live_explicitly_bound_but_capability_ineligible_worker_remains_ineligible():
    plan = plan_capabilities(synthetic_packet(), synthetic_model_index("NOT_QUALIFIED", worker_binding_ref="router"), fleet_snapshot=fleet_snapshot())
    assert plan["capability_eligibility"][0]["candidate_suppliers"][0]["worker_binding_ref"] == "router"
    assert plan["capability_eligibility"][0]["eligibility_status"] == "INELIGIBLE"
    assert plan["capabilities"][0]["availability_constraints"] == []
    assert plan["execution_steps"] == []


def test_transport_preflight_failure_does_not_mutate_capability_history():
    snapshot = fleet_snapshot(binding_status="UNVERIFIED", availability="UNAVAILABLE", failure_class="transport_timeout", advertised_models=[])
    plan = plan_capabilities(synthetic_packet(), synthetic_model_index(), fleet_snapshot=snapshot)
    candidate = plan["capability_eligibility"][0]["candidate_suppliers"][0]
    assert candidate["status"] == "QUALIFIED_EXPLORATORY"
    assert plan["capabilities"][0]["availability_constraints"][0]["failure_class"] == "transport_timeout"
    assert plan["overall_execution_status"] == "BLOCKED_BY_AVAILABILITY"


def test_binding_identity_mismatch_is_surfaced_without_negative_capability_evidence():
    snapshot = fleet_snapshot(binding_status="UNVERIFIED", availability="AVAILABLE", failure_class="expected_model_not_advertised", advertised_models=["wrong-model"])
    plan = plan_capabilities(synthetic_packet(), synthetic_model_index(), fleet_snapshot=snapshot)
    availability = plan["capabilities"][0]["availability_constraints"][0]
    assert plan["capability_eligibility"][0]["eligibility_status"] == "ELIGIBLE"
    assert availability["availability_status"] == "BINDING_IDENTITY_MISMATCH"
    assert availability["advertised_models"] == ["wrong-model"]
    assert plan["execution_steps"] == []


def test_supplied_fleet_snapshot_is_deterministic_and_no_live_probe_is_required(monkeypatch):
    monkeypatch.setattr("local_harness.binding_preflight.preflight_worker_binding", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live preflight must not run")))
    first = plan_capabilities(synthetic_packet(), synthetic_model_index(), fleet_snapshot=fleet_snapshot())
    second = plan_capabilities(synthetic_packet(), synthetic_model_index(), fleet_snapshot=fleet_snapshot())
    assert first == second


def test_legacy_callers_without_fleet_snapshot_keep_capability_only_execution_semantics():
    plan = plan_capabilities(synthetic_packet(), synthetic_model_index())
    capability = plan["capabilities"][0]
    assert plan["availability_source"] == "not_supplied_legacy"
    assert plan["overall_coverage"] == "COMPLETE"
    assert plan["overall_execution_status"] == "EXECUTABLE"
    assert capability["availability_constraints"][0]["availability_status"] == "NOT_SUPPLIED"
    assert capability["availability_constraints"][0]["execution_status"] == "LEGACY_UNCONSTRAINED"
    assert plan["execution_steps"][0]["supplier_id"] == "router_supplier"


def test_missing_explicit_binding_does_not_guess_from_model_identity():
    index = synthetic_model_index(worker_binding_ref=None)
    index["semantic.minimal_action_object_extraction"][0]["supplier_id"] = "qwen3_1_7b_labeled_2_032b_minimal_atom"
    plan = plan_capabilities(synthetic_packet(), index, fleet_snapshot=fleet_snapshot())
    availability = plan["capabilities"][0]["availability_constraints"][0]
    assert plan["overall_coverage"] == "COMPLETE"
    assert plan["overall_execution_status"] == "BLOCKED_BY_AVAILABILITY"
    assert availability["availability_status"] == "UNKNOWN"
    assert availability["mapping_source"] == "none"
    assert plan["execution_steps"] == []


def test_same_model_on_multiple_workers_does_not_create_implicit_mapping():
    snapshot = fleet_snapshot()
    snapshot["workers"].append({**snapshot["workers"][0], "worker": "alternate-router"})
    plan = plan_capabilities(synthetic_packet(), synthetic_model_index(worker_binding_ref=None), fleet_snapshot=snapshot)
    availability = plan["capabilities"][0]["availability_constraints"][0]
    assert availability["availability_status"] == "UNKNOWN"
    assert availability["mapping_source"] == "none"
    assert plan["execution_steps"] == []
