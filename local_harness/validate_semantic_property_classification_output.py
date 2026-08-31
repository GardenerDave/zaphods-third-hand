#!/usr/bin/env python3
"""Validation helpers for per-property semantic classification outputs."""

from __future__ import annotations

from typing import Any


ALLOWED_PROPERTIES = {
    "transport_qualification",
    "bounded_handoff_success",
    "semantic_capability",
    "raw_response_integrity",
    "semantic_acceptance",
}
ALLOWED_STATUSES = {"established", "not_established", "not_asserted"}


def validate(payload: dict[str, Any], *, expected_property: str) -> list[str]:
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]
    prop = payload.get("property")
    status = payload.get("assertion_status")
    if prop not in ALLOWED_PROPERTIES:
        problems.append("property must be one of the controlled vocabulary values")
    elif prop != expected_property:
        problems.append("property must equal the queried property")
    if status not in ALLOWED_STATUSES:
        problems.append("assertion_status must be established, not_established, or not_asserted")
    return problems
