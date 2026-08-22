from scripts.zth_qwen3_1_7b_operation_membership_lexical_counterbalance import load_binding


def test_lexical_counterbalance_and_pairs() -> None:
    binding = load_binding()
    assert len(binding["tasks"]) == 16
    assert len(binding["pairs"]) == 8
    assert all(value == {"member": 2, "non_member": 2, "allowed_set": 8} for value in binding["token_counts"].values())
    assert all(len(task["allowed_operations"]) == 2 for task in binding["tasks"])
    assert sum(value == "member_then_nonmember" for value in binding["orders"].values()) == 8
    assert sum(value == "nonmember_then_member" for value in binding["orders"].values()) == 8
    for pair in binding["pairs"]:
        member = binding["by_id"][pair["member_task_id"]]
        nonmember = binding["by_id"][pair["non_member_task_id"]]
        assert member["requested_operation"] == nonmember["requested_operation"]
        assert member["expected_operation_allowed"] is True
        assert nonmember["expected_operation_allowed"] is False


def test_prompts_are_operation_only_and_value_neutral() -> None:
    binding = load_binding()
    for prompt in binding["prompts"].values():
        lowered = prompt.casefold()
        assert "allowed_targets" not in lowered
        assert "requested_target" not in lowered
        assert "held_distractor" not in lowered
        assert "scope" not in lowered
        assert "authority" not in lowered
        assert '"operation_allowed": true' not in lowered
        assert '"operation_allowed": false' not in lowered
