"""Deterministic scorer primitives for the ZTH model audition harness."""

from __future__ import annotations

import json
from typing import Any


def _parse_json_from_text(text: str) -> tuple[Any | None, str]:
    """Parse JSON from model text.

    First attempts strict parsing of the full response. If that fails, attempts to
    recover the first JSON object or array embedded in the response text.
    """

    stripped = (text or "").strip()
    if not stripped:
        return None, "empty model text"

    try:
        return json.loads(stripped), ""
    except json.JSONDecodeError as exc:
        first_error = str(exc)

    decoder = json.JSONDecoder()
    candidate_starts = [
        idx for idx, char in enumerate(stripped) if char in "{["
    ]

    for start in candidate_starts:
        try:
            parsed, _end = decoder.raw_decode(stripped[start:])
            return parsed, ""
        except json.JSONDecodeError:
            continue

    return None, first_error


def _completion_metric(model_text: str) -> tuple[float, dict[str, Any], list[str]]:
    completed = bool((model_text or "").strip())
    return (
        1.0 if completed else 0.0,
        {"completed": completed},
        [] if completed else ["empty_output"],
    )


def _json_parse_metric(model_text: str) -> tuple[float, dict[str, Any], list[str]]:
    parsed, error = _parse_json_from_text(model_text)
    if error:
        return 0.0, {"parsed": False, "error": error}, ["json_parse_failed"]
    return 1.0, {"parsed": True, "parsed_type": type(parsed).__name__}, []


def _required_keys_metric(
    *,
    model_text: str,
    keys: list[str],
) -> tuple[float, dict[str, Any], list[str]]:
    parsed, error = _parse_json_from_text(model_text)
    if error:
        return (
            0.0,
            {"parsed": False, "error": error, "required_keys": keys},
            ["json_parse_failed", "missing_required_keys"],
        )

    if not isinstance(parsed, dict):
        return (
            0.0,
            {
                "parsed": True,
                "parsed_type": type(parsed).__name__,
                "required_keys": keys,
            },
            ["json_not_object", "missing_required_keys"],
        )

    if not keys:
        return 1.0, {"required_keys": [], "present_keys": [], "missing_keys": []}, []

    present = [key for key in keys if key in parsed]
    missing = [key for key in keys if key not in parsed]
    score = len(present) / len(keys)

    return (
        score,
        {
            "required_keys": keys,
            "present_keys": present,
            "missing_keys": missing,
        },
        [] if score == 1.0 else ["missing_required_keys"],
    )


def _expected_field_match_metric(
    *,
    fixture: dict[str, Any],
    model_text: str,
) -> tuple[float, dict[str, Any], list[str]]:
    expected = fixture.get("expected") or {}
    if not isinstance(expected, dict) or not expected:
        return 1.0, {"expected_fields": {}, "note": "no expected fields"}, []

    parsed, error = _parse_json_from_text(model_text)
    if error:
        return (
            0.0,
            {"parsed": False, "error": error, "expected_fields": expected},
            ["json_parse_failed", "expected_field_mismatch"],
        )

    if not isinstance(parsed, dict):
        return (
            0.0,
            {
                "parsed": True,
                "parsed_type": type(parsed).__name__,
                "expected_fields": expected,
            },
            ["json_not_object", "expected_field_mismatch"],
        )

    matches: dict[str, bool] = {}
    actual_values: dict[str, Any] = {}

    for key, expected_value in expected.items():
        actual_value = parsed.get(key)
        actual_values[key] = actual_value
        matches[key] = actual_value == expected_value

    score = sum(1 for did_match in matches.values() if did_match) / len(matches)

    return (
        score,
        {
            "expected_fields": expected,
            "actual_values": actual_values,
            "matches": matches,
        },
        [] if score == 1.0 else ["expected_field_mismatch"],
    )



def _flatten_json_strings(value: Any) -> list[str]:
    """Collect searchable string values from nested JSON-like data."""

    strings: list[str] = []

    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for key, nested in value.items():
            strings.append(str(key))
            strings.extend(_flatten_json_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            strings.extend(_flatten_json_strings(nested))
    elif value is not None:
        strings.append(str(value))

    return strings


def _expected_contains_metric(
    *,
    fixture: dict[str, Any],
    model_text: str,
) -> tuple[float, dict[str, Any], list[str]]:
    expected = fixture.get("expected") or {}
    required_terms = []

    if isinstance(expected, dict):
        raw_terms = expected.get("required_terms", [])
        if isinstance(raw_terms, list):
            required_terms = [str(term) for term in raw_terms]
        elif raw_terms:
            required_terms = [str(raw_terms)]

    if not required_terms:
        return 1.0, {"required_terms": [], "note": "no required terms"}, []

    parsed, _error = _parse_json_from_text(model_text)
    searchable_parts = [model_text]

    if parsed is not None:
        searchable_parts.extend(_flatten_json_strings(parsed))

    haystack = "\n".join(searchable_parts).lower()

    found = [term for term in required_terms if term.lower() in haystack]
    missing = [term for term in required_terms if term.lower() not in haystack]
    score = len(found) / len(required_terms)

    return (
        score,
        {
            "required_terms": required_terms,
            "found_terms": found,
            "missing_terms": missing,
        },
        [] if score == 1.0 else ["expected_contains_missing"],
    )

def _runtime_metric(
    *,
    runtime: dict[str, Any],
    target_seconds: float,
) -> tuple[float, dict[str, Any], list[str]]:
    actual = runtime.get("wall_time_seconds")

    if actual is None:
        return (
            0.0,
            {"target_seconds": target_seconds, "wall_time_seconds": None},
            ["runtime_missing"],
        )

    actual_float = float(actual)
    target_float = float(target_seconds)

    if target_float <= 0:
        score = 1.0
    elif actual_float <= target_float:
        score = 1.0
    else:
        score = max(0.0, min(1.0, target_float / actual_float))

    return (
        score,
        {
            "target_seconds": target_float,
            "wall_time_seconds": actual_float,
        },
        [] if score == 1.0 else ["runtime_over_target"],
    )


def score_case(
    *,
    fixture: dict[str, Any],
    model_text: str,
    scorer_profile: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    """Score one audition case using deterministic scorer primitives."""

    case_id = fixture.get("case_id", "")
    metric_results: dict[str, dict[str, Any]] = {}
    failure_modes: list[str] = []

    weighted_total = 0.0
    total_weight = 0.0

    for metric in scorer_profile.get("metrics", []):
        metric_id = metric.get("id") or metric.get("type") or "unknown_metric"
        metric_type = metric.get("type")
        weight = float(metric.get("weight", 0.0))

        if metric_type == "completion":
            score, details, failures = _completion_metric(model_text)
        elif metric_type == "json_parse":
            score, details, failures = _json_parse_metric(model_text)
        elif metric_type == "required_keys":
            keys = list(metric.get("keys", []))
            score, details, failures = _required_keys_metric(
                model_text=model_text,
                keys=keys,
            )
        elif metric_type == "expected_field_match":
            score, details, failures = _expected_field_match_metric(
                fixture=fixture,
                model_text=model_text,
            )
        elif metric_type == "runtime":
            score, details, failures = _runtime_metric(
                runtime=runtime,
                target_seconds=float(metric.get("target_seconds", 60)),
            )
        elif metric_type == "expected_contains":
            score, details, failures = _expected_contains_metric(
                fixture=fixture,
                model_text=model_text,
            )
        else:
            score = 0.0
            details = {"error": f"unknown scorer type: {metric_type}"}
            failures = [f"unknown_scorer_type:{metric_type}"]

        score = max(0.0, min(1.0, float(score)))

        metric_results[metric_id] = {
            "score": score,
            "weight": weight,
            "details": details,
        }

        if weight > 0:
            weighted_total += score * weight
            total_weight += weight

        failure_modes.extend(failures)

    overall = weighted_total / total_weight if total_weight else 0.0

    return {
        "case_id": case_id,
        "overall": overall,
        "metrics": metric_results,
        "failure_modes": sorted(set(failure_modes)),
    }
