from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.validate_queue_handoff_review import (
    QueueHandoffReviewError,
    validate_queue_handoff_review,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "validate_queue_handoff_review.py"


def valid_review() -> dict:
    return {
        "review_schema": "queue_handoff_review_v1",
        "source_review_schema": "front_door_chain_review_v1",
        "source_review_path": "docs/reports/model_auditions/FRONT_DOOR_CHAIN_REVIEW_COMMAND_2026-07-17.md",
        "queue_handoff_review_status": "approved_for_queue_candidate",
        "approval_scope": "Candidate-only scope for a later manual queue review step.",
        "reviewer_note": "Review-ready queue candidate only; no insertion is authorized.",
        "required_checks": [
            "front-door review is ready_for_review",
            "scorecard is ready",
            "chain validation passed",
        ],
        "authority_boundary": [
            "no_unattended_execution",
            "no_repo_mutation_without_review",
            "no_training_capture",
            "no_promotion",
            "no_deployment",
            "no_downstream_use_authority",
            "no_queue_insertion_without_explicit_approval",
        ],
        "automation_status": "not_automated",
        "queue_handoff_status": "not_inserted",
        "repo_mutation_status": "not_authorized",
        "downstream_use_status": "prohibited_until_review",
        "diagnostics": [],
        "recommended_next_step": "Retain as a queue candidate for separate manual review only.",
    }


def run_cli(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_packet(tmp_path: Path, payload: object, name: str = "packet.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_valid_approved_candidate_passes():
    payload = validate_queue_handoff_review(valid_review())
    assert payload["validation_status"] == "passed"
    assert payload["validation_schema"] == "queue_handoff_review_validation_v1"


def test_valid_rejected_review_passes_with_diagnostics():
    packet = valid_review()
    packet["queue_handoff_review_status"] = "rejected_for_queue"
    packet["diagnostics"] = ["front-door review not ready"]
    packet["approval_scope"] = "Rejected queue candidate scope."
    packet["recommended_next_step"] = "Keep the item review-only and return it for repair."
    payload = validate_queue_handoff_review(packet)
    assert payload["validation_status"] == "passed"


def test_valid_needs_repair_review_passes_with_diagnostics():
    packet = valid_review()
    packet["queue_handoff_review_status"] = "needs_repair_before_queue_review"
    packet["diagnostics"] = ["validation plan is too shallow"]
    packet["approval_scope"] = "Repair-needed queue candidate scope."
    packet["recommended_next_step"] = "Repair the packet before queue-handoff review."
    payload = validate_queue_handoff_review(packet)
    assert payload["validation_status"] == "passed"


@pytest.mark.parametrize(
    "override, expected",
    [
        ({"review_schema": "wrong"}, "review_schema"),
        ({"source_review_schema": "wrong"}, "source_review_schema"),
        ({"queue_handoff_status": "inserted"}, "not_inserted"),
        ({"automation_status": "automated"}, "not_automated"),
        ({"repo_mutation_status": "authorized"}, "not_authorized"),
        ({"downstream_use_status": "allowed"}, "prohibited_until_review"),
        ({"authority_boundary": ["no_unattended_execution"]}, "missing required authority boundary terms"),
        ({"approval_scope": "candidate ready"}, "candidate-only scope"),
        ({"recommended_next_step": "Insert into queue later."}, "insert into queue"),
    ],
)
def test_rejects_invalid_fields(override, expected):
    packet = valid_review()
    packet.update(override)
    with pytest.raises(QueueHandoffReviewError, match=expected):
        validate_queue_handoff_review(packet)


def test_missing_required_field_fails():
    packet = valid_review()
    del packet["reviewer_note"]
    with pytest.raises(QueueHandoffReviewError, match="missing required fields"):
        validate_queue_handoff_review(packet)


def test_unsafe_queue_insertion_language_fails():
    packet = valid_review()
    packet["recommended_next_step"] = "This item should be queued automatically."
    with pytest.raises(QueueHandoffReviewError, match="unsafe authority-granting language"):
        validate_queue_handoff_review(packet)


def test_unsafe_repo_mutation_language_fails():
    packet = valid_review()
    packet["reviewer_note"] = "Authorized repo mutation is requested."
    with pytest.raises(QueueHandoffReviewError, match="unsafe authority-granting language"):
        validate_queue_handoff_review(packet)


def test_approved_candidate_with_diagnostics_fails():
    packet = valid_review()
    packet["diagnostics"] = ["unexpected diagnostic"]
    with pytest.raises(QueueHandoffReviewError, match="must have empty diagnostics"):
        validate_queue_handoff_review(packet)


def test_rejected_review_without_diagnostics_fails():
    packet = valid_review()
    packet["queue_handoff_review_status"] = "rejected_for_queue"
    with pytest.raises(QueueHandoffReviewError, match="must include diagnostics"):
        validate_queue_handoff_review(packet)


def test_needs_repair_review_without_diagnostics_fails():
    packet = valid_review()
    packet["queue_handoff_review_status"] = "needs_repair_before_queue_review"
    with pytest.raises(QueueHandoffReviewError, match="must include diagnostics"):
        validate_queue_handoff_review(packet)


@pytest.mark.parametrize(
    "payload, expected",
    [
        ("{", "malformed JSON packet"),
        ("[1, 2, 3]", "review artifact must be a JSON object"),
    ],
)
def test_cli_rejects_malformed_json(tmp_path, payload, expected):
    path = tmp_path / "packet.json"
    path.write_text(payload, encoding="utf-8")
    result = run_cli(path)
    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["validation_status"] == "failed"
    assert expected in " ".join(output["diagnostics"])


def test_cli_rejects_non_object_json(tmp_path):
    path = tmp_path / "packet.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    result = run_cli(path)
    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["validation_status"] == "failed"
    assert "review artifact must be a JSON object" in " ".join(output["diagnostics"])


def test_cli_writes_json_result(tmp_path):
    path = write_packet(tmp_path, valid_review(), "packet.json")
    result = run_cli(path)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["validation_status"] == "passed"
    assert payload["review_path"] == str(path)
