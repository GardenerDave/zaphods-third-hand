from __future__ import annotations

from local_harness.render_supervised_model_attempt import render_supervised_model_attempt
from local_harness.supervised_model_attempt import REQUIRED_AUTHORITY_BOUNDARIES


def make_record() -> dict:
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
        "raw_model_output": "{\"result\":\"raw\"}\nline2",
        "output_format_claim": "json",
        "validation_status": "not_validated",
        "acceptance_status": "not_reviewed",
        "authority_boundaries": list(REQUIRED_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "manual_record",
            "input_artifact": "model_prompt_packet",
            "raw_output_preserved": True,
        },
    }


def test_renders_all_required_sections():
    rendered = render_supervised_model_attempt(make_record())
    for heading in [
        "# Supervised Model Attempt Record",
        "## Attempt IDs",
        "## Model Metadata",
        "## Operator Metadata",
        "## Source Prompt Packet",
        "## Raw Model Output",
        "## Validation Status",
        "## Acceptance Status",
        "## Authority Boundaries",
        "## Provenance",
        "## Review Requirement",
    ]:
        assert heading in rendered


def test_includes_attempt_id_and_model_metadata():
    record = make_record()
    rendered = render_supervised_model_attempt(record)
    assert record["attempt_id"] in rendered
    assert '"model_id": "qwen3-1.7b-gpu-40k"' in rendered


def test_includes_raw_model_output_exactly():
    record = make_record()
    raw = "{\n  \"a\": 1\n}\nline two"
    record["raw_model_output"] = raw
    rendered = render_supervised_model_attempt(record)
    assert f"```text\n{raw}\n```" in rendered


def test_includes_validation_acceptance_authority_and_review_requirement():
    record = make_record()
    rendered = render_supervised_model_attempt(record)
    assert "validation_status: not_validated" in rendered
    assert "acceptance_status: not_reviewed" in rendered
    for boundary in REQUIRED_AUTHORITY_BOUNDARIES:
        assert f"- {boundary}" in rendered
    assert "Human review is required before downstream use." in rendered


def test_does_not_claim_acceptance_or_validation():
    rendered = render_supervised_model_attempt(make_record()).lower()
    assert "acceptance_status: accepted" not in rendered
    assert "validation_status: validated" not in rendered
