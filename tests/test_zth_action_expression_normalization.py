from scripts import zth_qwen3_1_7b_action_expression_normalization as probe


def test_frozen_normalizer_rules_are_explicit_and_fail_closed():
    assert probe.normalize_operation_expression("determine")["canonical_operation"] == "observe_presence"
    assert probe.normalize_operation_expression("EXISTS")["canonical_operation"] == "observe_presence"
    assert probe.normalize_operation_expression("inspect")["canonical_operation"] == "inspect"
    assert probe.normalize_operation_expression("archive")["status"] == "UNRESOLVED"
    assert probe.normalize_operation_expression("check and inspect")["status"] == "AMBIGUOUS"
    assert probe.normalize_operation_expression("")["status"] == "UNRESOLVED"


def test_direct_operations_do_not_collapse_to_presence():
    for expression in ("inspect", "amend", "index", "dispatch"):
        result = probe.normalize_operation_expression(expression)
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
