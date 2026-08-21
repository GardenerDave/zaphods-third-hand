from scripts.zth_qwen3_1_7b_single_predicate_scope_probe import PREDICATE_TEXT, validate_inputs


def test_single_predicate_is_value_neutral_and_balanced() -> None:
    binding = validate_inputs()
    assert len(binding["tasks"]) == 16
    assert binding["audit"]["true_count"] == 8
    assert binding["audit"]["false_count"] == 8
    text = "\n".join(binding["prompts"].values()).casefold()
    assert text.count("evaluate this predicate:") == 16
    assert "is true when" not in text
    assert "is false when" not in text
    assert PREDICATE_TEXT


def test_single_predicate_has_no_worked_boolean_exemplars() -> None:
    binding = validate_inputs()
    assert all('"scope_expansion_required": true' not in p.casefold() for p in binding["prompts"].values())
    assert all('"scope_expansion_required": false' not in p.casefold() for p in binding["prompts"].values())
