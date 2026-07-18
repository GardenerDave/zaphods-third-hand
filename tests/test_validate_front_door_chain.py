from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.validate_front_door_chain import (
    FrontDoorChainError,
    validate_front_door_chain,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "validate_front_door_chain.py"
TRIAGE_FIXTURE = ROOT / "local_harness" / "fixtures" / "triage_to_bounded_task_bridge" / "valid_bridge_001.source_triage_packet.json"
BOUNDED_FIXTURE = ROOT / "local_harness" / "fixtures" / "triage_to_bounded_task_bridge" / "valid_bridge_001.bounded_task_packet_draft.json"
REVIEW_FIXTURE = ROOT / "local_harness" / "fixtures" / "bounded_task_review_packet" / "valid_review_packet_001.json"


def load_packet(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_tracked_fixture_chain_passes():
    result = validate_front_door_chain(
        triage_packet_path=TRIAGE_FIXTURE,
        bounded_task_packet_path=BOUNDED_FIXTURE,
        review_packet_path=REVIEW_FIXTURE,
    )
    assert result["validation_status"] == "passed"
    assert result["triage_validation_status"] == "passed"
    assert result["bounded_task_validation_status"] == "passed"
    assert result["review_packet_validation_status"] == "passed"
    assert result["linkage_status"] == "passed"
    assert result["lifecycle_status"] == "passed"
    assert result["authority_boundary_status"] == "passed"


@pytest.mark.parametrize(
    "payload, expected",
    [
        ("{", "malformed JSON packet"),
        ("[1, 2, 3]", "packet must be a JSON object"),
    ],
)
def test_cli_failure_diagnostics_are_explicit(tmp_path, payload, expected):
    triage = tmp_path / "triage.json"
    bounded = tmp_path / "bounded.json"
    review = tmp_path / "review.json"
    triage.write_text(load_packet(TRIAGE_FIXTURE).get("task_summary", "{}") and payload, encoding="utf-8")
    bounded.write_text(json.dumps(load_packet(BOUNDED_FIXTURE)), encoding="utf-8")
    review.write_text(json.dumps(load_packet(REVIEW_FIXTURE)), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--triage-packet",
            str(triage),
            "--bounded-task-packet",
            str(bounded),
            "--review-packet",
            str(review),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["validation_status"] == "failed"
    assert expected in " ".join(payload["diagnostics"])


def test_invalid_triage_fixture_fails_closed(tmp_path):
    triage = tmp_path / "triage.json"
    triage.write_text(json.dumps({"packet_schema": "messy_input_triage_packet_v1"}), encoding="utf-8")
    result = validate_front_door_chain(
        triage_packet_path=triage,
        bounded_task_packet_path=BOUNDED_FIXTURE,
        review_packet_path=REVIEW_FIXTURE,
    )
    assert result["validation_status"] == "failed"
    assert result["triage_validation_status"] == "failed"
    assert any("triage:" in item for item in result["diagnostics"])


def test_invalid_bounded_task_fixture_fails_closed(tmp_path):
    bounded = tmp_path / "bounded.json"
    packet = load_packet(BOUNDED_FIXTURE)
    packet["queue_handoff_status"] = "inserted"
    bounded.write_text(json.dumps(packet), encoding="utf-8")
    result = validate_front_door_chain(
        triage_packet_path=TRIAGE_FIXTURE,
        bounded_task_packet_path=bounded,
        review_packet_path=REVIEW_FIXTURE,
    )
    assert result["validation_status"] == "failed"
    assert result["bounded_task_validation_status"] == "failed"
    assert any("bounded_task:" in item for item in result["diagnostics"])


def test_invalid_review_fixture_fails_closed(tmp_path):
    review = tmp_path / "review.json"
    packet = load_packet(REVIEW_FIXTURE)
    packet["repo_mutation_status"] = "authorized"
    review.write_text(json.dumps(packet), encoding="utf-8")
    result = validate_front_door_chain(
        triage_packet_path=TRIAGE_FIXTURE,
        bounded_task_packet_path=BOUNDED_FIXTURE,
        review_packet_path=review,
    )
    assert result["validation_status"] == "failed"
    assert result["review_packet_validation_status"] == "failed"
    assert any("review:" in item for item in result["diagnostics"])


def test_linkage_and_status_checks_are_enforced(tmp_path):
    bounded = tmp_path / "bounded.json"
    review = tmp_path / "review.json"
    packet = load_packet(BOUNDED_FIXTURE)
    packet["source_packet_schema"] = "wrong"
    bounded.write_text(json.dumps(packet), encoding="utf-8")
    review.write_text(json.dumps(load_packet(REVIEW_FIXTURE)), encoding="utf-8")
    result = validate_front_door_chain(
        triage_packet_path=TRIAGE_FIXTURE,
        bounded_task_packet_path=bounded,
        review_packet_path=review,
    )
    assert result["validation_status"] == "failed"
    assert any("source_packet_schema" in item for item in result["diagnostics"])


def test_cli_writes_json_result(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--triage-packet",
            str(TRIAGE_FIXTURE),
            "--bounded-task-packet",
            str(BOUNDED_FIXTURE),
            "--review-packet",
            str(REVIEW_FIXTURE),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["validation_status"] == "passed"
    assert payload["triage_packet_path"] == str(TRIAGE_FIXTURE)
