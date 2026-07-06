#!/usr/bin/env python3
"""Render orchestration boundary packets as plain-text review artifacts."""

from __future__ import annotations

import json
from typing import Any

from local_harness.orchestration_packet import validate_orchestration_packet
from local_harness.prompt_patch_library import PromptPatchLibrary


SECTION_TITLES = [
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
    "## Provenance",
]


def _render_list(values: list[str]) -> list[str]:
    if not values:
        return ["- <none>"]
    return [f"- {value}" for value in values]


def render_orchestration_packet(
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

    lines = [SECTION_TITLES[0], "", SECTION_TITLES[1]]
    lines.extend(
        [
            f"- orchestration_id: {validated['orchestration_id']}",
            f"- triage_id: {validated['triage_id']}",
            f"- source_summary: {validated['source_summary']}",
            "",
            SECTION_TITLES[2],
            f"- recommended_workflow: {validated['recommended_workflow']}",
            f"- task_type: {validated['task_type']}",
            "",
            SECTION_TITLES[3],
        ]
    )
    lines.extend(_render_list(validated["allowed_targets"]))
    lines.extend(["", SECTION_TITLES[4]])
    lines.extend(_render_list(validated["held_targets"]))
    lines.extend(["", SECTION_TITLES[5]])
    lines.extend(_render_list(validated["risk_flags"]))
    lines.extend(["", SECTION_TITLES[6]])
    lines.extend(_render_list(validated["selected_prompt_patches"]))
    lines.extend(["", "### Rendered Patch Deltas", validated["rendered_patch_deltas"].rstrip(), ""])
    lines.extend([SECTION_TITLES[7], f"```json\n{json.dumps(validated['output_contract'], indent=2, sort_keys=True)}\n```", ""])
    lines.append(SECTION_TITLES[8])
    lines.extend(_render_list(validated["validation_hooks"]))
    lines.extend(["", SECTION_TITLES[9]])
    lines.extend(_render_list(validated["authority_boundaries"]))
    lines.extend(["", SECTION_TITLES[10], f"- review_required: {validated['review_required']}", ""])
    lines.extend([SECTION_TITLES[11], f"```json\n{json.dumps(validated['provenance'], indent=2, sort_keys=True)}\n```", ""])
    return "\n".join(lines).rstrip() + "\n"
