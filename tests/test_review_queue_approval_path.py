from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "review_queue_approval_path.py"
FIXTURE_APPROVED = ROOT / "local_harness" / "fixtures" / "queue_approval_path" / "approved_manual_candidate_valid_001.json"
FIXTURE_REJECTED = ROOT / "local_harness" / "fixtures" / "queue_approval_path" / "rejected_before_insertion_valid_001.json"
FIXTURE_REPAIR = ROOT / "local_harness" / "fixtures" / "queue_approval_path" / "needs_repair_before_insertion_valid_001.json"


def run_review(approval: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(approval), str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_approved_candidate_creates_review_artifact(tmp_path):
    output = tmp_path / "queue_approval_review.json"
    result = run_review(FIXTURE_APPROVED, output)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["review_schema"] == "queue_approval_path_review_v1"
    assert payload["review_status"] == "ready_for_manual_queue_insertion_review"
    assert payload["validation_status"] == "passed"
    assert payload["queue_approval_status"] == "approved_for_manual_queue_insertion_candidate"
    assert payload["automation_status"] == "not_automated"
    assert payload["queue_insertion_status"] == "not_inserted"
    assert payload["queue_writing_status"] == "not_implemented"
    assert payload["queue_running_status"] == "not_run"
    assert payload["repo_mutation_status"] == "explicit_review_output_only"
    assert payload["fixture_import_status"] == "not_imported"
    assert payload["training_capture_status"] == "not_captured"
    assert payload["promotion_status"] == "not_promoted"
    assert payload["deployment_status"] == "not_deployed"
    assert payload["downstream_use_status"] == "prohibited_until_review"
    assert payload["authority_boundary"]
    assert output.is_file()
    assert load_json(output) == payload


def test_valid_rejected_artifact_maps_to_rejected_status(tmp_path):
    output = tmp_path / "queue_approval_review.json"
    result = run_review(FIXTURE_REJECTED, output)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "rejected_before_queue_insertion"
    assert payload["queue_approval_status"] == "rejected_before_queue_insertion"
    assert payload["validation_status"] == "passed"
    assert output.is_file()


def test_valid_needs_repair_artifact_maps_to_needs_repair_status(tmp_path):
    output = tmp_path / "queue_approval_review.json"
    result = run_review(FIXTURE_REPAIR, output)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "needs_repair_before_queue_insertion_review"
    assert payload["queue_approval_status"] == "needs_repair_before_queue_insertion_review"
    assert payload["validation_status"] == "passed"
    assert output.is_file()


def test_invalid_approval_writes_blocked_review_artifact(tmp_path):
    packet = json.loads(FIXTURE_APPROVED.read_text(encoding="utf-8"))
    packet["queue_writing_status"] = "implemented"
    approval = tmp_path / "invalid_approval.json"
    approval.write_text(json.dumps(packet), encoding="utf-8")
    output = tmp_path / "queue_approval_review.json"
    result = run_review(approval, output)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "blocked_needs_repair"
    assert payload["validation_status"] == "failed"
    assert payload["diagnostic_codes"]
    assert output.is_file()
    assert load_json(output) == payload


def test_refuses_queue_path_output(tmp_path):
    output = tmp_path / "queues" / "queue_approval_review.json"
    result = run_review(FIXTURE_APPROVED, output)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "blocked_needs_repair"
    assert not output.exists()


def test_refuses_queue_directory_output(tmp_path):
    for output in [
        tmp_path / "queue" / "queue_approval_review.json",
        tmp_path / "queues" / "queue_approval_review.json",
    ]:
        result = run_review(FIXTURE_APPROVED, output)
        assert result.returncode != 0
        payload = json.loads(result.stdout)
        assert payload["review_status"] == "blocked_needs_repair"
        assert not output.exists()


def test_refuses_fixture_output(tmp_path):
    output = ROOT / "local_harness" / "fixtures" / "queue_approval_path" / "queue_approval_review.json"
    result = run_review(FIXTURE_APPROVED, output)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "blocked_needs_repair"
    assert "unsafe" in payload["diagnostics"][0]
    assert not output.exists()


def test_refuses_same_input_output_path(tmp_path):
    approval = tmp_path / "approval.json"
    approval.write_text(FIXTURE_APPROVED.read_text(encoding="utf-8"), encoding="utf-8")
    result = run_review(approval, approval)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "blocked_needs_repair"
    assert not approval.read_text(encoding="utf-8").startswith("{\"review_schema\"")


def test_review_output_includes_validator_diagnostics(tmp_path):
    packet = json.loads(FIXTURE_APPROVED.read_text(encoding="utf-8"))
    packet["queue_approval_status"] = "approved_for_manual_queue_insertion_candidate"
    packet["approval_scope"] = "approval ready"
    approval = tmp_path / "approval.json"
    approval.write_text(json.dumps(packet), encoding="utf-8")
    output = tmp_path / "queue_approval_review.json"
    result = run_review(approval, output)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "blocked_needs_repair"
    assert payload["diagnostic_codes"]
    assert payload["diagnostics"]
