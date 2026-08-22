import json
from pathlib import Path

from scripts import zth_qwen3_1_7b_fact_extraction_deterministic_scope as probe


def test_expected_manifest_and_policy_are_model_free():
    binding = probe.validate_model_free()
    assert len(binding["tasks"]) == 16
    assert sum(row["expected_scope_expansion_required"] for row in binding["derived"]) == 8
    assert sum(not row["expected_scope_expansion_required"] for row in binding["derived"]) == 8
    assert all(row["deterministic_scope_from_facts"] == row["expected_scope_expansion_required"] for row in binding["derived"])
    assert binding["schema"]["additionalProperties"] is False
    assert set(binding["schema"]["properties"]) == set(probe.FIELDS)
    assert set(binding["derived_by_id"]) == {task["task_id"] for task in binding["tasks"]}
    for task in binding["tasks"]:
        row = binding["derived_by_id"][task["task_id"]]
        assert row["task_id"] == task["task_id"]
        assert row["expected_scope_expansion_required"] == task["expected_scope_expansion_required"]


def test_execute_time_task_lookup_and_score_extraction():
    binding = probe.validate_model_free()
    inside = binding["derived_by_id"]["cross-scope-001"]
    outside = binding["derived_by_id"]["cross-scope-003"]
    inside_observed = {
        "authorized_target": "ledger-a.json",
        "requested_target": "ledger-a.json",
        "authorized_operation": "read",
        "requested_operation": "read",
    }
    outside_observed = {
        "authorized_target": "ledger-b.json",
        "requested_target": "change-record-b.json",
        "authorized_operation": "read",
        "requested_operation": "read",
    }
    inside_score = probe.score_extraction(inside_observed, inside, True, True)
    outside_score = probe.score_extraction(outside_observed, outside, True, True)
    assert inside_score["all_four_fields_correct"] is True
    assert inside_score["derived_scope_expansion_required"] is False
    assert inside_score["derived_scope_correct"] is True
    assert outside_score["all_four_fields_correct"] is True
    assert outside_score["derived_scope_expansion_required"] is True
    assert outside_score["derived_scope_correct"] is True


def test_extraction_prompt_has_no_decision_cues():
    binding = probe.validate_model_free()
    prompts = "\n".join(binding["prompts"].values()).casefold()
    assert "scope_expansion_required" not in prompts
    assert "scope expansion" not in prompts
    assert '"true"' not in prompts
    assert '"false"' not in prompts
    assert "target allowed" not in prompts
    assert "operation allowed" not in prompts
