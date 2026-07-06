from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.triage_packet_schema import validate_triage_packet
from local_harness.triage_router_rules import FORBIDDEN_OUTPUT_TERMS, route_messy_input


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "triage_router_rules.py"


def test_routes_presentation_requests_to_presentation_outline():
    packet = route_messy_input(
        "I need a presentation and demo about the supervised workflow.",
        triage_id="triage_presentation_001",
    )
    assert packet["recommended_workflow"] == "presentation_outline_workflow"
    assert packet["task_type"] == "presentation_outline"
    assert "presentation_outline" in packet["bounded_outputs"]


def test_routes_lora_requests_to_training_design_not_execution():
    packet = route_messy_input(
        "Can we fine-tune a LoRA adapter on our failure data?",
        triage_id="triage_lora_001",
    )
    assert packet["recommended_workflow"] == "training_design_packet"
    assert "training_pipeline_ambiguity" in packet["risk_flags"]
    assert "training execution" in packet["held_targets"]
    assert "execution" not in packet["recommended_workflow"]


def test_routes_prompt_patch_requests_to_prompt_patch_library_workflow():
    packet = route_messy_input(
        "Add a prompt patch for the placeholder failure mode.",
        triage_id="triage_patch_001",
    )
    assert packet["recommended_workflow"] == "prompt_patch_library_workflow"
    assert "scope_boundary_v1" in packet["recommended_prompt_patches"]


def test_routes_triage_router_requests_to_triage_router_workflow():
    packet = route_messy_input(
        "Build the triage router for messy input.",
        triage_id="triage_router_001",
    )
    assert packet["recommended_workflow"] == "triage_router_workflow"
    assert "orchestration_scope_risk" in packet["risk_flags"]


def test_routes_docs_requests_to_documentation_planning():
    packet = route_messy_input(
        "Update the readme and roadmap docs.",
        triage_id="triage_docs_001",
    )
    assert packet["recommended_workflow"] == "documentation_planning_workflow"
    assert packet["allowed_targets"] == ["docs/"]


def test_routes_bug_fix_requests_to_repo_patch_packet():
    packet = route_messy_input(
        "Fix the bug in the failing test.",
        triage_id="triage_fix_001",
    )
    assert packet["recommended_workflow"] == "repo_patch_packet"
    assert "unrelated files" in packet["held_targets"]


def test_routes_broad_ambiguous_request_to_design_packet():
    packet = route_messy_input(
        "Everything is tangled, make the whole repo better somehow.",
        triage_id="triage_broad_001",
    )
    assert packet["recommended_workflow"] == "design_packet"
    assert packet["requires_clarification"] is True
    assert packet["confidence"] == "low"
    assert "scope_creep" in packet["risk_flags"]
    assert "implementation_packet" in packet["held_targets"]


def test_multi_domain_messy_request_downgrades_to_design_packet():
    packet = route_messy_input(
        "The LoRA stuff and prompt injection got messy. We need to tie it back together.",
        triage_id="triage_multi_001",
    )
    assert packet["recommended_workflow"] == "design_packet"
    assert "training_pipeline_ambiguity" in packet["risk_flags"]
    assert "prompt_injection_surface" in packet["risk_flags"]
    assert "scope_creep" in packet["risk_flags"]


def test_router_output_validates_as_model_facing_packet():
    packet = route_messy_input(
        "Prepare a talk about the audit results.",
        triage_id="triage_valid_001",
    )
    assert validate_triage_packet(packet, model_facing=True)


def test_router_includes_conservative_defaults():
    packet = route_messy_input(
        "Fix the bug in the parser code.",
        triage_id="triage_defaults_001",
    )
    assert packet["output_contract"] == {"format": "json", "requires_reason": True}
    assert "no_execution_authority" in packet["validation_hooks"]
    assert "allowed_held_target_separation" in packet["validation_hooks"]
    assert packet["reason"]
    assert "production automation" in packet["held_targets"]
    assert "automatic curriculum capture" in packet["held_targets"]
    assert "automatic promotion" in packet["held_targets"]


def test_router_does_not_grant_execution_authority():
    prompts = [
        "Fix the bug in the failing test.",
        "Fine-tune a LoRA adapter now.",
        "Run the orchestration for everything.",
    ]
    for index, prompt in enumerate(prompts):
        packet = route_messy_input(prompt, triage_id=f"triage_noexec_{index:03d}")
        rendered = json.dumps(packet).lower()
        for term in FORBIDDEN_OUTPUT_TERMS:
            assert term not in rendered
        assert "execution_authority" not in packet
        assert "auto_train" not in packet
        assert "auto_promote" not in packet


def test_router_rejects_empty_input():
    with pytest.raises(ValueError):
        route_messy_input("   ", triage_id="triage_empty_001")


def test_router_rejects_bad_triage_id():
    with pytest.raises(ValueError):
        route_messy_input("Fix the bug.", triage_id="bad id with spaces")


def test_cli_writes_valid_packet(tmp_path):
    out = tmp_path / "packet.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--messy-input",
            "Prepare a presentation about the triage layer.",
            "--triage-id",
            "triage_cli_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    packet = json.loads(out.read_text(encoding="utf-8"))
    assert validate_triage_packet(packet, model_facing=True)
