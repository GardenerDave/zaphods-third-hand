from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.validate_queue_approval_path import (
    QueueApprovalPathError,
    validate_queue_approval_path,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "validate_queue_approval_path.py"


def valid_packet() -> dict:
    return {
        "approval_schema": "queue_approval_path_v1",
        "source_review_schema": "queue_handoff_review_v1",
        "source_review_path": "docs/reports/model_auditions/QUEUE_HANDOFF_REVIEW_FIXTURES_2026-07-17.md",
        "source_queue_handoff_review_status": "approved_for_queue_candidate",
        "queue_approval_status": "approved_for_manual_queue_insertion_candidate",
        "approval_scope": "Candidate-only manual review scope.",
        "reviewer_note": "Review-only manual candidate approval.",
        "required_checks": [
            "queue-handoff review is approved_for_queue_candidate",
            "manual review only",
        ],
        "authority_boundary": [
            "no_unattended_execution",
            "no_repo_mutation_without_review",
            "no_training_capture",
            "no_promotion",
            "no_deployment",
            "no_downstream_use_authority",
            "no_queue_insertion_without_explicit_approval",
            "no_queue_writing",
            "no_automatic_queue_handoff",
            "no_queue_running",
        ],
        "automation_status": "not_automated",
        "queue_insertion_status": "not_inserted",
        "queue_writing_status": "not_implemented",
        "repo_mutation_status": "not_authorized",
        "downstream_use_status": "prohibited_until_review",
        "diagnostics": [],
        "recommended_next_step": "Retain as a candidate-only review artifact.",
    }


def run_cli(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_valid_approved_candidate_passes():
    result = validate_queue_approval_path(valid_packet())
    assert result["validation_status"] == "passed"
    assert result["validation_schema"] == "queue_approval_path_validation_v1"
    assert result["diagnostic_codes"] == []


def test_valid_rejected_passes():
    packet = valid_packet()
    packet["queue_approval_status"] = "rejected_before_queue_insertion"
    packet["diagnostics"] = ["candidate approval is not approved"]
    packet["approval_scope"] = "Rejected manual review scope."
    packet["recommended_next_step"] = "Remain review-only and repair as needed."
    result = validate_queue_approval_path(packet)
    assert result["validation_status"] == "passed"
    assert result["diagnostic_codes"] == []


def test_valid_needs_repair_passes():
    packet = valid_packet()
    packet["queue_approval_status"] = "needs_repair_before_queue_insertion_review"
    packet["diagnostics"] = ["approval scope needs narrowing"]
    packet["approval_scope"] = "Repair-needed manual review scope."
    packet["recommended_next_step"] = "Repair the review artifact before another review pass."
    result = validate_queue_approval_path(packet)
    assert result["validation_status"] == "passed"
    assert result["diagnostic_codes"] == []


@pytest.mark.parametrize(
    "override, expected, diagnostic_code",
    [
        ({"approval_schema": "wrong"}, "approval_schema", "WRONG_APPROVAL_SCHEMA"),
        ({"source_review_schema": "wrong"}, "source_review_schema", "WRONG_SOURCE_REVIEW_SCHEMA"),
        ({"queue_insertion_status": "inserted"}, "not_inserted", "WRONG_LIFECYCLE_STATUS"),
        ({"queue_writing_status": "implemented"}, "not_implemented", "WRONG_LIFECYCLE_STATUS"),
        ({"automation_status": "automated"}, "not_automated", "WRONG_LIFECYCLE_STATUS"),
        ({"repo_mutation_status": "authorized"}, "not_authorized", "WRONG_LIFECYCLE_STATUS"),
        ({"downstream_use_status": "allowed"}, "prohibited_until_review", "WRONG_LIFECYCLE_STATUS"),
        ({"authority_boundary": ["no_unattended_execution"]}, "missing required authority boundary terms", "MISSING_AUTHORITY_TERMS"),
        ({"source_queue_handoff_review_status": "rejected_for_queue"}, "approved_for_queue_candidate", "SOURCE_STATUS_NOT_APPROVED"),
        ({"approval_scope": "approval ready"}, "candidate/manual/review-only", "INVALID_APPROVAL_SCOPE"),
        ({"recommended_next_step": "The queue was inserted automatically."}, "unsafe authority-granting language", "UNSAFE_AUTHORITY_LANGUAGE"),
    ],
)
def test_rejects_invalid_fields(tmp_path, override, expected, diagnostic_code):
    packet = valid_packet()
    packet.update(override)
    with pytest.raises(QueueApprovalPathError, match=expected):
        validate_queue_approval_path(packet)
    path = tmp_path / "queue_approval_path_invalid_packet.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    try:
        result = run_cli(path)
        assert result.returncode != 0
        payload = json.loads(result.stdout)
        assert payload["validation_status"] == "failed"
        assert payload["diagnostic_codes"] == [diagnostic_code]
    finally:
        if path.exists():
            path.unlink()


def test_missing_required_field_fails():
    packet = valid_packet()
    del packet["reviewer_note"]
    with pytest.raises(QueueApprovalPathError, match="missing required fields"):
        validate_queue_approval_path(packet)


def test_approval_with_diagnostics_fails():
    packet = valid_packet()
    packet["diagnostics"] = ["unexpected diagnostic"]
    with pytest.raises(QueueApprovalPathError, match="must have empty diagnostics"):
        validate_queue_approval_path(packet)


def test_rejected_without_diagnostics_fails():
    packet = valid_packet()
    packet["queue_approval_status"] = "rejected_before_queue_insertion"
    with pytest.raises(QueueApprovalPathError, match="must include diagnostics"):
        validate_queue_approval_path(packet)


def test_repair_without_diagnostics_fails():
    packet = valid_packet()
    packet["queue_approval_status"] = "needs_repair_before_queue_insertion_review"
    with pytest.raises(QueueApprovalPathError, match="must include diagnostics"):
        validate_queue_approval_path(packet)


def test_approval_when_source_status_is_not_approved_fails():
    packet = valid_packet()
    packet["source_queue_handoff_review_status"] = "rejected_for_queue"
    with pytest.raises(QueueApprovalPathError, match="source_queue_handoff_review_status"):
        validate_queue_approval_path(packet)


def test_unsafe_queue_writing_language_fails():
    packet = valid_packet()
    packet["recommended_next_step"] = "The queue was inserted automatically."
    with pytest.raises(QueueApprovalPathError, match="unsafe authority-granting language"):
        validate_queue_approval_path(packet)


def test_unsafe_queue_running_language_fails():
    packet = valid_packet()
    packet["reviewer_note"] = "ran queue automatically."
    with pytest.raises(QueueApprovalPathError, match="unsafe authority-granting language"):
        validate_queue_approval_path(packet)


def test_safe_phrases_do_not_trigger_false_positives():
    packet = valid_packet()
    packet["reviewer_note"] = "The item remains not_inserted and not_implemented."
    packet["recommended_next_step"] = "Keep it not_authorized and prohibited_until_review."
    result = validate_queue_approval_path(packet)
    assert result["validation_status"] == "passed"


@pytest.mark.parametrize(
    "payload, expected, code",
    [
        ("{", "malformed JSON packet", "MALFORMED_JSON"),
        ("[1, 2, 3]", "approval artifact must be a JSON object", "NON_OBJECT_JSON"),
    ],
)
def test_cli_rejects_malformed_json(tmp_path, payload, expected, code):
    path = tmp_path / "packet.json"
    path.write_text(payload, encoding="utf-8")
    result = run_cli(path)
    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["validation_status"] == "failed"
    assert output["diagnostic_codes"] == [code]
    assert expected in " ".join(output["diagnostics"])


def test_cli_writes_json_result(tmp_path):
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(valid_packet()), encoding="utf-8")
    result = run_cli(path)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["validation_status"] == "passed"
    assert payload["approval_path"] == str(path)
    assert payload["diagnostic_codes"] == []
