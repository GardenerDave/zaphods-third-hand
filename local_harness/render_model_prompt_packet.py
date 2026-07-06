#!/usr/bin/env python3
"""Render validated orchestration packets into bounded model prompt packets."""

from __future__ import annotations

import json
from typing import Any

from local_harness.orchestration_packet import validate_orchestration_packet
from local_harness.prompt_patch_library import PromptPatchLibrary


FORBIDDEN_OUTPUT_TERMS = {
    "execute this command",
    "modify files directly",
    "train the adapter",
    "promote this patch",
    "auto-add failure to curriculum",
    "default curriculum capture",
}


def _render_list(values: list[str]) -> list[str]:
    if not values:
        return ["- <none>"]
    return [f"- {value}" for value in values]


def _render_required_response_shape(output_contract: dict[str, Any]) -> list[str]:
    fmt = str(output_contract.get("format", "")).strip().lower()
    if fmt == "json":
        lines = [
            "- Return only JSON matching the output contract.",
            "- Do not include prose outside the JSON object.",
        ]
        if bool(output_contract.get("requires_reason")):
            lines.insert(1, "- Include a reason field when required.")
        return lines
    lines = [
        "- Return output matching the declared output contract format.",
        "- Keep the response bounded to contract-required fields.",
    ]
    if bool(output_contract.get("requires_reason")):
        lines.append("- Include a reason field when required.")
    return lines


def render_model_prompt_packet(
    packet: dict[str, Any],
    prompt_patch_library: PromptPatchLibrary,
    *,
    allow_deprecated_selected: bool = False,
) -> str:
    validated = validate_orchestration_packet(
        packet,
        prompt_patch_library,
        allow_deprecated_selected=allow_deprecated_selected,
    )

    lines = [
        "# ZTH Model Prompt Packet",
        "",
        "## Role",
        "You are a bounded model helper operating inside a supervised ZTH workflow.",
        "",
        "## Packet IDs",
        f"- orchestration_id: {validated['orchestration_id']}",
        f"- triage_id: {validated['triage_id']}",
        "",
        "## Task Summary",
        validated["source_summary"],
        "",
        "## Workflow",
        f"- recommended_workflow: {validated['recommended_workflow']}",
        f"- task_type: {validated['task_type']}",
        "",
        "## Allowed Targets",
    ]
    lines.extend(_render_list(validated["allowed_targets"]))
    lines.extend(["", "## Held Targets"])
    lines.extend(_render_list(validated["held_targets"]))
    lines.extend(["", "## Risk Flags"])
    lines.extend(_render_list(validated["risk_flags"]))
    lines.extend(["", "## Prompt Patch Instructions"])
    lines.extend(_render_list(validated["selected_prompt_patches"]))
    lines.extend(["", "### Rendered Patch Deltas", validated["rendered_patch_deltas"].rstrip(), ""])
    lines.extend(["## Output Contract", f"```json\n{json.dumps(validated['output_contract'], indent=2, sort_keys=True)}\n```", ""])
    lines.append("## Validation Hooks")
    lines.extend(_render_list(validated["validation_hooks"]))
    lines.extend(["", "## Authority Boundaries"])
    lines.extend(_render_list(validated["authority_boundaries"]))
    lines.extend(["", "## Required Response Shape"])
    lines.extend(_render_required_response_shape(validated["output_contract"]))
    lines.extend(["", "## Review Requirement", "- Human review is required before any downstream model-facing action."])

    rendered = "\n".join(lines).rstrip() + "\n"
    lowered = rendered.lower()
    for term in sorted(FORBIDDEN_OUTPUT_TERMS):
        if term in lowered:
            raise ValueError(f"rendered model prompt packet contains forbidden term: {term}")
    return rendered
