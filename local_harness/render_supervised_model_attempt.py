#!/usr/bin/env python3
"""Render supervised model attempt records as plain-text review artifacts."""

from __future__ import annotations

import json
from typing import Any

from local_harness.supervised_model_attempt import validate_supervised_model_attempt_record


def _render_dict(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _render_list(values: list[str]) -> list[str]:
    if not values:
        return ["- <none>"]
    return [f"- {value}" for value in values]


def render_supervised_model_attempt(record: dict[str, Any]) -> str:
    validated = validate_supervised_model_attempt_record(record)

    lines = [
        "# Supervised Model Attempt Record",
        "",
        "## Attempt IDs",
        f"- attempt_id: {validated['attempt_id']}",
        f"- orchestration_id: {validated['orchestration_id']}",
        f"- triage_id: {validated['triage_id']}",
        f"- prompt_packet_id: {validated.get('prompt_packet_id') or '<none>'}",
        "",
        "## Model Metadata",
        f"```json\n{_render_dict(validated['model_metadata'])}\n```",
        "",
        "## Operator Metadata",
        f"```json\n{_render_dict(validated['operator_metadata'])}\n```",
        "",
        "## Source Prompt Packet",
        f"- source_prompt_packet_path: {validated.get('source_prompt_packet_path') or '<none>'}",
        "",
        "## Raw Model Output",
        "```text",
        validated["raw_model_output"],
        "```",
        "",
        "## Validation Status",
        f"- validation_status: {validated['validation_status']}",
        "",
        "## Acceptance Status",
        f"- acceptance_status: {validated['acceptance_status']}",
        "",
        "## Authority Boundaries",
    ]
    lines.extend(_render_list(validated["authority_boundaries"]))
    lines.extend(
        [
            "",
            "## Provenance",
            f"```json\n{_render_dict(validated['provenance'])}\n```",
            "",
            "## Review Requirement",
            "- Human review is required before downstream use.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
