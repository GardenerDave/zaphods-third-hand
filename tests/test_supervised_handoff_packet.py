from __future__ import annotations

import pytest

from local_harness.supervised_handoff_packet import (
    REQUIRED_AUTHORITY_BOUNDARIES,
    REQUIRED_PROHIBITED_DOWNSTREAM_USE,
    SupervisedHandoffPacketError,
    build_supervised_handoff_packet,
    validate_supervised_handoff_packet,
)


def make_gate_record(gate_status: str = "allowed") -> dict:
    return {
        "gate_id": "gate_example_001",
        "decision_id": "decision_example_001",
        "attempt_id": "attempt_example_001",
        "validation_id": "validation_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "review_decision": "accepted" if gate_status == "allowed" else "rejected",
        "requested_downstream_use": "next_supervised_step_input",
        "gate_status": gate_status,
        "gate_scope": "bounded_supervised_input_only",
        "gated_at": "2026-07-06T00:00:00Z",
        "operator_metadata": {
            "operator": "manual",
            "review_required": True,
        },
        "gate_reason": "Gate decision for bounded supervised next-step input.",
        "allowed_downstream_use": [
            "may_be_used_as_reviewed_input_for_next_supervised_step"
            if gate_status == "allowed"
            else "not_authorized_for_next_supervised_step_input"
        ],
        "prohibited_downstream_use": [
            "no_command_execution",
            "no_direct_file_modification",
            "no_patch_application",
            "no_automatic_patch_promotion",
            "no_automatic_training",
            "no_default_failure_to_curriculum_capture",
        ],
        "authority_boundaries": [
            "Downstream-use gate is not command execution authority.",
            "Downstream-use gate is not file modification authority.",
            "Downstream-use gate is not patch application authority.",
            "No automatic patch promotion authority is granted.",
            "No automatic training authority is granted.",
            "No default failure-to-curriculum capture authority is granted.",
            "Downstream use must remain supervised.",
        ],
        "provenance": {
            "source": "supervised_downstream_use_gate",
            "input_decision_id": "decision_example_001",
        },
    }


def make_handoff_record(handoff_status: str = "prepared", gate_status: str = "allowed") -> dict:
    return {
        "handoff_id": "handoff_example_001",
        "gate_id": "gate_example_001",
        "decision_id": "decision_example_001",
        "attempt_id": "attempt_example_001",
        "validation_id": "validation_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "gate_status": gate_status,
        "handoff_status": handoff_status,
        "handoff_scope": "bounded_supervised_input_only",
        "next_step_type": "next_supervised_step_input",
        "next_step_summary": "Use the reviewed output as bounded input for the next supervised planning step.",
        "next_step_objective": "Produce the bounded downstream comparison report.",
        "handoff_payload": {
            "payload_kind": "reviewed_model_output_reference",
            "source_attempt_id": "attempt_example_001",
            "source_validation_id": "validation_example_001",
            "source_decision_id": "decision_example_001",
            "source_gate_id": "gate_example_001",
        },
        "operator_metadata": {
            "operator": "manual",
            "review_required": True,
        },
        "handoff_reason": "Downstream-use gate allowed bounded supervised input for the next step."
        if handoff_status == "prepared"
        else "Gate blocked downstream use, so handoff is blocked.",
        "allowed_downstream_use": [
            "may_be_used_as_reviewed_input_for_next_supervised_step"
            if handoff_status == "prepared"
            else "not_authorized_for_next_supervised_step_input"
        ],
        "prohibited_downstream_use": list(REQUIRED_PROHIBITED_DOWNSTREAM_USE),
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "supervised_handoff_packet",
            "input_gate_id": "gate_example_001",
        },
    }


def test_accepts_valid_prepared_handoff_packet():
    record = make_handoff_record("prepared", "allowed")
    assert validate_supervised_handoff_packet(record)["handoff_status"] == "prepared"


def test_accepts_valid_blocked_handoff_packet():
    record = make_handoff_record("blocked", "blocked")
    assert validate_supervised_handoff_packet(record)["handoff_status"] == "blocked"


@pytest.mark.parametrize(
    "missing_key",
    [
        "handoff_id",
        "gate_id",
        "decision_id",
        "attempt_id",
        "validation_id",
        "triage_id",
        "orchestration_id",
        "gate_status",
        "handoff_status",
        "handoff_scope",
        "next_step_type",
        "next_step_summary",
        "handoff_payload",
        "operator_metadata",
        "handoff_reason",
        "allowed_downstream_use",
        "prohibited_downstream_use",
        "authority_boundaries",
        "provenance",
    ],
)
def test_rejects_missing_required_fields(missing_key):
    record = make_handoff_record()
    del record[missing_key]
    with pytest.raises(SupervisedHandoffPacketError):
        validate_supervised_handoff_packet(record)


def test_rejects_unknown_handoff_status_values():
    record = make_handoff_record()
    record["handoff_status"] = "pending"
    with pytest.raises(SupervisedHandoffPacketError, match="handoff_status"):
        validate_supervised_handoff_packet(record)


def test_rejects_empty_next_step_summary():
    record = make_handoff_record()
    record["next_step_summary"] = ""
    with pytest.raises(SupervisedHandoffPacketError, match="next_step_summary"):
        validate_supervised_handoff_packet(record)


def test_rejects_empty_handoff_reason():
    record = make_handoff_record()
    record["handoff_reason"] = ""
    with pytest.raises(SupervisedHandoffPacketError, match="handoff_reason"):
        validate_supervised_handoff_packet(record)


def test_rejects_review_required_false():
    record = make_handoff_record()
    record["operator_metadata"]["review_required"] = False
    with pytest.raises(SupervisedHandoffPacketError, match="review_required"):
        validate_supervised_handoff_packet(record)


def test_rejects_prepared_handoff_when_gate_status_blocked():
    record = make_handoff_record("prepared", "blocked")
    with pytest.raises(SupervisedHandoffPacketError, match="requires gate_status 'allowed'"):
        validate_supervised_handoff_packet(record)


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
    record = make_handoff_record()
    record["authority_boundaries"] = list(REQUIRED_AUTHORITY_BOUNDARIES) + [forbidden_text]
    with pytest.raises(SupervisedHandoffPacketError, match="forbidden authority language"):
        validate_supervised_handoff_packet(record)


def test_builds_prepared_handoff_from_allowed_gate():
    record = build_supervised_handoff_packet(
        handoff_id="handoff_build_001",
        gate_record=make_gate_record("allowed"),
        next_step_type="next_supervised_step_input",
        next_step_summary="Use reviewed output as bounded input for next supervised step.",
        next_step_objective="Produce the bounded downstream comparison report.",
        handoff_payload={"payload_kind": "reviewed_model_output_reference"},
        operator_metadata={"operator": "manual", "review_required": True},
        handoff_reason="Allowed gate permits bounded supervised handoff.",
    )
    assert record["handoff_status"] == "prepared"
    assert record["gate_status"] == "allowed"


def test_builds_blocked_handoff_from_blocked_gate():
    record = build_supervised_handoff_packet(
        handoff_id="handoff_build_002",
        gate_record=make_gate_record("blocked"),
        next_step_type="next_supervised_step_input",
        next_step_summary="Gate blocked use as next supervised input.",
        next_step_objective="Produce the bounded downstream comparison report.",
        handoff_payload={"payload_kind": "reviewed_model_output_reference"},
        operator_metadata={"operator": "manual", "review_required": True},
        handoff_reason="Blocked gate forces blocked handoff.",
    )
    assert record["handoff_status"] == "blocked"
    assert record["gate_status"] == "blocked"


def test_rejects_prepared_handoff_from_blocked_gate():
    with pytest.raises(SupervisedHandoffPacketError, match="requires gate_status 'allowed'"):
        build_supervised_handoff_packet(
            handoff_id="handoff_build_003",
            gate_record=make_gate_record("blocked"),
            next_step_type="next_supervised_step_input",
            next_step_summary="must fail",
            next_step_objective="Produce the bounded downstream comparison report.",
            handoff_payload={"payload_kind": "reviewed_model_output_reference"},
            operator_metadata={"operator": "manual", "review_required": True},
            handoff_reason="must fail",
            handoff_status="prepared",
        )


def test_builder_preserves_lineage_ids():
    record = build_supervised_handoff_packet(
        handoff_id="handoff_build_004",
        gate_record=make_gate_record("allowed"),
        next_step_type="next_supervised_step_input",
        next_step_summary="preserve ids",
        next_step_objective="Produce the bounded downstream comparison report.",
        handoff_payload={"payload_kind": "reviewed_model_output_reference"},
        operator_metadata={"operator": "manual", "review_required": True},
        handoff_reason="preserve lineage",
    )
    assert record["gate_id"] == "gate_example_001"
    assert record["decision_id"] == "decision_example_001"
    assert record["attempt_id"] == "attempt_example_001"
    assert record["validation_id"] == "validation_example_001"
    assert record["triage_id"] == "triage_example_001"
    assert record["orchestration_id"] == "orch_example_001"
    assert record["prompt_packet_id"] == "prompt_packet_example_001"


def test_builder_requires_explicit_operator_metadata():
    with pytest.raises(TypeError):
        build_supervised_handoff_packet(
            handoff_id="handoff_build_005",
            gate_record=make_gate_record("allowed"),
            next_step_type="next_supervised_step_input",
            next_step_summary="requires metadata",
            next_step_objective="Produce the bounded downstream comparison report.",
            handoff_payload={"payload_kind": "reviewed_model_output_reference"},
            handoff_reason="has reason",
        )


def test_builder_requires_explicit_next_step_summary():
    with pytest.raises(TypeError):
        build_supervised_handoff_packet(
            handoff_id="handoff_build_006",
            gate_record=make_gate_record("allowed"),
            next_step_type="next_supervised_step_input",
            handoff_payload={"payload_kind": "reviewed_model_output_reference"},
            operator_metadata={"operator": "manual", "review_required": True},
            handoff_reason="has reason",
        )


def test_builder_requires_explicit_handoff_reason():
    with pytest.raises(TypeError):
        build_supervised_handoff_packet(
            handoff_id="handoff_build_007",
            gate_record=make_gate_record("allowed"),
            next_step_type="next_supervised_step_input",
            next_step_summary="has summary",
            next_step_objective="Produce the bounded downstream comparison report.",
            handoff_payload={"payload_kind": "reviewed_model_output_reference"},
            operator_metadata={"operator": "manual", "review_required": True},
        )


def test_builder_does_not_infer_execution_or_application_or_training_authority():
    record = build_supervised_handoff_packet(
        handoff_id="handoff_build_008",
        gate_record=make_gate_record("allowed"),
        next_step_type="next_supervised_step_input",
        next_step_summary="bounded handoff only",
        next_step_objective="Produce the bounded downstream comparison report.",
        handoff_payload={"payload_kind": "reviewed_model_output_reference"},
        operator_metadata={"operator": "manual", "review_required": True},
        handoff_reason="bounded only",
    )
    assert "no_command_execution" in record["prohibited_downstream_use"]
    assert "no_direct_file_modification" in record["prohibited_downstream_use"]
    assert "no_patch_application" in record["prohibited_downstream_use"]
    assert "no_automatic_patch_promotion" in record["prohibited_downstream_use"]
    assert "no_automatic_training" in record["prohibited_downstream_use"]
    assert "no_default_failure_to_curriculum_capture" in record["prohibited_downstream_use"]
