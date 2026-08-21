from scripts.zth_qwen3_1_7b_generic_boolean_selection_prior import (
    FT_RULE, PROMPT_SUFFIX, STRUCTURED_SCHEMA, TF_RULE, schema_allows_both,
    validate_inputs,
)


def test_generic_manifest_balance_and_no_scope_terminology() -> None:
    b = validate_inputs()
    assert len(b["tasks"]) == 16
    assert b["scope_terminology_findings"] == 0
    assert b["payload"]["marker_mapping"] == {"KAPPA-7": True, "LAMBDA-4": False}


def test_rule_order_diff_preserves_mapping() -> None:
    assert TF_RULE.split("\n\n") == ["decision_flag is true when the marker code is KAPPA-7.", "decision_flag is false when the marker code is LAMBDA-4."]
    assert FT_RULE.split("\n\n") == list(reversed(TF_RULE.split("\n\n")))
    assert "decision_flag" in PROMPT_SUFFIX


def test_schema_is_symmetric_and_value_neutral() -> None:
    assert schema_allows_both() is True
    assert STRUCTURED_SCHEMA["properties"] == {"decision_flag": {"type": "boolean"}}
