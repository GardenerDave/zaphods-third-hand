from scripts.zth_qwen3_1_7b_scope_field_name_isolation import validate_inputs


def test_field_name_isolation_is_balanced_and_rename_only() -> None:
    binding = validate_inputs()
    assert binding["audit"]["true_count"] == 8
    assert binding["audit"]["false_count"] == 8
    assert binding["field_rename_only"] is True
    assert sum(v == ["S", "N"] for v in binding["orders"].values()) == 8
    assert sum(v == ["N", "S"] for v in binding["orders"].values()) == 8
    assert binding["schema_sha256"]["S"] != binding["schema_sha256"]["N"]
    assert binding["formats"]["N"]["json_schema"]["name"] == binding["formats"]["S"]["json_schema"]["name"]
    assert binding["formats"]["N"]["json_schema"]["schema"] == {
        "type": "object",
        "properties": {"decision_flag": {"type": "boolean"}},
        "required": ["decision_flag"],
        "additionalProperties": False,
    }


def test_field_name_prompts_have_no_worked_boolean_examples() -> None:
    binding = validate_inputs()
    for arm_prompts in binding["prompts"].values():
        for prompt in arm_prompts.values():
            lowered = prompt.casefold()
            assert '"scope_expansion_required": true' not in lowered
            assert '"scope_expansion_required": false' not in lowered
            assert '"decision_flag": true' not in lowered
            assert '"decision_flag": false' not in lowered
