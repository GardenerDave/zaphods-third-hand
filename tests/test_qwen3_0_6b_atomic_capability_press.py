from scripts.zth_qwen3_0_6b_atomic_capability_press import score_object, target_metrics


REFERENCE = {
    "required_allowed_targets": ["a.json"],
    "required_held_targets": ["b.json", "c.json"],
    "requires_scope_expansion_flag": True,
    "review_status": "ready_for_review",
}


def test_target_metrics_precision_recall_and_exact_set() -> None:
    result = target_metrics(["a.json", "extra.json"], ["a.json"])
    assert result["exact_set_match"] is False
    assert result["true_positives"] == 1
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 0
    assert result["precision"] == 0.5
    assert result["recall"] == 1.0


def test_string_singleton_preserves_identity_but_not_type() -> None:
    score = score_object({
        "allowed_targets": "a.json",
        "held_targets": ["b.json", "c.json"],
        "scope_expansion_required": "true",
        "review_status": "ready_for_review",
    }, REFERENCE)
    assert score["allowed_targets"]["target_identity_semantically_usable"] is True
    assert score["allowed_targets"]["type_correct"] is False
    assert score["scope_expansion"]["correct"] is True
    assert score["scope_expansion"]["type_correct"] is False
    assert score["semantic_fields_correct"] == 4
    assert score["structural_contract_valid"] is False


def test_overlap_is_separate_from_target_identity() -> None:
    score = score_object({
        "allowed_targets": ["a.json"],
        "held_targets": ["a.json", "b.json", "c.json"],
        "scope_expansion_required": True,
        "review_status": "ready_for_review",
    }, REFERENCE)
    assert score["allowed_targets"]["exact_set_match"] is True
    assert score["held_targets"]["exact_set_match"] is False
    assert score["authority_separation"]["no_allowed_held_overlap"] is False
    assert score["structural_contract_valid"] is False


def test_empty_target_precision_is_none_and_recall_is_zero() -> None:
    result = target_metrics([], ["a.json"])
    assert result["precision"] is None
    assert result["recall"] == 0.0
