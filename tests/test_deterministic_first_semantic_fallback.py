from scripts import zth_deterministic_first_semantic_fallback as probe
from scripts import zth_qwen3_1_7b_action_expression_normalization as normalizer


def test_fresh_matrix_is_balanced_and_target_derivation_is_model_free():
    task_rows = probe.tasks()
    assert len(task_rows) == 12
    assert sum(t["regime"] == "DETERMINISTIC_SUFFICIENT" for t in task_rows) == 6
    assert sum(t["regime"] == "SEMANTIC_FALLBACK_REQUIRED" for t in task_rows) == 4
    assert sum(t["regime"] == "FAIL_CLOSED" for t in task_rows) == 2
    assert all(probe.extract_target(t["input_request"]) == t["expected_requested_target"] for t in task_rows)


def test_deterministic_first_derivation_never_calls_model():
    rows = {t["task_id"]: probe.operation_derivation(t["input_request"]) for t in probe.tasks()}
    assert sum(r["status"] == "RESOLVED" for r in rows.values()) == 6
    assert sum(r["model_required"] for r in rows.values()) == 4
    assert rows["dff-011"]["status"] == "AMBIGUOUS"
    assert rows["dff-012"]["status"] == "UNSUPPORTED"


def test_fallback_expression_uses_same_context_gated_normalizer():
    fallback = probe.tasks()[6]
    assert normalizer.derive_normalization_context(fallback["input_request"]) == "PRESENCE_OBSERVATION_CONTEXT"
    result = normalizer.normalize_operation_expression("check", fallback["input_request"])
    assert result["status"] == "NORMALIZED"
    assert result["canonical_operation"] == "observe_presence"


def test_model_free_plan_has_no_model_for_deterministic_tasks():
    binding = probe.model_free_prepare(probe.ROOT / ".work" / "deterministic_first_test_prepare")
    deterministic = [item for item in binding["prepared"] if item[0]["regime"] == "DETERMINISTIC_SUFFICIENT"]
    fallback = [item for item in binding["prepared"] if item[0]["regime"] == "SEMANTIC_FALLBACK_REQUIRED"]
    assert all(item[6]["planned_model_calls"] == 0 for item in deterministic)
    assert all(item[6]["planned_model_calls"] == 1 for item in fallback)
    assert binding["model_calls"] == 4
    assert binding["tool_calls_planned"] == 6
