from __future__ import annotations

import hashlib
import json
from pathlib import Path

from local_harness.typed_semantic_invariant import (
    evaluate_typed_invariant,
    load_json_object,
    validate_invariant_fixture,
    validate_typed_assertion_fixture,
    validate_typed_evidence_fixture,
)


ROOT = Path(__file__).resolve().parent / "fixtures" / "semantic_invariant_representation"
INVARIANT_PATH = Path(__file__).resolve().parents[1] / "local_harness" / "experimental_semantic_invariant" / "transport_qualification_implies_semantic_capability_not_established_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_pair(name: str) -> tuple[dict, dict]:
    evidence = load_json_object(ROOT / f"{name}_evidence.json")
    assertions = load_json_object(ROOT / f"{name}_assertions.json")
    return evidence, assertions


def test_invariant_fixture_is_machine_readable():
    invariant = load_json_object(INVARIANT_PATH)
    assert validate_invariant_fixture(invariant) == []
    assert invariant["status"] == "conceptual_only"
    assert _sha256(INVARIANT_PATH) == "66bbcd09a020d9388a9b0365eba2a6bc8e8680b563926b027eeda2dadaf74b01"


def test_t1_and_t2_hold():
    invariant = load_json_object(INVARIANT_PATH)
    for name in ("t1", "t2"):
        evidence, assertions = _load_pair(name)
        assert validate_typed_evidence_fixture(evidence) == []
        assert validate_typed_assertion_fixture(assertions) == []
        result = evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=assertions)
        assert result.result == "hold"
        assert result.violating_properties == ["semantic_capability"]
        assert result.applicable is True
        assert result.established_asserted_properties == ["semantic_capability"]
        assert result.not_established_asserted_properties == []
        assert "transport_qualification_implies_semantic_capability_not_established_v1" in result.reason


def test_t3_is_not_applicable():
    invariant = load_json_object(INVARIANT_PATH)
    evidence, assertions = _load_pair("t3")
    assert validate_typed_evidence_fixture(evidence) == []
    assert validate_typed_assertion_fixture(assertions) == []
    result = evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=assertions)
    assert result.result == "not_applicable"
    assert result.violating_properties == []
    assert result.applicable is False
    assert result.established_asserted_properties == []
    assert result.not_established_asserted_properties == ["semantic_acceptance"]


def test_synthetic_transport_only_passes():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = load_json_object(ROOT / "controls_transport_only_evidence.json")
    assertions = load_json_object(ROOT / "controls_transport_only_assertions.json")
    result = evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=assertions)
    assert result.result == "pass"
    assert result.violating_properties == []
    assert result.established_asserted_properties == ["transport_qualification"]
    assert result.not_established_asserted_properties == []


def test_synthetic_semantic_capability_passes():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = load_json_object(ROOT / "controls_semantic_capability_evidence.json")
    assertions = load_json_object(ROOT / "controls_semantic_capability_assertions.json")
    result = evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=assertions)
    assert result.result == "pass"
    assert result.violating_properties == []
    assert result.established_asserted_properties == ["semantic_capability"]
    assert result.not_established_asserted_properties == []


def test_checker_never_inspects_prose():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = {"evidence_id": "x", "evidence_scope": {"established_properties": ["transport_qualification"]}}
    assertions = {"assertions": [{"property": "transport_qualification", "epistemic_status": "established", "evidence_refs": ["x"], "claim_text": "NO PROSE NEEDED"}]}
    result = evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=assertions)
    assert result.result == "pass"
    assert result.established_asserted_properties == ["transport_qualification"]


def test_not_established_semantic_capability_passes_under_transport_evidence():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = load_json_object(ROOT / "controls_transport_only_evidence.json")
    assertions = {
        "typing_source": "frozen_experiment_fixture",
        "assertions": [
            {
                "property": "semantic_capability",
                "epistemic_status": "not_established",
                "evidence_refs": ["controls_transport_only_evidence"],
            }
        ],
    }
    assert validate_typed_evidence_fixture(evidence) == []
    assert validate_typed_assertion_fixture(assertions) == []
    result = evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=assertions)
    assert result.result == "pass"
    assert result.not_established_asserted_properties == ["semantic_capability"]
    assert result.established_asserted_properties == []


def test_wrong_evidence_reference_fails():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = load_json_object(ROOT / "controls_transport_only_evidence.json")
    assertions = {
        "assertions": [
            {
                "property": "transport_qualification",
                "epistemic_status": "established",
                "evidence_refs": ["controls_transport_only_evidence", "wrong_evidence"],
            }
        ]
    }
    try:
        evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=assertions)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "exactly one evidence_refs entry" in str(exc)


def test_unsupported_property_rejected():
    problems = validate_typed_assertion_fixture(
        {
            "assertions": [
                {
                    "property": "unknown_property",
                    "epistemic_status": "established",
                    "evidence_refs": ["x"],
                }
            ]
        }
    )
    assert any("unsupported property" in problem for problem in problems)


def test_missing_epistemic_status_rejected():
    problems = validate_typed_assertion_fixture(
        {
            "assertions": [
                {
                    "property": "transport_qualification",
                    "evidence_refs": ["x"],
                }
            ]
        }
    )
    assert any("epistemic_status" in problem for problem in problems)


def test_t3_polarity_mutation_preserves_non_applicability():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = load_json_object(ROOT / "t3_evidence.json")
    mutated = {
        "assertions": [
            {
                "property": "semantic_acceptance",
                "epistemic_status": "established",
                "evidence_refs": ["t3_evidence"],
            }
        ]
    }
    result = evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=mutated)
    assert result.result == "not_applicable"


def test_polarity_mutation_pair():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = load_json_object(ROOT / "controls_transport_only_evidence.json")
    established = {
        "typing_source": "frozen_experiment_fixture",
        "assertions": [
            {
                "property": "semantic_capability",
                "epistemic_status": "established",
                "evidence_refs": ["controls_transport_only_evidence"],
            }
        ]
    }
    not_established = {
        "typing_source": "frozen_experiment_fixture",
        "assertions": [
            {
                "property": "semantic_capability",
                "epistemic_status": "not_established",
                "evidence_refs": ["controls_transport_only_evidence"],
            }
        ]
    }
    established_result = evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=established)
    not_established_result = evaluate_typed_invariant(invariant=invariant, evidence=evidence, assertions=not_established)
    assert established_result.result == "hold"
    assert not_established_result.result == "pass"
