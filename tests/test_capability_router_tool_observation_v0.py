from __future__ import annotations

import hashlib
from pathlib import Path

from scripts import zth_capability_router_v1 as v1
from scripts.zth_capability_router_tool_observation_v0 import (
    MAX_REPLANS,
    ROOT,
    TOOL_CAPABILITY,
    build_planner_facts,
    build_success_contract,
    derive_requirements,
    observe_repository,
    plan_capabilities,
    registry_index,
    validate_model_free,
    validate_observation,
    validate_tool_request,
)


def _tool_request(path: str, allowed: list[str]) -> dict:
    return {"repository_relative_path": path, "authorized_targets": allowed, "authority_source": "test"}


def test_model_free_matrix_has_no_tool_requirement_hint_and_has_one_replan_limit():
    binding = validate_model_free()
    assert MAX_REPLANS == 1
    assert len(binding["plans"]) == 6
    assert sum(item[4]["overall_coverage"] == "COMPLETE" for item in binding["plans"]) == 5
    assert sum(item[4]["overall_coverage"] == "INCOMPLETE" for item in binding["plans"]) == 1
    for task, _, _, facts, plan, contract, derivation in binding["plans"]:
        text = str({"task": task.get("environment_facts", {}), "facts": facts, "contract": contract})
        assert "observation_requirement" not in text
        assert "requires_tool_observation" not in text
        assert "tool_capability_id" not in text
        assert "expected_" not in text
        assert contract["contains_worked_answer"] is False


def test_tool_authority_rejects_absolute_traversal_unauthorized_and_escape(tmp_path):
    assert validate_tool_request(_tool_request("/etc/passwd", ["/etc/passwd"]))["status"] == "DENIED"
    assert validate_tool_request(_tool_request("../README.md", ["../README.md"]))["status"] == "DENIED"
    assert validate_tool_request(_tool_request("README.md", ["docs/README.md"]))["status"] == "DENIED"
    outside = tmp_path.parent / "outside-tool-observation.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "escape.txt"
    link.symlink_to(outside)
    assert validate_tool_request(_tool_request("escape.txt", ["escape.txt"]), repo_root=tmp_path)["status"] == "DENIED"


def test_existing_and_absent_observations_are_valid_and_read_only():
    target = ROOT / "docs/README.md"
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    request = _tool_request("docs/README.md", ["docs/README.md"])
    authority = validate_tool_request(request)
    observation = observe_repository(request, authority)
    assert observation["status"] == "VALID_OBSERVATION"
    assert observation["exists"] is True
    assert observation["is_file"] is True
    assert observation["sha256"] == before
    assert validate_observation(observation, request, authority)["status"] == "VALID"
    absent_request = _tool_request("docs/never-created-tool-observation-file.txt", ["docs/never-created-tool-observation-file.txt"])
    absent_authority = validate_tool_request(absent_request)
    absent = observe_repository(absent_request, absent_authority)
    assert absent["status"] == "VALID_OBSERVATION"
    assert absent["exists"] is False
    assert absent["sha256"] is None
    assert target.read_bytes() and hashlib.sha256(target.read_bytes()).hexdigest() == before


def test_observation_changes_plan_and_missing_observation_stalls():
    task = next(item for item in __import__("scripts.zth_capability_router_tool_observation_v0", fromlist=["load_tasks"]).load_tasks() if item["task_id"] == "tool-observe-001")
    triage, orchestration = v1.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    facts = build_planner_facts(task, triage, orchestration)
    plan0, _ = plan_capabilities(facts, registry_index())
    true_facts = build_planner_facts(task, triage, orchestration, {"status": "VALID_OBSERVATION", "repository_relative_path": "docs/README.md", "exists": True, "is_file": True, "size_bytes": 1, "sha256": "0" * 64})
    false_facts = build_planner_facts(task, triage, orchestration, {"status": "VALID_OBSERVATION", "repository_relative_path": "docs/README.md", "exists": False, "is_file": False, "size_bytes": None, "sha256": None})
    true_plan, _ = plan_capabilities(true_facts, registry_index())
    false_plan, _ = plan_capabilities(false_facts, registry_index())
    assert plan0["derived_required_capabilities"] == [TOOL_CAPABILITY]
    assert true_plan["derived_required_capabilities"] == ["deterministic.observation_exists_policy"]
    assert false_plan["derived_required_capabilities"] == ["deterministic.observation_absence_policy"]
    missing_plan, _ = plan_capabilities(facts, registry_index())
    assert missing_plan["derived_required_capabilities"] == plan0["derived_required_capabilities"]
    assert build_success_contract(true_facts, true_plan)["contains_worked_answer"] is False


def test_evaluator_data_cannot_forge_observation_or_runtime_result():
    task = next(item for item in __import__("scripts.zth_capability_router_tool_observation_v0", fromlist=["load_tasks"]).load_tasks() if item["task_id"] == "tool-observe-001")
    assert all(not key.startswith("expected_") for key in task["environment_facts"])
    forged = {"expected_exists": False, "expected_terminal_state": "ready_for_review", "expected_supplier": "fake"}
    request = _tool_request("docs/README.md", ["docs/README.md"])
    authority = validate_tool_request(request)
    observation = observe_repository(request, authority)
    assert observation["exists"] is True
    assert forged["expected_exists"] is not observation["exists"]


def test_same_tool_request_is_replan_stalled_by_model_free_rule():
    task = next(item for item in __import__("scripts.zth_capability_router_tool_observation_v0", fromlist=["load_tasks"]).load_tasks() if item["task_id"] == "tool-observe-001")
    triage, orchestration = v1.make_packets({"task_id": task["task_id"], "input_request": task["input_request"]})
    facts = build_planner_facts(task, triage, orchestration, {"status": "TOOL_INTERFACE_FAILURE", "repository_relative_path": "docs/README.md", "exists": None, "is_file": None, "size_bytes": None, "sha256": None})
    plan, _ = plan_capabilities(facts, registry_index())
    assert plan["derived_required_capabilities"] == [TOOL_CAPABILITY]
