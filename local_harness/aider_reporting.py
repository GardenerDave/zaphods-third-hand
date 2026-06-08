#!/usr/bin/env python3
"""Attempt archiving, output parsing, and event helpers for Aider runs."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence


ATTEMPTS_DIRNAME = "00_aider_attempts"


def reset_debug_artifacts(run_folder: Path) -> None:
    for name in ("AIDER_REQUEST.json", "AIDER_EVENTS.jsonl"):
        path = run_folder / name
        if path.exists():
            path.unlink()


def archive_attempt_artifacts(
    run_folder: Path,
    attempt_number: int,
    output_text: str,
    prewarm: dict[str, Any] | None,
    parse_aider_event_log: Any,
) -> dict[str, Any]:
    attempts_dir = run_folder / ATTEMPTS_DIRNAME
    attempt_dir = attempts_dir / f"attempt_{attempt_number:02d}"
    attempt_dir.mkdir(parents=True, exist_ok=True)

    output_path = attempt_dir / "OUTPUT.md"
    output_path.write_text(output_text, encoding="utf-8")

    if prewarm is not None:
        (attempt_dir / "PREWARM.json").write_text(json.dumps(prewarm, indent=2) + "\n", encoding="utf-8")

    request_dump_path = run_folder / "AIDER_REQUEST.json"
    archived_request_path = None
    if request_dump_path.is_file():
        archived_request_path = attempt_dir / "AIDER_REQUEST.json"
        archived_request_path.write_bytes(request_dump_path.read_bytes())

    events_path = run_folder / "AIDER_EVENTS.jsonl"
    archived_events_path = None
    event_summary = None
    if events_path.is_file():
        archived_events_path = attempt_dir / "AIDER_EVENTS.jsonl"
        archived_events_path.write_bytes(events_path.read_bytes())
        event_summary = parse_aider_event_log(events_path)

    return {
        "attempt_number": attempt_number,
        "attempt_dir": str(attempt_dir),
        "output_path": str(output_path),
        "request_dump_path": str(archived_request_path) if archived_request_path else None,
        "events_path": str(archived_events_path) if archived_events_path else None,
        "event_summary": event_summary,
        "prewarm": prewarm,
    }


def should_retry_after_connection_failure(
    result: subprocess.CompletedProcess[str],
    summary: dict[str, Any],
    event_summary: dict[str, Any] | None,
) -> bool:
    if summary["applied_edit_count"] > 0:
        return False
    if summary["connection_error_detected"]:
        return True
    if result.returncode != 0 and event_summary:
        return bool(event_summary["error_count"] and not event_summary["success_count"])
    return False


def render_attempt_outputs(attempts: Sequence[dict[str, Any]]) -> str:
    if len(attempts) == 1:
        return attempts[0]["output_text"]

    sections: list[str] = []
    for attempt in attempts:
        sections.append(f"# Aider Attempt {attempt['attempt_number']}\n")
        if attempt.get("prewarm") is not None:
            prewarm = attempt["prewarm"]
            sections.append(
                f"- Prewarm success: {prewarm.get('success')}\n"
                f"- Prewarm elapsed seconds: {prewarm.get('elapsed_seconds')}\n"
            )
        sections.append(attempt["output_text"].rstrip() + "\n")
    return "\n".join(section.rstrip() for section in sections).rstrip() + "\n"


def parse_token_count(raw_value: str) -> int | None:
    value = raw_value.strip().lower().replace(",", "")
    multiplier = 1
    if value.endswith("k"):
        multiplier = 1000
        value = value[:-1]
    try:
        return int(float(value) * multiplier)
    except ValueError:
        return None


def summarize_aider_output(output_text: str, selected_files: Sequence[str]) -> dict[str, Any]:
    applied_edits = re.findall(r"Applied edit to\s+([^\n]+)", output_text)
    token_match = re.search(r"Tokens:\s+([0-9.,]+k?) sent,\s+([0-9.,]+k?) received\.", output_text)
    tokens_sent = parse_token_count(token_match.group(1)) if token_match else None
    tokens_received = parse_token_count(token_match.group(2)) if token_match else None
    selected_set = set(selected_files)
    applied_set = set(applied_edits)
    connection_error_detected = "Connection error" in output_text or "OpenAIException" in output_text
    provider_retry_count = len(re.findall(r"Retrying in [0-9.]+ seconds", output_text))
    timeout_hint_detected = "timed out" in output_text.lower() or "timeout" in output_text.lower()
    context_error_detected = "exceeds the available context size" in output_text
    return {
        "thinking_block_present": "► **THINKING**" in output_text,
        "answer_block_present": "► **ANSWER**" in output_text,
        "applied_edits": applied_edits,
        "applied_edit_count": len(applied_edits),
        "all_selected_files_edited": bool(selected_set) and selected_set.issubset(applied_set),
        "unexpected_edit_paths": sorted(applied_set - selected_set),
        "tokens_sent": tokens_sent,
        "tokens_received": tokens_received,
        "context_error_detected": context_error_detected,
        "timeout_hint_detected": timeout_hint_detected,
        "connection_error_detected": connection_error_detected,
        "provider_retry_count": provider_retry_count,
        "fatal_error_detected": connection_error_detected or context_error_detected or timeout_hint_detected,
    }


def parse_aider_event_log(events_path: Path) -> dict[str, Any] | None:
    if not events_path.is_file():
        return None

    entries: list[dict[str, Any]] = []
    for raw_line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    success_previews = [
        entry.get("response_preview")
        for entry in entries
        if entry.get("event") == "send_completion_success" and entry.get("response_preview")
    ]
    error_entries = [entry for entry in entries if entry.get("event") == "send_completion_error"]
    return {
        "event_count": len(entries),
        "start_count": sum(1 for entry in entries if entry.get("event") == "send_completion_start"),
        "success_count": sum(1 for entry in entries if entry.get("event") == "send_completion_success"),
        "error_count": len(error_entries),
        "last_event": entries[-1].get("event") if entries else None,
        "last_error": error_entries[-1] if error_entries else None,
        "success_previews": success_previews[:5],
    }


def build_output_text(result: subprocess.CompletedProcess[str]) -> str:
    sections: list[str] = []
    if result.stdout:
        sections.append(result.stdout.rstrip())
    if result.stderr:
        sections.append("STDERR:\n" + result.stderr.rstrip())
    if not sections:
        sections.append("[no output]")
    return "\n\n".join(sections) + "\n"
