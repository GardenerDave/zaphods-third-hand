#!/usr/bin/env python3
"""Validation helpers for candidate-side semantic assertion extraction outputs."""

from __future__ import annotations

from typing import Any


ALLOWED_PROPERTIES = {
    "transport_qualification",
    "bounded_handoff_success",
    "semantic_capability",
    "raw_response_integrity",
    "semantic_acceptance",
}
ALLOWED_EPISTEMIC_STATUSES = {"established", "not_established"}


def validate(payload: dict[str, Any], *, expected_evidence_id: str) -> list[str]:
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    assertions = payload.get("assertions")
    if not isinstance(assertions, list):
        problems.append("assertions must be a list")
        return problems

    for idx, assertion in enumerate(assertions):
        if not isinstance(assertion, dict):
            problems.append(f"assertions[{idx}] must be an object")
            continue

        prop = assertion.get("property")
        status = assertion.get("epistemic_status")
        evidence_refs = assertion.get("evidence_refs")

        if prop not in ALLOWED_PROPERTIES:
            problems.append(f"assertions[{idx}].property must be one of the controlled vocabulary values")
        if status not in ALLOWED_EPISTEMIC_STATUSES:
            problems.append(f"assertions[{idx}].epistemic_status must be established or not_established")
        if not isinstance(evidence_refs, list):
            problems.append(f"assertions[{idx}].evidence_refs must be a list")
            continue
        if len(evidence_refs) != 1:
            problems.append(f"assertions[{idx}].evidence_refs must contain exactly one reference")
            continue
        ref = evidence_refs[0]
        if not isinstance(ref, str) or not ref.strip():
            problems.append(f"assertions[{idx}].evidence_refs[0] must be a non-empty string")
        elif ref != expected_evidence_id:
            problems.append(f"assertions[{idx}].evidence_refs[0] must equal expected evidence id")

    return problems
