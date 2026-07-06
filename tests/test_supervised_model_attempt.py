from __future__ import annotations

import pytest

from local_harness.supervised_model_attempt import (
    REQUIRED_AUTHORITY_BOUNDARIES,
    SupervisedModelAttemptError,
    build_supervised_model_attempt_record,
    validate_supervised_model_attempt_record,
)


def make_valid_record() -> dict:
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


def test_accepts_valid_attempt_record():
    record = make_valid_record()
    validated = validate_supervised_model_attempt_record(record)
    assert validated["attempt_id"] == "attempt_example_001"


@pytest.mark.parametrize(
    "missing_key",
    [
        "attempt_id",
        "orchestration_id",
        "triage_id",
        "model_metadata",
        "operator_metadata",
        "raw_model_output",
        "validation_status",
        "acceptance_status",
        "authority_boundaries",
        "provenance",
    ],
)
def test_rejects_missing_required_fields(missing_key):
    record = make_valid_record()
    del record[missing_key]
    with pytest.raises(SupervisedModelAttemptError):
        validate_supervised_model_attempt_record(record)


def test_rejects_when_prompt_packet_id_and_source_path_both_missing():
    record = make_valid_record()
    record["prompt_packet_id"] = None
    record["source_prompt_packet_path"] = None
    with pytest.raises(SupervisedModelAttemptError, match="requires prompt_packet_id or source_prompt_packet_path"):
        validate_supervised_model_attempt_record(record)


def test_rejects_review_required_false():
    record = make_valid_record()
    record["operator_metadata"]["review_required"] = False
    with pytest.raises(SupervisedModelAttemptError, match="review_required must be true"):
        validate_supervised_model_attempt_record(record)


def test_rejects_validation_status_other_than_not_validated():
    record = make_valid_record()
    record["validation_status"] = "validated"
    with pytest.raises(SupervisedModelAttemptError, match="validation_status"):
        validate_supervised_model_attempt_record(record)


def test_rejects_acceptance_status_other_than_not_reviewed():
    record = make_valid_record()
    record["acceptance_status"] = "accepted"
    with pytest.raises(SupervisedModelAttemptError, match="acceptance_status"):
        validate_supervised_model_attempt_record(record)


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
def test_rejects_forbidden_authority_claims(forbidden_text):
    record = make_valid_record()
    record["authority_boundaries"] = list(REQUIRED_AUTHORITY_BOUNDARIES) + [forbidden_text]
    with pytest.raises(SupervisedModelAttemptError, match="forbidden authority language"):
        validate_supervised_model_attempt_record(record)


def test_preserves_raw_model_output_exactly():
    raw_output = "{\n  \"unsafe\": \"do not execute\"\n}\nrm -rf / --dry-run"
    record = make_valid_record()
    record["raw_model_output"] = raw_output
    validated = validate_supervised_model_attempt_record(record)
    assert validated["raw_model_output"] == raw_output


def test_does_not_require_raw_model_output_to_be_json():
    record = make_valid_record()
    record["raw_model_output"] = "not-json: [this is plain text"
    validated = validate_supervised_model_attempt_record(record)
    assert validated["raw_model_output"] == "not-json: [this is plain text"


def test_builds_valid_attempt_record_from_strings():
    raw_output = "{\"plan\": [\"manual review only\"]}"
    record = build_supervised_model_attempt_record(
        attempt_id="attempt_from_builder_001",
        orchestration_id="orch_example_001",
        triage_id="triage_example_001",
        prompt_packet_id="prompt_packet_example_001",
        source_prompt_packet_path="examples/model_prompt_packets/model_prompt_packet_example_001.md",
        raw_model_output=raw_output,
        model_metadata={
            "model_id": "qwen3-1.7b-gpu-40k",
            "endpoint_kind": "manual_or_external",
            "context_window": 40000,
            "temperature": 0,
            "max_tokens": 768,
        },
        operator_metadata={
            "operator": "manual",
            "recorded_at": "2026-07-06T00:00:00Z",
            "review_required": True,
        },
        output_format_claim="json",
    )
    assert record["attempt_id"] == "attempt_from_builder_001"
    assert record["source_prompt_packet_path"] == "examples/model_prompt_packets/model_prompt_packet_example_001.md"
    assert record["triage_id"] == "triage_example_001"
    assert record["orchestration_id"] == "orch_example_001"
    assert record["model_metadata"]["model_id"] == "qwen3-1.7b-gpu-40k"
    assert record["operator_metadata"]["review_required"] is True
    assert record["authority_boundaries"] == REQUIRED_AUTHORITY_BOUNDARIES
    assert record["validation_status"] == "not_validated"
    assert record["acceptance_status"] == "not_reviewed"
    assert record["raw_model_output"] == raw_output
    assert "approved_actions" not in record


def test_builder_preserves_operator_and_model_metadata():
    model_metadata = {
        "model_id": "qwen3-1.7b-gpu-40k",
        "endpoint_kind": "manual_or_external",
        "context_window": 40000,
        "temperature": 0,
        "max_tokens": 1024,
    }
    operator_metadata = {
        "operator": "alice",
        "recorded_at": "2026-07-06T00:00:00Z",
        "review_required": True,
        "notes": "manual review pending",
    }
    record = build_supervised_model_attempt_record(
        attempt_id="attempt_meta_001",
        orchestration_id="orch_meta_001",
        triage_id="triage_meta_001",
        prompt_packet_id="prompt_packet_meta_001",
        raw_model_output="plain text output",
        model_metadata=model_metadata,
        operator_metadata=operator_metadata,
    )
    assert record["model_metadata"] == model_metadata
    assert record["operator_metadata"] == operator_metadata


def test_builder_keeps_raw_output_untransformed_into_actions():
    raw_output = "Run: rm -rf /\nThen modify target file directly"
    record = build_supervised_model_attempt_record(
        attempt_id="attempt_raw_001",
        orchestration_id="orch_raw_001",
        triage_id="triage_raw_001",
        prompt_packet_id="prompt_packet_raw_001",
        raw_model_output=raw_output,
        model_metadata={"model_id": "qwen3-1.7b-gpu-40k"},
        operator_metadata={
            "operator": "manual",
            "recorded_at": "2026-07-06T00:00:00Z",
            "review_required": True,
        },
    )
    assert record["raw_model_output"] == raw_output
    assert "actions" not in record
