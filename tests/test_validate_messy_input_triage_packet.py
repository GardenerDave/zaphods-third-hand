from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.validate_messy_input_triage_packet import (
    MessyInputTriagePacketError,
    validate_messy_input_triage_packet,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "validate_messy_input_triage_packet.py"


def make_packet(**overrides):
    packet = {
        "packet_schema": "messy_input_triage_packet_v1",
        "task_summary": "Turn a messy request into a bounded triage packet.",
        "request_type": "triage_request",
        "allowed_targets": [],
        "held_targets": [],
        "evidence_needed": ["repo context", "validation command"],
        "authority_boundary": [
            "no_unattended_execution",
            "no_repo_mutation_without_review",
            "no_training_capture",
            "no_promotion",
            "no_deployment",
            "no_downstream_use_authority",
        ],
        "proposed_next_action": "Draft the triage packet for human review.",
        "validation_plan": ["check required fields", "check authority boundary"],
        "stop_conditions": ["scope is unclear", "authorization is missing"],
        "review_required": True,
    }
    packet.update(overrides)
    return packet


def test_valid_minimal_packet_passes():
    result = validate_messy_input_triage_packet(make_packet())
    assert result["validation_status"] == "passed"
    assert result["packet_schema"] == "messy_input_triage_packet_v1"
    assert result["allowed_targets_count"] == 0
    assert result["held_targets_count"] == 0
    assert result["evidence_needed_count"] == 2
    assert result["stop_conditions_count"] == 2


@pytest.mark.parametrize(
    "payload, expected",
    [
        ("{", "malformed JSON packet"),
        ({"packet_schema": "messy_input_triage_packet_v1"}, "missing required fields"),
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
        ({"review_required": False}, "must be true"),
        ({"authority_boundary": ["no_unattended_execution"]}, "authority boundary terms"),
        ({"proposed_next_action": "Promote this patch automatically."}, "unsafe authority"),
        ({"task_summary": "   "}, "task_summary"),
    ],
)
def test_rejects_unsafe_or_incomplete_packets(override, expected):
    with pytest.raises(MessyInputTriagePacketError, match=expected):
        validate_messy_input_triage_packet(make_packet(**override))


def test_rejects_missing_required_field():
    packet = make_packet()
    del packet["allowed_targets"]
    with pytest.raises(MessyInputTriagePacketError, match="missing required fields"):
        validate_messy_input_triage_packet(packet)


def test_rejects_missing_held_targets_field():
    packet = make_packet()
    del packet["held_targets"]
    with pytest.raises(MessyInputTriagePacketError, match="missing required fields"):
        validate_messy_input_triage_packet(packet)


def test_rejects_missing_evidence_needed_field():
    packet = make_packet()
    del packet["evidence_needed"]
    with pytest.raises(MessyInputTriagePacketError, match="missing required fields"):
        validate_messy_input_triage_packet(packet)


def test_rejects_bad_packet_schema():
    with pytest.raises(MessyInputTriagePacketError, match="packet_schema"):
        validate_messy_input_triage_packet(make_packet(packet_schema="wrong"))


def test_cli_writes_json_result(tmp_path):
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(make_packet()), encoding="utf-8")
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
