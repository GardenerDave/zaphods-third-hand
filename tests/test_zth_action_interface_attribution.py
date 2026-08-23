from scripts import zth_qwen3_1_7b_action_interface_attribution as probe
from scripts import zth_qwen3_1_7b_action_expression_normalization as norm


def test_fresh_holdout_is_balanced_and_model_free():
    tasks = probe.holdout()
    assert len(tasks) == 12
    assert sum(t["regime"] == "PRESENCE_OBSERVATION" for t in tasks) == 4
    assert sum(t["regime"].startswith("DIRECT_") for t in tasks) == 4
    assert sum(t["regime"] == "AMBIGUOUS" for t in tasks) == 2
    assert sum(t["regime"] == "UNSUPPORTED" for t in tasks) == 2
    assert all(probe.deterministic_availability(t) for t in tasks)


def test_context_gate_and_shared_normalizer_are_model_free():
    assert norm.invariants()["pass"]
    task = probe.holdout()[0]
    assert norm.normalize_operation_expression("find", task["input_request"])["canonical_operation"] == "observe_presence"
    assert norm.normalize_operation_expression("exists", "Inspect docs/example.txt.")["status"] == "UNRESOLVED"
    assert norm.normalize_operation_expression("inspect", "Check and inspect docs/example.txt.")["status"] == "AMBIGUOUS"


def test_old_and_new_contracts_are_distinct_but_downstream_input_is_same():
    assert set(probe.OLD_SCHEMA["required"]) == {"action", "object_expression"}
    assert set(probe.NEW_SCHEMA["required"]) == {"action_expression", "object_expression"}
    assert probe.prompt_for(probe.holdout()[0], "old") != probe.prompt_for(probe.holdout()[0], "new")
    assert probe.schema_for("old") is probe.OLD_SCHEMA
    assert probe.schema_for("new") is probe.NEW_SCHEMA


def test_model_freeze_has_zero_calls_and_same_normalizer():
    checks = probe.model_free_checks()
    assert checks["normalizer_invariants_pass"]
    assert checks["MODEL_CALLS_MADE"] == 0
    assert checks["TEACHER_CALLS_MADE"] == 0
    assert checks["TOOL_CALLS_MADE"] == 0
    assert checks["same_downstream_normalizer"] is True
    assert checks["evaluator_separate"] is True
