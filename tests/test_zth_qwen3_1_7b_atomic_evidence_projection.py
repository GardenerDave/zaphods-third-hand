from scripts.zth_qwen3_1_7b_atomic_evidence_projection import load_binding


def test_projection_preserves_frozen_tasks_and_hides_irrelevant_factors() -> None:
    binding = load_binding()
    assert len(binding["tasks"]) == 16
    assert sum(task["expected_target_allowed"] for task in binding["tasks"]) == 8
    assert sum(task["expected_operation_allowed"] for task in binding["tasks"]) == 8
    assert sum(order == ["target_allowed", "operation_allowed"] for order in binding["orders"].values()) == 8
    assert sum(order == ["operation_allowed", "target_allowed"] for order in binding["orders"].values()) == 8
    for prompt in binding["prompts"]["target_allowed"].values():
        lowered = prompt.casefold()
        assert "allowed_operations" not in lowered
        assert "requested_operation" not in lowered
        assert "held_distractor" not in lowered
        assert "target_factor" not in lowered
        assert "operation_factor" not in lowered
    for prompt in binding["prompts"]["operation_allowed"].values():
        lowered = prompt.casefold()
        assert "allowed_targets" not in lowered
        assert "requested_target" not in lowered
        assert "held_distractor" not in lowered
        assert "target_factor" not in lowered
        assert "operation_factor" not in lowered


def test_projection_has_no_worked_boolean_or_scope_contract_cues() -> None:
    binding = load_binding()
    for prompt_set in binding["prompts"].values():
        for prompt in prompt_set.values():
            lowered = prompt.casefold()
            assert "scope_expansion_required" not in lowered
            assert "scope expansion" not in lowered
            assert '"target_allowed": true' not in lowered
            assert '"target_allowed": false' not in lowered
            assert '"operation_allowed": true' not in lowered
            assert '"operation_allowed": false' not in lowered
