#!/usr/bin/env python3
"""Model-free atomic capability scoring for the preserved Qwen3-0.6B screens."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from local_harness.supervised_capability_loop import _validator_result


ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = ROOT / "local_harness/fixtures/capability_loop/run7_scope"
STAGE_A_ROOT = ROOT / ".work/model_size_supplier_floor/qwen3_0_6b_stage_a/run_20260820T171851Z"
INTERFACE_ROOT = ROOT / ".work/model_size_supplier_floor/qwen3_0_6b_interface_disambiguation/run_20260820T181000Z"
TASK_IDS = [f"run7-scope-{i:03d}" for i in range(1, 13)]
REPORT_SHA = "51543cc07aa89922e86c554b669b8da689d151ace7f181f5f39cac3eb6eda14b"
FORENSIC_SHA = "c3b95e43a9e9c5d68ca2f54f8920f02886bd8f0930561618ca1bf60bb57e361b"
INTERFACE_REPORT_SHA = "303496298d725ba95b74952e2d7844f4997249a6eafe920b397dc09777bdd1bd"


def sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes(root: Path) -> dict[str, str]:
    """Record a read-only manifest for the preserved run tree."""
    return {
        str(path.relative_to(root)): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def strip_outer_fence(text: str) -> tuple[str, bool]:
    value = text.strip()
    if value.startswith("```") and value.endswith("```"):
        value = re.sub(r"^```[^\n]*\n", "", value)
        value = re.sub(r"\n```$", "", value)
        return value, True
    return value, False


def fixture_map() -> dict[str, dict[str, Any]]:
    result = {}
    for path in TASK_ROOT.glob("*.json"):
        payload = json.loads(path.read_text())
        if payload.get("task_id") in TASK_IDS:
            result[payload["task_id"]] = {"payload": payload, "path": path, "sha256": sha256(path)}
    return result


def target_literal_set(value: Any, expected: list[str]) -> tuple[set[str], bool, bool]:
    """Return literal target identities, type validity, and identity usability."""
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            return set(), False, False
        return set(value), True, True
    if isinstance(value, str):
        # Only an exact singleton string is semantically usable. Do not parse
        # comma-separated prose or infer list structure.
        return ({value}, False, len(expected) == 1 and value == expected[0])
    return set(), False, False


def target_metrics(observed: Any, expected: list[str]) -> dict[str, Any]:
    observed_set, type_correct, identity_usable = target_literal_set(observed, expected)
    expected_set = set(expected)
    tp = len(observed_set & expected_set)
    fp = len(observed_set - expected_set)
    fn = len(expected_set - observed_set)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and precision + recall else None
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


def score_object(obj: Any, reference: dict[str, Any]) -> dict[str, Any]:
    expected_allowed = reference["required_allowed_targets"]
    expected_held = reference["required_held_targets"]
    required = ["allowed_targets", "held_targets", "scope_expansion_required", "review_status"]
    is_object = isinstance(obj, dict)
    present = is_object and all(key in obj for key in required)
    allowed = obj.get("allowed_targets") if is_object else None
    held = obj.get("held_targets") if is_object else None
    expansion = obj.get("scope_expansion_required") if is_object else None
    review = obj.get("review_status") if is_object else None
    allowed_m = target_metrics(allowed, expected_allowed)
    held_m = target_metrics(held, expected_held)
    allowed_set = set(allowed_m["observed_literal_set"])
    held_set = set(held_m["observed_literal_set"])
    overlap = sorted(allowed_set & held_set)
    expected_expansion = bool(reference["requires_scope_expansion_flag"])
    if isinstance(expansion, bool):
        expansion_intent = expansion
        expansion_type = True
    elif isinstance(expansion, str) and expansion in {"true", "false"}:
        expansion_intent = expansion == "true"
        expansion_type = False
    else:
        expansion_intent = None
        expansion_type = False
    expansion_correct = expansion_intent is not None and expansion_intent == expected_expansion
    review_exact = isinstance(review, str) and review == reference["review_status"]
    field_types = {
        "allowed_targets": isinstance(allowed, list) and all(isinstance(x, str) for x in allowed),
        "held_targets": isinstance(held, list) and all(isinstance(x, str) for x in held),
        "scope_expansion_required": isinstance(expansion, bool),
        "review_status": isinstance(review, str),
    }
    semantic_fields = [
        allowed_m["exact_set_match"],
        held_m["exact_set_match"],
        expansion_correct,
        review_exact,
    ]
    structural_contract = is_object and present and all(field_types.values()) and not overlap
    error_tags = []
    if not is_object:
        error_tags.append("missing_structured_object")
    if is_object and not all(field_types.values()):
        error_tags.append("type_or_representation_error")
    if overlap:
        error_tags.append("allowed_held_overlap")
    if not allowed_m["exact_set_match"]:
        error_tags.append("allowed_target_mismatch")
    if not held_m["exact_set_match"]:
        error_tags.append("held_target_mismatch")
    if not expansion_correct:
        error_tags.append("scope_expansion_mismatch" if expansion_intent is not None else "scope_expansion_uninterpretable")
    if not review_exact:
        error_tags.append("review_status_mismatch")
    return {
        "object": is_object,
        "required_fields_present": present,
        "field_types_correct": field_types,
        "field_type_count": sum(field_types.values()),
        "allowed_targets": allowed_m,
        "held_targets": held_m,
        "authority_separation": {
            "no_allowed_held_overlap": not overlap,
            "overlap_targets": overlap,
            "unauthorized_target_in_allowed": sorted(set(allowed_m["observed_literal_set"]) - set(expected_allowed)),
            "authorized_target_incorrectly_held": sorted(set(expected_allowed) & set(held_m["observed_literal_set"])),
        },
        "scope_expansion": {
            "expected": expected_expansion,
            "observed": expansion,
            "semantic_intent": expansion_intent,
            "correct": expansion_correct,
            "type_correct": expansion_type,
            "false_positive": expansion_correct is False and expansion_intent is False,
            "false_negative": expansion_correct is False and expansion_intent is True,
        },
        "review_status": {
            "expected": reference["review_status"],
            "observed": review,
            "exact_match": review_exact,
        },
        "semantic_fields_correct": sum(semantic_fields),
        "semantic_field_vector": {
            "allowed_targets": semantic_fields[0],
            "held_targets": semantic_fields[1],
            "scope_expansion_required": semantic_fields[2],
            "review_status": semantic_fields[3],
        },
        "structural_contract_valid": structural_contract,
        "error_cluster_tags": error_tags,
    }


def validator_summary(raw: str, task: dict[str, Any]) -> dict[str, Any]:
    validation = _validator_result(raw, task, attempt_id="atomic-press")
    return {
        "validation_status": validation.get("validation_status"),
        "structural_failed_checks": [c["check_id"] for c in validation.get("structural_checks", []) if c.get("status") == "failed"],
        "semantic_failed_checks": [c["check_id"] for c in validation.get("semantic_checks", []) if c.get("status") == "failed"],
    }


def analyze_run(root: Path, fixtures: dict[str, dict[str, Any]], *, normalized: bool) -> dict[str, Any]:
    result = {}
    for task_id in TASK_IDS:
        task = fixtures[task_id]["payload"]
        response = json.loads((root / "tasks" / task_id / "response.json").read_text())
        raw = response.get("content", "")
        text, fenced = strip_outer_fence(raw)
        source = text if normalized else raw.strip()
        try:
            obj = json.loads(source)
            parse_valid = True
        except json.JSONDecodeError:
            obj = None
            parse_valid = False
        score = score_object(obj, task["validator"]["reference_facts"]) if parse_valid else score_object(None, task["validator"]["reference_facts"])
        saved_validation = json.loads((root / "tasks" / task_id / "validation.json").read_text())
        diagnostic_validation = validator_summary(json.dumps(obj, sort_keys=True), task) if parse_valid else None
        result[task_id] = {
            "raw_parse_valid": parse_valid,
            "markdown_fenced": fenced,
            "mechanically_recoverable": normalized and parse_valid,
            "score": score,
            "saved_validator": {
                "validation_status": saved_validation.get("validation_status"),
                "structural_failed_checks": [c["check_id"] for c in saved_validation.get("structural_checks", []) if c.get("status") == "failed"],
                "semantic_failed_checks": [c["check_id"] for c in saved_validation.get("semantic_checks", []) if c.get("status") == "failed"],
            },
            "diagnostic_validator": diagnostic_validation,
        }
    return result


def aggregate(run: dict[str, Any], *, normalized: bool) -> dict[str, Any]:
    rows = list(run.values())
    scores = [row["score"] for row in rows]
    return {
        "task_count": len(rows),
        "raw_parse_valid": sum(row["raw_parse_valid"] for row in rows) if not normalized else None,
        "mechanically_recoverable": sum(row["mechanically_recoverable"] for row in rows) if normalized else None,
        "contract_usable": sum(score["structural_contract_valid"] for score in scores),
        "reference_semantic_all_fields": sum(score["semantic_fields_correct"] == 4 for score in scores),
        "fully_validator_valid": sum(row["saved_validator"]["validation_status"] == "passed" for row in rows),
        "field_types_all_correct": sum(all(score["field_types_correct"].values()) for score in scores),
        "allowed_exact": sum(score["allowed_targets"]["exact_set_match"] for score in scores),
        "held_exact": sum(score["held_targets"]["exact_set_match"] for score in scores),
        "no_overlap": sum(score["authority_separation"]["no_allowed_held_overlap"] for score in scores),
        "scope_expansion_correct": sum(score["scope_expansion"]["correct"] for score in scores),
        "scope_expansion_type_correct": sum(score["scope_expansion"]["type_correct"] and score["scope_expansion"]["correct"] for score in scores),
        "review_status_exact": sum(score["review_status"]["exact_match"] for score in scores),
        "semantic_fields_distribution": dict(sorted(Counter(score["semantic_fields_correct"] for score in scores).items())),
        "semantic_fields_3_of_4": sum(score["semantic_fields_correct"] == 3 for score in scores),
        "allowed_micro": micro_target(scores, "allowed_targets"),
        "held_micro": micro_target(scores, "held_targets"),
        "review_status_observed": dict(Counter(str(score["review_status"]["observed"]) for score in scores)),
        "error_cluster_tags": dict(Counter(tag for score in scores for tag in score["error_cluster_tags"])),
    }


def micro_target(scores: list[dict[str, Any]], key: str) -> dict[str, Any]:
    tp = sum(score[key]["true_positives"] for score in scores)
    fp = sum(score[key]["false_positives"] for score in scores)
    fn = sum(score[key]["false_negatives"] for score in scores)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {"true_positives": tp, "false_positives": fp, "false_negatives": fn, "precision": precision, "recall": recall, "f1": f1}


def paired(stage: dict[str, Any], interface: dict[str, Any]) -> dict[str, Any]:
    result = {}
    components = ["allowed_targets", "held_targets", "scope_expansion_required", "review_status"]
    for task_id in TASK_IDS:
        before = stage[task_id]["score"]
        after = interface[task_id]["score"]
        before_vector = [before["semantic_field_vector"][key] for key in components]
        after_vector = [after["semantic_field_vector"][key] for key in components]
        before_struct = [all(before["field_types_correct"].values()), before["authority_separation"]["no_allowed_held_overlap"]]
        after_struct = [all(after["field_types_correct"].values()), after["authority_separation"]["no_allowed_held_overlap"]]
        changed = [components[i] for i in range(4) if before_vector[i] != after_vector[i]]
        if after["semantic_fields_correct"] > before["semantic_fields_correct"] or after_struct > before_struct:
            classification = "IMPROVED"
        elif after["semantic_fields_correct"] < before["semantic_fields_correct"] or after_struct < before_struct:
            classification = "REGRESSED"
        else:
            classification = "UNCHANGED"
        result[task_id] = {"classification": classification, "changed_components": changed, "stage_a_semantic_fields_correct": before["semantic_fields_correct"], "interface_semantic_fields_correct": after["semantic_fields_correct"], "stage_a_field_types_all_correct": all(before["field_types_correct"].values()), "interface_field_types_all_correct": all(after["field_types_correct"].values())}
    return result


def feature_conditioning(run: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for task_id, row in run.items():
        for feature in references[task_id]["difficulty_features"]:
            buckets[feature].append(row["score"]["semantic_fields_correct"])
    return {
        feature: {
            "task_observations": len(values),
            "semantic_fields_correct_total": sum(values),
            "semantic_fields_correct_mean": sum(values) / len(values),
            "distribution": dict(sorted(Counter(values).items())),
        }
        for feature, values in sorted(buckets.items())
    }


def capability_map() -> dict[str, Any]:
    return {
        "machine_readable_json": {"classification": "PARTIAL", "qualifiers": ["INTERFACE_DEPENDENT"], "evidence": "Stage A normalized 12/12 objects; raw 0/12. Interface raw 6/12 bare objects."},
        "required_field_types": {"classification": "PARTIAL", "qualifiers": ["INTERFACE_DEPENDENT"], "evidence": "Stage A normalized 3/12 all types; interface 12/12."},
        "allowed_target_identification": {"classification": "PARTIAL", "qualifiers": [], "evidence": "Normalized exact-set 6/12 in both runs; interface micro precision/recall improved."},
        "held_target_identification": {"classification": "PARTIAL", "qualifiers": [], "evidence": "Normalized exact-set Stage A 2/12; interface 6/12."},
        "allowed_held_separation": {"classification": "PARTIAL", "qualifiers": [], "evidence": "No-overlap 10/12 in each normalized run."},
        "scope_expansion_detection": {"classification": "DEMONSTRATED", "qualifiers": ["positive-required-branch-only"], "evidence": "Interface normalized 12/12 correct; no negative-required branch in this sample."},
        "review_status_selection": {"classification": "NOT_DEMONSTRATED", "qualifiers": [], "evidence": "0/12 exact in both normalized runs."},
        "complete_bounded_scope_authority_decision": {"classification": "NOT_DEMONSTRATED", "qualifiers": [], "evidence": "0/12 fully validated in both runs."},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixtures = fixture_map()
    if set(fixtures) != set(TASK_IDS):
        raise SystemExit("fixture population mismatch")
    stage_raw = analyze_run(STAGE_A_ROOT, fixtures, normalized=False)
    stage_norm = analyze_run(STAGE_A_ROOT, fixtures, normalized=True)
    interface_raw = analyze_run(INTERFACE_ROOT, fixtures, normalized=False)
    interface_norm = analyze_run(INTERFACE_ROOT, fixtures, normalized=True)
    matrix = {
        "schema": "zth_qwen3_0_6b_atomic_capability_matrix_v1",
        "provenance": {
            "stage_a_run": str(STAGE_A_ROOT.relative_to(ROOT)),
            "interface_run": str(INTERFACE_ROOT.relative_to(ROOT)),
            "stage_a_report_sha256": REPORT_SHA,
            "stage_a_forensic_report_sha256": FORENSIC_SHA,
            "interface_report_sha256": INTERFACE_REPORT_SHA,
            "stage_a_artifact_hashes": artifact_hashes(STAGE_A_ROOT),
            "interface_artifact_hashes": artifact_hashes(INTERFACE_ROOT),
            "model_calls_made": 0,
            "raw_artifacts_changed": False,
            "validator_artifacts_changed": False,
            "reference_scoring": "frozen fixture validator reference_facts",
            "normalization": "Stage A and secondary interface analysis remove at most one outer markdown fence in memory; no values or types changed",
        },
        "reference_facts": {task_id: {"source_path": str(fixtures[task_id]["path"].relative_to(ROOT)), "source_sha256": fixtures[task_id]["sha256"], "task_family": fixtures[task_id]["payload"]["task_family"], "reference": fixtures[task_id]["payload"]["validator"]["reference_facts"], "difficulty_features": fixtures[task_id]["payload"].get("calibration", {}).get("difficulty_features", [])} for task_id in TASK_IDS},
        "runs": {
            "stage_a_raw": stage_raw,
            "stage_a_normalized": stage_norm,
            "interface_raw": interface_raw,
            "interface_normalized": interface_norm,
        },
        "aggregates": {
            "stage_a_raw": aggregate(stage_raw, normalized=False),
            "stage_a_normalized": aggregate(stage_norm, normalized=True),
            "interface_raw": aggregate(interface_raw, normalized=False),
            "interface_normalized": aggregate(interface_norm, normalized=True),
        },
        "paired_interface_effect": paired(stage_norm, interface_norm),
        "feature_conditioning": {
            "stage_a_normalized": feature_conditioning(stage_norm, matrix_references := {task_id: {"difficulty_features": json.loads((fixtures[task_id]["path"]).read_text()).get("calibration", {}).get("difficulty_features", [])} for task_id in TASK_IDS}),
            "interface_normalized": feature_conditioning(interface_norm, matrix_references),
        },
        "capability_map": capability_map(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "atomic_matrix_written", "tasks": 12, "responses": 24, "model_calls": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
