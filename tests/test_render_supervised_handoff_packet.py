from __future__ import annotations

from local_harness.render_supervised_handoff_packet import render_supervised_handoff_packet
from local_harness.supervised_handoff_packet import (
    REQUIRED_AUTHORITY_BOUNDARIES,
    REQUIRED_PROHIBITED_DOWNSTREAM_USE,
)


def make_record() -> dict:
    return {
        "handoff_id": "handoff_example_001",
        "gate_id": "gate_example_001",
        "decision_id": "decision_example_001",
        "attempt_id": "attempt_example_001",
        "validation_id": "validation_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "gate_status": "allowed",
        "handoff_status": "prepared",
        "handoff_scope": "bounded_supervised_input_only",
        "next_step_type": "next_supervised_step_input",
        "next_step_summary": "Use the reviewed output as bounded input for the next supervised planning step.",
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
        "handoff_reason": "Downstream-use gate allowed bounded supervised input for the next step.",
        "allowed_downstream_use": [
            "may_be_used_as_reviewed_input_for_next_supervised_step"
        ],
        "prohibited_downstream_use": list(REQUIRED_PROHIBITED_DOWNSTREAM_USE),
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "supervised_handoff_packet",
            "input_gate_id": "gate_example_001",
        },
    }


def test_renders_all_required_sections():
    rendered = render_supervised_handoff_packet(make_record())
    for heading in [
        "# Supervised Handoff Packet",
        "## Handoff IDs",
        "## Gate Status",
        "## Handoff Status",
        "## Handoff Scope",
        "## Next Step",
        "## Handoff Payload",
        "## Operator Metadata",
        "## Handoff Reason",
        "## Allowed Downstream Use",
        "## Prohibited Downstream Use",
        "## Authority Boundaries",
        "## Provenance",
        "## Review Requirement",
    ]:
        assert heading in rendered


def test_includes_handoff_gate_and_decision_ids_and_statuses():
    record = make_record()
    rendered = render_supervised_handoff_packet(record)
    assert record["handoff_id"] in rendered
    assert record["gate_id"] in rendered
    assert record["decision_id"] in rendered
    assert f"gate_status: {record['gate_status']}" in rendered
    assert f"handoff_status: {record['handoff_status']}" in rendered


def test_includes_next_step_payload_prohibited_use_and_boundaries():
    rendered = render_supervised_handoff_packet(make_record())
    assert "next_step_type: next_supervised_step_input" in rendered
    assert "Use the reviewed output as bounded input" in rendered
    assert '"payload_kind": "reviewed_model_output_reference"' in rendered
    for prohibited in REQUIRED_PROHIBITED_DOWNSTREAM_USE:
        assert f"- {prohibited}" in rendered
    for boundary in REQUIRED_AUTHORITY_BOUNDARIES:
        assert f"- {boundary}" in rendered


def test_states_bounded_supervised_input_only():
    rendered = render_supervised_handoff_packet(make_record())
    assert "Handoff means bounded supervised input only for the next supervised step." in rendered


def test_does_not_include_execution_instructions():
    lowered = render_supervised_handoff_packet(make_record()).lower()
    for forbidden in ["execute this command", "run this command", "bash -lc", "sudo "]:
        assert forbidden not in lowered
