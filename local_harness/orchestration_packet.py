#!/usr/bin/env python3
"""Model-free orchestration boundary packet assembly and validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from local_harness.prompt_patch_library import PromptPatchLibrary, render_prompt_deltas
from local_harness.triage_packet_schema import validate_triage_packet


REQUIRED_PACKET_KEYS = {
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
}
FORBIDDEN_AUTHORITY_KEYS = {
    "execution_authority",
    "auto_promote",
    "auto_train",
    "auto_curriculum_capture",
    "lifecycle_authority",
    "file_write_authority",
    "direct_file_modification_authority",
}
REQUIRED_AUTHORITY_BOUNDARIES = {
    "no_execution_authority",
    "no_automatic_patch_promotion",
    "no_automatic_training",
    "no_default_failure_to_curriculum_capture",
    "no_direct_file_modification_authority",
}
FORBIDDEN_COMMAND_TERMS = {
    "execute this command",
    "run this command",
    "bash -lc",
    "powershell -command",
    "sudo ",
    "rm -rf",
    "curl ",
    "wget ",
}


class OrchestrationPacketError(ValueError):
    """Raised when an orchestration packet is malformed or grants authority."""


def _require_nonempty_str(packet: dict[str, Any], key: str) -> str:
    value = packet.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OrchestrationPacketError(f"packet field {key!r} must be a non-empty string")
    return value


def _require_str_list(packet: dict[str, Any], key: str, *, allow_empty: bool = False) -> list[str]:
    value = packet.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise OrchestrationPacketError(f"packet field {key!r} must be a list of non-empty strings")
    if not value and not allow_empty:
        raise OrchestrationPacketError(f"packet field {key!r} must not be empty")
    return value


def _iter_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_iter_string_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for key, item in value.items():
            if isinstance(key, str):
                values.append(key)
            values.extend(_iter_string_values(item))
        return values
    return []


def validate_orchestration_packet(
    packet: Any,
    prompt_patch_library: PromptPatchLibrary,
    *,
    allow_deprecated_selected: bool = False,
) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise OrchestrationPacketError("orchestration packet must be a JSON object")
    missing = sorted(REQUIRED_PACKET_KEYS - set(packet))
    if missing:
        raise OrchestrationPacketError(f"packet missing required fields: {', '.join(missing)}")

    forbidden = sorted(FORBIDDEN_AUTHORITY_KEYS & set(packet))
    if forbidden:
        raise OrchestrationPacketError(
            f"packet contains forbidden authority fields: {', '.join(forbidden)}"
        )

    _require_nonempty_str(packet, "orchestration_id")
    _require_nonempty_str(packet, "triage_id")
    _require_nonempty_str(packet, "source_summary")
    _require_nonempty_str(packet, "recommended_workflow")
    _require_nonempty_str(packet, "task_type")

    allowed_targets = _require_str_list(packet, "allowed_targets", allow_empty=True)
    held_targets = _require_str_list(packet, "held_targets", allow_empty=True)
    overlap = sorted(set(allowed_targets) & set(held_targets))
    if overlap:
        raise OrchestrationPacketError(
            f"allowed_targets and held_targets overlap: {', '.join(overlap)}"
        )

    _require_str_list(packet, "risk_flags", allow_empty=True)

    selected_prompt_patches = _require_str_list(
        packet,
        "selected_prompt_patches",
        allow_empty=True,
    )
    for patch_id in selected_prompt_patches:
        try:
            patch = prompt_patch_library.get(patch_id)
        except KeyError as exc:
            raise OrchestrationPacketError(f"unknown selected patch_id: {patch_id}") from exc
        if patch["status"] == "deprecated" and not allow_deprecated_selected:
            raise OrchestrationPacketError(
                f"deprecated selected patch_id not allowed by default: {patch_id}"
            )

    _require_nonempty_str(packet, "rendered_patch_deltas")

    output_contract = packet.get("output_contract")
    if not isinstance(output_contract, dict) or not output_contract:
        raise OrchestrationPacketError("packet field 'output_contract' must be a non-empty object")

    _require_str_list(packet, "validation_hooks")

    authority_boundaries = set(_require_str_list(packet, "authority_boundaries"))
    missing_boundaries = sorted(REQUIRED_AUTHORITY_BOUNDARIES - authority_boundaries)
    if missing_boundaries:
        raise OrchestrationPacketError(
            "packet missing required authority boundaries: " + ", ".join(missing_boundaries)
        )

    if packet.get("review_required") is not True:
        raise OrchestrationPacketError("packet field 'review_required' must be true")

    provenance = packet.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise OrchestrationPacketError("packet field 'provenance' must be a non-empty object")
    if provenance.get("triage_id") != packet["triage_id"]:
        raise OrchestrationPacketError("provenance.triage_id must match packet triage_id")

    lowered_strings = [value.lower() for value in _iter_string_values(packet)]
    for term in sorted(FORBIDDEN_COMMAND_TERMS):
        if any(term in value for value in lowered_strings):
            raise OrchestrationPacketError(
                f"packet contains forbidden command execution instruction term: {term}"
            )

    if any("execution authority granted" in value for value in lowered_strings):
        raise OrchestrationPacketError("packet grants forbidden execution authority")
    if any("automatic training allowed" in value for value in lowered_strings):
        raise OrchestrationPacketError("packet grants forbidden automatic training authority")
    if any("automatic promotion allowed" in value for value in lowered_strings):
        raise OrchestrationPacketError("packet grants forbidden automatic promotion authority")
    if any(
        "default failure to curriculum capture allowed" in value for value in lowered_strings
    ):
        raise OrchestrationPacketError(
            "packet grants forbidden default failure-to-curriculum capture authority"
        )

    return packet


def assemble_orchestration_packet(
    triage_packet: dict[str, Any],
    prompt_patch_library: PromptPatchLibrary,
    *,
    orchestration_id: str,
    source_summary: str | None = None,
    allow_deprecated_selected: bool = False,
) -> dict[str, Any]:
    validated_triage = validate_triage_packet(triage_packet, model_facing=True)

    selected_patch_ids = list(validated_triage["recommended_prompt_patches"])
    selected_patches: list[dict[str, Any]] = []
    for patch_id in selected_patch_ids:
        try:
            patch = prompt_patch_library.get(patch_id)
        except KeyError as exc:
            raise OrchestrationPacketError(
                f"recommended patch_id missing from prompt patch library: {patch_id}"
            ) from exc
        if patch["status"] == "deprecated" and not allow_deprecated_selected:
            raise OrchestrationPacketError(
                f"deprecated recommended patch_id not allowed by default: {patch_id}"
            )
        selected_patches.append(patch)

    packet = {
        "orchestration_id": orchestration_id,
        "triage_id": validated_triage["triage_id"],
        "source_summary": source_summary or validated_triage["normalized_intent"],
        "recommended_workflow": validated_triage["recommended_workflow"],
        "task_type": validated_triage["task_type"],
        "allowed_targets": list(validated_triage["allowed_targets"]),
        "held_targets": list(validated_triage["held_targets"]),
        "risk_flags": list(validated_triage["risk_flags"]),
        "selected_prompt_patches": selected_patch_ids,
        "rendered_patch_deltas": render_prompt_deltas(selected_patches),
        "output_contract": deepcopy(validated_triage["output_contract"]),
        "validation_hooks": list(validated_triage["validation_hooks"]),
        "authority_boundaries": sorted(REQUIRED_AUTHORITY_BOUNDARIES),
        "review_required": True,
        "provenance": {
            "source": "orchestration_assembler",
            "triage_id": validated_triage["triage_id"],
            "triage_packet_provenance": deepcopy(validated_triage["provenance"]),
            "selected_patch_ids": selected_patch_ids,
            "selected_patch_statuses": {
                patch["patch_id"]: patch["status"] for patch in selected_patches
            },
        },
    }
    return validate_orchestration_packet(
        packet,
        prompt_patch_library,
        allow_deprecated_selected=allow_deprecated_selected,
    )
