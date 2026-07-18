from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.validate_bounded_task_packet_draft import (
    BoundedTaskPacketDraftError,
    validate_bounded_task_packet_draft,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "validate_bounded_task_packet_draft.py"


def make_packet(**overrides):
    packet = {
        "packet_schema": "bounded_task_packet_draft_v1",
        "source_packet_schema": "messy_input_triage_packet_v1",
        "source_packet_path": ".work/messy_input_triage_bridge/20260717_triage_to_bounded_task_001/source_triage_packet.json",
        "task_summary": "Create fixture coverage for validated triage-packet-to-bounded-task handoff without automating routing or queue insertion.",
        "allowed_targets": ["docs/"],
        "held_targets": ["training/"],
        "evidence_needed": ["validated triage packet", "manual bridge review"],
        "proposed_action": "Draft fixture coverage for validated triage-packet-to-bounded-task handoff and keep routing and repo mutation under human review.",
        "validation_plan": ["check draft fields", "check authority boundary"],
        "stop_conditions": ["routing automation appears", "queue insertion appears"],
        "authority_boundary": [
            "no_unattended_execution",
            "no_repo_mutation_without_review",
            "no_training_capture",
            "no_promotion",
            "no_deployment",
            "no_downstream_use_authority",
        ],
        "review_required": True,
        "downstream_use_status": "prohibited_until_review",
        "automation_status": "not_automated",
        "queue_handoff_status": "not_inserted",
    }
    packet.update(overrides)
    return packet


def test_valid_minimal_bounded_task_packet_passes():
    result = validate_bounded_task_packet_draft(make_packet())
    assert result["validation_status"] == "passed"
    assert result["packet_schema"] == "bounded_task_packet_draft_v1"
    assert result["source_packet_schema"] == "messy_input_triage_packet_v1"
    assert result["allowed_targets_count"] == 1
    assert result["held_targets_count"] == 1
    assert result["evidence_needed_count"] == 2
    assert result["validation_plan_count"] == 2
    assert result["stop_conditions_count"] == 2


@pytest.mark.parametrize(
    "payload, expected",
    [
        ("{", "malformed JSON packet"),
        (["not", "an", "object"], "packet must be a JSON object"),
        ({"packet_schema": "bounded_task_packet_draft_v1"}, "missing required fields"),
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
        ({"review_required": False}, "must be true"),
        ({"downstream_use_status": "reviewed"}, "downstream_use_status"),
        ({"automation_status": "automated"}, "automation_status"),
        ({"queue_handoff_status": "inserted"}, "queue_handoff_status"),
        ({"authority_boundary": {"bad": True}}, "list of strings"),
        ({"authority_boundary": ["no_unattended_execution"]}, "authority boundary terms"),
        ({"proposed_action": "Promote this patch automatically."}, "unsafe authority"),
    ],
)
def test_rejects_unsafe_or_incomplete_packets(override, expected):
    with pytest.raises(BoundedTaskPacketDraftError, match=expected):
        validate_bounded_task_packet_draft(make_packet(**override))


def test_rejects_missing_required_field():
    packet = make_packet()
    del packet["allowed_targets"]
    with pytest.raises(BoundedTaskPacketDraftError, match="missing required fields"):
        validate_bounded_task_packet_draft(packet)


def test_allows_empty_allowed_and_held_targets():
    result = validate_bounded_task_packet_draft(
        make_packet(allowed_targets=[], held_targets=[])
    )
    assert result["allowed_targets_count"] == 0
    assert result["held_targets_count"] == 0


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
