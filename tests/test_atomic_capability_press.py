from local_harness.atomic_capability_press import (
    compare_components,
    component_vector,
    score_scope_object,
    target_metrics,
)


REFERENCE = {
    "required_allowed_targets": ["allowed.json"],
    "required_held_targets": ["held.json"],
    "requires_scope_expansion_flag": True,
    "review_status": "ready_for_review",
}


def valid_object() -> dict:
    return {
        "allowed_targets": ["allowed.json"],
        "held_targets": ["held.json"],
        "scope_expansion_required": True,
        "review_status": "ready_for_review",
    }


def test_exact_target_tp_fp_fn_and_empty_precision() -> None:
    scored = target_metrics(["allowed.json", "extra.json"], ["allowed.json"])
    assert scored["true_positives"] == 1
    assert scored["false_positives"] == 1
    assert scored["false_negatives"] == 0
    assert scored["precision"] == 0.5
    assert scored["recall"] == 1.0
    empty = target_metrics([], ["allowed.json"])
    assert empty["precision"] is None
    assert empty["recall"] == 0.0


def test_representation_error_preserves_literal_identity_without_passing() -> None:
    value = valid_object()
    value["allowed_targets"] = "allowed.json"
    scored = score_scope_object(value, REFERENCE)
    assert scored["allowed_targets"]["target_identity_semantically_usable"] is True
    assert scored["allowed_targets"]["type_correct"] is False
    assert scored["structural_contract_valid"] is False


def test_expansion_direction_and_vacuous_observability() -> None:
    false_positive = valid_object()
    false_positive["scope_expansion_required"] = False
    scored_fp = score_scope_object(false_positive, {**REFERENCE, "requires_scope_expansion_flag": False})
    assert scored_fp["scope_expansion"]["false_positive"] is False
    scored_fp = score_scope_object(false_positive, REFERENCE)
    assert scored_fp["scope_expansion"]["false_negative"] is True
    assert scored_fp["scope_expansion"]["false_positive"] is False
    true_positive_against_false = valid_object()
    scored_fp = score_scope_object(true_positive_against_false, {**REFERENCE, "requires_scope_expansion_flag": False})
    assert scored_fp["scope_expansion"]["false_positive"] is True
    missing = score_scope_object(None, REFERENCE)
    assert missing["authority_separation"]["no_allowed_held_overlap"] is None
    assert missing["scope_expansion"]["correct"] is None


def test_status_exact_mismatch_is_not_normalized() -> None:
    value = valid_object()
    value["review_status"] = "ready"
    scored = score_scope_object(value, REFERENCE)
    assert scored["review_status"]["exact_match"] is False
    assert scored["review_status"]["confusion_pair"] == "ready_for_review -> ready"


def test_semantic_profile_covers_zero_through_four() -> None:
    profiles = []
    for mutation in [
        {"allowed_targets": ["wrong.json"], "held_targets": ["wrong-held.json"], "scope_expansion_required": False, "review_status": "hold"},
        {"allowed_targets": ["wrong.json"]},
        {"allowed_targets": ["wrong.json"], "held_targets": ["wrong-held.json"]},
        {"allowed_targets": ["wrong.json"], "held_targets": ["held.json"], "scope_expansion_required": True},
        valid_object(),
    ]:
        value = valid_object()
        value.update(mutation)
        profiles.append(score_scope_object(value, REFERENCE)["semantic_fields_correct"])
    assert profiles == [0, 3, 2, 3, 4]


def test_paired_classifier_improved_regressed_mixed_unchanged() -> None:
    def pair(before, after):
        return compare_components(before, after)["classification"]

    same = {"x": True, "semantic_fields_correct": 2}
    improved = {"x": False, "semantic_fields_correct": 1}
    better = {"x": True, "semantic_fields_correct": 3}
    worse = {"x": False, "semantic_fields_correct": 0}
    assert pair(same, same) == "UNCHANGED"
    assert pair(improved, better) == "IMPROVED"
    assert pair(better, improved) == "REGRESSED"
    assert pair(improved, {"x": True, "semantic_fields_correct": 0}) == "MIXED"


def test_repair_delta_identifies_scope_only_repair() -> None:
    before = valid_object()
    before["scope_expansion_required"] = False
    after = valid_object()
    delta = compare_components(
        component_vector(score_scope_object(before, REFERENCE), parse_valid=True),
        component_vector(score_scope_object(after, REFERENCE), parse_valid=True),
    )
    assert delta["classification"] == "IMPROVED"
    assert "scope_expansion_correctness" in delta["improvements"]
    assert delta["regressions"] == []
