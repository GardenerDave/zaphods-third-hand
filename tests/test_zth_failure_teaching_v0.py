import json

from scripts import zth_capability_router_failure_teaching_v0 as teaching


def test_preserved_failure_localizes_without_replay():
    loc = teaching.localize_failure()
    assert loc["task_id"] == "composition-v0-003"
    assert loc["failed_field"] == "action"
    assert loc["observed_value"] == "exists"
    assert loc["failure_class"] == "ACTION_OPERATION_STATE_PREDICATE_CONFUSION"
    assert loc["raw_evidence_unchanged"] is True


def test_teacher_packet_has_no_holdout_material():
    packet = teaching.teacher_packet(teaching.localize_failure())
    text = json.dumps(packet).casefold()
    assert packet["holdout_material_included"] is False
    assert "teach-holdout" not in text
    assert "expected_action" not in text


def test_patch_validation_is_bounded_and_does_not_promote():
    patch = {
        "failure_mechanism": "state predicate selected as action",
        "intervention_type": "PROMPT_PATCH",
        "target_capability": teaching.CAPABILITY,
        "target_interface": teaching.INTERFACE,
        "patch_instruction": "Treat action as the operation requested by the clause; do not use a state predicate as the action.",
        "intended_effect": "Keep operation extraction distinct from state description.",
        "must_not_change": ["object_expression"],
        "regression_risks": ["overconstraining action vocabulary"],
    }
    validation = teaching.validate_patch(patch)
    assert validation["valid"] is True
    assert validation["qualification_change"] is False


def test_fresh_holdout_is_balanced_and_fresh():
    tasks = teaching.fresh_holdout()
    assert len(tasks) == 8
    assert sum(t["regime"] == "OPERATION_VS_STATE_PREDICATE" for t in tasks) == 4
    assert sum(t["regime"] == "DIRECT_OPERATION_CONTROL" for t in tasks) == 4
    assert all("composition-v0" not in t["input_request"] for t in tasks)
