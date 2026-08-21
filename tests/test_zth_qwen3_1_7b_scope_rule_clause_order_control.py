from scripts.zth_qwen3_1_7b_scope_rule_clause_order_control import (
    validate_inputs, rules, rule_diff,
)


def test_scope_task_and_interface_bindings_are_fixed() -> None:
    b = validate_inputs()
    assert len(b["tasks"]) == 16
    assert b["audit"]["true_count"] == 8
    assert b["audit"]["false_count"] == 8
    assert b["audit"]["answer_leakage_findings"] == 0
    assert b["schema_sha256"] == "5b9aef0b84726bd3ad42147d84d73d332e69241966301aeb5b4f0dc5881193c5"


def test_only_first_two_semantic_clauses_are_reordered() -> None:
    tf, ft = rules()
    tf_parts, ft_parts = tf.split("\n\n"), ft.split("\n\n")
    assert tf_parts[2] == ft_parts[2]
    assert tf_parts[:2] == list(reversed(ft_parts[:2]))
    assert rule_diff(tf, ft)


def test_temporal_arm_order_is_balanced() -> None:
    b = validate_inputs()
    assert sum(order == ["TF", "FT"] for order in b["orders"].values()) == 8
    assert sum(order == ["FT", "TF"] for order in b["orders"].values()) == 8
