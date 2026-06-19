"""Scoring helpers for local model auditions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any


_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(?P<body>.*?)\s*```\s*$", re.IGNORECASE | re.DOTALL)
_FILE_PATH_RE = re.compile(
    r"(?:(?:^|\s)(?:/[\w.\-]+){2,}|(?:^|\s)(?:[\w.\-]+/){2,}[\w.\-]+\.[A-Za-z0-9]+)"
)
_WORKFLOW_TERM_RE = re.compile(
    r"\b(model|models|audition|auditions|score|scoring|rank|ranking|json|schema|route|router|benchmark|latency|markdown|fence|reasoning_content|no_think)\b",
    re.IGNORECASE,
)


@dataclass
class ScoreEnvelope:
    model_key: str
    prompt_key: str
    prompt_kind: str
    score: int
    max_score: int
    verdict: str
    checks: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def strip_markdown_json_fence(text: str) -> tuple[str, bool]:
    match = _JSON_FENCE_RE.match(text or "")
    if not match:
        return text, False
    return match.group("body"), True


def parse_json_candidate(text: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    raw = text or ""
    unfenced, had_fence = strip_markdown_json_fence(raw)
    diagnostics = {
        "raw_json_valid": False,
        "recoverable_json_valid": False,
        "markdown_fence_leakage": had_fence,
        "json_error": None,
    }

    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            diagnostics["raw_json_valid"] = True
            diagnostics["recoverable_json_valid"] = True
            return obj, diagnostics
        diagnostics["json_error"] = "JSON root is not an object."
        return None, diagnostics
    except json.JSONDecodeError as exc:
        diagnostics["json_error"] = str(exc)

    if had_fence:
        try:
            obj = json.loads(unfenced)
            if isinstance(obj, dict):
                diagnostics["recoverable_json_valid"] = True
                return obj, diagnostics
            diagnostics["json_error"] = "Fenced JSON root is not an object."
        except json.JSONDecodeError as exc:
            diagnostics["json_error"] = str(exc)
    return None, diagnostics


def validate_schema(obj: dict[str, Any] | None, schema: dict[str, str] | None) -> tuple[bool, list[str]]:
    if obj is None:
        return False, ["No JSON object to validate."]
    if not schema:
        return True, []

    errors: list[str] = []
    type_map = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    for key, type_name in schema.items():
        if key not in obj:
            errors.append(f"Missing key: {key}")
            continue
        expected = type_map.get(type_name)
        if expected is None:
            errors.append(f"Unsupported schema type for {key}: {type_name}")
            continue
        value = obj[key]
        if type_name == "number" and isinstance(value, bool):
            errors.append(f"Key {key} expected number, got boolean")
        elif not isinstance(value, expected):
            errors.append(f"Key {key} expected {type_name}, got {type(value).__name__}")
    return not errors, errors


def count_bullets(text: str) -> int:
    return len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", text or ""))


def has_invented_file_path(text: str) -> bool:
    return bool(_FILE_PATH_RE.search(text or ""))


def section_presence(text: str, sections: list[str]) -> dict[str, bool]:
    return {section: bool(re.search(rf"(?mi)^\s*{re.escape(section)}\s*:", text or "")) for section in sections}


def phrase_presence(text: str, phrases: list[str]) -> dict[str, bool]:
    lowered = (text or "").lower()
    return {phrase: phrase.lower() in lowered for phrase in phrases}


def request_text(record: dict[str, Any]) -> str:
    request = record.get("request") or {}
    messages = request.get("messages") or []
    parts: list[str] = []
    for message in messages:
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                parts.append(content)
    return "\n".join(parts)


def confidence_value(obj: dict[str, Any] | None) -> float | None:
    if not obj:
        return None
    value = obj.get("confidence")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def has_workflow_terms(text: str) -> bool:
    return bool(_WORKFLOW_TERM_RE.search(text or ""))


def classify_verdict(score: int, max_score: int) -> str:
    if max_score <= 0:
        return "unscored"
    ratio = score / max_score
    if ratio >= 0.9:
        return "pass"
    if ratio >= 0.65:
        return "watch"
    return "fail"


def extract_message(raw_response: dict[str, Any]) -> dict[str, Any]:
    try:
        return raw_response["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return {}


def score_record(record: dict[str, Any]) -> ScoreEnvelope:
    model_key = record.get("model_key", "unknown_model")
    prompt_key = record.get("prompt_key", "unknown_prompt")
    prompt_kind = record.get("prompt_kind", "unknown")
    expected = record.get("expected") or {}
    raw_response = record.get("response") or {}
    message = extract_message(raw_response)
    content = message.get("content") or ""
    reasoning_content = message.get("reasoning_content") or ""
    finish_reason = None
    try:
        finish_reason = raw_response["choices"][0].get("finish_reason")
    except (KeyError, IndexError, TypeError):
        pass

    timings = raw_response.get("timings") or {}
    predicted_tps = timings.get("predicted_per_second")

    checks: dict[str, Any] = {
        "empty_content": not bool(content.strip()),
        "reasoning_content_present": bool(str(reasoning_content).strip()),
        "finish_reason": finish_reason,
        "predicted_tokens_per_second": predicted_tps,
    }
    notes: list[str] = []
    score = 0
    max_score = 0

    # Universal checks.
    max_score += 1
    if content.strip():
        score += 1
    else:
        notes.append("Empty assistant content.")

    max_score += 1
    if not reasoning_content:
        score += 1
    else:
        notes.append("reasoning_content leaked or consumed output budget.")

    max_score += 1
    if finish_reason == "stop":
        score += 1
    else:
        notes.append(f"finish_reason was {finish_reason!r}, not 'stop'.")

    if prompt_kind == "json_route":
        obj, json_checks = parse_json_candidate(content)
        checks.update(json_checks)
        schema_ok, schema_errors = validate_schema(obj, expected.get("schema"))
        checks["schema_valid"] = schema_ok
        checks["schema_errors"] = schema_errors
        actual_route = obj.get("route") if obj else None
        expected_route = expected.get("route")
        checks["expected_route"] = expected_route
        checks["actual_route"] = actual_route
        checks["route_match"] = actual_route == expected_route
        confidence = confidence_value(obj)
        req_text = request_text(record)
        high_confidence_unknown = (
            actual_route == "unknown"
            and confidence is not None
            and confidence >= 0.75
            and has_workflow_terms(req_text)
        )
        checks["high_confidence_unknown_on_workflow_terms"] = high_confidence_unknown

        max_score += 6
        if json_checks["raw_json_valid"]:
            score += 1
        else:
            notes.append("Output was not raw JSON.")
        if not json_checks["markdown_fence_leakage"]:
            score += 1
        else:
            notes.append("Output had markdown fence leakage.")
        if schema_ok:
            score += 1
        else:
            notes.extend(schema_errors)
        if actual_route == expected_route:
            score += 2
        else:
            notes.append(f"Route mismatch: expected {expected_route!r}, got {actual_route!r}.")
        if not high_confidence_unknown:
            score += 1
        else:
            notes.append("High-confidence unknown on workflow-specific terms; escalate.")

    elif prompt_kind == "structured_report":
        sections = expected.get("sections", [])
        present = section_presence(content, sections)
        checks["sections"] = present
        checks["invented_file_path"] = has_invented_file_path(content)
        max_score += len(sections) + 1
        score += sum(1 for ok in present.values() if ok)
        missing = [name for name, ok in present.items() if not ok]
        if missing:
            notes.append("Missing sections: " + ", ".join(missing))
        if not checks["invented_file_path"]:
            score += 1
        else:
            notes.append("Possible invented file path detected.")

    else:
        must_include = expected.get("must_include", [])
        phrase_checks = phrase_presence(content, must_include)
        checks["must_include"] = phrase_checks
        max_score += len(must_include)
        score += sum(1 for ok in phrase_checks.values() if ok)
        missing = [phrase for phrase, ok in phrase_checks.items() if not ok]
        if missing:
            notes.append("Missing required phrases: " + ", ".join(missing))

        exact_bullets = expected.get("exact_bullets")
        if exact_bullets is not None:
            bullets = count_bullets(content)
            checks["bullet_count"] = bullets
            checks["expected_bullets"] = exact_bullets
            max_score += 1
            if bullets == exact_bullets:
                score += 1
            else:
                notes.append(f"Expected {exact_bullets} bullets, got {bullets}.")

    return ScoreEnvelope(
        model_key=model_key,
        prompt_key=prompt_key,
        prompt_kind=prompt_kind,
        score=score,
        max_score=max_score,
        verdict=classify_verdict(score, max_score),
        checks=checks,
        notes=notes,
    )
