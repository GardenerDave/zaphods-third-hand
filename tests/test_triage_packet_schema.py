from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.triage_packet_schema import (
    TriagePacketError,
    load_triage_packet,
    required_risk_flags_for_input,
    validate_triage_packet,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "triage_packet_schema.py"
PACKET_DIR = ROOT / "examples" / "triage_packets"


def make_packet(**overrides):
    packet = {
        "triage_id": "triage_test_001",
        "messy_input": "Please update the workflow notes for the review step.",
        "normalized_intent": "User wants a bounded docs update packet for review-step notes.",
        "task_type": "docs_update",
        "recommended_workflow": "documentation_planning_workflow",
        "confidence": "medium",
        "requires_clarification": False,
        "bounded_outputs": ["docs_update_packet"],
        "allowed_targets": ["docs/"],
        "held_targets": ["production automation"],
        "risk_flags": [],
        "recommended_prompt_patches": ["scope_boundary_v1"],
        "output_contract": {"format": "json", "requires_reason": True},
        "validation_hooks": [
            "allowed_held_target_separation",
            "required_reason",
            "no_execution_authority",
        ],
        "provenance": {"source": "test"},
    }
    packet.update(overrides)
    return packet


def test_accepts_valid_packet():
    assert validate_triage_packet(make_packet())["triage_id"] == "triage_test_001"


@pytest.mark.parametrize("missing_key", [
    "triage_id",
    "messy_input",
    "normalized_intent",
    "task_type",
    "recommended_workflow",
    "confidence",
    "requires_clarification",
    "bounded_outputs",
    "allowed_targets",
    "held_targets",
    "risk_flags",
    "recommended_prompt_patches",
    "output_contract",
    "validation_hooks",
    "provenance",
])
def test_rejects_missing_required_field(missing_key):
    packet = make_packet()
    del packet[missing_key]
    with pytest.raises(TriagePacketError):
        validate_triage_packet(packet)


def test_rejects_allowed_held_target_overlap():
    packet = make_packet(
        allowed_targets=["docs/", "training/"],
        held_targets=["training/"],
    )
    with pytest.raises(TriagePacketError, match="overlap"):
        validate_triage_packet(packet)


def test_rejects_execution_authority_field():
    with pytest.raises(TriagePacketError, match="forbidden authority"):
        validate_triage_packet(make_packet(execution_authority=True))


def test_rejects_execution_workflow():
    with pytest.raises(TriagePacketError, match="forbidden authority"):
        validate_triage_packet(make_packet(recommended_workflow="execute_repo_patch"))


def test_rejects_auto_training_authority():
    with pytest.raises(TriagePacketError, match="forbidden authority"):
        validate_triage_packet(make_packet(auto_train=True))


def test_rejects_auto_curriculum_capture_authority():
    with pytest.raises(TriagePacketError, match="forbidden authority"):
        validate_triage_packet(make_packet(auto_curriculum_capture=True))


def test_rejects_auto_train_workflow():
    with pytest.raises(TriagePacketError, match="forbidden authority"):
        validate_triage_packet(make_packet(recommended_workflow="auto_train_adapter"))


def test_requires_output_contract_shape():
    with pytest.raises(TriagePacketError, match="output_contract"):
        validate_triage_packet(make_packet(output_contract={}))
    with pytest.raises(TriagePacketError, match="format"):
        validate_triage_packet(make_packet(output_contract={"requires_reason": True}))
    with pytest.raises(TriagePacketError, match="requires_reason"):
        validate_triage_packet(make_packet(output_contract={"format": "json"}))


def test_requires_provenance_source():
    with pytest.raises(TriagePacketError, match="provenance"):
        validate_triage_packet(make_packet(provenance={}))


def test_model_facing_requires_reason_contract():
    packet = make_packet(output_contract={"format": "json", "requires_reason": False})
    validate_triage_packet(packet)
    with pytest.raises(TriagePacketError, match="requires_reason"):
        validate_triage_packet(packet, model_facing=True)


@pytest.mark.parametrize("messy_input,expected_flag", [
    ("We should fine-tune a LoRA adapter for this.", "training_pipeline_ambiguity"),
    ("Handle the prompt injection failure modes.", "prompt_injection_surface"),
    ("Design the orchestration layer for the agents.", "orchestration_scope_risk"),
    ("Just clean up everything in one pass.", "scope_creep"),
])
def test_requires_risk_flags_for_risky_inputs(messy_input, expected_flag):
    assert expected_flag in required_risk_flags_for_input(messy_input)
    packet = make_packet(messy_input=messy_input, risk_flags=[])
    with pytest.raises(TriagePacketError, match="risk flags"):
        validate_triage_packet(packet)
    packet_with_flag = make_packet(messy_input=messy_input, risk_flags=[expected_flag])
    validate_triage_packet(packet_with_flag)


def test_example_packets_validate():
    paths = sorted(PACKET_DIR.glob("*.json"))
    assert paths
    for path in paths:
        packet = load_triage_packet(path)
        assert packet["triage_id"]


def test_cli_accepts_example_packet():
    example = sorted(PACKET_DIR.glob("*.json"))[0]
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--packet", str(example)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["valid"] is True


def test_cli_rejects_malformed_packet(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"triage_id": "broken"}) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--packet", str(bad)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "missing required fields" in result.stdout
