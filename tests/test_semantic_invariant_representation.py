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
    assert _sha256(INVARIANT_PATH) == "b70b9d1e1a271153cde1e1039cb57fcdaa07f538bce39a2cff4b6f2a3c951f28"


def test_t1_and_t2_hold():
    invariant = load_json_object(INVARIANT_PATH)
    for name in ("t1", "t2"):
        evidence, assertions = _load_pair(name)
        assert validate_typed_evidence_fixture(evidence) == []
        assert validate_typed_assertion_fixture(assertions) == []
        result = evaluate_typed_invariant(invariant=invariant, evidence_scope=evidence["evidence_scope"], assertions=assertions)
        assert result.result == "hold"
        assert result.violating_properties == ["semantic_capability"]
        assert result.applicable is True
        assert "transport_qualification_implies_semantic_capability_not_established_v1" in result.reason


def test_t3_is_not_applicable():
    invariant = load_json_object(INVARIANT_PATH)
    evidence, assertions = _load_pair("t3")
    assert validate_typed_evidence_fixture(evidence) == []
    assert validate_typed_assertion_fixture(assertions) == []
    result = evaluate_typed_invariant(invariant=invariant, evidence_scope=evidence["evidence_scope"], assertions=assertions)
    assert result.result in {"pass", "not_applicable"}
    assert result.violating_properties == []
    assert result.applicable is False or result.result == "pass"


def test_synthetic_transport_only_passes():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = load_json_object(ROOT / "controls_transport_only_evidence.json")
    assertions = load_json_object(ROOT / "controls_transport_only_assertions.json")
    result = evaluate_typed_invariant(invariant=invariant, evidence_scope=evidence["evidence_scope"], assertions=assertions)
    assert result.result == "pass"
    assert result.violating_properties == []


def test_synthetic_semantic_capability_passes():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = load_json_object(ROOT / "controls_semantic_capability_evidence.json")
    assertions = load_json_object(ROOT / "controls_semantic_capability_assertions.json")
    result = evaluate_typed_invariant(invariant=invariant, evidence_scope=evidence["evidence_scope"], assertions=assertions)
    assert result.result == "pass"
    assert result.violating_properties == []


def test_checker_never_inspects_prose():
    invariant = load_json_object(INVARIANT_PATH)
    evidence = {"evidence_scope": {"established_properties": ["transport_qualification"]}}
    assertions = {"assertions": [{"asserted_property": "transport_qualification", "evidence_refs": ["x"], "claim_text": "NO PROSE NEEDED"}]}
    result = evaluate_typed_invariant(invariant=invariant, evidence_scope=evidence["evidence_scope"], assertions=assertions)
    assert result.result == "pass"
