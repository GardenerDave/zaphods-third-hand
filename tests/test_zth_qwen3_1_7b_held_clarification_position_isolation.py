from scripts.zth_qwen3_1_7b_held_clarification_position_isolation import validate_inputs


def test_clarification_arms_are_balanced_and_l_is_exact_control() -> None:
    binding = validate_inputs()
    assert binding["audit"]["true_count"] == 8
    assert binding["audit"]["false_count"] == 8
    assert all(binding["prompts"][t["task_id"]]["L"].endswith("A held or out-of-scope target that is not required to complete the requested operation does not by itself satisfy the predicate.") for t in binding["tasks"])
    assert max(binding["permutation_counts"].values()) - min(binding["permutation_counts"].values()) <= 1
    assert sum(v == ["L", "M", "A"] for v in binding["orders"].values()) == binding["permutation_counts"]["L-M-A"]


def test_clarification_diffs_are_restricted() -> None:
    binding = validate_inputs()
    assert len(binding["schema_sha256"]) == 64
    assert len(binding["response_format_sha256"]) == 64
    assert all('"scope_expansion_required": true' not in p.casefold() and '"scope_expansion_required": false' not in p.casefold() for row in binding["prompts"].values() for p in row.values())
    assert binding["clarification"]
