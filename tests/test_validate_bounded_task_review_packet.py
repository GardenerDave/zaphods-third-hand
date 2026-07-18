from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.validate_bounded_task_review_packet import (
    BoundedTaskReviewPacketError,
    validate_bounded_task_review_packet,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "validate_bounded_task_review_packet.py"
FIXTURE_DIR = ROOT / "local_harness" / "fixtures" / "bounded_task_review_packet"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_valid_review_fixture_passes():
    packet = load_fixture("valid_review_packet_001.json")
    result = validate_bounded_task_review_packet(packet)
    assert result["validation_status"] == "passed"
    assert result["packet_schema"] == "bounded_task_review_packet_v1"
    assert result["reviewed_artifacts_count"] == 2
    assert result["required_checks_count"] == 3
    assert result["diagnostics_count"] == 0
    assert packet["review_status"] == "review_required"
    assert packet["downstream_use_status"] == "prohibited_until_review"
    assert packet["automation_status"] == "not_automated"
    assert packet["queue_handoff_status"] == "not_inserted"


@pytest.mark.parametrize(
    "payload, expected",
    [
        ("{", "malformed JSON packet"),
        (["not", "an", "object"], "packet must be a JSON object"),
        ({"packet_schema": "bounded_task_review_packet_v1"}, "missing required fields"),
    ],
)
def test_cli_failure_diagnostics_are_explicit(tmp_path, payload, expected):
    packet_path = tmp_path / "packet.json"
    if isinstance(payload, str):
        packet_path.write_text(payload, encoding="utf-8")
    else:
        packet_path.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--packet", str(packet_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["validation_status"] == "failed"
    assert expected in " ".join(payload["diagnostics"])


@pytest.mark.parametrize(
    "override, expected",
    [
        ({"packet_schema": "wrong"}, "packet_schema must be"),
        ({"source_packet_schema": "wrong"}, "source_packet_schema must be"),
        ({"source_validation_status": "failed"}, "source_validation_status"),
        ({"review_status": "reviewed"}, "review_status"),
        ({"downstream_use_status": "reviewed"}, "downstream_use_status"),
        ({"automation_status": "automated"}, "automation_status"),
        ({"queue_handoff_status": "inserted"}, "queue_handoff_status"),
        ({"repo_mutation_status": "authorized"}, "repo_mutation_status"),
        ({"authority_boundary": {"bad": True}}, "list of strings"),
        ({"authority_boundary": ["no_unattended_execution"]}, "authority boundary terms"),
        ({"recommended_next_step": "Complete the handoff."}, "unsafe authority"),
    ],
)
def test_rejects_unsafe_or_incomplete_packets(override, expected):
    packet = load_fixture("valid_review_packet_001.json")
    packet.update(override)
    with pytest.raises(BoundedTaskReviewPacketError, match=expected):
        validate_bounded_task_review_packet(packet)


def test_rejects_missing_required_field():
    packet = load_fixture("valid_review_packet_001.json")
    del packet["review_status"]
    with pytest.raises(BoundedTaskReviewPacketError, match="missing required fields"):
        validate_bounded_task_review_packet(packet)


def test_cli_writes_json_result(tmp_path):
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(load_fixture("valid_review_packet_001.json")), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--packet", str(packet_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["validation_status"] == "passed"
    assert payload["packet_path"] == str(packet_path)
