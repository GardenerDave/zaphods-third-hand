#!/usr/bin/env python3
"""Render supervised review decision records as plain-text review artifacts."""

from __future__ import annotations

import json
from typing import Any

from local_harness.supervised_review_decision import validate_supervised_review_decision_record


def _render_dict(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _render_list(values: list[str]) -> list[str]:
    if not values:
        return ["- <none>"]
    return [f"- {value}" for value in values]


def render_supervised_review_decision(record: dict[str, Any]) -> str:
    validated = validate_supervised_review_decision_record(record)

    lines = [
        "# Supervised Review Decision Record",
        "",
        "## Decision IDs",
        f"- decision_id: {validated['decision_id']}",
        f"- attempt_id: {validated['attempt_id']}",
        f"- validation_id: {validated['validation_id']}",
        f"- triage_id: {validated['triage_id']}",
        f"- orchestration_id: {validated['orchestration_id']}",
        f"- prompt_packet_id: {validated.get('prompt_packet_id') or '<none>'}",
        "",
        "## Decision",
        f"- decision: {validated['decision']}",
        f"- decision_scope: {validated['decision_scope']}",
        "",
        "## Validation Evidence",
        f"- validation_status: {validated['validation_status']}",
        "- Validation is evidence, not automatic acceptance.",
        "",
        "## Reviewer Metadata",
        f"```json\n{_render_dict(validated['reviewer_metadata'])}\n```",
        "",
        "## Decision Reason",
        validated["decision_reason"],
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
            "- Accepted means reviewed for bounded downstream supervised use only.",
            "- No execution/application/promotion/training authority is granted.",
        ]
    )

    rendered = "\n".join(lines).rstrip() + "\n"
    lowered = rendered.lower()
    for term in ["execute this command", "run this command", "bash -lc", "sudo "]:
        if term in lowered:
            raise ValueError(f"rendered decision artifact contains forbidden instruction term: {term}")
    return rendered
