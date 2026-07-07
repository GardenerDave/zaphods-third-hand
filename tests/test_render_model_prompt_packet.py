from __future__ import annotations

import json
from copy import deepcopy

import pytest

from local_harness.orchestration_packet import OrchestrationPacketError, assemble_orchestration_packet
from local_harness.prompt_patch_library import PromptPatchLibrary
from local_harness.render_model_prompt_packet import build_model_prompt_output_contract, render_model_prompt_packet


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


def _output_contract_from_rendered(rendered: str) -> dict:
    marker = "## Output Contract\n```json\n"
    start = rendered.index(marker) + len(marker)
    end = rendered.index("\n```", start)
    return json.loads(rendered[start:end])


def test_renders_from_valid_orchestration_packet():
    packet, library = make_orchestration_packet()
    rendered = render_model_prompt_packet(packet, library)
    assert "# ZTH Model Prompt Packet" in rendered


def test_validates_orchestration_packet_before_rendering():
    packet, library = make_orchestration_packet()
    packet["review_required"] = False
    with pytest.raises(OrchestrationPacketError):
        render_model_prompt_packet(packet, library)


def test_includes_orchestration_and_triage_ids():
    packet, library = make_orchestration_packet()
    rendered = render_model_prompt_packet(packet, library)
    assert packet["orchestration_id"] in rendered
    assert packet["triage_id"] in rendered


def test_includes_allowed_and_held_targets_exactly():
    packet, library = make_orchestration_packet()
    rendered = render_model_prompt_packet(packet, library)
    for item in packet["allowed_targets"]:
        assert f"- {item}" in rendered
    for item in packet["held_targets"]:
        assert f"- {item}" in rendered


def test_includes_selected_patch_ids_and_patch_deltas():
    packet, library = make_orchestration_packet()
    rendered = render_model_prompt_packet(packet, library)
    for patch_id in packet["selected_prompt_patches"]:
        assert patch_id in rendered
    assert packet["rendered_patch_deltas"].strip() in rendered


def test_includes_output_contract_validation_hooks_and_authority_boundaries():
    packet, library = make_orchestration_packet()
    rendered = render_model_prompt_packet(packet, library)
    output_contract = _output_contract_from_rendered(rendered)
    assert output_contract["format"] == "json"
    for hook in packet["validation_hooks"]:
        assert hook in rendered
    for boundary in packet["authority_boundaries"]:
        assert boundary in rendered


def test_merges_required_fields_from_selected_prompt_patches_with_reason_last():
    packet, library = make_orchestration_packet()
    packet["output_contract"] = {
        "format": "json",
        "requires_reason": True,
        "required_fields": ["existing_first", "allowed_targets", "reason"],
    }
    merged = build_model_prompt_output_contract(packet, library)
    assert merged["required_fields"] == [
        "existing_first",
        "allowed_targets",
        "scope_expansion_required",
        "required_fields_present",
        "claims",
        "evidence_basis",
        "unverified_claims",
        "reason",
    ]


def test_deduplicates_repeated_required_fields_deterministically():
    packet, library = make_orchestration_packet()
    packet["output_contract"] = {
        "format": "json",
        "requires_reason": True,
        "required_fields": ["allowed_targets", "allowed_targets", "reason"],
    }
    merged = build_model_prompt_output_contract(packet, library)
    assert merged["required_fields"].count("allowed_targets") == 1
    assert merged["required_fields"][0] == "allowed_targets"
    assert merged["required_fields"][-1] == "reason"


def test_does_not_mutate_input_orchestration_packet_output_contract():
    packet, library = make_orchestration_packet()
    original = deepcopy(packet)
    render_model_prompt_packet(packet, library)
    assert packet == original


def test_renderer_output_contract_includes_merged_required_fields_and_no_authority_grant_fields():
    packet, library = make_orchestration_packet()
    rendered = render_model_prompt_packet(packet, library)
    output_contract = _output_contract_from_rendered(rendered)
    required = output_contract["required_fields"]
    assert "allowed_targets" in required
    assert "held_targets" in required
    assert "scope_expansion_required" in required
    assert "claims" in required
    assert "evidence_basis" in required
    assert "unverified_claims" in required
    assert "required_fields_present" in required
    assert required[-1] == "reason"
    forbidden = {
        "execution_authority",
        "direct_file_modification_authority",
        "patch_application_authority",
        "auto_promote",
        "auto_train",
        "auto_curriculum_capture",
    }
    assert forbidden.isdisjoint(set(required))


def test_includes_review_requirement():
    packet, library = make_orchestration_packet()
    rendered = render_model_prompt_packet(packet, library)
    assert "Human review is required" in rendered


def test_includes_required_response_shape_for_json_contracts():
    packet, library = make_orchestration_packet()
    rendered = render_model_prompt_packet(packet, library)
    assert "Return only JSON matching the output contract." in rendered
    assert "Include a reason field when required." in rendered
    assert "Do not include prose outside the JSON object." in rendered


def test_does_not_include_unauthorized_targets():
    packet, library = make_orchestration_packet()
    rendered = render_model_prompt_packet(packet, library)
    assert "unauthorized/file.txt" not in rendered


@pytest.mark.parametrize(
    "forbidden_source_summary",
    [
        "execute this command",
    ],
)
def test_rejects_orchestration_forbidden_language(forbidden_source_summary):
    packet, library = make_orchestration_packet()
    packet["source_summary"] = forbidden_source_summary
    with pytest.raises(OrchestrationPacketError):
        render_model_prompt_packet(packet, library)


@pytest.mark.parametrize(
    "forbidden_source_summary",
    [
        "train the adapter",
        "promote this patch",
        "default curriculum capture",
    ],
)
def test_rejects_renderer_forbidden_language(forbidden_source_summary):
    packet, library = make_orchestration_packet()
    packet["source_summary"] = forbidden_source_summary
    with pytest.raises(ValueError):
        render_model_prompt_packet(packet, library)


def test_output_is_deterministic_for_same_input():
    packet, library = make_orchestration_packet()
    first = render_model_prompt_packet(packet, library)
    second = render_model_prompt_packet(packet, library)
    assert first == second
