"""Reusable, model-free atomic capability scoring primitives.

This module scores preserved response values only.  It never calls a model and
never writes evidence trees.  Task-family-specific readers should supply the
reference facts; these primitives do not assume that every task family is a
scope-authority task.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCOPE_FIELDS = (
    "allowed_targets",
    "held_targets",
    "scope_expansion_required",
    "review_status",
)


def target_metrics(observed: Any, expected: list[str]) -> dict[str, Any]:
    """Score literal target identities without repairing representation."""
    expected_set = set(expected)
    type_correct = isinstance(observed, list) and all(isinstance(x, str) for x in observed)
    identity_usable = False
    if type_correct:
        observed_set = set(observed)
        identity_usable = True
    elif isinstance(observed, str):
        # A singleton literal can preserve identity diagnostically, but it is
        # never treated as a valid list-valued field.
        observed_set = {observed}
        identity_usable = len(expected) == 1 and observed == expected[0]
    else:
        observed_set = set()
    tp = len(observed_set & expected_set)
    fp = len(observed_set - expected_set)
    fn = len(expected_set - observed_set)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "exact_set_match": observed_set == expected_set,
        "exact_set_and_type_match": observed_set == expected_set and type_correct,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "type_correct": type_correct,
        "target_identity_semantically_usable": identity_usable,
        "observed_literal_set": sorted(observed_set),
        "expected_set": sorted(expected_set),
    }


def score_scope_object(obj: Any, reference: Mapping[str, Any]) -> dict[str, Any]:
    """Score one four-field scope object with explicit observability states."""
    is_object = isinstance(obj, dict)
    present = is_object and all(key in obj for key in SCOPE_FIELDS)
    allowed = obj.get("allowed_targets") if is_object else None
    held = obj.get("held_targets") if is_object else None
    expansion = obj.get("scope_expansion_required") if is_object else None
    review = obj.get("review_status") if is_object else None
    allowed_m = target_metrics(allowed, list(reference["required_allowed_targets"]))
    held_m = target_metrics(held, list(reference["required_held_targets"]))
    allowed_set = set(allowed_m["observed_literal_set"])
    held_set = set(held_m["observed_literal_set"])
    overlap = sorted(allowed_set & held_set)
    expected_expansion = bool(reference["requires_scope_expansion_flag"])
    if isinstance(expansion, bool):
        expansion_intent, expansion_type = expansion, True
    elif isinstance(expansion, str) and expansion in {"true", "false"}:
        expansion_intent, expansion_type = expansion == "true", False
    else:
        expansion_intent, expansion_type = None, False
    expansion_correct = (
        expansion_intent is not None and expansion_intent == expected_expansion
    )
    field_types = {
        "allowed_targets": allowed_m["type_correct"],
        "held_targets": held_m["type_correct"],
        "scope_expansion_required": isinstance(expansion, bool),
        "review_status": isinstance(review, str),
    }
    semantic_vector = {
        "allowed_targets": allowed_m["exact_set_match"],
        "held_targets": held_m["exact_set_match"],
        "scope_expansion_required": expansion_correct,
        "review_status": isinstance(review, str) and review == reference["review_status"],
    }
    tags: list[str] = []
    if not is_object:
        tags.append("missing_structured_object")
    if is_object and not present:
        tags.append("missing_required_field")
    if is_object and not all(field_types.values()):
        tags.append("type_or_representation_error")
    if overlap:
        tags.append("allowed_held_overlap")
    if not allowed_m["exact_set_match"]:
        tags.append("allowed_target_mismatch")
    if not held_m["exact_set_match"]:
        tags.append("held_target_mismatch")
    if expansion_intent is None:
        tags.append("scope_expansion_uninterpretable")
    elif not expansion_correct:
        tags.append("scope_expansion_false_negative" if expected_expansion else "scope_expansion_false_positive")
    if not semantic_vector["review_status"]:
        tags.append("review_status_mismatch")
    return {
        "object_observable": is_object,
        "required_fields_present": present,
        "field_types_correct": field_types,
        "field_type_count": sum(field_types.values()),
        "allowed_targets": allowed_m,
        "held_targets": held_m,
        "authority_separation": {
            "observability": "OBSERVED_AND_CORRECT" if is_object and not overlap else ("OBSERVED_AND_FAILED" if is_object else "NOT_OBSERVABLE"),
            "no_allowed_held_overlap": (not overlap) if is_object else None,
            "overlap_targets": overlap if is_object else None,
            "unauthorized_target_in_allowed": sorted(allowed_set - set(reference["required_allowed_targets"])) if is_object else None,
            "authorized_target_incorrectly_held": sorted(set(reference["required_allowed_targets"]) & held_set) if is_object else None,
        },
        "scope_expansion": {
            "expected": expected_expansion,
            "observed": expansion,
            "semantic_intent": expansion_intent,
            "correct": expansion_correct if is_object else None,
            "type_correct": expansion_type if is_object else None,
            "false_positive": bool(is_object and expansion_intent is True and not expected_expansion),
            "false_negative": bool(is_object and expansion_intent is False and expected_expansion),
        },
        "review_status": {
            "expected": reference["review_status"],
            "observed": review,
            "exact_match": (isinstance(review, str) and review == reference["review_status"]) if is_object else None,
            "confusion_pair": (f"{reference['review_status']} -> {review}" if is_object and review != reference["review_status"] else None),
        },
        "semantic_fields_correct": sum(bool(value) for value in semantic_vector.values()) if is_object else 0,
        "semantic_field_vector": semantic_vector,
        "structural_contract_valid": bool(is_object and present and all(field_types.values()) and not overlap),
        "error_cluster_tags": tags,
    }


def component_vector(score: Mapping[str, Any], *, parse_valid: bool | None = None) -> dict[str, bool | None]:
    """Return explicit comparable components; no list ordering comparisons."""
    field_types = score["field_types_correct"]
    separation = score["authority_separation"]["no_allowed_held_overlap"]
    return {
        "serialization": parse_valid,
        "required_field_types": all(field_types.values()) if score["object_observable"] else None,
        "allowed_target_correctness": score["semantic_field_vector"]["allowed_targets"] if score["object_observable"] else None,
        "held_target_correctness": score["semantic_field_vector"]["held_targets"] if score["object_observable"] else None,
        "allowed_held_separation": separation,
        "scope_expansion_correctness": score["semantic_field_vector"]["scope_expansion_required"] if score["object_observable"] else None,
        "review_status_correctness": score["semantic_field_vector"]["review_status"] if score["object_observable"] else None,
        "semantic_fields_correct": score["semantic_fields_correct"],
    }


def compare_components(before: Mapping[str, bool | None], after: Mapping[str, bool | None]) -> dict[str, Any]:
    """Classify paired deltas using explicit boolean/score deltas."""
    improvements: list[str] = []
    regressions: list[str] = []
    for key in before:
        old, new = before[key], after.get(key)
        if key == "semantic_fields_correct":
            if isinstance(old, int) and isinstance(new, int):
                if new > old: improvements.append(key)
                elif new < old: regressions.append(key)
            continue
        if old is False and new is True:
            improvements.append(key)
        elif old is True and new is False:
            regressions.append(key)
        # None means NOT_OBSERVABLE and is not silently treated as false.
    if improvements and regressions:
        classification = "MIXED"
    elif improvements:
        classification = "IMPROVED"
    elif regressions:
        classification = "REGRESSED"
    else:
        classification = "UNCHANGED"
    return {
        "classification": classification,
        "improvements": improvements,
        "regressions": regressions,
        "before": dict(before),
        "after": dict(after),
    }


def exact_status_confusion(score_rows: list[Mapping[str, Any]]) -> dict[str, int]:
    """Preserve exact ontology labels; no alias normalization."""
    counts: dict[str, int] = {}
    for row in score_rows:
        status = row["review_status"]
        expected, observed = status["expected"], status["observed"]
        if observed is not None:
            key = f"{expected} -> {observed}"
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))
