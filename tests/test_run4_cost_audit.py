from __future__ import annotations

import copy

from local_harness.run4_cost_audit import (
    COST_AWARE_INTERVENTIONS,
    enumerate_cost_choice_sets,
    immediate_action_cost,
    summarize_cost_choice_sets,
)


WEIGHTS = {
    "worker_time_ms": 10.0,
    "local_teacher_time_ms": 20.0,
    "external_teacher_time_ms": 40.0,
}


def _card(source: str, signature: dict, task_ids: list[str], rescued: list[str]) -> dict:
    return {
        "identity": {"intervention_type": source, "intervention_id": source},
        "context": {"source_runs": ["run1"], "task_family": signature["task_family"], "failure_signature": signature},
        "observations": {
            "eligible_task_opportunities": len(task_ids),
            "eligible_attempts": len(task_ids),
            "valid_model_attempts": len(task_ids),
            "successes": len(rescued),
            "failures": len(task_ids) - len(rescued),
            "task_ids": task_ids,
            "rescued_task_ids": rescued,
            "rescued_tasks": len(rescued),
            "teacher_call_count": 0,
        },
        "provenance": {"source_runs": ["run1"], "source_commits": [], "artifacts": []},
    }


def test_immediate_cost_includes_resulting_worker_retry():
    assert immediate_action_cost("deterministic_patch_retry", WEIGHTS) == 10.0
    assert immediate_action_cost("local_teacher", WEIGHTS) == 30.0
    assert immediate_action_cost("external_teacher", WEIGHTS) == 50.0


def test_choice_set_includes_absent_interventions_as_insufficient():
    signature = {"task_family": "family", "structural": ["parse_json"], "semantic": []}
    bundle = {"cards": [_card("deterministic_patch_retry", signature, ["a", "b", "c"], ["a", "b"])]}
    audit = enumerate_cost_choice_sets(bundle, {"weights": WEIGHTS})
    choices = audit["choice_sets"][0]["choices"]
    assert {choice["intervention"] for choice in choices} == set(COST_AWARE_INTERVENTIONS)
    assert next(choice for choice in choices if choice["intervention"] == "local_teacher")["evidence_status"] == "insufficient"


def test_cost_choice_distribution_and_lower_success_cheaper_case():
    signature = {"task_family": "family", "structural": ["parse_json"], "semantic": []}
    bundle = {"cards": [
        _card("deterministic_patch_retry", signature, ["a", "b", "c"], ["a", "b"]),
        _card("external_teacher", signature, ["a", "b", "c"], ["a", "b", "c"]),
    ]}
    summary = summarize_cost_choice_sets(enumerate_cost_choice_sets(bundle, {"weights": WEIGHTS}))
    assert summary["evidence_key_count"] == 4
    assert summary["supported_positive_choice_distribution"] == {"zero": 0, "one": 0, "two": 4, "three_or_more": 0}
    assert summary["cost_can_change_supported_choice_count"] == 4
    assert summary["cheaper_supported_alternative_with_lower_empirical_success"] == 4


def test_audit_does_not_mutate_bundle():
    signature = {"task_family": "family", "structural": [], "semantic": ["reference_uncertainty"]}
    bundle = {"cards": [_card("local_teacher", signature, ["a"], ["a"])]}
    before = copy.deepcopy(bundle)
    enumerate_cost_choice_sets(bundle, {"weights": WEIGHTS})
    assert bundle == before
