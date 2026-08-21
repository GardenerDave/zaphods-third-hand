from __future__ import annotations

from scripts.zth_qwen3_1_7b_neutral_constrained_scope_probe import (
    PROMPT_SUFFIX,
    STRUCTURED_SCHEMA,
    no_worked_boolean_object,
    schema_allows_both,
    validate_inputs,
)


def test_structure_only_schema_allows_both_boolean_values() -> None:
    assert schema_allows_both() is True
    prop = STRUCTURED_SCHEMA["properties"]["scope_expansion_required"]
    assert prop == {"type": "boolean"}
    assert all(key not in str(STRUCTURED_SCHEMA) for key in ("const", "default", "example", "examples", "enum"))


def test_neutral_prompt_has_no_worked_boolean_object() -> None:
    assert no_worked_boolean_object(PROMPT_SUFFIX) is True
    assert '{"scope_expansion_required": true}' not in PROMPT_SUFFIX
    assert '{"scope_expansion_required": false}' not in PROMPT_SUFFIX


def test_frozen_factorial_bindings_remain_balanced_and_leakage_free() -> None:
    binding = validate_inputs()
    assert len(binding["tasks"]) == 16
    assert binding["audit"]["answer_leakage_findings"] == 0
    assert binding["audit"]["true_count"] == 8
    assert binding["audit"]["false_count"] == 8
