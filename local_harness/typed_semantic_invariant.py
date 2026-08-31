#!/usr/bin/env python3
"""Deterministic checks for experimental typed semantic invariants."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_PROPERTIES = {
    "transport_qualification",
    "bounded_handoff_success",
    "semantic_capability",
    "raw_response_integrity",
    "semantic_acceptance",
}

ALLOWED_EPISTEMIC_STATUSES = {
    "established",
    "not_established",
}

ALLOWED_RESULTS = {
    "pass",
    "hold",
    "not_applicable",
}


@dataclass(frozen=True)
class DeterministicInvariantResult:
    invariant_id: str
    result: str
    applicable: bool
    evidence_id: str
    established_properties: list[str]
    asserted_properties: list[str]
    violating_properties: list[str]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "result": self.result,
            "applicable": self.applicable,
            "evidence_id": self.evidence_id,
            "established_properties": list(self.established_properties),
            "asserted_properties": list(self.asserted_properties),
            "violating_properties": list(self.violating_properties),
            "reason": self.reason,
        }


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    return payload


def _require_list_of_strings(values: Any, *, field: str, allowed: set[str] | None = None) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{field} must be a list")
    normalized: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field} must contain non-empty strings")
        value = item.strip()
        if allowed is not None and value not in allowed:
            raise ValueError(f"unsupported value in {field}: {value}")
        if value not in normalized:
            normalized.append(value)
    return normalized


def validate_typed_evidence_fixture(payload: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if payload.get("typing_source") != "frozen_experiment_fixture":
        problems.append("typing_source must be frozen_experiment_fixture")
    evidence_id = payload.get("evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        problems.append("evidence_id must be a non-empty string")
    evidence_scope = payload.get("evidence_scope")
    if not isinstance(evidence_scope, dict):
        problems.append("evidence_scope must be an object")
        return problems
    try:
        established = _require_list_of_strings(
            evidence_scope.get("established_properties"),
            field="evidence_scope.established_properties",
            allowed=ALLOWED_PROPERTIES,
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
        prop = assertion.get("property")
        if not isinstance(prop, str) or not prop.strip():
            problems.append(f"assertions[{idx}].property must be a non-empty string")
        elif prop.strip() not in ALLOWED_PROPERTIES:
            problems.append(f"unsupported property: {prop.strip()}")
        status = assertion.get("epistemic_status")
        if not isinstance(status, str) or not status.strip():
            problems.append(f"assertions[{idx}].epistemic_status must be a non-empty string")
        elif status.strip() not in ALLOWED_EPISTEMIC_STATUSES:
            problems.append(f"unsupported epistemic_status: {status.strip()}")
        evidence_refs = assertion.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            problems.append(f"assertions[{idx}].evidence_refs must be a non-empty list")
        else:
            for ref in evidence_refs:
                if not isinstance(ref, str) or not ref.strip():
                    problems.append(f"assertions[{idx}].evidence_refs must contain non-empty strings")
        if "claim_text" in assertion and (not isinstance(assertion["claim_text"], str) or not assertion["claim_text"].strip()):
            problems.append(f"assertions[{idx}].claim_text must be a non-empty string when present")
    return problems


def validate_invariant_fixture(payload: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if not isinstance(payload.get("id"), str) or not payload["id"].strip():
        problems.append("id must be a non-empty string")
    if payload.get("status") != "conceptual_only":
        problems.append("status must be conceptual_only")
    if payload.get("antecedent_match") not in {"all", "any"}:
        problems.append("antecedent_match must be all or any")
    try:
        antecedent_props = _require_list_of_strings(
            payload.get("antecedent_properties"),
            field="antecedent_properties",
            allowed=ALLOWED_PROPERTIES,
        )
        if not antecedent_props:
            problems.append("antecedent_properties must be non-empty")
    except ValueError as exc:
        problems.append(str(exc))
    try:
        insufficient_props = _require_list_of_strings(
            payload.get("insufficient_for"),
            field="insufficient_for",
            allowed=ALLOWED_PROPERTIES,
        )
        if not insufficient_props:
            problems.append("insufficient_for must be non-empty")
    except ValueError as exc:
        problems.append(str(exc))
    return problems


def _resolve_refs(assertion: dict[str, Any], evidence_id: str) -> None:
    refs = assertion.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("assertions entries must include a non-empty evidence_refs list")
    resolved = []
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError("assertions entries must include non-empty evidence_refs strings")
        resolved.append(ref.strip())
    if evidence_id not in resolved:
        raise ValueError(f"assertion evidence_refs do not resolve to supplied evidence_id: {evidence_id}")


def evaluate_typed_invariant(
    *,
    invariant: dict[str, Any],
    evidence: dict[str, Any],
    assertions: dict[str, Any],
) -> DeterministicInvariantResult:
    invariant_id = str(invariant["id"])
    antecedent_properties = _require_list_of_strings(
        invariant["antecedent_properties"], field="antecedent_properties", allowed=ALLOWED_PROPERTIES
    )
    insufficient_for = _require_list_of_strings(
        invariant["insufficient_for"], field="insufficient_for", allowed=ALLOWED_PROPERTIES
    )
    match_mode = invariant.get("antecedent_match")
    if match_mode not in {"all", "any"}:
        raise ValueError("antecedent_match must be all or any")

    evidence_id = evidence.get("evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("evidence.evidence_id must be a non-empty string")
    evidence_id = evidence_id.strip()
    evidence_scope = evidence.get("evidence_scope")
    if not isinstance(evidence_scope, dict):
        raise ValueError("evidence.evidence_scope must be an object")
    established_properties = _require_list_of_strings(
        evidence_scope.get("established_properties"),
        field="evidence_scope.established_properties",
        allowed=ALLOWED_PROPERTIES,
    )

    assertion_list = assertions.get("assertions")
    if not isinstance(assertion_list, list) or not assertion_list:
        raise ValueError("assertions must be a non-empty list")

    asserted_properties: list[str] = []
    for assertion in assertion_list:
        if not isinstance(assertion, dict):
            raise ValueError("assertions entries must be objects")
        _resolve_refs(assertion, evidence_id)
        prop = assertion.get("property")
        if not isinstance(prop, str) or not prop.strip():
            raise ValueError("assertions entries must include a non-empty property")
        prop = prop.strip()
        if prop not in ALLOWED_PROPERTIES:
            raise ValueError(f"unsupported property: {prop}")
        status = assertion.get("epistemic_status")
        if status not in ALLOWED_EPISTEMIC_STATUSES:
            raise ValueError("assertions entries must include a valid epistemic_status")
        if prop not in asserted_properties:
            asserted_properties.append(prop)

    if match_mode == "all":
        antecedent_applies = set(antecedent_properties).issubset(set(established_properties))
    else:
        antecedent_applies = bool(set(antecedent_properties) & set(established_properties))

    violating_properties = sorted(
        prop for prop in asserted_properties if prop in insufficient_for and prop not in established_properties
    )

    if violating_properties and antecedent_applies:
        result = "hold"
        reason = (
            f"{invariant_id}: asserted properties {', '.join(violating_properties)} are not established by the supplied evidence"
        )
    elif set(asserted_properties).issubset(set(established_properties)) and asserted_properties:
        result = "pass"
        reason = f"{invariant_id}: asserted properties are directly established by the supplied evidence"
    elif antecedent_applies:
        if any(prop in insufficient_for for prop in asserted_properties):
            result = "hold"
            reason = f"{invariant_id}: evidence establishes the antecedent but not the asserted stronger property"
        else:
            result = "pass"
            reason = f"{invariant_id}: assertion is outside the forbidden relation for the supplied evidence"
    else:
        result = "not_applicable"
        reason = f"{invariant_id}: the evidence/assertion pair is outside the frozen invariant scope"

    if result not in ALLOWED_RESULTS:
        raise ValueError(f"unexpected result: {result}")

    applicable = antecedent_applies
    return DeterministicInvariantResult(
        invariant_id=invariant_id,
        result=result,
        applicable=applicable,
        evidence_id=evidence_id,
        established_properties=established_properties,
        asserted_properties=asserted_properties,
        violating_properties=violating_properties,
        reason=reason,
    )


def parse_fixture(path: Path) -> dict[str, Any]:
    return load_json_object(path)

