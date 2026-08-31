from __future__ import annotations

import json
from pathlib import Path

from local_harness.evidence_semantic_typing import (
    build_source_inventory,
    derive_typed_evidence_from_bundle,
    HandoffCompletionRef,
    TransportQualificationRef,
    resolve_handoff_completion_reference,
    resolve_transport_qualification_reference,
)


ROOT = Path(__file__).resolve().parents[1]


def test_task_b_bundle_derives_raw_response_integrity_only():
    bundle = [
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/raw_model_output.txt",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/local_model_call.json",
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


def test_raw_response_integrity_survives_failed_output_validation():
    bundle = [
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/patched/20260831T133000Z/raw_model_output.txt",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/patched/20260831T133000Z/local_model_call.json",
        ROOT / ".work/semantic_claim_discipline_final_20260831/task_a/patched/20260831T133000Z/output_validation.json",
    ]
    result = derive_typed_evidence_from_bundle(evidence_id="case_a2_evidence", source_paths=bundle)
    derived = {item.property: item for item in result.derived_properties}
    assert "raw_response_integrity" in derived
    assert derived["raw_response_integrity"].derivation_method == "deterministic"
    assert derived["raw_response_integrity"].semantic_source == "machine_observable"
    assert derived["raw_response_integrity"].policy_trust == "trusted"


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


def test_transport_qualification_reference_resolves_authoritatively():
    artifact = ROOT / "docs/research/EXPLICIT_INTERFACE_V3_TRANSPORT_REQUALIFICATION_FINAL_2026-08-24.json"
    ref = TransportQualificationRef(
        artifact_ref=str(artifact),
        artifact_sha256="a002ff5e7d190fae429a0f84e57eaa03c3fdcdb247d7a06756a7ed65ed022466",
        qualification_id="v3-explicit-interface",
    )
    verification = resolve_transport_qualification_reference(
        qualification_ref=ref,
        transaction_endpoint="http://192.168.1.16:8080/v1/chat/completions",
        transaction_model="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
    )
    assert verification.artifact_integrity is True
    assert verification.qualification_passed is True
    assert verification.endpoint_match is True
    assert verification.model_match is True
    assert verification.policy_usable is False
    assert verification.scope_match is None


def test_transport_qualification_reference_hash_failure_fails_closed():
    artifact = ROOT / "docs/research/EXPLICIT_INTERFACE_V3_TRANSPORT_REQUALIFICATION_FINAL_2026-08-24.json"
    ref = TransportQualificationRef(
        artifact_ref=str(artifact),
        artifact_sha256="0" * 64,
    )
    try:
        resolve_transport_qualification_reference(
            qualification_ref=ref,
            transaction_endpoint="http://192.168.1.16:8080/v1",
            transaction_model="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected transport qualification hash failure")


def test_handoff_completion_reference_requires_authoritative_artifact():
    base = ROOT / ".work/operator_handoffs/1p7b_to_30b_structured_continuous_v2_20260830/20260831T020000Z/20260831T020000Z"
    completion_ref = HandoffCompletionRef(
        artifact_ref=str(base / "worker_b_call_intent.transport_events.jsonl"),
        artifact_sha256="ae0d74b23be5e36e63751e05ba91eb2e6dc141d754192f08dc98eb7dc470b008",
        handoff_id="manual_handoff_20260831t020103z",
        downstream_attempt_id="icm_call_28027750761",
    )
    verification = resolve_handoff_completion_reference(
        completion_ref=completion_ref,
        prepared_handoff_id="manual_handoff_20260831t020103z",
        transaction_endpoint="http://192.168.1.16:8080/v1/chat/completions",
        transaction_model="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
    )
    assert verification.completion_detected is True
    assert verification.policy_usable is False


def test_handoff_completion_reference_hash_failure_fails_closed():
    base = ROOT / ".work/operator_handoffs/1p7b_to_30b_structured_continuous_v2_20260830/20260831T020000Z/20260831T020000Z"
    completion_ref = HandoffCompletionRef(
        artifact_ref=str(base / "worker_b_local_model_call.json"),
        artifact_sha256="0" * 64,
    )
    try:
        resolve_handoff_completion_reference(
            completion_ref=completion_ref,
            prepared_handoff_id="manual_handoff_20260831t020103z",
            transaction_endpoint="http://192.168.1.16:8080/v1/chat/completions",
            transaction_model="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected handoff completion hash failure")
