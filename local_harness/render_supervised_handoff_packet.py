#!/usr/bin/env python3
"""Render supervised handoff packets as plain-text review artifacts."""

from __future__ import annotations

import json
from typing import Any

from local_harness.supervised_handoff_packet import validate_supervised_handoff_packet


def _render_dict(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _render_list(values: list[str]) -> list[str]:
    if not values:
        return ["- <none>"]
    return [f"- {value}" for value in values]


def render_supervised_handoff_packet(record: dict[str, Any]) -> str:
    validated = validate_supervised_handoff_packet(record)

    lines = [
        "# Supervised Handoff Packet",
        "",
        "## Handoff IDs",
        f"- handoff_id: {validated['handoff_id']}",
        f"- gate_id: {validated['gate_id']}",
        f"- decision_id: {validated['decision_id']}",
        f"- attempt_id: {validated['attempt_id']}",
        f"- validation_id: {validated['validation_id']}",
        f"- triage_id: {validated['triage_id']}",
        f"- orchestration_id: {validated['orchestration_id']}",
        f"- prompt_packet_id: {validated.get('prompt_packet_id') or '<none>'}",
        "",
        "## Gate Status",
        f"- gate_status: {validated['gate_status']}",
        "",
        "## Handoff Status",
        f"- handoff_status: {validated['handoff_status']}",
        "",
        "## Handoff Scope",
        f"- handoff_scope: {validated['handoff_scope']}",
        "",
        "## Next Step",
        f"- next_step_type: {validated['next_step_type']}",
        f"- next_step_summary: {validated['next_step_summary']}",
        "",
        "## Handoff Payload",
        f"```json\n{_render_dict(validated['handoff_payload'])}\n```",
        "",
        "## Operator Metadata",
        f"```json\n{_render_dict(validated['operator_metadata'])}\n```",
        "",
        "## Handoff Reason",
        validated["handoff_reason"],
        "",
        "## Allowed Downstream Use",
    ]
    lines.extend(_render_list(validated["allowed_downstream_use"]))
    lines.extend(["", "## Prohibited Downstream Use"])
    lines.extend(_render_list(validated["prohibited_downstream_use"]))
    lines.extend(["", "## Authority Boundaries"])
    lines.extend(_render_list(validated["authority_boundaries"]))
    lines.extend(
        [
            "",
            "## Provenance",
            f"```json\n{_render_dict(validated['provenance'])}\n```",
            "",
            "## Review Requirement",
            "- Handoff means bounded supervised input only for the next supervised step.",
            "- No command execution authority is granted.",
            "- No file modification authority is granted.",
            "- No patch application authority is granted.",
            "- No promotion/training/curriculum authority is granted.",
        ]
    )

    rendered = "\n".join(lines).rstrip() + "\n"
    lowered = rendered.lower()
    for term in ["execute this command", "run this command", "bash -lc", "sudo "]:
        if term in lowered:
            raise ValueError(f"rendered supervised handoff artifact contains forbidden instruction term: {term}")
    return rendered
