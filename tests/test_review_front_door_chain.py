from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "review_front_door_chain.py"
TRIAGE_FIXTURE = ROOT / "local_harness" / "fixtures" / "triage_to_bounded_task_bridge" / "valid_bridge_001.source_triage_packet.json"
BOUNDED_FIXTURE = ROOT / "local_harness" / "fixtures" / "triage_to_bounded_task_bridge" / "valid_bridge_001.bounded_task_packet_draft.json"
REVIEW_FIXTURE = ROOT / "local_harness" / "fixtures" / "bounded_task_review_packet" / "valid_review_packet_001.json"


def run_review(*, triage: Path, bounded: Path, review: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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


def test_valid_tracked_fixture_chain_returns_ready_for_human_review():
    result = run_review(
        triage=TRIAGE_FIXTURE,
        bounded=BOUNDED_FIXTURE,
        review=REVIEW_FIXTURE,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["review_schema"] == "front_door_chain_review_v1"
    assert payload["review_status"] == "ready_for_human_review"
    assert payload["automation_status"] == "not_automated"
    assert payload["queue_handoff_status"] == "not_inserted"
    assert payload["downstream_use_status"] == "prohibited_until_review"
    assert payload["repo_mutation_status"] == "not_authorized"
    assert "chain_validation" in payload
    assert "scorecard" in payload


def test_invalid_triage_packet_returns_blocked(tmp_path):
    triage = tmp_path / "triage.json"
    triage.write_text(json.dumps({"packet_schema": "messy_input_triage_packet_v1"}), encoding="utf-8")
    result = run_review(triage=triage, bounded=BOUNDED_FIXTURE, review=REVIEW_FIXTURE)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "blocked"
    assert payload["automation_status"] == "not_automated"
    assert payload["queue_handoff_status"] == "not_inserted"
    assert payload["downstream_use_status"] == "prohibited_until_review"
    assert payload["repo_mutation_status"] == "not_authorized"


def test_invalid_bounded_task_packet_returns_blocked(tmp_path):
    bounded = tmp_path / "bounded.json"
    packet = json.loads(BOUNDED_FIXTURE.read_text(encoding="utf-8"))
    packet["queue_handoff_status"] = "inserted"
    bounded.write_text(json.dumps(packet), encoding="utf-8")
    result = run_review(triage=TRIAGE_FIXTURE, bounded=bounded, review=REVIEW_FIXTURE)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "blocked"
    assert "chain_validation" in payload
    assert "scorecard" in payload


def test_invalid_review_packet_returns_blocked(tmp_path):
    review = tmp_path / "review.json"
    packet = json.loads(REVIEW_FIXTURE.read_text(encoding="utf-8"))
    packet["repo_mutation_status"] = "authorized"
    review.write_text(json.dumps(packet), encoding="utf-8")
    result = run_review(triage=TRIAGE_FIXTURE, bounded=BOUNDED_FIXTURE, review=review)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["review_status"] == "blocked"


@pytest.mark.parametrize(
    "payload, expected",
    [
        ("{", "malformed JSON packet"),
        ("[1, 2, 3]", "packet must be a JSON object"),
    ],
)
def test_invalid_triage_packet_json_returns_blocked(tmp_path, payload, expected):
    triage = tmp_path / "triage.json"
    triage.write_text(payload, encoding="utf-8")
    result = run_review(triage=triage, bounded=BOUNDED_FIXTURE, review=REVIEW_FIXTURE)
    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["review_status"] == "blocked"
    assert expected in " ".join(output["diagnostics"])


def test_output_always_keeps_authority_boundaries():
    result = run_review(
        triage=TRIAGE_FIXTURE,
        bounded=BOUNDED_FIXTURE,
        review=REVIEW_FIXTURE,
    )
    payload = json.loads(result.stdout)
    assert payload["automation_status"] == "not_automated"
    assert payload["queue_handoff_status"] == "not_inserted"
    assert payload["downstream_use_status"] == "prohibited_until_review"
    assert payload["repo_mutation_status"] == "not_authorized"


def test_output_includes_chain_validation_and_scorecard():
    result = run_review(
        triage=TRIAGE_FIXTURE,
        bounded=BOUNDED_FIXTURE,
        review=REVIEW_FIXTURE,
    )
    payload = json.loads(result.stdout)
    assert "chain_validation" in payload
    assert "scorecard" in payload
    assert payload["chain_validation"]["validation_schema"] == "front_door_chain_validation_v1"
    assert payload["scorecard"]["scorecard_schema"] == "front_door_chain_scorecard_v1"
