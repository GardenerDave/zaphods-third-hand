#!/usr/bin/env python3
"""Model-free validation for the corrected prospective freeze boundary."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs" / "research"
ORIGINAL_FREEZE = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_FREEZE_2026-08-24.json"
ORIGINAL_CONTRACT = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_INTERFACE_CONTRACT_2026-08-24.json"
V2_CONTRACT = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_INTERFACE_CONTRACT_V2_2026-08-24.json"
RUNTIME_MANIFEST = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_RUNTIME_MANIFEST_2026-08-24.json"
PREDICTORS = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_PREDICTORS_2026-08-24.json"
EVALUATOR = RESEARCH / "DELEGATION_PREDICTION_PROSPECTIVE_EVALUATOR_CASES_2026-08-24.json"

ORIGINAL_FREEZE_SHA256 = "4fe343eead59c13b9e42146491e15a0fccfaeda048c89556a2aaa44b66b27dbf"
ORIGINAL_CONTRACT_SHA256 = "cb6388fa675cf1b3031b224afd1258454102d2bef935b851bfa1ce92de6fce5c"
CASE_IDS = [f"dpt-scope-{index:03d}" for index in range(1, 17)]
BANNED_RUNTIME_KEYS = {
    "evaluator_reference",
    "evaluator_path",
    "expected_allowed_targets",
    "expected_held_targets",
    "expected_scope_expansion",
    "expected_review_status",
    "scoring_outcome",
    "validation_label",
    "success_failure_answer",
    "counterfactual_outcome",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        result = set(value)
        for child in value.values():
            result.update(walk_keys(child))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for child in value:
            result.update(walk_keys(child))
        return result
    return set()


def main() -> None:
    original = load(ORIGINAL_FREEZE)
    original_contract = load(ORIGINAL_CONTRACT)
    v2_contract = load(V2_CONTRACT)
    runtime = load(RUNTIME_MANIFEST)
    predictors = load(PREDICTORS)
    evaluator = load(EVALUATOR)

    assert sha256(ORIGINAL_FREEZE) == ORIGINAL_FREEZE_SHA256
    assert sha256(ORIGINAL_CONTRACT) == ORIGINAL_CONTRACT_SHA256
    assert original["cohort"]["case_count"] == 16
    assert original["cohort"]["supplier_selection_disagreement_count"] == 8
    assert original["cohort"]["delegate_vs_abstain_disagreement_count"] == 8
    assert original["cohort"]["binary_expected_success_disagreement_count"] == 8

    cases = runtime["cases"]
    assert len(cases) == 16
    assert [case["case_id"] for case in cases] == CASE_IDS
    assert sum(case["category"] == "SUPPLIER_SELECTION" for case in cases) == 8
    assert sum(case["category"] == "DELEGATE_VS_ABSTAIN" for case in cases) == 8
    assert sum(case["generalized_policy"]["expected_success"] != case["degeneralized_policy"]["expected_success"] for case in cases) == 8

    evaluator_by_id = {case["task_id"]: case for case in evaluator["cases"]}
    assert list(evaluator_by_id) == CASE_IDS
    for case in cases:
        assert case["request"] == evaluator_by_id[case["case_id"]]["request"]
        assert "evaluator_reference" not in case
        assert case["generalized_policy"]["selected_supplier"] in {"local_teacher", "external_teacher"}
        assert case["degeneralized_policy"]["selected_supplier"] in {None, "local_teacher", "external_teacher"}

    runtime_keys = walk_keys(runtime)
    assert not (runtime_keys & BANNED_RUNTIME_KEYS)
    runtime_text = RUNTIME_MANIFEST.read_text(encoding="utf-8")
    assert "DELEGATION_PREDICTION_PROSPECTIVE_EVALUATOR_CASES" not in runtime_text
    assert "evaluator_reference" not in runtime_text
    assert "expected_allowed_targets" not in runtime_text
    assert "expected_held_targets" not in runtime_text

    assert "additionalProperties" not in v2_contract["experiment_authored_payload"]["output_schema"]
    assert v2_contract["experiment_authored_payload"]["output_schema"]["required"] == [
        "allowed_targets", "held_targets", "scope_expansion_required", "review_status"
    ]
    assert v2_contract["experiment_authored_payload"]["tool_calls"] == 0
    assert v2_contract["experiment_authored_payload"]["evaluator_access"] is False
    assert original_contract["experiment_authored_payload"]["output_schema"]["additionalProperties"] is False

    # Evaluator corruption is test-only and cannot mutate runtime inputs.
    runtime_before = json.dumps(runtime, sort_keys=True, separators=(",", ":"))
    evaluator_copy = copy.deepcopy(evaluator)
    evaluator_copy["cases"][0]["expected"]["allowed_targets"] = ["CORRUPTION_ONLY"]
    evaluator_copy["cases"][0]["expected"]["scope_expansion_required"] = not evaluator_copy["cases"][0]["expected"]["scope_expansion_required"]
    assert evaluator_copy != evaluator
    assert evaluator_copy["cases"][0]["expected"] != evaluator["cases"][0]["expected"]
    assert json.dumps(runtime, sort_keys=True, separators=(",", ":")) == runtime_before
    assert runtime["cases"] == load(RUNTIME_MANIFEST)["cases"]
    assert predictors["schema"].startswith("zth_delegation_prediction_prospective_predictors")

    prospective_root = ROOT / ".work" / "model_size_supplier_floor" / "delegation_prediction_test_scope_v0"
    assert not prospective_root.exists()
    assert not list(ROOT.glob("**/dpt-scope-*/response.json"))
    assert not list(ROOT.glob("**/dpt-scope-*/runtime_result.json"))

    print("delegation prediction freeze v2 model-free validation: PASS")
    print("cases=16 supplier_selection=8 delegate_vs_abstain=8 binary_success=8")
    print("original_freeze_hash=PASS original_contract_hash=PASS")
    print("runtime_evaluator_isolation=PASS corrected_contract_semantics=PASS")
    print("prospective_runtime_artifacts=0 model_calls=0 teacher_calls=0 tool_calls=0 external_calls=0")


if __name__ == "__main__":
    main()
