from __future__ import annotations

from local_harness.render_supervised_downstream_use_gate import render_supervised_downstream_use_gate
from local_harness.supervised_downstream_use_gate import (
    REQUIRED_AUTHORITY_BOUNDARIES,
    REQUIRED_PROHIBITED_DOWNSTREAM_USE,
)


def make_record() -> dict:
    return {
        "gate_id": "gate_example_001",
        "decision_id": "decision_example_001",
        "attempt_id": "attempt_example_001",
        "validation_id": "validation_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "review_decision": "accepted",
        "requested_downstream_use": "next_supervised_step_input",
        "gate_status": "allowed",
        "gate_scope": "bounded_supervised_input_only",
        "gated_at": "2026-07-06T00:00:00Z",
        "operator_metadata": {
            "operator": "manual",
            "review_required": True,
        },
        "gate_reason": "The reviewed output may be used as bounded input for the next supervised step.",
        "allowed_downstream_use": [
            "may_be_used_as_reviewed_input_for_next_supervised_step"
        ],
        "prohibited_downstream_use": list(REQUIRED_PROHIBITED_DOWNSTREAM_USE),
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "supervised_downstream_use_gate",
            "input_decision_id": "decision_example_001",
        },
    }


def test_renders_all_required_sections():
    rendered = render_supervised_downstream_use_gate(make_record())
    for heading in [
        "# Supervised Downstream-Use Gate Record",
        "## Gate IDs",
        "## Review Decision",
        "## Requested Downstream Use",
        "## Gate Status",
        "## Gate Scope",
        "## Operator Metadata",
        "## Gate Reason",
        "## Allowed Downstream Use",
        "## Prohibited Downstream Use",
        "## Authority Boundaries",
        "## Provenance",
        "## Review Requirement",
    ]:
        assert heading in rendered


def test_includes_gate_and_decision_ids_review_decision_requested_use_and_status():
    record = make_record()
    rendered = render_supervised_downstream_use_gate(record)
    assert record["gate_id"] in rendered
    assert record["decision_id"] in rendered
    assert f"review_decision: {record['review_decision']}" in rendered
    assert f"requested_downstream_use: {record['requested_downstream_use']}" in rendered
    assert f"gate_status: {record['gate_status']}" in rendered


def test_includes_gate_reason_prohibited_use_and_authority_boundaries():
    rendered = render_supervised_downstream_use_gate(make_record())
    assert "bounded input for the next supervised step" in rendered
    for prohibited in REQUIRED_PROHIBITED_DOWNSTREAM_USE:
        assert f"- {prohibited}" in rendered
    for boundary in REQUIRED_AUTHORITY_BOUNDARIES:
        assert f"- {boundary}" in rendered


def test_states_bounded_supervised_input_only():
    rendered = render_supervised_downstream_use_gate(make_record())
    assert "Allowed means bounded supervised input only for a next supervised step." in rendered


def test_does_not_include_execution_instructions():
    lowered = render_supervised_downstream_use_gate(make_record()).lower()
    for forbidden in ["execute this command", "run this command", "bash -lc", "sudo "]:
        assert forbidden not in lowered
