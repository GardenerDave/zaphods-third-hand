import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/research/QWEN3_1_7B_TEACHING_INTERVENTION_FAILURE_DIAGNOSIS_MATRIX_2026-08-23.json"


def load_matrix():
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def test_diagnosis_preserves_mixed_failure_and_zero_call_boundary():
    matrix = load_matrix()
    assert matrix["calls_made_in_this_diagnosis"] == {"model": 0, "teacher": 0, "tool": 0, "retries": 0}
    assert matrix["classification"]["teacher_diagnosis_supported"] is True
    assert matrix["classification"]["intervention_design_error"] is True
    assert matrix["classification"]["interface_ontology_error"] is True
    assert matrix["classification"]["evaluator_or_scorer_error"] is False
    assert matrix["classification"]["mixed"] is True


def test_safe_binding_is_not_exact_competence():
    matrix = load_matrix()
    rows = matrix["task_rows"]
    assert sum(row["baseline_safe_binding"] for row in rows) == 3
    assert sum(row["patched_safe_binding"] for row in rows) == 6
    assert sum(row["patched_action_exact"] for row in rows) == 1
    assert any(row["patched_safe_binding"] and not row["patched_action_exact"] for row in rows)


def test_patch_overgeneralization_is_observable_without_rescoring():
    matrix = load_matrix()
    assert {row["patched_action"] for row in matrix["task_rows"]} == {"check"}
    assert matrix["validation"]["intervention_safety_validation_passed"] is True
    assert matrix["validation"]["intervention_semantic_invariant_validation_demonstrated"] is False
    assert matrix["next_decision"] == "TEST_ACTION_EXPRESSION_PLUS_DETERMINISTIC_OPERATION_NORMALIZATION"
