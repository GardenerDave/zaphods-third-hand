"""Collect normalized failure events from audition or probe rows."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable

from .common import read_jsonl, sha256_text, write_jsonl


FAILURE_SCORE_RESULTS = {"fail", "partial", "unknown"}
PASS_SCORE_RESULTS = {"pass", "passed", "accept", "accepted", "ok", "success"}


def normalized_score_result(row: dict[str, Any]) -> str:
    """Return a controlled score_result value for a raw row."""

    for key in ("score_result", "result", "status", "outcome"):
        value = row.get(key)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in FAILURE_SCORE_RESULTS:
                return normalized
            if normalized in PASS_SCORE_RESULTS:
                return "pass"

    passed = row.get("passed")
    if isinstance(passed, bool):
        return "pass" if passed else "fail"

    return "unknown"


def is_failure_row(row: dict[str, Any]) -> bool:
    """Return true when a raw row should become a failure event."""

    return normalized_score_result(row) in FAILURE_SCORE_RESULTS


def _text_field(row: dict[str, Any], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if isinstance(value, str):
            return value
    return ""


def _list_field(row: dict[str, Any], name: str) -> list[str]:
    value = row.get(name)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []


def normalize_failure_event(
    row: dict[str, Any],
    *,
    cycle_id: str,
    source_run_id: str,
    index: int,
) -> dict[str, Any]:
    """Normalize a raw failure row into the failure_event schema shape."""

    prompt = _text_field(row, "prompt", "input", "user_prompt")
    raw_output = _text_field(row, "raw_output", "output", "model_output", "response")
    model_id = _text_field(row, "model_id", "model", "worker_model") or "unknown"
    probe_id = _text_field(row, "probe_id", "task_id", "case_id", "id") or f"row_{index:04d}"
    failure_mode = _text_field(row, "failure_mode", "failure_type", "error_type") or "unknown"
    severity = _text_field(row, "severity") or "medium"
    expected_contract = _text_field(row, "expected_contract", "contract")
    suite = _text_field(row, "suite", "board", "category")
    source_paths = _list_field(row, "source_artifact_paths")

    event_hash = sha256_text(
        "|".join([cycle_id, source_run_id, model_id, probe_id, prompt, raw_output])
    )[:12]

    event = {
        "id": f"failure_{index:04d}_{event_hash}",
        "cycle_id": cycle_id,
        "source_run_id": source_run_id,
        "model_id": model_id,
        "probe_id": probe_id,
        "suite": suite,
        "prompt": prompt,
        "raw_output": raw_output,
        "score_result": normalized_score_result(row),
        "failure_mode": failure_mode,
        "severity": severity,
        "expected_contract": expected_contract,
        "prompt_hash": sha256_text(prompt),
        "raw_output_hash": sha256_text(raw_output),
        "source_artifact_paths": source_paths,
        "source_row": row,
    }

    for key in ("corrected_output", "expected_output", "gold_output", "desired_output"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            event[key] = value

    return event


def collect_failure_events(
    rows: Iterable[dict[str, Any]],
    *,
    cycle_id: str,
    source_run_id: str,
) -> list[dict[str, Any]]:
    """Collect normalized failure events from raw rows."""

    events: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if is_failure_row(row):
            events.append(
                normalize_failure_event(
                    row,
                    cycle_id=cycle_id,
                    source_run_id=source_run_id,
                    index=index,
                )
            )
    return events


def collect_failures_from_jsonl(
    input_path: str | Path,
    output_path: str | Path,
    *,
    cycle_id: str,
    source_run_id: str,
) -> list[dict[str, Any]]:
    """Read raw rows from JSONL and write normalized failure events to JSONL."""

    events = collect_failure_events(
        read_jsonl(input_path),
        cycle_id=cycle_id,
        source_run_id=source_run_id,
    )
    write_jsonl(output_path, events)
    return events


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Raw audition/probe rows JSONL")
    parser.add_argument("--output", required=True, help="Failure events JSONL")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--source-run-id", required=True)
    args = parser.parse_args(argv)

    collect_failures_from_jsonl(
        args.input,
        args.output,
        cycle_id=args.cycle_id,
        source_run_id=args.source_run_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
