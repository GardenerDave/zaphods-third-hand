from __future__ import annotations

import pytest

from local_harness.orchestration_packet import (
    OrchestrationPacketError,
    assemble_orchestration_packet,
)
from local_harness.prompt_patch_library import PromptPatchLibrary
from local_harness.render_orchestration_packet import render_orchestration_packet


def make_patch(patch_id: str) -> dict:
    return {
        "patch_id": patch_id,
        "title": patch_id,
        "status": "candidate",
        "failure_signature": ["failure mode"],
        "applies_to": {
            "stage": ["prompt_assembly"],
            "task_type": ["architecture_planning", "any"],
            "model_size": ["any"],
        },
        "prompt_delta": f"delta for {patch_id}",
        "required_output_fields": ["reason"],
        "validator_expectations": ["reason required"],
    }


def make_library() -> PromptPatchLibrary:
    library = PromptPatchLibrary()
    library.add_patch(make_patch("scope_boundary_v1"))
    library.add_patch(make_patch("output_contract_v1"))
    library.add_patch(make_patch("unsupported_certainty_v1"))
    return library


def make_triage_packet() -> dict:
    return {
        "triage_id": "triage_example_001",
        "messy_input": "The LoRA stuff and prompt injection got messy. We need to tie it back together.",
        "normalized_intent": "Messy input normalized into a bounded design packet.",
        "task_type": "architecture_planning",
        "recommended_workflow": "design_packet",
        "confidence": "medium",
        "requires_clarification": False,
        "bounded_outputs": ["prompt_patch_library_spec", "triage_router_spec"],
        "allowed_targets": ["docs/PROMPT_PATCH_LIBRARY.md", "docs/TRIAGE_ROUTER.md"],
        "held_targets": ["training/", "production automation", "automatic curriculum capture"],
        "risk_flags": ["scope_creep", "training_pipeline_ambiguity", "prompt_injection_surface"],
        "recommended_prompt_patches": [
            "scope_boundary_v1",
            "output_contract_v1",
            "unsupported_certainty_v1",
        ],
        "output_contract": {"format": "json", "requires_reason": True},
        "validation_hooks": [
            "allowed_held_target_separation",
            "required_reason",
            "no_execution_authority",
        ],
        "provenance": {"source": "test"},
    }


def make_orchestration_packet() -> tuple[dict, PromptPatchLibrary]:
    library = make_library()
    packet = assemble_orchestration_packet(
        make_triage_packet(),
        library,
        orchestration_id="orch_example_001",
        source_summary="Messy input normalized into a bounded design packet.",
    )
    return packet, library


def test_renders_all_required_sections():
    packet, library = make_orchestration_packet()
    rendered = render_orchestration_packet(packet, library)
    for heading in [
        "# Orchestration Packet",
        "## Source / Triage",
        "## Workflow",
        "## Allowed Targets",
        "## Held Targets",
        "## Risk Flags",
        "## Prompt Patches",
        "## Output Contract",
        "## Validation Hooks",
        "## Authority Boundaries",
        "## Review Requirement",
    ]:
        assert heading in rendered


def test_includes_patch_ids():
    packet, library = make_orchestration_packet()
    rendered = render_orchestration_packet(packet, library)
    for patch_id in packet["selected_prompt_patches"]:
        assert patch_id in rendered


def test_includes_authority_boundaries_and_review_requirement():
    packet, library = make_orchestration_packet()
    rendered = render_orchestration_packet(packet, library)
    assert "no_execution_authority" in rendered
    assert "no_automatic_training" in rendered
    assert "review_required: True" in rendered


def test_does_not_include_unauthorized_targets():
    packet, library = make_orchestration_packet()
    rendered = render_orchestration_packet(packet, library)
    assert "unauthorized/file.txt" not in rendered


@pytest.mark.parametrize(
    "forbidden_term",
    ["execute this command", "run this command", "bash -lc", "sudo "],
)
def test_does_not_include_execution_instructions(forbidden_term):
    packet, library = make_orchestration_packet()
    packet["source_summary"] = forbidden_term
    with pytest.raises(OrchestrationPacketError):
        render_orchestration_packet(packet, library)
