from __future__ import annotations

import pytest

from local_harness.supervised_review_decision import (
    REQUIRED_AUTHORITY_BOUNDARIES,
    REQUIRED_PROHIBITED_DOWNSTREAM_USE,
    SupervisedReviewDecisionError,
    build_supervised_review_decision_record,
    validate_supervised_review_decision_record,
)


def make_attempt_record() -> dict:
    return {
        "attempt_id": "attempt_example_001",
        "orchestration_id": "orch_example_001",
        "triage_id": "triage_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "source_prompt_packet_path": "examples/model_prompt_packets/model_prompt_packet_example_001.md",
        "model_metadata": {
            "model_id": "qwen3-1.7b-gpu-40k",
            "endpoint_kind": "manual_or_external",
            "context_window": 40000,
            "temperature": 0,
            "max_tokens": 768,
        },
        "operator_metadata": {
            "operator": "manual",
            "recorded_at": "2026-07-06T00:00:00Z",
            "review_required": True,
        },
        "raw_model_output": '{"allowed_targets": [], "held_targets": [], "reason": "ok"}',
        "output_format_claim": "json",
        "validation_status": "not_validated",
        "acceptance_status": "not_reviewed",
        "authority_boundaries": [
            "No command execution authority is granted.",
            "No direct file modification authority is granted.",
            "No automatic patch promotion authority is granted.",
            "No automatic training authority is granted.",
            "No default failure-to-curriculum capture authority is granted.",
            "Human review is required before downstream use.",
        ],
        "provenance": {
            "source": "manual_record",
            "input_artifact": "model_prompt_packet",
            "raw_output_preserved": True,
            "orchestration_id": "orch_example_001",
            "triage_id": "triage_example_001",
            "prompt_packet_id": "prompt_packet_example_001",
            "source_prompt_packet_path": "examples/model_prompt_packets/model_prompt_packet_example_001.md",
        },
    }


def make_validation_record(status: str = "passed") -> dict:
    checks = [
        {"check_id": "parse_json", "status": "passed", "message": "Raw model output parsed as JSON."},
        {"check_id": "required_fields", "status": "passed", "message": "All required fields are present."},
    ]
    if status == "failed":
        checks[0]["status"] = "failed"
        checks[0]["message"] = "Raw model output is not valid JSON."
    return {
        "validation_id": "validation_example_001",
        "attempt_id": "attempt_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "validation_status": status,
        "acceptance_status": "not_reviewed",
        "validated_at": "2026-07-06T00:00:00Z",
        "output_contract": {
            "format": "json",
            "requires_reason": True,
            "required_fields": ["allowed_targets", "held_targets", "reason"],
        },
        "checks": checks,
        "diagnostics": [] if status == "passed" else ["JSON parse failed"],
        "raw_output_preserved": True,
        "authority_boundaries": [
            "Validation is evidence, not acceptance.",
            "No command execution authority is granted.",
            "No direct file modification authority is granted.",
            "No automatic patch promotion authority is granted.",
            "No automatic training authority is granted.",
            "No default failure-to-curriculum capture authority is granted.",
            "Human review is required before downstream use.",
        ],
        "provenance": {
            "source": "supervised_attempt_output_validation",
            "input_attempt_id": "attempt_example_001",
        },
        "review_required": True,
    }


def make_decision_record(decision: str = "accepted", validation_status: str = "passed") -> dict:
    return {
        "decision_id": "decision_example_001",
        "attempt_id": "attempt_example_001",
        "validation_id": "validation_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "validation_status": validation_status,
        "decision": decision,
        "decision_scope": "output_contract_only",
        "decided_at": "2026-07-06T00:00:00Z",
        "reviewer_metadata": {
            "reviewer": "manual",
            "review_required": True,
        },
        "decision_reason": "Reviewed decision with explicit supervised reasoning.",
        "allowed_downstream_use": ["may_be_used_as_reviewed_input_for_next_supervised_step"],
        "prohibited_downstream_use": list(REQUIRED_PROHIBITED_DOWNSTREAM_USE),
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "supervised_review_decision",
            "input_attempt_id": "attempt_example_001",
            "input_validation_id": "validation_example_001",
        },
    }


def test_accepts_valid_accepted_decision_record():
    record = make_decision_record("accepted", "passed")
    assert validate_supervised_review_decision_record(record)["decision"] == "accepted"


def test_accepts_valid_rejected_decision_record():
    record = make_decision_record("rejected", "failed")
    assert validate_supervised_review_decision_record(record)["decision"] == "rejected"


def test_accepts_valid_revision_requested_decision_record():
    record = make_decision_record("revision_requested", "failed")
    assert validate_supervised_review_decision_record(record)["decision"] == "revision_requested"


@pytest.mark.parametrize(
    "missing_key",
    [
        "decision_id",
        "attempt_id",
        "validation_id",
        "triage_id",
        "orchestration_id",
        "validation_status",
        "decision",
        "decision_scope",
        "decided_at",
        "reviewer_metadata",
        "decision_reason",
        "allowed_downstream_use",
        "prohibited_downstream_use",
        "authority_boundaries",
        "provenance",
    ],
)
def test_rejects_missing_required_fields(missing_key):
    record = make_decision_record()
    del record[missing_key]
    with pytest.raises(SupervisedReviewDecisionError):
        validate_supervised_review_decision_record(record)


def test_rejects_unknown_decision_values():
    record = make_decision_record()
    record["decision"] = "unknown"
    with pytest.raises(SupervisedReviewDecisionError, match="decision must be one of"):
        validate_supervised_review_decision_record(record)


def test_rejects_empty_decision_reason():
    record = make_decision_record()
    record["decision_reason"] = ""
    with pytest.raises(SupervisedReviewDecisionError, match="decision_reason"):
        validate_supervised_review_decision_record(record)


def test_rejects_review_required_false():
    record = make_decision_record()
    record["reviewer_metadata"]["review_required"] = False
    with pytest.raises(SupervisedReviewDecisionError, match="review_required"):
        validate_supervised_review_decision_record(record)


def test_rejects_accepted_decision_when_validation_failed():
    record = make_decision_record("accepted", "failed")
    with pytest.raises(SupervisedReviewDecisionError, match="accepted decision requires validation_status"):
        validate_supervised_review_decision_record(record)


@pytest.mark.parametrize(
    "forbidden_text",
    [
        "Execution authority granted.",
        "Direct file modification authority granted.",
        "Automatic patch promotion authority granted.",
        "Automatic training authority granted.",
        "Default failure-to-curriculum capture authority granted.",
    ],
)
def test_rejects_forbidden_authority_language(forbidden_text):
    record = make_decision_record()
    record["authority_boundaries"] = list(REQUIRED_AUTHORITY_BOUNDARIES) + [forbidden_text]
    with pytest.raises(SupervisedReviewDecisionError, match="forbidden authority language"):
        validate_supervised_review_decision_record(record)


def test_builds_accepted_record_from_passed_validation():
    attempt = make_attempt_record()
    validation = make_validation_record("passed")
    record = build_supervised_review_decision_record(
        decision_id="decision_build_001",
        attempt_record=attempt,
        validation_record=validation,
        decision="accepted",
        decision_reason="Passed contract checks and approved for bounded supervised use.",
        decided_at="2026-07-06T00:00:00Z",
        reviewer_metadata={"reviewer": "manual", "review_required": True},
    )
    assert record["decision"] == "accepted"
    assert record["validation_status"] == "passed"


def test_builds_rejected_record_from_failed_validation():
    attempt = make_attempt_record()
    validation = make_validation_record("failed")
    record = build_supervised_review_decision_record(
        decision_id="decision_build_002",
        attempt_record=attempt,
        validation_record=validation,
        decision="rejected",
        decision_reason="Validation failed, rejected pending correction.",
        decided_at="2026-07-06T00:00:00Z",
        reviewer_metadata={"reviewer": "manual", "review_required": True},
    )
    assert record["decision"] == "rejected"
    assert record["validation_status"] == "failed"


def test_builder_rejects_accepted_decision_from_failed_validation():
    attempt = make_attempt_record()
    validation = make_validation_record("failed")
    with pytest.raises(SupervisedReviewDecisionError, match="accepted decision requires validation_status"):
        build_supervised_review_decision_record(
            decision_id="decision_build_003",
            attempt_record=attempt,
            validation_record=validation,
            decision="accepted",
            decision_reason="should fail",
            decided_at="2026-07-06T00:00:00Z",
            reviewer_metadata={"reviewer": "manual", "review_required": True},
        )


def test_builder_rejects_mismatched_attempt_ids():
    attempt = make_attempt_record()
    validation = make_validation_record("passed")
    validation["attempt_id"] = "attempt_other_001"
    validation["provenance"]["input_attempt_id"] = "attempt_other_001"
    with pytest.raises(SupervisedReviewDecisionError, match="attempt_id mismatch"):
        build_supervised_review_decision_record(
            decision_id="decision_build_004",
            attempt_record=attempt,
            validation_record=validation,
            decision="rejected",
            decision_reason="mismatch",
            decided_at="2026-07-06T00:00:00Z",
            reviewer_metadata={"reviewer": "manual", "review_required": True},
        )


def test_builder_preserves_ids_and_validation_evidence():
    attempt = make_attempt_record()
    validation = make_validation_record("passed")
    record = build_supervised_review_decision_record(
        decision_id="decision_build_005",
        attempt_record=attempt,
        validation_record=validation,
        decision="accepted",
        decision_reason="explicit manual acceptance with bounded scope",
        decided_at="2026-07-06T00:00:00Z",
        reviewer_metadata={"reviewer": "manual", "review_required": True},
    )
    assert record["triage_id"] == attempt["triage_id"]
    assert record["orchestration_id"] == attempt["orchestration_id"]
    assert record["prompt_packet_id"] == attempt["prompt_packet_id"]
    assert record["validation_id"] == validation["validation_id"]
    assert record["validation_status"] == validation["validation_status"]


def test_builder_requires_explicit_reviewer_metadata():
    attempt = make_attempt_record()
    validation = make_validation_record("passed")
    with pytest.raises(TypeError):
        build_supervised_review_decision_record(
            decision_id="decision_build_006",
            attempt_record=attempt,
            validation_record=validation,
            decision="accepted",
            decision_reason="has reason",
            decided_at="2026-07-06T00:00:00Z",
        )


def test_builder_requires_explicit_decision_reason():
    attempt = make_attempt_record()
    validation = make_validation_record("passed")
    with pytest.raises(TypeError):
        build_supervised_review_decision_record(
            decision_id="decision_build_007",
            attempt_record=attempt,
            validation_record=validation,
            decision="accepted",
            decided_at="2026-07-06T00:00:00Z",
            reviewer_metadata={"reviewer": "manual", "review_required": True},
        )


def test_builder_does_not_infer_acceptance_automatically():
    attempt = make_attempt_record()
    validation = make_validation_record("passed")
    record = build_supervised_review_decision_record(
        decision_id="decision_build_008",
        attempt_record=attempt,
        validation_record=validation,
        decision="revision_requested",
        decision_reason="validation passed but scope notes require revision",
        decided_at="2026-07-06T00:00:00Z",
        reviewer_metadata={"reviewer": "manual", "review_required": True},
    )
    assert record["validation_status"] == "passed"
    assert record["decision"] == "revision_requested"
