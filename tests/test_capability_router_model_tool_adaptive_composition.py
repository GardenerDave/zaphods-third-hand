import json
from pathlib import Path

from scripts import zth_capability_router_model_tool_adaptive_composition as router


def _task(task_id):
    return next(task for task in router.load_tasks() if task["task_id"] == task_id)


def test_model_free_freeze_has_four_model_plans_and_no_runtime_hints(tmp_path):
    binding = router.model_free_binding()
    assert len(binding["prepared"]) == 6
    assert sum(item["plan0"]["planned_model_calls"] for item in binding["prepared"]) == 4
    assert sum(item["plan0"]["overall_coverage"] == "INCOMPLETE" for item in binding["prepared"]) == 1
    for item in binding["prepared"]:
        runtime_text = json.dumps(item["runtime_task"])
        facts_text = json.dumps(item["facts0"])
        assert "expected_" not in runtime_text
        assert "required_capabilities" not in runtime_text
        assert "tool_capability_id" not in runtime_text
        assert "observation_requirement" not in runtime_text
        assert "expected_" not in facts_text
        assert "required_capabilities" not in facts_text
        assert item["contract0"]["contains_worked_answer"] is False


def test_semantic_output_derives_tool_only_after_exact_authorized_binding():
    task = _task("model-tool-001")
    triage, orchestration = router.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    runtime_task = {"task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"]}
    facts0 = router.build_planner_facts(runtime_task, triage, orchestration)
    plan0, _ = router.plan_capabilities(facts0, router.registry_index())
    assert plan0["derived_required_capabilities"] == [router.MODEL_CAPABILITY]
    semantic = {"action": "verify", "object_expression": "docs/README.md"}
    facts1 = router.build_planner_facts(runtime_task, triage, orchestration, semantic=semantic)
    plan1, _ = router.plan_capabilities(facts1, router.registry_index())
    assert plan1["derived_required_capabilities"] == [router.TOOL_CAPABILITY]
    assert plan1["execution_steps"][0]["input_provenance"]["authorized_targets"] == "ENVIRONMENT_AUTHORITY_RECORD"


def test_model_output_cannot_grant_authority_or_trigger_tool():
    task = _task("model-tool-004")
    triage, orchestration = router.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    runtime_task = {"task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"]}
    facts1 = router.build_planner_facts(runtime_task, triage, orchestration, semantic={"action": "verify", "object_expression": "docs/README.md"})
    plan1, _ = router.plan_capabilities(facts1, router.registry_index())
    assert plan1["overall_coverage"] == "INCOMPLETE"
    assert plan1["planned_tool_calls"] == 0
    assert any("outside" in reason for reason in plan1["unresolved_requirements"])


def test_observation_changes_plan_and_contract_evaluator_is_runtime_grounded():
    task = _task("model-tool-001")
    triage, orchestration = router.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    runtime_task = {"task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"]}
    semantic = {"action": "verify", "object_expression": "docs/README.md"}
    facts1 = router.build_planner_facts(runtime_task, triage, orchestration, semantic=semantic)
    plan1, _ = router.plan_capabilities(facts1, router.registry_index())
    true_observation = {"status": "VALID_OBSERVATION", "repository_relative_path": "docs/README.md", "exists": True, "is_file": True, "size_bytes": 1, "sha256": "0" * 64}
    false_observation = {**true_observation, "exists": False, "is_file": False, "size_bytes": None, "sha256": None}
    true_facts = router.build_planner_facts(runtime_task, triage, orchestration, semantic=semantic, observation=true_observation)
    false_facts = router.build_planner_facts(runtime_task, triage, orchestration, semantic=semantic, observation=false_observation)
    true_plan, _ = router.plan_capabilities(true_facts, router.registry_index())
    false_plan, _ = router.plan_capabilities(false_facts, router.registry_index())
    assert true_plan["derived_required_capabilities"] == ["deterministic.observation_exists_policy"]
    assert false_plan["derived_required_capabilities"] == ["deterministic.observation_absence_policy"]
    contract = router.build_success_contract(true_facts, true_plan)
    assert router.evaluate_success_contract(contract, {"validated_observation_present": True, "coverage_complete": True})["passed"]
    assert not router.evaluate_success_contract(contract, {"validated_observation_present": False, "coverage_complete": True})["passed"]


def test_missing_observation_cannot_be_assumed_and_duplicate_request_fails_closed():
    task = _task("model-tool-001")
    triage, orchestration = router.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    runtime_task = {"task_id": task["task_id"], "input_request": task["input_request"], "environment_facts": task["environment_facts"]}
    semantic = {"action": "verify", "object_expression": "docs/README.md"}
    facts1 = router.build_planner_facts(runtime_task, triage, orchestration, semantic=semantic)
    plan1, _ = router.plan_capabilities(facts1, router.registry_index())
    contract1 = router.build_success_contract(facts1, plan1)
    assert not router.evaluate_success_contract(contract1, {"semantic_contract_valid": True, "action": "verify", "object_expression": "docs/README.md", "tool_authority_valid": True, "tool_observation_schema_valid": False, "observation_path_matches_bound_target": False, "coverage_complete": True})["passed"]
    assert router.MAX_REPLANS == 2

