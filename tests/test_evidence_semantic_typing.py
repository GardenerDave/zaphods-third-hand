from __future__ import annotations

import json
from pathlib import Path

from local_harness.evidence_semantic_typing import (
    build_source_inventory,
    derive_typed_evidence_from_bundle,
)


ROOT = Path(__file__).resolve().parents[1]


def test_task_b_bundle_derives_raw_response_integrity_only():
    bundle = [
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/raw_model_output.txt",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/local_model_call.json",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/output_validation.json",
    ]
    result = derive_typed_evidence_from_bundle(evidence_id="case_a3_evidence", source_paths=bundle)
    derived = {item.property: item for item in result.derived_properties}
    assert "raw_response_integrity" in derived
    assert derived["raw_response_integrity"].derivation_method == "deterministic"
    assert derived["raw_response_integrity"].semantic_source == "machine_observable"
    assert derived["raw_response_integrity"].policy_trust == "trusted"
    assert "transport_qualification" in result.unknown_properties
    assert "bounded_handoff_success" in result.unknown_properties
    assert "semantic_capability" in result.unknown_properties
    assert "semantic_acceptance" in result.unknown_properties


def test_transport_and_capability_remain_unknown_for_natural_a1_bundle():
    bundle = [
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/raw_model_output.txt",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/local_model_call.json",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/output_validation.json",
    ]
    result = derive_typed_evidence_from_bundle(evidence_id="case_a1_evidence", source_paths=bundle)
    derived = {item.property: item for item in result.derived_properties}
    assert "raw_response_integrity" in derived
    assert "transport_qualification" not in derived
    assert "bounded_handoff_success" not in derived
    assert "semantic_capability" not in derived


def test_handoff_bundle_only_derives_advisory_semantic_acceptance():
    base = ROOT / ".work/operator_handoffs/1p7b_to_30b_structured_continuous_v2_20260830/20260831T020000Z/20260831T020000Z"
    bundle = [
        base / "review_decision.json",
        base / "downstream_use_gate.json",
        base / "handoff_packet.json",
    ]
    result = derive_typed_evidence_from_bundle(evidence_id="manual_handoff_20260831t020103z", source_paths=bundle)
    derived = {item.property: item for item in result.derived_properties}
    assert "bounded_handoff_success" not in derived
    assert derived["semantic_acceptance"].derivation_method == "deterministic"
    assert derived["semantic_acceptance"].semantic_source == "reviewer_model"
    assert derived["semantic_acceptance"].policy_trust == "advisory"
    assert "bounded_handoff_success" in result.unknown_properties
    assert "semantic_capability" in result.unknown_properties


def test_provenance_binding_failure_is_conservative(tmp_path: Path):
    src = ROOT / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z"
    local_model_call = json.loads((src / "local_model_call.json").read_text(encoding="utf-8"))
    local_model_call["raw_output_sha256"] = "0" * 64
    bad_local = tmp_path / "local_model_call.json"
    bad_local.write_text(json.dumps(local_model_call), encoding="utf-8")
    bundle = [
        src / "raw_model_output.txt",
        bad_local,
        src / "output_validation.json",
    ]
    result = derive_typed_evidence_from_bundle(evidence_id="case_a3_evidence", source_paths=bundle)
    assert all(item.property != "raw_response_integrity" for item in result.derived_properties)


def test_source_inventory_preserves_paths_and_hashes():
    projected = ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/evidence_projection.json"
    bundle = [
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/raw_model_output.txt",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/local_model_call.json",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/output_validation.json",
    ]
    inventory = build_source_inventory(
        evidence_id="case_a1_evidence",
        projected_evidence_path=projected,
        bundle_paths=bundle,
        source_type="model_produced_and_evaluator_produced",
    )
    assert inventory["evidence_id"] == "case_a1_evidence"
    assert inventory["projected_evidence_path"].endswith("evidence_projection.json")
    assert inventory["projected_evidence_source_count"] == 2
    assert len(inventory["bundle_sources"]) == 3
    assert inventory["bundle_sources"][0]["sha256"]


def test_mixed_bundle_does_not_receive_blanket_trust():
    base = ROOT / ".work/operator_handoffs/1p7b_to_30b_structured_continuous_v2_20260830/20260831T020000Z/20260831T020000Z"
    bundle = [
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/raw_model_output.txt",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/local_model_call.json",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/output_validation.json",
        base / "review_decision.json",
        base / "downstream_use_gate.json",
        base / "handoff_packet.json",
    ]
    result = derive_typed_evidence_from_bundle(evidence_id="mixed_evidence", source_paths=bundle)
    assert result.trust_summary == "mixed"


def test_transport_qualification_and_semantic_capability_remain_unknown_for_natural_lineage():
    bundle = [
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/raw_model_output.txt",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/local_model_call.json",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/output_validation.json",
    ]
    result = derive_typed_evidence_from_bundle(evidence_id="case_a1_evidence", source_paths=bundle)
    assert "transport_qualification" in result.unknown_properties
    assert "semantic_capability" in result.unknown_properties
