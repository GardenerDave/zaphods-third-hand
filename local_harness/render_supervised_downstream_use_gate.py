#!/usr/bin/env python3
"""Render supervised downstream-use gate records as plain-text review artifacts."""

from __future__ import annotations

import json
from typing import Any

from local_harness.supervised_downstream_use_gate import validate_supervised_downstream_use_gate_record


def _render_dict(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _render_list(values: list[str]) -> list[str]:
    if not values:
        return ["- <none>"]
    return [f"- {value}" for value in values]


def render_supervised_downstream_use_gate(record: dict[str, Any]) -> str:
    validated = validate_supervised_downstream_use_gate_record(record)

    lines = [
        "# Supervised Downstream-Use Gate Record",
        "",
        "## Gate IDs",
        f"- gate_id: {validated['gate_id']}",
        f"- decision_id: {validated['decision_id']}",
        f"- attempt_id: {validated['attempt_id']}",
        f"- validation_id: {validated['validation_id']}",
        f"- triage_id: {validated['triage_id']}",
        f"- orchestration_id: {validated['orchestration_id']}",
        f"- prompt_packet_id: {validated.get('prompt_packet_id') or '<none>'}",
        "",
        "## Review Decision",
        f"- review_decision: {validated['review_decision']}",
        "",
        "## Requested Downstream Use",
        f"- requested_downstream_use: {validated['requested_downstream_use']}",
        "",
        "## Gate Status",
        f"- gate_status: {validated['gate_status']}",
        "",
        "## Gate Scope",
        f"- gate_scope: {validated['gate_scope']}",
        "",
        "## Operator Metadata",
        f"```json\n{_render_dict(validated['operator_metadata'])}\n```",
        "",
        "## Gate Reason",
        validated["gate_reason"],
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
            "- Allowed means bounded supervised input only for a next supervised step.",
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
            raise ValueError(f"rendered downstream-use gate artifact contains forbidden instruction term: {term}")
    return rendered
