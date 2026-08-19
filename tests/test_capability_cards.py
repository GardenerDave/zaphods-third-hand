from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_harness.capability_cards import (
    CapabilityEvidenceError,
    build_accounting_audit,
    build_capability_cards,
    build_hierarchical_evidence,
    failure_classes,
    failure_signature,
    recommend_intervention,
)


def _task(root: Path, task_id: str, *, source: str = "none", passed: bool = False, transport: str = "model_response", patch_id: str | None = None) -> None:
    task_dir = root / task_id
    task_dir.mkdir(parents=True)
    validation = {
        "validation_status": "passed" if passed else "failed",
        "structural_checks": [{"check_id": "parse_json", "status": "passed" if passed else "failed"}],
        "semantic_checks": [{"check_id": "reference_status", "status": "passed" if passed else "failed"}],
        "checks": [],
    }
    metadata = {
        "attempt": 1,
        "intervention_source": source,
        "intervention_id": f"{source}:1",
        "transport_valid": transport == "model_response",
        "transport_classification": transport,
        "validation_status": validation["validation_status"] if transport == "model_response" else None,
        "deterministic_patch_id": patch_id,
        "deterministic_patch_hash": "a" * 64 if patch_id else None,
    }
    raw = {"status": "ok" if transport == "model_response" else "request_error", "content": "{}", "metadata": {"model": "small"}}
    (task_dir / "attempt-1.metadata.json").write_text(json.dumps(metadata))
    (task_dir / "attempt-1.raw.json").write_text(json.dumps(raw))
    if transport == "model_response":
        (task_dir / "attempt-1.validation.json").write_text(json.dumps(validation))
    record = {"record_type": "worker_attempt", **metadata, "validation": validation if transport == "model_response" else None, "artifact_refs": {"raw": "attempt-1.raw.json"}}
    (task_dir / "trajectory.jsonl").write_text(json.dumps(record) + "\n")
    (task_dir / "trajectory_summary.json").write_text(json.dumps({"task_id": task_id, "task_family": "scope-authority-boundary", "worker_model": "small", "external_teacher_call_count": 0}))


def _append_intervention(task_dir: Path, *, source: str, passed: bool, patch_id: str) -> None:
    validation = {"validation_status": "passed" if passed else "failed", "structural_checks": [{"check_id": "parse_json", "status": "passed" if passed else "failed"}], "semantic_checks": [{"check_id": "reference_status", "status": "passed" if passed else "failed"}], "checks": []}
    metadata = {"attempt": 2, "intervention_source": source, "intervention_id": f"{source}:1", "transport_valid": True, "transport_classification": "model_response", "validation_status": validation["validation_status"], "deterministic_patch_id": patch_id, "deterministic_patch_hash": "a" * 64}
    record = {"record_type": "worker_attempt", **metadata, "validation": validation, "artifact_refs": {"raw": "attempt-2.raw.json"}}
    with (task_dir / "trajectory.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")


def test_transport_invalid_attempt_is_excluded(tmp_path: Path):
    _task(tmp_path, "transport", transport="transport_request_error")
    _task(tmp_path, "valid", passed=False)
    bundle = build_capability_cards([tmp_path])
    assert bundle["source_task_count"] == 2
    assert bundle["transport_excluded_task_count"] == 1


def test_attempts_and_rescues_are_separate_and_patch_identity_preserved(tmp_path: Path):
    for i in range(3):
        _task(tmp_path, f"base-{i}", passed=False)
    _append_intervention(tmp_path / "base-0", source="deterministic_patch_retry", passed=True, patch_id="patch-a")
    bundle = build_capability_cards([tmp_path])
    cards = [c for c in bundle["cards"] if c["identity"]["intervention_type"] == "deterministic_patch_retry"]
    assert cards[0]["observations"]["eligible_attempts"] == 1
    assert cards[0]["observations"]["successes"] == 1
    assert cards[0]["identity"]["patch_id"] == "patch-a"


def test_failure_signature_is_order_normalized():
    value = failure_signature("family", {"checks": [{"check_id": "z", "status": "failed"}, {"check_id": "a", "status": "failed"}]})
    assert value["task_family"] == "family"
    assert value["structural"] == ["a", "z"]


def test_supported_recommendation_is_advisory_only(tmp_path: Path):
    for i in range(3):
        _task(tmp_path, f"t-{i}", passed=False)
        _append_intervention(tmp_path / f"t-{i}", source="deterministic_patch_retry", passed=True, patch_id="p")
    bundle = build_capability_cards([tmp_path])
    validation = {"structural_checks": [{"check_id": "parse_json", "status": "failed"}], "semantic_checks": [{"check_id": "reference_status", "status": "failed"}]}
    recommendation = recommend_intervention(task_family="scope-authority-boundary", validation=validation, available_interventions=["deterministic_patch_retry"], cards=bundle)
    assert recommendation["recommended_intervention"] == "deterministic_patch_retry"
    assert recommendation["evidence_status"] == "supported"
    assert recommendation["authority"] == "advisory_only"


def test_insufficient_and_malformed_evidence_fail_closed(tmp_path: Path):
    _task(tmp_path, "one", passed=False)
    bundle = build_capability_cards([tmp_path])
    assert bundle["cards"][0]["evidence"]["status"] == "observed"
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "trajectory.jsonl").write_text(json.dumps({"record_type": "worker_attempt", "intervention_source": "none", "transport_valid": True, "transport_classification": "model_response", "validation": None}) + "\n")
    (bad / "trajectory_summary.json").write_text(json.dumps({"task_id": "bad", "task_family": "x"}))
    with pytest.raises(CapabilityEvidenceError):
        build_capability_cards([bad])


def _card(source: str, signature: dict, task_ids: list[str], rescued: list[str], *, runs: list[str] | None = None, teacher_calls: int = 0) -> dict:
    return {
        "identity": {"intervention_type": source, "intervention_id": source},
        "context": {"source_runs": runs or ["run2"], "task_family": signature["task_family"], "failure_signature": signature},
        "observations": {
            "eligible_task_opportunities": len(task_ids), "eligible_attempts": len(task_ids),
            "valid_model_attempts": len(task_ids), "successes": len(rescued), "failures": len(task_ids) - len(rescued),
            "task_ids": task_ids, "rescued_task_ids": rescued, "rescued_tasks": len(rescued), "teacher_call_count": teacher_calls,
        },
        "provenance": {"source_runs": runs or ["run2"], "source_commits": [], "artifacts": []},
    }


def test_hierarchy_exact_supported_wins_and_backoff_is_labeled():
    target = {"task_family": "family", "structural": ["parse_json"], "semantic": ["reference_uncertainty"]}
    same_semantic = {"task_family": "family", "structural": ["required_fields"], "semantic": ["reference_uncertainty"]}
    cards = {"cards": [
        _card("deterministic_patch_retry", target, ["e1", "e2", "e3"], ["e1", "e2", "e3"]),
        _card("local_teacher", target, ["l1"], []),
        _card("local_teacher", same_semantic, ["l2", "l3", "l4"], ["l2", "l3", "l4"]),
    ]}
    hierarchy = build_hierarchical_evidence(cards)
    exact = recommend_intervention(task_family="family", validation={"structural_checks": [{"check_id": "parse_json", "status": "failed"}], "semantic_checks": [{"check_id": "reference_uncertainty", "status": "failed"}]}, available_interventions=["deterministic_patch_retry", "local_teacher"], cards={**cards, "hierarchy": hierarchy})
    assert exact["recommended_intervention"] == "deterministic_patch_retry"
    assert exact["evidence_resolution"] == "exact_signature"

    backoff = recommend_intervention(task_family="family", validation={"structural_checks": [{"check_id": "required_field_types", "status": "failed"}], "semantic_checks": [{"check_id": "reference_uncertainty", "status": "failed"}]}, available_interventions=["local_teacher"], cards={**cards, "hierarchy": hierarchy})
    assert backoff["recommended_intervention"] == "local_teacher"
    assert backoff["evidence_resolution"] == "semantic_signature"
    assert backoff["more_specific_evidence"]


def test_family_backoff_and_negative_evidence_abstention():
    family = "family"
    cards = {"cards": [
        _card("deterministic_patch_retry", {"task_family": family, "structural": ["parse_json"], "semantic": ["reference_uncertainty"]}, ["n1", "n2", "n3", "n4"], []),
        _card("local_teacher", {"task_family": family, "structural": ["required_fields"], "semantic": ["reference_must_include"]}, ["p1", "p2", "p3"], ["p1", "p2"]),
    ]}
    rec = recommend_intervention(task_family=family, validation={"structural_checks": [{"check_id": "required_field_types", "status": "failed"}], "semantic_checks": [{"check_id": "reference_queue_handoff_status", "status": "failed"}]}, available_interventions=["deterministic_patch_retry", "local_teacher"], cards=cards)
    assert rec["recommended_intervention"] == "local_teacher"
    assert rec["evidence_resolution"] == "task_family"
    assert rec["alternatives"][0]["evidence_polarity"] == "supported_negative"

    none = recommend_intervention(task_family="unknown-family", validation={"structural_checks": [{"check_id": "parse_json", "status": "failed"}], "semantic_checks": []}, available_interventions=["local_teacher"], cards=cards)
    assert none["routing_disposition"] == "abstain"
    assert none["recommended_intervention"] is None


def test_unknown_check_is_unclassified_and_accounting_does_not_double_count_teacher_passes(tmp_path: Path):
    assert failure_classes({"structural": ["future_check"], "semantic": [], "task_family": "x"}) == ["unclassified:future_check"]
    _task(tmp_path, "multi", passed=False)
    _append_intervention(tmp_path / "multi", source="local_teacher", passed=False, patch_id="")
    _append_intervention(tmp_path / "multi", source="local_teacher", passed=True, patch_id="")
    (tmp_path / "multi" / "local-teacher-1.json").write_text("{}")
    (tmp_path / "multi" / "local-teacher-2.json").write_text("{}")
    audit = build_accounting_audit([tmp_path])
    local = next(row for row in audit if row["intervention"] == "local_teacher")
    assert local["eligible_task_opportunities"] == 1
    assert local["worker_retry_attempts"] == 2
    assert local["rescued_tasks"] == 1
    assert local["teacher_calls"] == 2
