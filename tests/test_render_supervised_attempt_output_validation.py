from __future__ import annotations

from local_harness.render_supervised_attempt_output_validation import (
    render_supervised_attempt_output_validation,
)
from local_harness.supervised_attempt_output_validator import REQUIRED_VALIDATION_AUTHORITY_BOUNDARIES


def make_validation_record() -> dict:
    return {
        "validation_id": "validation_example_001",
        "attempt_id": "attempt_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "validation_status": "failed",
        "acceptance_status": "not_reviewed",
        "validated_at": "2026-07-06T00:00:00Z",
        "output_contract": {
            "format": "json",
            "requires_reason": True,
            "required_fields": ["allowed_targets", "held_targets", "reason"],
        },
        "checks": [
            {
                "check_id": "parse_json",
                "status": "failed",
                "message": "Raw model output is not valid JSON.",
            }
        ],
        "diagnostics": ["JSON parse failed: Expecting ',' delimiter at line 1, column 21"],
        "raw_output_preserved": True,
        "authority_boundaries": list(REQUIRED_VALIDATION_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "supervised_attempt_output_validation",
            "input_attempt_id": "attempt_example_001",
        },
        "review_required": True,
    }


def test_renders_all_required_sections():
    rendered = render_supervised_attempt_output_validation(make_validation_record())
    for heading in [
        "# Supervised Attempt Output Validation",
        "## Validation IDs",
        "## Validation Status",
        "## Acceptance Status",
        "## Output Contract",
        "## Checks",
        "## Diagnostics",
        "## Authority Boundaries",
        "## Provenance",
        "## Review Requirement",
    ]:
        assert heading in rendered


def test_includes_validation_and_attempt_ids():
    record = make_validation_record()
    rendered = render_supervised_attempt_output_validation(record)
    assert record["validation_id"] in rendered
    assert record["attempt_id"] in rendered


def test_includes_validation_and_acceptance_statuses():
    rendered = render_supervised_attempt_output_validation(make_validation_record())
    assert "validation_status: failed" in rendered
    assert "acceptance_status: not_reviewed" in rendered


def test_includes_output_contract_checks_and_diagnostics():
    rendered = render_supervised_attempt_output_validation(make_validation_record())
    assert '"format": "json"' in rendered
    assert "parse_json" in rendered
    assert "JSON parse failed" in rendered


def test_includes_authority_boundaries_and_evidence_statement():
    rendered = render_supervised_attempt_output_validation(make_validation_record())
    for boundary in REQUIRED_VALIDATION_AUTHORITY_BOUNDARIES:
        assert f"- {boundary}" in rendered
    assert "Validation is evidence, not acceptance." in rendered


def test_does_not_claim_acceptance():
    rendered = render_supervised_attempt_output_validation(make_validation_record()).lower()
    assert "accepted for use" not in rendered
    assert "output accepted" not in rendered


def test_does_not_include_execution_instructions():
    rendered = render_supervised_attempt_output_validation(make_validation_record()).lower()
    for forbidden in ["execute this command", "run this command", "bash -lc", "sudo "]:
        assert forbidden not in rendered
