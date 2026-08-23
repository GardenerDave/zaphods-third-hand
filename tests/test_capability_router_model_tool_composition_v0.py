import json

from scripts import zth_capability_router_model_tool_composition_v0 as router


def test_fresh_slice_is_model_free_and_separates_runtime_expectations():
    binding = router.model_free_binding()
    assert len(binding["prepared"]) == 6
    assert router.MAX_REPLANS == 2
    assert sum(item["plan0"]["planned_model_calls"] for item in binding["prepared"]) == 4
    for item in binding["prepared"]:
        runtime_text = json.dumps(item["runtime_task"])
        facts_text = json.dumps(item["facts0"])
        assert "expected_" not in runtime_text
        assert "required_capabilities" not in runtime_text
        assert "tool_capability_id" not in runtime_text
        assert "observation_requirement" not in runtime_text
        assert "expected_" not in facts_text


def test_authority_provenance_and_unsafe_semantic_target_fail_closed():
    task = next(item for item in router.load_tasks() if item["task_id"] == "composition-v0-004")
    triage, orchestration = router.engine.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    runtime_task = {"task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"]}
    facts = router.build_planner_facts(runtime_task, triage, orchestration, semantic={"action": "inspect", "object_expression": "docs/README.md"})
    plan, _ = router.plan_capabilities(facts, router.registry_index())
    assert plan["overall_coverage"] == "INCOMPLETE"
    assert plan["planned_tool_calls"] == 0
    assert any("outside" in reason for reason in plan["unresolved_requirements"])


def test_contract_evaluator_fails_without_observation():
    task = next(item for item in router.load_tasks() if item["task_id"] == "composition-v0-001")
    triage, orchestration = router.engine.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    runtime_task = {"task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"]}
    semantic = {"action": "inspect", "object_expression": "docs/README.md"}
    facts = router.build_planner_facts(runtime_task, triage, orchestration, semantic=semantic)
    plan, _ = router.plan_capabilities(facts, router.registry_index())
    contract = router.engine.build_success_contract(facts, plan)
    state = {"semantic_contract_valid": True, "action": "inspect", "object_expression": "docs/README.md", "tool_authority_valid": True, "tool_observation_schema_valid": False, "observation_path_matches_bound_target": False, "coverage_complete": True}
    assert router.evaluate_success_contract(contract, state)["passed"] is False
