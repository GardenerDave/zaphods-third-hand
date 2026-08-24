#!/usr/bin/env python3
"""Pure, model-free evaluator for the V2 explicit-interface unit.

The evaluator has no filesystem, network, model, or supplier dependencies.  It
accepts only raw supplier content, one scoring-only case record, and protocol
metadata.  Matching is deliberately exact after frozen Unicode/case/whitespace
normalization; there is no synonym expansion or stemming.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any


NORMALIZATION_RULE = (
    "Unicode NFKC; casefold; replace every contiguous Unicode whitespace run with one ASCII space; "
    "strip leading/trailing spaces; no synonym expansion; no stemming"
)


def normalize_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("normalize_text requires a string")
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def contains_required(phrase: str, text: str) -> bool:
    return normalize_text(phrase) in normalize_text(text)


def parse_json_no_duplicate_keys(raw_supplier_content: str | bytes) -> tuple[Any, bool, bool]:
    if isinstance(raw_supplier_content, bytes):
        raw_supplier_content = raw_supplier_content.decode("utf-8")
    duplicate = False

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        nonlocal duplicate
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                duplicate = True
            result[key] = value
        return result

    try:
        parsed = json.loads(raw_supplier_content, object_pairs_hook=pairs_hook)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None, duplicate, False
    return parsed, duplicate, True


def _required_fields(case: dict[str, Any]) -> list[str]:
    return list(case["interface_contract"]["required_fields"])


def _field_types(case: dict[str, Any]) -> dict[str, str]:
    return dict(case["interface_contract"]["field_types"])


def _field_has_facts(value: Any, facts: list[str]) -> bool:
    if isinstance(value, list):
        return all(any(contains_required(fact, item) for item in value if isinstance(item, str)) for fact in facts)
    if isinstance(value, str):
        return all(contains_required(fact, value) for fact in facts)
    return False


def _declared_semantic_text(parsed: dict[str, Any]) -> str:
    fields = ("known_facts", "uncertainty", "next_step")
    values: list[str] = []
    for field in fields:
        value = parsed.get(field)
        if isinstance(value, list):
            values.extend(item for item in value if isinstance(item, str))
        elif isinstance(value, str):
            values.append(value)
    return " ".join(values)


def evaluate(
    raw_supplier_content: str | bytes,
    case_evaluator_record: dict[str, Any],
    protocol_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Return every frozen component dimension and the final direct verdict."""
    parsed, duplicate_keys, parse_valid = parse_json_no_duplicate_keys(raw_supplier_content)
    contract = case_evaluator_record["interface_contract"]
    expected = case_evaluator_record["expected"]
    transport_valid = protocol_metadata.get("transport_valid") is True
    protocol_valid = protocol_metadata.get("protocol_valid") is True
    required_fields_valid = parse_valid and isinstance(parsed, dict) and all(field in parsed for field in _required_fields(case_evaluator_record))
    field_types = _field_types(case_evaluator_record)
    required_field_types_valid = required_fields_valid
    if required_field_types_valid:
        for field, type_name in field_types.items():
            value = parsed.get(field)
            if type_name == "string" and not isinstance(value, str):
                required_field_types_valid = False
            elif type_name == "array_of_strings" and not (isinstance(value, list) and all(isinstance(item, str) for item in value)):
                required_field_types_valid = False
    review_status_valid = required_field_types_valid and parsed.get("review_status") == expected["review_status_exact"]
    if case_evaluator_record["family"] == "triage-routing":
        explicit_interface_valid = required_field_types_valid and parsed.get("route") == expected["route_exact"]
        rationale = parsed.get("rationale") if isinstance(parsed, dict) else None
        task_semantics_valid = isinstance(rationale, str)
        if task_semantics_valid:
            task_semantics_valid = _field_has_facts(rationale, expected["rationale_required_facts"])
            task_semantics_valid = task_semantics_valid and not any(contains_required(fact, rationale) for fact in expected["rationale_forbidden_facts"])
    else:
        explicit_interface_valid = required_field_types_valid
        task_semantics_valid = required_field_types_valid
        if task_semantics_valid:
            task_semantics_valid = _field_has_facts(parsed["known_facts"], expected["known_facts_required"])
            task_semantics_valid = task_semantics_valid and _field_has_facts(parsed["uncertainty"], expected["uncertainty_required"])
            task_semantics_valid = task_semantics_valid and _field_has_facts(parsed["next_step"], expected["next_step_required"])
            task_semantics_valid = task_semantics_valid and not any(contains_required(fact, _declared_semantic_text(parsed)) for fact in expected["prohibited_claims"])
    dimensions = {
        "TRANSPORT_VALID": transport_valid,
        "PARSE_VALID": parse_valid and isinstance(parsed, dict) and not duplicate_keys,
        "DUPLICATE_KEYS_VALID": not duplicate_keys,
        "REQUIRED_FIELDS_VALID": required_fields_valid,
        "REQUIRED_FIELD_TYPES_VALID": required_field_types_valid,
        "EXPLICIT_INTERFACE_VALID": explicit_interface_valid,
        "TASK_SEMANTICS_VALID": task_semantics_valid,
        "REVIEW_STATUS_VALID": review_status_valid,
        "PROTOCOL_VALID": protocol_valid,
    }
    direct_capability_valid = all(dimensions.values())
    return {
        "dimensions": dimensions,
        "DIRECT_CAPABILITY_VALID": direct_capability_valid,
        "parsed": parsed,
        "duplicate_keys": duplicate_keys,
        "normalization_rule": NORMALIZATION_RULE,
        "failure_dimensions": [name for name, value in dimensions.items() if not value],
        "interface_id": contract["interface_id"],
    }
