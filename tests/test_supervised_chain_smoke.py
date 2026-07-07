from __future__ import annotations

import pytest

from local_harness.supervised_chain_smoke import (
    REQUIRED_AUTHORITY_BOUNDARIES,
    REQUIRED_CHECK_IDS,
    SupervisedChainSmokeError,
    run_supervised_chain_smoke,
    validate_supervised_chain_smoke_record,
)


MESSY_INPUT = "The LoRA stuff and prompt injection got messy. We need to tie it back together."


def _build_record() -> dict:
    return run_supervised_chain_smoke(messy_input=MESSY_INPUT)


def test_builds_full_smoke_record_from_messy_input_fixture():
    record = _build_record()
    assert record["smoke_id"] == "supervised_chain_smoke_example_001"
    assert record["smoke_status"] == "passed"
    assert record["started_from"] == "messy_input_fixture"


def test_validates_every_generated_artifact():
    record = _build_record()
    validated = validate_supervised_chain_smoke_record(record)
    assert validated["smoke_id"] == record["smoke_id"]


def test_preserves_triage_and_orchestration_ids_through_chain():
    record = _build_record()
    chain = record["chain"]
    artifacts = record["artifacts"]
    assert chain["triage_id"] == artifacts["triage_packet"]["triage_id"]
    assert chain["orchestration_id"] == artifacts["orchestration_packet"]["orchestration_id"]


def test_preserves_attempt_validation_decision_and_gate_ids_through_chain():
    record = _build_record()
    chain = record["chain"]
    artifacts = record["artifacts"]
    assert chain["attempt_id"] == artifacts["supervised_model_attempt"]["attempt_id"]
    assert chain["validation_id"] == artifacts["output_validation"]["validation_id"]
    assert chain["decision_id"] == artifacts["review_decision"]["decision_id"]
    assert chain["gate_id"] == artifacts["downstream_use_gate"]["gate_id"]
    assert chain["handoff_id"] == artifacts["handoff_packet"]["handoff_id"]


def test_creates_prepared_handoff_only_after_allowed_gate():
    allowed_record = _build_record()
    assert allowed_record["artifacts"]["downstream_use_gate"]["gate_status"] == "allowed"
    assert allowed_record["artifacts"]["handoff_packet"]["handoff_status"] == "prepared"

    blocked_record = run_supervised_chain_smoke(messy_input=MESSY_INPUT, review_decision="revision_requested")
    assert blocked_record["artifacts"]["downstream_use_gate"]["gate_status"] == "blocked"
    assert blocked_record["artifacts"]["handoff_packet"]["handoff_status"] == "blocked"


def test_validation_is_evidence_not_automatic_acceptance():
    record = _build_record()
    assert record["artifacts"]["output_validation"]["acceptance_status"] == "not_reviewed"


def test_marks_raw_model_output_provenance_as_synthetic_fixture_output():
    record = _build_record()
    assert record["artifacts"]["supervised_model_attempt"]["provenance"]["source"] == "synthetic_fixture_output"


def test_does_not_call_model_or_endpoint_and_preserves_no_authority_boundaries():
    record = _build_record()
    attempt = record["artifacts"]["supervised_model_attempt"]
    assert attempt["model_metadata"]["provider"] == "none"
    assert "No command execution authority is granted." in attempt["authority_boundaries"]
    assert "No direct file modification authority is granted." in attempt["authority_boundaries"]


def test_does_not_grant_execution_file_patch_promotion_training_or_curriculum_authority():
    record = _build_record()
    prohibited = record["artifacts"]["handoff_packet"]["prohibited_downstream_use"]
    assert "no_command_execution" in prohibited
    assert "no_direct_file_modification" in prohibited
    assert "no_patch_application" in prohibited
    assert "no_automatic_patch_promotion" in prohibited
    assert "no_automatic_training" in prohibited
    assert "no_default_failure_to_curriculum_capture" in prohibited


def test_accepts_valid_smoke_record():
    record = _build_record()
    assert validate_supervised_chain_smoke_record(record)["smoke_status"] == "passed"


@pytest.mark.parametrize(
    "missing_key",
    [
        "smoke_id",
        "smoke_status",
        "started_from",
        "completed_at",
        "chain",
        "artifacts",
        "checks",
        "diagnostics",
        "authority_boundaries",
        "provenance",
    ],
)
def test_rejects_missing_required_fields(missing_key):
    record = _build_record()
    del record[missing_key]
    with pytest.raises(SupervisedChainSmokeError):
        validate_supervised_chain_smoke_record(record)


def test_rejects_unknown_smoke_status():
    record = _build_record()
    record["smoke_status"] = "unknown"
    with pytest.raises(SupervisedChainSmokeError, match="smoke_status"):
        validate_supervised_chain_smoke_record(record)


def test_rejects_empty_checks():
    record = _build_record()
    record["checks"] = []
    with pytest.raises(SupervisedChainSmokeError, match="checks"):
        validate_supervised_chain_smoke_record(record)


def test_rejects_failed_required_checks_when_smoke_status_is_passed():
    record = _build_record()
    record["checks"][0]["status"] = "failed"
    record["smoke_status"] = "passed"
    with pytest.raises(SupervisedChainSmokeError, match="smoke_status"):
        validate_supervised_chain_smoke_record(record)


def test_rejects_missing_required_check_ids():
    record = _build_record()
    record["checks"] = [
        check for check in record["checks"] if check["check_id"] != "triage_id_preserved"
    ]
    with pytest.raises(SupervisedChainSmokeError, match="missing required check_id"):
        validate_supervised_chain_smoke_record(record)


def test_rejects_forbidden_authority_language():
    record = _build_record()
    record["diagnostics"] = ["Execution authority granted."]
    with pytest.raises(SupervisedChainSmokeError, match="forbidden authority language"):
        validate_supervised_chain_smoke_record(record)


def test_rejects_authority_boundaries_that_omit_required_denials():
    record = _build_record()
    record["authority_boundaries"] = [
        boundary for boundary in REQUIRED_AUTHORITY_BOUNDARIES if "patch application" not in boundary
    ]
    with pytest.raises(SupervisedChainSmokeError, match="missing required authority boundaries"):
        validate_supervised_chain_smoke_record(record)


def test_includes_all_required_check_ids():
    record = _build_record()
    check_ids = {check["check_id"] for check in record["checks"]}
    assert REQUIRED_CHECK_IDS.issubset(check_ids)
