"""Classify normalized failure events into deterministic failure modes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from .common import read_jsonl, write_jsonl


PLACEHOLDER_MARKERS = (
    "todo",
    "tbd",
    "placeholder",
    "lorem ipsum",
    "replace me",
    "xxx",
)

CERTAINTY_MARKERS = (
    "all files",
    "no files",
    "every file",
    "none of the files",
    "everything",
    "nothing",
    "always",
    "never",
)

JSON_CONTRACT_MARKERS = (
    "json",
    "schema",
    "object",
    "array",
    "required",
    "valid",
)


def looks_like_json_contract(event: dict[str, Any]) -> bool:
    text = " ".join(
        str(event.get(name, ""))
        for name in ("prompt", "expected_contract", "failure_mode")
    ).lower()
    return any(marker in text for marker in JSON_CONTRACT_MARKERS)


def output_is_valid_json(raw_output: str) -> bool:
    try:
        json.loads(raw_output)
    except json.JSONDecodeError:
        return False
    return True


def classify_failure_mode(event: dict[str, Any]) -> str:
    """Return a deterministic failure mode label for a failure event."""

    prompt = str(event.get("prompt", ""))
    raw_output = str(event.get("raw_output", ""))
    existing = str(event.get("failure_mode", "")).strip().lower()

    if existing and existing != "unknown":
        return existing

    output_lower = raw_output.lower()

    if not raw_output.strip():
        return "empty_output"

    if any(marker in output_lower for marker in PLACEHOLDER_MARKERS):
        return "placeholder_leak"

    if looks_like_json_contract(event) and not output_is_valid_json(raw_output):
        return "invalid_json"

    if any(marker in output_lower for marker in CERTAINTY_MARKERS):
        return "unsupported_certainty"

    if prompt.strip() and raw_output.strip() and len(raw_output.strip()) < 8:
        return "underspecified_output"

    return "unclassified_failure"


def classify_severity(event: dict[str, Any], failure_mode: str) -> str:
    """Return a conservative deterministic severity label."""

    existing = str(event.get("severity", "")).strip().lower()
    if existing and existing not in {"unknown", "medium"}:
        return existing

    if failure_mode in {"invalid_json", "empty_output"}:
        return "high"

    if failure_mode in {"placeholder_leak", "unsupported_certainty"}:
        return "medium"

    return existing or "medium"


def classify_failure_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a failure event with classification fields set."""

    classified = dict(event)
    failure_mode = classify_failure_mode(classified)
    classified["failure_mode"] = failure_mode
    classified["severity"] = classify_severity(classified, failure_mode)
    classified["classification_method"] = "deterministic_rules_v1"
    return classified


def classify_failure_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classify a sequence of normalized failure events."""

    return [classify_failure_event(event) for event in events]


def classify_failures_jsonl(input_path: str | Path, output_path: str | Path) -> list[dict[str, Any]]:
    """Read failure events from JSONL, classify them, and write JSONL."""

    classified = classify_failure_events(read_jsonl(input_path))
    write_jsonl(output_path, classified)
    return classified


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Failure events JSONL")
    parser.add_argument("--output", required=True, help="Classified failure events JSONL")
    args = parser.parse_args(argv)

    classify_failures_jsonl(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
