from __future__ import annotations

import json

import pytest

from local_harness.supervised_attempt_output_validator import (
    REQUIRED_VALIDATION_AUTHORITY_BOUNDARIES,
    SupervisedAttemptOutputValidationError,
    validate_supervised_attempt_output_against_contract,
    validate_supervised_attempt_output_validation_record,
)


def make_attempt_record(raw_output: str = '{"allowed_targets": [], "held_targets": [], "reason": "ok"}') -> dict:
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
        "raw_model_output": raw_output,
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


def make_validation_record(validation_status: str = "passed") -> dict:
    return {
        "validation_id": "validation_example_001",
        "attempt_id": "attempt_example_001",
        "triage_id": "triage_example_001",
        "orchestration_id": "orch_example_001",
        "prompt_packet_id": "prompt_packet_example_001",
        "validation_status": validation_status,
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
                "status": "passed",
                "message": "Raw model output parsed as JSON.",
            }
        ],
        "diagnostics": [],
        "raw_output_preserved": True,
        "authority_boundaries": list(REQUIRED_VALIDATION_AUTHORITY_BOUNDARIES),
        "provenance": {
            "source": "supervised_attempt_output_validation",
            "input_attempt_id": "attempt_example_001",
        },
        "review_required": True,
    }


def test_accepts_valid_passed_validation_record():
    record = make_validation_record("passed")
    validated = validate_supervised_attempt_output_validation_record(record)
    assert validated["validation_status"] == "passed"


def test_accepts_valid_failed_validation_record():
    record = make_validation_record("failed")
    record["checks"][0]["status"] = "failed"
    validated = validate_supervised_attempt_output_validation_record(record)
    assert validated["validation_status"] == "failed"


@pytest.mark.parametrize(
    "missing_key",
    [
        "validation_id",
        "attempt_id",
        "triage_id",
        "orchestration_id",
        "validation_status",
        "acceptance_status",
        "validated_at",
        "output_contract",
        "checks",
        "diagnostics",
        "raw_output_preserved",
        "authority_boundaries",
        "provenance",
        "review_required",
    ],
)
def test_rejects_missing_required_fields(missing_key):
    record = make_validation_record("passed")
    del record[missing_key]
    with pytest.raises(SupervisedAttemptOutputValidationError):
        validate_supervised_attempt_output_validation_record(record)


def test_rejects_acceptance_status_other_than_not_reviewed():
    record = make_validation_record("passed")
    record["acceptance_status"] = "accepted"
    with pytest.raises(SupervisedAttemptOutputValidationError, match="acceptance_status"):
        validate_supervised_attempt_output_validation_record(record)


def test_rejects_empty_checks():
    record = make_validation_record("failed")
    record["checks"] = []
    with pytest.raises(SupervisedAttemptOutputValidationError, match="checks"):
        validate_supervised_attempt_output_validation_record(record)


def test_rejects_raw_output_preserved_false():
    record = make_validation_record("passed")
    record["raw_output_preserved"] = False
    with pytest.raises(SupervisedAttemptOutputValidationError, match="raw_output_preserved"):
        validate_supervised_attempt_output_validation_record(record)


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
    record = make_validation_record("passed")
    record["authority_boundaries"] = list(REQUIRED_VALIDATION_AUTHORITY_BOUNDARIES) + [forbidden_text]
    with pytest.raises(SupervisedAttemptOutputValidationError, match="forbidden authority language"):
        validate_supervised_attempt_output_validation_record(record)


def test_rejects_records_that_claim_acceptance():
    record = make_validation_record("passed")
    record["diagnostics"] = ["output accepted for use"]
    with pytest.raises(SupervisedAttemptOutputValidationError, match="forbidden authority language"):
        validate_supervised_attempt_output_validation_record(record)


def test_passes_valid_json_output_with_required_fields_and_reason():
    attempt = make_attempt_record('{"allowed_targets": [], "held_targets": [], "reason": "ok"}')
    output_contract = {
        "format": "json",
        "requires_reason": True,
        "required_fields": ["allowed_targets", "held_targets", "reason"],
    }
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_001",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "passed"


def test_passes_valid_json_output_with_required_field_types():
    attempt = make_attempt_record(
        json.dumps(
            {
                "allowed_targets": [],
                "held_targets": [],
                "scope_expansion_required": False,
                "claims": [],
                "evidence_basis": [],
                "unverified_claims": [],
                "format": "json",
                "required_fields_present": True,
                "reason": "bounded",
            }
        )
    )
    output_contract = {"format": "json", "requires_reason": True, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_001_types",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "passed"


def test_rejects_duplicate_json_keys():
    attempt = make_attempt_record(
        '{"allowed_targets": [], "held_targets": [], "scope_expansion_required": false, "claims": [], "evidence_basis": [], "unverified_claims": [], "format": "json", "required_fields_present": true, "reason": "bounded", "required_fields_present": false}'
    )
    output_contract = {"format": "json", "requires_reason": True, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_dup_keys",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "failed"
    assert any(check["check_id"] == "duplicate_json_keys" and check["status"] == "failed" for check in record["checks"])
    assert "Duplicate JSON key in raw model output: required_fields_present" in "\n".join(record["diagnostics"])


def test_duplicate_required_fields_present_fails_even_if_last_value_is_valid():
    attempt = make_attempt_record(
        '{"allowed_targets": [], "held_targets": [], "scope_expansion_required": false, "claims": [], "evidence_basis": [], "unverified_claims": [], "format": "json", "required_fields_present": false, "reason": "bounded", "required_fields_present": true}'
    )
    output_contract = {"format": "json", "requires_reason": True, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_dup_required_fields_present",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "failed"
    assert any(check["check_id"] == "duplicate_json_keys" and check["status"] == "failed" for check in record["checks"])
    assert any(check["check_id"] == "required_field_types" and check["status"] == "passed" for check in record["checks"])
    assert "Duplicate JSON key in raw model output: required_fields_present" in "\n".join(record["diagnostics"])


def test_passes_when_allowed_targets_are_within_authorized_targets():
    attempt = make_attempt_record(
        '{"allowed_targets": ["docs/reports/"], "held_targets": [], "scope_expansion_required": false, "claims": [], "evidence_basis": [], "unverified_claims": [], "format": "json", "required_fields_present": true, "reason": "bounded"}'
    )
    output_contract = {"format": "json", "requires_reason": True, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_target_ok",
        validated_at="2026-07-06T00:00:00Z",
        authorized_targets=["docs/reports/"],
    )
    assert record["validation_status"] == "passed"
    assert any(check["check_id"] == "target_authority" and check["status"] == "passed" for check in record["checks"])


def test_rejects_unauthorized_allowed_targets():
    attempt = make_attempt_record(
        '{"allowed_targets": ["design_packet"], "held_targets": [], "scope_expansion_required": false, "claims": [], "evidence_basis": [], "unverified_claims": [], "format": "json", "required_fields_present": true, "reason": "bounded"}'
    )
    output_contract = {"format": "json", "requires_reason": True, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_target_bad",
        validated_at="2026-07-06T00:00:00Z",
        authorized_targets=["docs/reports/"],
    )
    assert record["validation_status"] == "failed"
    assert any(check["check_id"] == "target_authority" and check["status"] == "failed" for check in record["checks"])
    assert "Unauthorized allowed target in raw model output: design_packet" in "\n".join(record["diagnostics"])


def test_target_authority_not_applicable_without_structured_authority():
    attempt = make_attempt_record(
        '{"allowed_targets": ["design_packet"], "held_targets": [], "scope_expansion_required": false, "claims": [], "evidence_basis": [], "unverified_claims": [], "format": "json", "required_fields_present": true, "reason": "bounded"}'
    )
    output_contract = {"format": "json", "requires_reason": True, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_target_na",
        validated_at="2026-07-06T00:00:00Z",
        authorized_targets=None,
    )
    assert any(check["check_id"] == "target_authority" and check["status"] == "not_applicable" for check in record["checks"])


@pytest.mark.parametrize(
    "payload, expected_message",
    [
        ({"required_fields_present": ["true"]}, "required_fields_present must be boolean true"),
        ({"required_fields_present": False}, "required_fields_present must be boolean true"),
        ({"format": "yaml"}, 'format must be exactly "json"'),
        ({"allowed_targets": "docs"}, "allowed_targets must be a list"),
        ({"held_targets": "docs"}, "held_targets must be a list"),
        ({"scope_expansion_required": "false"}, "scope_expansion_required must be a boolean"),
        ({"claims": "claim"}, "claims must be a list"),
        ({"evidence_basis": "evidence"}, "evidence_basis must be a list"),
        ({"unverified_claims": "claim"}, "unverified_claims must be a list"),
    ],
)
def test_rejects_invalid_required_field_types(payload, expected_message):
    base = {
        "allowed_targets": [],
        "held_targets": [],
        "scope_expansion_required": False,
        "claims": [],
        "evidence_basis": [],
        "unverified_claims": [],
        "format": "json",
        "required_fields_present": True,
        "reason": "bounded",
    }
    base.update(payload)
    attempt = make_attempt_record(json.dumps(base))
    output_contract = {"format": "json", "requires_reason": True, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_types_bad",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "failed"
    assert any(check["check_id"] == "required_field_types" and check["status"] == "failed" for check in record["checks"])
    assert expected_message in "\n".join(record["diagnostics"])


def test_fails_malformed_json_output():
    attempt = make_attempt_record('{"allowed_targets": []')
    output_contract = {"format": "json", "requires_reason": False, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_002",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "failed"
    assert any(check["check_id"] == "parse_json" and check["status"] == "failed" for check in record["checks"])


def test_fails_missing_required_fields():
    attempt = make_attempt_record('{"allowed_targets": [], "reason": "ok"}')
    output_contract = {
        "format": "json",
        "requires_reason": True,
        "required_fields": ["allowed_targets", "held_targets", "reason"],
    }
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_003",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "failed"
    assert any(check["check_id"] == "required_fields" and check["status"] == "failed" for check in record["checks"])


def test_fails_empty_reason_when_requires_reason_true():
    attempt = make_attempt_record('{"allowed_targets": [], "held_targets": [], "reason": ""}')
    output_contract = {"format": "json", "requires_reason": True, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_004",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "failed"
    assert any(check["check_id"] == "requires_reason" and check["status"] == "failed" for check in record["checks"])


def test_passes_non_empty_reason_when_requires_reason_true():
    attempt = make_attempt_record('{"reason": "bounded"}')
    output_contract = {"format": "json", "requires_reason": True, "required_fields": ["reason"]}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_005",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "passed"


def test_preserves_attempt_triage_and_orchestration_ids_and_not_reviewed_status():
    attempt = make_attempt_record('{"reason": "ok"}')
    output_contract = {"format": "json", "requires_reason": True, "required_fields": ["reason"]}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_006",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["attempt_id"] == attempt["attempt_id"]
    assert record["triage_id"] == attempt["triage_id"]
    assert record["orchestration_id"] == attempt["orchestration_id"]
    assert record["acceptance_status"] == "not_reviewed"


def test_returns_structured_diagnostics():
    attempt = make_attempt_record('{"allowed_targets": []')
    output_contract = {"format": "json", "requires_reason": False, "required_fields": []}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_007",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert isinstance(record["diagnostics"], list)
    assert any("JSON parse failed" in message for message in record["diagnostics"])


def test_does_not_execute_or_transform_raw_output_into_actions():
    attempt = make_attempt_record('{"reason":"ok","note":"run this command"}')
    output_contract = {"format": "json", "requires_reason": True, "required_fields": ["reason"]}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_008",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert "actions" not in record
    assert record["raw_output_preserved"] is True


def test_does_not_require_semantic_correctness_beyond_output_contract():
    attempt = make_attempt_record('{"reason":"nonsensical but non-empty","held_targets":"wrong-type-but-allowed"}')
    output_contract = {"format": "json", "requires_reason": True, "required_fields": ["reason"]}
    record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt,
        output_contract=output_contract,
        validation_id="validation_009",
        validated_at="2026-07-06T00:00:00Z",
    )
    assert record["validation_status"] == "failed"
    assert any(check["check_id"] == "required_field_types" and check["status"] == "failed" for check in record["checks"])


def test_rejects_input_attempt_already_marked_accepted():
    attempt = make_attempt_record('{"reason":"ok"}')
    attempt["acceptance_status"] = "accepted"
    output_contract = {"format": "json", "requires_reason": True, "required_fields": ["reason"]}
    with pytest.raises(SupervisedAttemptOutputValidationError):
        validate_supervised_attempt_output_against_contract(
            attempt_record=attempt,
            output_contract=output_contract,
            validation_id="validation_010",
            validated_at="2026-07-06T00:00:00Z",
        )
