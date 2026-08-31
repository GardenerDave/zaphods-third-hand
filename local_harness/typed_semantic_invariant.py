#!/usr/bin/env python3
"""Deterministic checks for experimental typed semantic invariants."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ALLOWED_PROPERTIES = {
    "transport_qualification",
    "bounded_handoff_success",
    "semantic_capability",
    "raw_response_integrity",
    "semantic_acceptance",
}


@dataclass(frozen=True)
class DeterministicInvariantResult:
    invariant_id: str
    result: str
    established_properties: list[str]
    asserted_properties: list[str]
    violating_properties: list[str]
    applicable: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "result": self.result,
            "established_properties": list(self.established_properties),
            "asserted_properties": list(self.asserted_properties),
            "violating_properties": list(self.violating_properties),
            "applicable": self.applicable,
            "reason": self.reason,
        }


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    return payload


def _require_list_of_properties(values: Any, *, field: str) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{field} must be a list")
    normalized: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field} must contain non-empty strings")
        prop = item.strip()
        if prop not in ALLOWED_PROPERTIES:
            raise ValueError(f"unsupported property: {prop}")
        if prop not in normalized:
            normalized.append(prop)
    return normalized


def validate_typed_evidence_fixture(payload: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if payload.get("typing_source") != "frozen_experiment_fixture":
        problems.append("typing_source must be frozen_experiment_fixture")
    evidence_scope = payload.get("evidence_scope")
    if not isinstance(evidence_scope, dict):
        problems.append("evidence_scope must be an object")
        return problems
    try:
        established = _require_list_of_properties(
            evidence_scope.get("established_properties"), field="evidence_scope.established_properties"
        )
        if not established:
            problems.append("evidence_scope.established_properties must be non-empty")
    except ValueError as exc:
        problems.append(str(exc))
    return problems


def validate_typed_assertion_fixture(payload: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if payload.get("typing_source") != "frozen_experiment_fixture":
        problems.append("typing_source must be frozen_experiment_fixture")
    assertions = payload.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        problems.append("assertions must be a non-empty list")
        return problems
    for idx, assertion in enumerate(assertions):
        if not isinstance(assertion, dict):
            problems.append(f"assertions[{idx}] must be an object")
            continue
        try:
            _require_list_of_properties([assertion.get("asserted_property")], field=f"assertions[{idx}].asserted_property")
        except ValueError as exc:
            problems.append(str(exc))
        evidence_refs = assertion.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            problems.append(f"assertions[{idx}].evidence_refs must be a non-empty list")
        else:
            for ref in evidence_refs:
                if not isinstance(ref, str) or not ref.strip():
                    problems.append(f"assertions[{idx}].evidence_refs must contain non-empty strings")
    return problems


def validate_invariant_fixture(payload: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if not isinstance(payload.get("id"), str) or not payload["id"].strip():
        problems.append("id must be a non-empty string")
    if payload.get("status") != "conceptual_only":
        problems.append("status must be conceptual_only")
    antecedent = payload.get("antecedent_properties")
    insufficient = payload.get("insufficient_for")
    try:
        antecedent_props = _require_list_of_properties(antecedent, field="antecedent_properties")
        if not antecedent_props:
            problems.append("antecedent_properties must be non-empty")
    except ValueError as exc:
        problems.append(str(exc))
    try:
        insufficient_props = _require_list_of_properties(insufficient, field="insufficient_for")
        if not insufficient_props:
            problems.append("insufficient_for must be non-empty")
    except ValueError as exc:
        problems.append(str(exc))
    return problems


def evaluate_typed_invariant(
    *,
    invariant: dict[str, Any],
    evidence_scope: dict[str, Any],
    assertions: dict[str, Any],
) -> DeterministicInvariantResult:
    invariant_id = str(invariant["id"])
    antecedent_properties = _require_list_of_properties(
        invariant["antecedent_properties"], field="antecedent_properties"
    )
    insufficient_for = _require_list_of_properties(invariant["insufficient_for"], field="insufficient_for")
    established_properties = _require_list_of_properties(
        evidence_scope["established_properties"], field="evidence_scope.established_properties"
    )
    assertion_list = assertions["assertions"]
    if not isinstance(assertion_list, list) or not assertion_list:
        raise ValueError("assertions must be a non-empty list")

    asserted_properties: list[str] = []
    for assertion in assertion_list:
        if not isinstance(assertion, dict):
            raise ValueError("assertions entries must be objects")
        prop = assertion.get("asserted_property")
        if not isinstance(prop, str) or not prop.strip():
            raise ValueError("asserted_property must be a non-empty string")
        normalized = prop.strip()
        if normalized not in ALLOWED_PROPERTIES:
            raise ValueError(f"unsupported property: {normalized}")
        if normalized not in asserted_properties:
            asserted_properties.append(normalized)

    applicable = bool(set(antecedent_properties) & set(established_properties) or set(asserted_properties) & set(insufficient_for))
    violating_properties = sorted(
        prop
        for prop in asserted_properties
        if prop in insufficient_for and prop not in established_properties
        and bool(set(antecedent_properties) & set(established_properties))
    )
    if violating_properties:
        result = "hold"
        reason = (
            f"{invariant_id}: asserted properties {', '.join(violating_properties)} are not established by the supplied evidence"
        )
    elif set(asserted_properties) & set(established_properties):
        result = "pass"
        reason = f"{invariant_id}: asserted properties are directly established by the supplied evidence"
    elif applicable:
        result = "hold"
        reason = f"{invariant_id}: evidence establishes the antecedent but not the asserted stronger property"
    else:
        result = "not_applicable"
        reason = f"{invariant_id}: the evidence/assertion pair is outside the frozen invariant scope"

    return DeterministicInvariantResult(
        invariant_id=invariant_id,
        result=result,
        established_properties=established_properties,
        asserted_properties=asserted_properties,
        violating_properties=violating_properties,
        applicable=applicable,
        reason=reason,
    )


def parse_fixture(path: Path) -> dict[str, Any]:
    return load_json_object(path)

