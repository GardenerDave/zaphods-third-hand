#!/usr/bin/env python3
"""Render supervised chain smoke records as plain-text reports."""

from __future__ import annotations

import json
from typing import Any

from local_harness.supervised_chain_smoke import validate_supervised_chain_smoke_record


def _render_dict(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _render_list(values: list[str]) -> list[str]:
    if not values:
        return ["- <none>"]
    return [f"- {value}" for value in values]


def render_supervised_chain_smoke_report(record: dict[str, Any]) -> str:
    validated = validate_supervised_chain_smoke_record(record)

    lines = [
        "# Supervised Chain Smoke Report",
        "",
        "## Smoke Status",
        f"- smoke_id: {validated['smoke_id']}",
        f"- smoke_status: {validated['smoke_status']}",
        f"- completed_at: {validated['completed_at']}",
        "",
        "## Chain IDs",
        f"- triage_id: {validated['chain']['triage_id']}",
        f"- orchestration_id: {validated['chain']['orchestration_id']}",
        f"- prompt_packet_id: {validated['chain']['prompt_packet_id']}",
        f"- attempt_id: {validated['chain']['attempt_id']}",
        f"- validation_id: {validated['chain']['validation_id']}",
        f"- decision_id: {validated['chain']['decision_id']}",
        f"- gate_id: {validated['chain']['gate_id']}",
        f"- handoff_id: {validated['chain']['handoff_id']}",
        "",
        "## Input Summary",
        f"- started_from: {validated['started_from']}",
        f"- messy_input: {validated['artifacts']['triage_packet']['messy_input']}",
        "",
        "## Artifact Summary",
        "- triage_packet: recorded",
        "- orchestration_packet: recorded",
        "- model_prompt_packet: recorded",
        "- supervised_model_attempt: recorded",
        "- output_validation: recorded",
        "- review_decision: recorded",
        "- downstream_use_gate: recorded",
        "- handoff_packet: recorded",
        "",
        "## Checks",
    ]
    for check in validated["checks"]:
        lines.append(f"- [{check['status']}] {check['check_id']}: {check['message']}")

    lines.extend(["", "## Diagnostics"])
    lines.extend(_render_list(validated["diagnostics"]))

    lines.extend(["", "## Authority Boundaries"])
    lines.extend(_render_list(validated["authority_boundaries"]))

    lines.extend(
        [
            "",
            "## Provenance",
            f"```json\n{_render_dict(validated['provenance'])}\n```",
            "",
            "## Review Requirement",
            "- This smoke report is evidence of deterministic chain integration.",
            "- Smoke evidence is not execution authority.",
            "- Smoke evidence is not file modification authority.",
            "- Smoke evidence is not patch application authority.",
            "- All downstream use remains supervised.",
        ]
    )

    rendered = "\n".join(lines).rstrip() + "\n"
    lowered = rendered.lower()
    for term in ["execute this command", "run this command", "bash -lc", "sudo "]:
        if term in lowered:
            raise ValueError(f"rendered supervised chain smoke report contains forbidden instruction term: {term}")
    return rendered
