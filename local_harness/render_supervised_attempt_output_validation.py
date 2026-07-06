#!/usr/bin/env python3
"""Render supervised attempt output-validation records as plain-text review artifacts."""

from __future__ import annotations

import json
from typing import Any

from local_harness.supervised_attempt_output_validator import (
    validate_supervised_attempt_output_validation_record,
)


def _render_dict(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _render_str_list(values: list[str]) -> list[str]:
    if not values:
        return ["- <none>"]
    return [f"- {value}" for value in values]


def _render_checks(checks: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for check in checks:
        lines.append(f"- [{check['status']}] {check['check_id']}: {check['message']}")
    return lines


def render_supervised_attempt_output_validation(record: dict[str, Any]) -> str:
    validated = validate_supervised_attempt_output_validation_record(record)

    lines = [
        "# Supervised Attempt Output Validation",
        "",
        "## Validation IDs",
        f"- validation_id: {validated['validation_id']}",
        f"- attempt_id: {validated['attempt_id']}",
        f"- orchestration_id: {validated['orchestration_id']}",
        f"- triage_id: {validated['triage_id']}",
        f"- prompt_packet_id: {validated.get('prompt_packet_id') or '<none>'}",
        "",
        "## Validation Status",
        f"- validation_status: {validated['validation_status']}",
        "",
        "## Acceptance Status",
        f"- acceptance_status: {validated['acceptance_status']}",
        "",
        "## Output Contract",
        f"```json\n{_render_dict(validated['output_contract'])}\n```",
        "",
        "## Checks",
    ]
    lines.extend(_render_checks(validated["checks"]))
    lines.extend(["", "## Diagnostics"])
    lines.extend(_render_str_list(validated["diagnostics"]))
    lines.extend(["", "## Authority Boundaries"])
    lines.extend(_render_str_list(validated["authority_boundaries"]))
    lines.extend(
        [
            "",
            "## Provenance",
            f"```json\n{_render_dict(validated['provenance'])}\n```",
            "",
            "## Review Requirement",
            "- Validation is evidence, not acceptance.",
            "- Human review is required before downstream use.",
        ]
    )

    rendered = "\n".join(lines).rstrip() + "\n"
    lowered = rendered.lower()
    if "accepted for use" in lowered or "output accepted" in lowered:
        raise ValueError("rendered validation artifact must not claim acceptance")
    forbidden_instructions = ["execute this command", "run this command", "bash -lc", "sudo "]
    for term in forbidden_instructions:
        if term in lowered:
            raise ValueError(f"rendered validation artifact contains forbidden instruction term: {term}")
    return rendered
