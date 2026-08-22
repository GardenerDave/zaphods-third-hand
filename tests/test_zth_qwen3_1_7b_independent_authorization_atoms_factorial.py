from scripts.zth_qwen3_1_7b_independent_authorization_atoms_factorial import load_binding


def test_independent_factorial_balance_and_deterministic_scope_rule() -> None:
    binding = load_binding()
    tasks = binding["tasks"]
    assert len(tasks) == 16
    assert sum(task["expected_target_allowed"] for task in tasks) == 8
    assert sum(task["expected_operation_allowed"] for task in tasks) == 8
    assert set(binding["cells"].values()) == {4}
    assert set(binding["cells3"].values()) == {2}
    assert sum(order == ["target_allowed", "operation_allowed"] for order in binding["orders"].values()) == 8
    assert sum(order == ["operation_allowed", "target_allowed"] for order in binding["orders"].values()) == 8
    for task in tasks:
        derived = binding["derived"][task["task_id"]]
        assert derived["expected_scope_expansion_required"] == (not (derived["expected_target_allowed"] and derived["expected_operation_allowed"]))


def test_atoms_are_independent_membership_judgments_and_prompts_are_neutral() -> None:
    binding = load_binding()
    target_values = [row["expected_target_allowed"] for row in binding["derived"].values()]
    operation_values = [row["expected_operation_allowed"] for row in binding["derived"].values()]
    assert len(set(target_values)) == 2
    assert len(set(operation_values)) == 2
    for prompt_set in binding["prompts"].values():
        for prompt in prompt_set.values():
            lowered = prompt.casefold()
            assert "scope_expansion_required" not in lowered
            assert "scope expansion" not in lowered
            assert '"target_allowed": true' not in lowered
            assert '"target_allowed": false' not in lowered
            assert '"operation_allowed": true' not in lowered
            assert '"operation_allowed": false' not in lowered
