from __future__ import annotations

import pytest

from local_harness.orchestration_packet import (
    OrchestrationPacketError,
    assemble_orchestration_packet,
    validate_orchestration_packet,
)
from local_harness.prompt_patch_library import PromptPatchLibrary
from local_harness.triage_packet_schema import TriagePacketError


def make_patch(
    patch_id: str = "scope_boundary_v1",
    *,
    status: str = "candidate",
    stage: str = "prompt_assembly",
) -> dict:
    return {
        "patch_id": patch_id,
        "title": f"Patch {patch_id}",
        "status": status,
        "failure_signature": ["failure mode"],
        "applies_to": {
            "stage": [stage],
            "task_type": ["architecture_planning", "any"],
            "model_size": ["any"],
        },
        "prompt_delta": f"delta for {patch_id}",
        "required_output_fields": ["reason"],
        "validator_expectations": ["reason required"],
    }


def make_library(*, include_recommended: bool = True, deprecated: bool = False) -> PromptPatchLibrary:
    library = PromptPatchLibrary()
    library.add_patch(make_patch("reason_required_v1"))
    library.add_patch(make_patch("scope_boundary_v1", status="deprecated" if deprecated else "candidate"))
    if include_recommended:
        library.add_patch(make_patch("output_contract_v1"))
        library.add_patch(make_patch("unsupported_certainty_v1"))
    return library


def make_triage_packet(**overrides) -> dict:
    packet = {
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
    packet.update(overrides)
    return packet


def make_orchestration_packet(
    library: PromptPatchLibrary,
    *,
    allow_deprecated_selected: bool = False,
    **overrides,
) -> dict:
    packet = assemble_orchestration_packet(
        make_triage_packet(),
        library,
        orchestration_id="orch_example_001",
        source_summary="Messy input normalized into a bounded design packet.",
        allow_deprecated_selected=allow_deprecated_selected,
    )
    packet.update(overrides)
    return packet


def test_accepts_valid_orchestration_packet():
    library = make_library()
    packet = make_orchestration_packet(library)
    assert validate_orchestration_packet(packet, library)["orchestration_id"] == "orch_example_001"


@pytest.mark.parametrize(
    "missing_key",
    [
        "orchestration_id",
        "triage_id",
        "source_summary",
        "recommended_workflow",
        "task_type",
        "allowed_targets",
        "held_targets",
        "risk_flags",
        "selected_prompt_patches",
        "rendered_patch_deltas",
        "output_contract",
        "validation_hooks",
        "authority_boundaries",
        "review_required",
        "provenance",
    ],
)
def test_rejects_missing_required_fields(missing_key):
    library = make_library()
    packet = make_orchestration_packet(library)
    del packet[missing_key]
    with pytest.raises(OrchestrationPacketError):
        validate_orchestration_packet(packet, library)


def test_rejects_review_required_false():
    library = make_library()
    packet = make_orchestration_packet(library, review_required=False)
    with pytest.raises(OrchestrationPacketError, match="must be true"):
        validate_orchestration_packet(packet, library)


def test_rejects_allowed_held_overlap():
    library = make_library()
    packet = make_orchestration_packet(
        library,
        allowed_targets=["docs/TRIAGE_ROUTER.md"],
        held_targets=["docs/TRIAGE_ROUTER.md"],
    )
    with pytest.raises(OrchestrationPacketError, match="overlap"):
        validate_orchestration_packet(packet, library)


def test_rejects_unknown_selected_patch_ids():
    library = make_library()
    packet = make_orchestration_packet(library, selected_prompt_patches=["unknown_patch_v1"])
    with pytest.raises(OrchestrationPacketError, match="unknown selected patch_id"):
        validate_orchestration_packet(packet, library)


def test_rejects_deprecated_selected_patch_by_default():
    library = make_library(deprecated=True)
    with pytest.raises(OrchestrationPacketError, match="deprecated recommended patch_id"):
        make_orchestration_packet(library)


def test_accepts_deprecated_selected_patch_when_explicitly_allowed():
    library = make_library(deprecated=True)
    packet = make_orchestration_packet(
        library,
        allow_deprecated_selected=True,
        selected_prompt_patches=["scope_boundary_v1", "output_contract_v1"],
    )
    assert validate_orchestration_packet(packet, library, allow_deprecated_selected=True)


def test_rejects_packets_with_execution_authority_language():
    library = make_library()
    packet = make_orchestration_packet(library)
    packet["source_summary"] = "execution authority granted for follow-up"
    with pytest.raises(OrchestrationPacketError, match="forbidden execution authority"):
        validate_orchestration_packet(packet, library)


def test_rejects_packets_with_automatic_training_authority_language():
    library = make_library()
    packet = make_orchestration_packet(library)
    packet["source_summary"] = "automatic training allowed for next run"
    with pytest.raises(OrchestrationPacketError, match="automatic training authority"):
        validate_orchestration_packet(packet, library)


def test_rejects_packets_with_automatic_promotion_authority_language():
    library = make_library()
    packet = make_orchestration_packet(library)
    packet["source_summary"] = "automatic promotion allowed for selected patch"
    with pytest.raises(OrchestrationPacketError, match="automatic promotion authority"):
        validate_orchestration_packet(packet, library)


def test_rejects_packets_with_default_failure_to_curriculum_capture_authority_language():
    library = make_library()
    packet = make_orchestration_packet(library)
    packet["source_summary"] = "default failure to curriculum capture allowed"
    with pytest.raises(
        OrchestrationPacketError,
        match="failure-to-curriculum capture authority",
    ):
        validate_orchestration_packet(packet, library)


def test_rejects_command_execution_instructions():
    library = make_library()
    packet = make_orchestration_packet(library)
    packet["source_summary"] = "run this command to apply patch"
    with pytest.raises(OrchestrationPacketError, match="forbidden command execution"):
        validate_orchestration_packet(packet, library)


def test_rejects_direct_file_modification_authority_boundary_removal():
    library = make_library()
    packet = make_orchestration_packet(library)
    packet["authority_boundaries"] = [
        boundary
        for boundary in packet["authority_boundaries"]
        if boundary != "no_direct_file_modification_authority"
    ]
    with pytest.raises(OrchestrationPacketError, match="missing required authority boundaries"):
        validate_orchestration_packet(packet, library)


def test_assembles_from_valid_triage_packet_and_patch_library():
    library = make_library()
    triage_packet = make_triage_packet()
    packet = assemble_orchestration_packet(
        triage_packet,
        library,
        orchestration_id="orch_assemble_001",
        source_summary="Messy input normalized into a bounded design packet.",
    )
    assert packet["triage_id"] == triage_packet["triage_id"]
    assert packet["allowed_targets"] == triage_packet["allowed_targets"]
    assert packet["held_targets"] == triage_packet["held_targets"]
    assert packet["risk_flags"] == triage_packet["risk_flags"]
    assert packet["selected_prompt_patches"] == triage_packet["recommended_prompt_patches"]
    assert "scope_boundary_v1" in packet["rendered_patch_deltas"]
    assert packet["output_contract"] == triage_packet["output_contract"]
    assert packet["validation_hooks"] == triage_packet["validation_hooks"]
    assert "no_execution_authority" in packet["authority_boundaries"]
    assert "run this command" not in packet["rendered_patch_deltas"].lower()


def test_assembler_fails_when_triage_packet_is_invalid():
    library = make_library()
    bad_triage = make_triage_packet(output_contract={})
    with pytest.raises(TriagePacketError):
        assemble_orchestration_packet(
            bad_triage,
            library,
            orchestration_id="orch_invalid_triage_001",
        )


def test_assembler_fails_when_recommended_patch_missing():
    library = make_library(include_recommended=False)
    with pytest.raises(OrchestrationPacketError, match="missing from prompt patch library"):
        assemble_orchestration_packet(
            make_triage_packet(),
            library,
            orchestration_id="orch_missing_patch_001",
        )


def test_assembler_rejects_deprecated_recommended_patch_by_default():
    library = make_library(deprecated=True)
    triage = make_triage_packet()
    with pytest.raises(OrchestrationPacketError, match="deprecated recommended patch_id"):
        assemble_orchestration_packet(
            triage,
            library,
            orchestration_id="orch_deprecated_001",
        )


def test_assembler_accepts_deprecated_recommended_patch_when_explicitly_allowed():
    library = make_library(deprecated=True)
    triage = make_triage_packet()
    packet = assemble_orchestration_packet(
        triage,
        library,
        orchestration_id="orch_deprecated_allowed_001",
        allow_deprecated_selected=True,
    )
    assert packet["selected_prompt_patches"][0] == "scope_boundary_v1"


def test_provenance_links_triage_and_patch_ids():
    library = make_library()
    packet = make_orchestration_packet(library)
    assert packet["provenance"]["triage_id"] == packet["triage_id"]
    assert packet["provenance"]["selected_patch_ids"] == packet["selected_prompt_patches"]
