from __future__ import annotations

import pytest

from local_harness.supervised_downstream_use_gate import (
    REQUIRED_AUTHORITY_BOUNDARIES,
    REQUIRED_PROHIBITED_DOWNSTREAM_USE,
    SupervisedDownstreamUseGateError,
    build_supervised_downstream_use_gate_record,
    validate_supervised_downstream_use_gate_record,
)


def make_decision_record(decision: str = "accepted") -> dict:
    return {
        "decision_id": "decision_example_001",
        "attempt_id": "attempt_example_001",
        "validation_id": "validation_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "validation_status": "passed" if decision == "accepted" else "failed",
        "decision": decision,
        "decision_scope": "output_contract_only",
        "decided_at": "2026-07-06T00:00:00Z",
        "reviewer_metadata": {
            "reviewer": "manual",
            "review_required": True,
        },
        "decision_reason": "Reviewed decision with explicit supervised reasoning.",
        "allowed_downstream_use": ["may_be_used_as_reviewed_input_for_next_supervised_step"],
        "prohibited_downstream_use": [
            "no_command_execution",
            "no_direct_file_modification",
            "no_automatic_patch_promotion",
            "no_automatic_training",
            "no_default_failure_to_curriculum_capture",
        ],
        "authority_boundaries": [
            "Review decision is not command execution authority.",
            "No direct file modification authority is granted.",
            "No automatic patch promotion authority is granted.",
            "No automatic training authority is granted.",
            "No default failure-to-curriculum capture authority is granted.",
            "Downstream use must remain supervised.",
        ],
        "provenance": {
            "source": "supervised_review_decision",
            "input_attempt_id": "attempt_example_001",
            "input_validation_id": "validation_example_001",
        },
    }


def make_gate_record(gate_status: str = "allowed", review_decision: str = "accepted") -> dict:
    return {
        "gate_id": "gate_example_001",
        "decision_id": "decision_example_001",
        "attempt_id": "attempt_example_001",
        "validation_id": "validation_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "review_decision": review_decision,
        "requested_downstream_use": "next_supervised_step_input",
        "gate_status": gate_status,
        "gate_scope": "bounded_supervised_input_only",
        "gated_at": "2026-07-06T00:00:00Z",
        "operator_metadata": {
            "operator": "manual",
            "review_required": True,
        },
        "gate_reason": "The reviewed output may be used as bounded input for the next supervised step.",
        "allowed_downstream_use": [
            "may_be_used_as_reviewed_input_for_next_supervised_step"
        ]
        if gate_status == "allowed"
        else ["not_authorized_for_next_supervised_step_input"],
        "prohibited_downstream_use": list(REQUIRED_PROHIBITED_DOWNSTREAM_USE),
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "supervised_downstream_use_gate",
            "input_decision_id": "decision_example_001",
        },
    }


def test_accepts_valid_allowed_gate_record():
    record = make_gate_record("allowed", "accepted")
    assert validate_supervised_downstream_use_gate_record(record)["gate_status"] == "allowed"


def test_accepts_valid_blocked_gate_record():
    record = make_gate_record("blocked", "rejected")
    assert validate_supervised_downstream_use_gate_record(record)["gate_status"] == "blocked"


@pytest.mark.parametrize(
    "missing_key",
    [
        "gate_id",
        "decision_id",
        "attempt_id",
        "validation_id",
        "triage_id",
        "orchestration_id",
        "review_decision",
        "requested_downstream_use",
        "gate_status",
        "gate_scope",
        "gated_at",
        "operator_metadata",
        "gate_reason",
        "allowed_downstream_use",
        "prohibited_downstream_use",
        "authority_boundaries",
        "provenance",
    ],
)
def test_rejects_missing_required_fields(missing_key):
    record = make_gate_record()
    del record[missing_key]
    with pytest.raises(SupervisedDownstreamUseGateError):
        validate_supervised_downstream_use_gate_record(record)


def test_rejects_unknown_gate_status_values():
    record = make_gate_record()
    record["gate_status"] = "pending"
    with pytest.raises(SupervisedDownstreamUseGateError, match="gate_status"):
        validate_supervised_downstream_use_gate_record(record)


def test_rejects_empty_gate_reason():
    record = make_gate_record()
    record["gate_reason"] = ""
    with pytest.raises(SupervisedDownstreamUseGateError, match="gate_reason"):
        validate_supervised_downstream_use_gate_record(record)


def test_rejects_review_required_false():
    record = make_gate_record()
    record["operator_metadata"]["review_required"] = False
    with pytest.raises(SupervisedDownstreamUseGateError, match="review_required"):
        validate_supervised_downstream_use_gate_record(record)


def test_rejects_allowed_gate_when_review_decision_is_rejected():
    record = make_gate_record("allowed", "rejected")
    with pytest.raises(SupervisedDownstreamUseGateError, match="requires review_decision 'accepted'"):
        validate_supervised_downstream_use_gate_record(record)


def test_rejects_allowed_gate_when_review_decision_is_revision_requested():
    record = make_gate_record("allowed", "revision_requested")
    with pytest.raises(SupervisedDownstreamUseGateError, match="requires review_decision 'accepted'"):
        validate_supervised_downstream_use_gate_record(record)


@pytest.mark.parametrize(
    "forbidden_text",
    [
        "Execution authority granted.",
        "Direct file modification authority granted.",
        "Patch application authority granted.",
        "Automatic patch promotion authority granted.",
        "Automatic training authority granted.",
        "Default failure-to-curriculum capture authority granted.",
    ],
)
def test_rejects_forbidden_authority_language(forbidden_text):
    record = make_gate_record()
    record["authority_boundaries"] = list(REQUIRED_AUTHORITY_BOUNDARIES) + [forbidden_text]
    with pytest.raises(SupervisedDownstreamUseGateError, match="forbidden authority language"):
        validate_supervised_downstream_use_gate_record(record)


def test_builds_allowed_gate_from_accepted_decision():
    record = build_supervised_downstream_use_gate_record(
        gate_id="gate_build_001",
        decision_record=make_decision_record("accepted"),
        requested_downstream_use="next_supervised_step_input",
        operator_metadata={"operator": "manual", "review_required": True},
        gate_reason="Accepted output may be used as bounded supervised input.",
        gated_at="2026-07-06T00:00:00Z",
    )
    assert record["gate_status"] == "allowed"
    assert record["review_decision"] == "accepted"


def test_builds_blocked_gate_from_rejected_decision():
    record = build_supervised_downstream_use_gate_record(
        gate_id="gate_build_002",
        decision_record=make_decision_record("rejected"),
        requested_downstream_use="next_supervised_step_input",
        operator_metadata={"operator": "manual", "review_required": True},
        gate_reason="Rejected output is blocked from next supervised step input.",
        gated_at="2026-07-06T00:00:00Z",
    )
    assert record["gate_status"] == "blocked"
    assert record["review_decision"] == "rejected"


def test_builds_blocked_gate_from_revision_requested_decision():
    record = build_supervised_downstream_use_gate_record(
        gate_id="gate_build_003",
        decision_record=make_decision_record("revision_requested"),
        requested_downstream_use="next_supervised_step_input",
        operator_metadata={"operator": "manual", "review_required": True},
        gate_reason="Revision-requested output is blocked until supervised revision review.",
        gated_at="2026-07-06T00:00:00Z",
    )
    assert record["gate_status"] == "blocked"
    assert record["review_decision"] == "revision_requested"


def test_rejects_allowed_gate_from_rejected_decision():
    with pytest.raises(SupervisedDownstreamUseGateError, match="requires review_decision 'accepted'"):
        build_supervised_downstream_use_gate_record(
            gate_id="gate_build_004",
            decision_record=make_decision_record("rejected"),
            requested_downstream_use="next_supervised_step_input",
            operator_metadata={"operator": "manual", "review_required": True},
            gate_reason="must fail",
            gated_at="2026-07-06T00:00:00Z",
            gate_status="allowed",
        )


def test_rejects_allowed_gate_from_revision_requested_decision():
    with pytest.raises(SupervisedDownstreamUseGateError, match="requires review_decision 'accepted'"):
        build_supervised_downstream_use_gate_record(
            gate_id="gate_build_005",
            decision_record=make_decision_record("revision_requested"),
            requested_downstream_use="next_supervised_step_input",
            operator_metadata={"operator": "manual", "review_required": True},
            gate_reason="must fail",
            gated_at="2026-07-06T00:00:00Z",
            gate_status="allowed",
        )


def test_builder_preserves_decision_and_lineage_ids():
    record = build_supervised_downstream_use_gate_record(
        gate_id="gate_build_006",
        decision_record=make_decision_record("accepted"),
        requested_downstream_use="next_supervised_step_input",
        operator_metadata={"operator": "manual", "review_required": True},
        gate_reason="preserve ids",
        gated_at="2026-07-06T00:00:00Z",
    )
    assert record["decision_id"] == "decision_example_001"
    assert record["attempt_id"] == "attempt_example_001"
    assert record["validation_id"] == "validation_example_001"
    assert record["triage_id"] == "triage_example_001"
    assert record["orchestration_id"] == "orch_example_001"
    assert record["prompt_packet_id"] == "prompt_packet_example_001"


def test_builder_requires_explicit_operator_metadata():
    with pytest.raises(TypeError):
        build_supervised_downstream_use_gate_record(
            gate_id="gate_build_007",
            decision_record=make_decision_record("accepted"),
            requested_downstream_use="next_supervised_step_input",
            gate_reason="requires explicit metadata",
            gated_at="2026-07-06T00:00:00Z",
        )


def test_builder_requires_explicit_gate_reason():
    with pytest.raises(TypeError):
        build_supervised_downstream_use_gate_record(
            gate_id="gate_build_008",
            decision_record=make_decision_record("accepted"),
            requested_downstream_use="next_supervised_step_input",
            operator_metadata={"operator": "manual", "review_required": True},
            gated_at="2026-07-06T00:00:00Z",
        )


def test_builder_does_not_infer_execution_or_application_or_training_authority():
    record = build_supervised_downstream_use_gate_record(
        gate_id="gate_build_009",
        decision_record=make_decision_record("accepted"),
        requested_downstream_use="next_supervised_step_input",
        operator_metadata={"operator": "manual", "review_required": True},
        gate_reason="bounded downstream use only",
        gated_at="2026-07-06T00:00:00Z",
    )
    assert "no_command_execution" in record["prohibited_downstream_use"]
    assert "no_direct_file_modification" in record["prohibited_downstream_use"]
    assert "no_patch_application" in record["prohibited_downstream_use"]
    assert "no_automatic_patch_promotion" in record["prohibited_downstream_use"]
    assert "no_automatic_training" in record["prohibited_downstream_use"]
    assert "no_default_failure_to_curriculum_capture" in record["prohibited_downstream_use"]
