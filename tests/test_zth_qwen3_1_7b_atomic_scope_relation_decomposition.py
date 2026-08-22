from scripts.zth_qwen3_1_7b_atomic_scope_relation_decomposition import load_binding


def test_fixture_decomposition_is_supported_and_recombines_exactly() -> None:
    binding = load_binding()
    assert binding["audit"]["true_count"] == 8
    assert binding["audit"]["false_count"] == 8
    assert all(row["deterministic_scope_from_atoms"] == row["expected_scope_expansion_required"] for row in binding["decomp"]["tasks"])
    assert sum(order == ["target_authorized", "operation_authorized"] for order in binding["orders"].values()) == 8
    assert sum(order == ["operation_authorized", "target_authorized"] for order in binding["orders"].values()) == 8


def test_atomic_prompts_are_scope_neutral_and_symmetric() -> None:
    binding = load_binding()
    for prompts in binding["prompts"].values():
        for prompt in prompts.values():
            lowered = prompt.casefold()
            assert "scope_expansion_required" not in lowered
            assert "scope expansion" not in lowered
            assert '"target_authorized": true' not in lowered
            assert '"target_authorized": false' not in lowered
            assert '"operation_authorized": true' not in lowered
            assert '"operation_authorized": false' not in lowered
