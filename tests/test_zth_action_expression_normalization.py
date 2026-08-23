from scripts import zth_qwen3_1_7b_action_expression_normalization as probe


def test_frozen_normalizer_rules_are_explicit_and_fail_closed():
    presence = "Determine whether docs/example.txt exists right now."
    direct = "Inspect docs/example.txt."
    assert probe.normalize_operation_expression("determine", presence)["canonical_operation"] == "observe_presence"
    assert probe.normalize_operation_expression("EXISTS", presence)["canonical_operation"] == "observe_presence"
    assert probe.normalize_operation_expression("inspect", direct)["canonical_operation"] == "inspect"
    assert probe.normalize_operation_expression("archive", direct)["status"] == "UNRESOLVED"
    assert probe.normalize_operation_expression("check", "Check and inspect docs/example.txt.")["status"] == "AMBIGUOUS"
    assert probe.normalize_operation_expression("", presence)["status"] == "UNRESOLVED"


def test_direct_operations_do_not_collapse_to_presence():
    for expression in ("inspect", "amend", "index", "dispatch"):
        result = probe.normalize_operation_expression(expression, expression.capitalize() + " docs/example.txt.")
        assert result["status"] == "NORMALIZED"
        assert result["canonical_operation"] != "observe_presence"


def test_model_free_historical_projection_recovers_bounded_canonical_meaning():
    projection = probe.historical_projection()
    assert projection["baseline_canonical_correct"] == 8
    assert projection["patched_canonical_correct"] == 4
    assert projection["historical_scores_unchanged"] is True


def test_semantic_invariants_pass_without_calls():
    checks = probe.invariants()
    assert checks["pass"] is True
    assert checks["model_calls"] == 0
    assert checks["teacher_calls"] == 0
    assert checks["tool_calls"] == 0


def test_context_gating_is_explicit_and_fail_closed():
    presence = "Check whether docs/example.txt is present right now."
    non_presence = "Inspect docs/example.txt."
    assert probe.derive_normalization_context(presence) == "PRESENCE_OBSERVATION_CONTEXT"
    assert probe.derive_normalization_context(non_presence) == "DIRECT_OPERATION_CONTEXT"
    assert probe.normalize_operation_expression("find", presence)["canonical_operation"] == "observe_presence"
    assert probe.normalize_operation_expression("exists", non_presence)["status"] == "UNRESOLVED"
    assert probe.normalize_operation_expression("check", "Check and inspect docs/example.txt.")["status"] == "AMBIGUOUS"
    assert probe.normalize_operation_expression("inspect", "Unknown request about docs/example.txt.")["status"] == "UNRESOLVED"
