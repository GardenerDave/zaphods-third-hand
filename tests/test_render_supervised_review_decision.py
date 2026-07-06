from __future__ import annotations

from local_harness.render_supervised_review_decision import render_supervised_review_decision
from local_harness.supervised_review_decision import (
    REQUIRED_AUTHORITY_BOUNDARIES,
    REQUIRED_PROHIBITED_DOWNSTREAM_USE,
)


def make_record() -> dict:
    return {
        "decision_id": "decision_example_001",
        "attempt_id": "attempt_example_001",
        "validation_id": "validation_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "validation_status": "passed",
        "decision": "accepted",
        "decision_scope": "output_contract_only",
        "decided_at": "2026-07-06T00:00:00Z",
        "reviewer_metadata": {
            "reviewer": "manual",
            "review_required": True,
        },
        "decision_reason": "Passed contract checks and explicitly approved for bounded supervised use.",
        "allowed_downstream_use": [
            "may_be_used_as_reviewed_input_for_next_supervised_step"
        ],
        "prohibited_downstream_use": list(REQUIRED_PROHIBITED_DOWNSTREAM_USE),
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "supervised_review_decision",
            "input_attempt_id": "attempt_example_001",
            "input_validation_id": "validation_example_001",
        },
    }


def test_renders_all_required_sections():
    rendered = render_supervised_review_decision(make_record())
    for heading in [
        "# Supervised Review Decision Record",
        "## Decision IDs",
        "## Decision",
        "## Validation Evidence",
        "## Reviewer Metadata",
        "## Decision Reason",
        "## Allowed Downstream Use",
        "## Prohibited Downstream Use",
        "## Authority Boundaries",
        "## Provenance",
        "## Review Requirement",
    ]:
        assert heading in rendered


def test_includes_ids_decision_and_validation_status():
    record = make_record()
    rendered = render_supervised_review_decision(record)
    assert record["decision_id"] in rendered
    assert record["attempt_id"] in rendered
    assert record["validation_id"] in rendered
    assert f"decision: {record['decision']}" in rendered
    assert f"validation_status: {record['validation_status']}" in rendered


def test_includes_reviewer_metadata_reason_authority_and_prohibited_use():
    rendered = render_supervised_review_decision(make_record())
    assert '"reviewer": "manual"' in rendered
    assert "explicitly approved for bounded supervised use" in rendered
    for boundary in REQUIRED_AUTHORITY_BOUNDARIES:
        assert f"- {boundary}" in rendered
    for prohibited in REQUIRED_PROHIBITED_DOWNSTREAM_USE:
        assert f"- {prohibited}" in rendered


def test_states_validation_is_evidence_not_automatic_acceptance():
    rendered = render_supervised_review_decision(make_record())
    assert "Validation is evidence, not automatic acceptance." in rendered


def test_does_not_include_execution_instructions():
    lowered = render_supervised_review_decision(make_record()).lower()
    for forbidden in ["execute this command", "run this command", "bash -lc", "sudo "]:
        assert forbidden not in lowered
