#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROFILE_SETTINGS: dict[str, dict[str, int]] = {
    "smoke": {
        "ZTH_DISTILLER_SESSION_MAX_TOKENS": 320,
        "ZTH_DISTILLER_PATCH_MAX_TOKENS": 240,
        "ZTH_DISTILLER_TIMEOUT": 240,
    },
    "normal": {
        "ZTH_DISTILLER_SESSION_MAX_TOKENS": 700,
        "ZTH_DISTILLER_PATCH_MAX_TOKENS": 280,
        "ZTH_DISTILLER_TIMEOUT": 900,
    },
    "chunked": {
        "ZTH_DISTILLER_CHUNK_LINES": 200,
        "ZTH_DISTILLER_CHUNK_MAX_TOKENS": 600,
        "ZTH_DISTILLER_SESSION_MAX_TOKENS": 1200,
        "ZTH_DISTILLER_PATCH_MAX_TOKENS": 900,
        "ZTH_DISTILLER_TIMEOUT": 900,
    },
}
DEFAULT_MIN_RECENT_RUNS_FOR_CHUNKED = 3
DEFAULT_CALIBRATION_WINDOW = 20


@dataclass
class RunSummary:
    run_dir: Path
    source_id: str
    short_title: str
    status: str
    failure_stage: str
    compact_mode: bool
    chunked_mode: bool
    run_profile: str
    run_purpose: str
    chunk_line_size: int
    chunk_max_tokens: int
    session_max_tokens: int
    patch_max_tokens: int
    call_timeout_seconds: int
    total_elapsed_seconds: int
    source_bytes: int
    source_lines: int
    source_estimated_tokens: int
    session_prompt_bytes: int
    session_prompt_lines: int
    session_prompt_estimated_tokens: int
    patch_prompt_bytes: int
    patch_prompt_lines: int
    patch_prompt_estimated_tokens: int
    session_bytes: int
    session_lines: int
    session_estimated_tokens: int
    patch_bytes: int
    patch_lines: int
    patch_estimated_tokens: int
    usage_available: bool
    session_finish_reason: str
    session_prompt_tokens_actual: int
    session_completion_tokens_actual: int
    session_total_tokens_actual: int
    session_prompt_ms: float
    session_predicted_ms: float
    session_prompt_per_second: float
    session_predicted_per_second: float
    patch_finish_reason: str
    patch_prompt_tokens_actual: int
    patch_completion_tokens_actual: int
    patch_total_tokens_actual: int
    patch_prompt_ms: float
    patch_predicted_ms: float
    patch_prompt_per_second: float
    patch_predicted_per_second: float
    total_prompt_tokens_actual: int
    total_completion_tokens_actual: int
    total_tokens_actual: int
    chunk_attempted: int
    chunk_succeeded: int
    chunk_failed: int
    chunk_retry_count: int
    chunk_split_seconds: int
    chunk_summary_seconds: int
    session_stage_seconds: int
    patch_stage_seconds: int
    completed_at: str
    sort_epoch: float
    chunk_rows: int
    chunk_row_failures: int


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip() == "1"


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def usage_has_tokens(usage: dict[str, Any]) -> bool:
    return any(is_number(usage.get(key)) for key in ("prompt_tokens", "completion_tokens", "total_tokens"))


def usage_total(prompt_tokens: int, completion_tokens: int, total_tokens: int) -> int:
    if total_tokens > 0:
        return total_tokens
    if prompt_tokens > 0 or completion_tokens > 0:
        return prompt_tokens + completion_tokens
    return 0


def safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def format_optional_ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def normalize_label(value: Any, default: str = "") -> str:
    normalized = str(value or "").strip().lower().replace(" ", "_")
    return normalized or default


def infer_run_profile(chunked_mode: bool, session_max_tokens: int, patch_max_tokens: int) -> str:
    if chunked_mode:
        return "chunked"
    if session_max_tokens > 0 and patch_max_tokens > 0:
        if session_max_tokens <= 320 and patch_max_tokens <= 240:
            return "smoke"
        if session_max_tokens <= 900 and patch_max_tokens <= 700:
            return "normal"
    return "custom"


def infer_run_purpose(run_profile: str, source_id: str, short_title: str) -> str:
    combined = f"{source_id} {short_title}".lower()
    if run_profile == "smoke":
        return "connectivity"
    if "connectivity" in combined or "smoke" in combined:
        return "connectivity"
    if "tuning" in combined or "budget" in combined or "finish-reason" in combined:
        return "tuning"
    if "test" in combined:
        return "test"
    return "handoff"


def parse_filter_values(values: list[str]) -> set[str]:
    labels: set[str] = set()
    for value in values:
        for item in value.split(","):
            label = normalize_label(item)
            if label:
                labels.add(label)
    return labels


def filter_runs(
    runs: list[RunSummary],
    profiles: set[str],
    purposes: set[str],
    excluded_purposes: set[str],
) -> list[RunSummary]:
    filtered: list[RunSummary] = []
    for run in runs:
        if profiles and run.run_profile not in profiles:
            continue
        if purposes and run.run_purpose not in purposes:
            continue
        if excluded_purposes and run.run_purpose in excluded_purposes:
            continue
        filtered.append(run)
    return filtered


def parse_chunk_metrics(path: str, run_dir: Path) -> tuple[int, int]:
    if not path:
        return (0, 0)
    chunk_path = Path(path)
    if not chunk_path.is_file() and not chunk_path.is_absolute():
        chunk_path = run_dir / chunk_path
    if not chunk_path.is_file():
        chunk_path = run_dir / Path(path).name
    if not chunk_path.is_file():
        return (0, 0)
    lines = chunk_path.read_text(encoding="utf-8").splitlines()
    if len(lines) <= 1:
        return (0, 0)
    rows = lines[1:]
    failures = 0
    for row in rows:
        cols = row.split("\t")
        if len(cols) >= 3 and cols[2] != "completed":
            failures += 1
    return (len(rows), failures)


def parse_sort_epoch(completed_at: str) -> float:
    if not completed_at:
        return 0.0
    try:
        return datetime.fromisoformat(completed_at.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def load_json_sidecar(path: str, run_dir: Path) -> dict[str, Any]:
    if not path:
        return {}
    sidecar = Path(path)
    if not sidecar.is_absolute():
        sidecar = run_dir / sidecar
    if not sidecar.is_file():
        sidecar = run_dir / Path(path).name
    if not sidecar.is_file():
        return {}
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def model_call_section(model_usage: dict[str, Any], key: str, metadata: dict[str, Any]) -> dict[str, Any]:
    section = model_usage.get(key, {}) if isinstance(model_usage, dict) else {}
    if not isinstance(section, dict):
        section = {}
    usage = section
    metadata_usage = metadata.get("usage", {})
    if not usage_has_tokens(usage) and isinstance(metadata_usage, dict):
        usage = {**metadata_usage, **section}
    finish_reason = section.get("finish_reason") or metadata.get("finish_reason")
    timings = section.get("timings")
    if not isinstance(timings, dict):
        metadata_timings = metadata.get("timings", {})
        timings = metadata_timings if isinstance(metadata_timings, dict) else {}
    return {**usage, "finish_reason": finish_reason, "timings": timings}


def parse_run(metrics_path: Path) -> RunSummary:
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    stages = data.get("stages", {})
    chunk_split = stages.get("chunk_split", {})
    chunk_summary = stages.get("chunk_summary", {})
    session_stage = stages.get("session", {})
    patch_stage = stages.get("review_patch", {})
    prompts = data.get("prompts", {})
    outputs = data.get("outputs", {})
    source = data.get("source", {})
    model_usage = data.get("model_usage", {})
    session_metadata = (
        load_json_sidecar(str(model_usage.get("session_metadata_file", "")), metrics_path.parent)
        if isinstance(model_usage, dict)
        else {}
    )
    patch_metadata = (
        load_json_sidecar(str(model_usage.get("patch_metadata_file", "")), metrics_path.parent)
        if isinstance(model_usage, dict)
        else {}
    )
    session_usage = model_call_section(model_usage, "session", session_metadata) if isinstance(model_usage, dict) else {}
    patch_usage = model_call_section(model_usage, "review_patch", patch_metadata) if isinstance(model_usage, dict) else {}
    session_timings = session_usage.get("timings", {}) if isinstance(session_usage, dict) else {}
    patch_timings = patch_usage.get("timings", {}) if isinstance(patch_usage, dict) else {}
    session_finish_reason = str(session_usage.get("finish_reason") or "") if isinstance(session_usage, dict) else ""
    patch_finish_reason = str(patch_usage.get("finish_reason") or "") if isinstance(patch_usage, dict) else ""
    session_prompt_tokens_actual = to_int(session_usage.get("prompt_tokens", 0)) if isinstance(session_usage, dict) else 0
    session_completion_tokens_actual = to_int(session_usage.get("completion_tokens", 0)) if isinstance(session_usage, dict) else 0
    session_total_tokens_actual = (
        to_int(session_usage.get("total_tokens", 0)) if isinstance(session_usage, dict) else 0
    )
    session_total_tokens_actual = usage_total(
        session_prompt_tokens_actual,
        session_completion_tokens_actual,
        session_total_tokens_actual,
    )
    patch_prompt_tokens_actual = to_int(patch_usage.get("prompt_tokens", 0)) if isinstance(patch_usage, dict) else 0
    patch_completion_tokens_actual = (
        to_int(patch_usage.get("completion_tokens", 0)) if isinstance(patch_usage, dict) else 0
    )
    patch_total_tokens_actual = to_int(patch_usage.get("total_tokens", 0)) if isinstance(patch_usage, dict) else 0
    patch_total_tokens_actual = usage_total(
        patch_prompt_tokens_actual,
        patch_completion_tokens_actual,
        patch_total_tokens_actual,
    )
    usage_available = (
        (isinstance(session_usage, dict) and usage_has_tokens(session_usage))
        or (isinstance(patch_usage, dict) and usage_has_tokens(patch_usage))
    )
    completed_at = str(data.get("run_completed_at", ""))
    sort_epoch = parse_sort_epoch(completed_at)
    if sort_epoch == 0.0:
        sort_epoch = metrics_path.stat().st_mtime
    chunk_metrics_file = str(chunk_summary.get("chunk_metrics_file", ""))
    chunk_rows, chunk_row_failures = parse_chunk_metrics(chunk_metrics_file, metrics_path.parent)
    compact_mode = to_bool(data.get("compact_mode", "0"))
    chunked_mode = to_bool(data.get("chunked_mode", "0"))
    session_max_tokens = to_int(data.get("session_max_tokens", 0))
    patch_max_tokens = to_int(data.get("patch_max_tokens", 0))
    source_id = str(data.get("source_id", ""))
    short_title = str(data.get("short_title", ""))
    run_profile = normalize_label(
        data.get("run_profile"),
        infer_run_profile(chunked_mode, session_max_tokens, patch_max_tokens),
    )
    run_purpose = normalize_label(
        data.get("run_purpose"),
        infer_run_purpose(run_profile, source_id, short_title),
    )

    return RunSummary(
        run_dir=metrics_path.parent,
        source_id=source_id,
        short_title=short_title,
        status=str(data.get("status", "unknown")),
        failure_stage=str(data.get("failure_stage", "")),
        compact_mode=compact_mode,
        chunked_mode=chunked_mode,
        run_profile=run_profile,
        run_purpose=run_purpose,
        chunk_line_size=to_int(data.get("chunk_line_size", 0)),
        chunk_max_tokens=to_int(data.get("chunk_max_tokens", 0)),
        session_max_tokens=session_max_tokens,
        patch_max_tokens=patch_max_tokens,
        call_timeout_seconds=to_int(data.get("call_timeout_seconds", 0)),
        total_elapsed_seconds=to_int(data.get("total_elapsed_seconds", 0)),
        source_bytes=to_int(source.get("bytes", 0)),
        source_lines=to_int(source.get("lines", 0)),
        source_estimated_tokens=to_int(source.get("estimated_tokens", 0)),
        session_prompt_bytes=to_int(prompts.get("session_prompt_bytes", 0)),
        session_prompt_lines=to_int(prompts.get("session_prompt_lines", 0)),
        session_prompt_estimated_tokens=to_int(prompts.get("session_prompt_estimated_tokens", 0)),
        patch_prompt_bytes=to_int(prompts.get("patch_prompt_bytes", 0)),
        patch_prompt_lines=to_int(prompts.get("patch_prompt_lines", 0)),
        patch_prompt_estimated_tokens=to_int(prompts.get("patch_prompt_estimated_tokens", 0)),
        session_bytes=to_int(outputs.get("session_bytes", 0)),
        session_lines=to_int(outputs.get("session_lines", 0)),
        session_estimated_tokens=to_int(outputs.get("session_estimated_tokens", 0)),
        patch_bytes=to_int(outputs.get("patch_bytes", 0)),
        patch_lines=to_int(outputs.get("patch_lines", 0)),
        patch_estimated_tokens=to_int(outputs.get("patch_estimated_tokens", 0)),
        usage_available=usage_available,
        session_finish_reason=session_finish_reason,
        session_prompt_tokens_actual=session_prompt_tokens_actual,
        session_completion_tokens_actual=session_completion_tokens_actual,
        session_total_tokens_actual=session_total_tokens_actual,
        session_prompt_ms=to_float(session_timings.get("prompt_ms", 0)) if isinstance(session_timings, dict) else 0.0,
        session_predicted_ms=(
            to_float(session_timings.get("predicted_ms", 0)) if isinstance(session_timings, dict) else 0.0
        ),
        session_prompt_per_second=(
            to_float(session_timings.get("prompt_per_second", 0)) if isinstance(session_timings, dict) else 0.0
        ),
        session_predicted_per_second=(
            to_float(session_timings.get("predicted_per_second", 0)) if isinstance(session_timings, dict) else 0.0
        ),
        patch_finish_reason=patch_finish_reason,
        patch_prompt_tokens_actual=patch_prompt_tokens_actual,
        patch_completion_tokens_actual=patch_completion_tokens_actual,
        patch_total_tokens_actual=patch_total_tokens_actual,
        patch_prompt_ms=to_float(patch_timings.get("prompt_ms", 0)) if isinstance(patch_timings, dict) else 0.0,
        patch_predicted_ms=(
            to_float(patch_timings.get("predicted_ms", 0)) if isinstance(patch_timings, dict) else 0.0
        ),
        patch_prompt_per_second=(
            to_float(patch_timings.get("prompt_per_second", 0)) if isinstance(patch_timings, dict) else 0.0
        ),
        patch_predicted_per_second=(
            to_float(patch_timings.get("predicted_per_second", 0)) if isinstance(patch_timings, dict) else 0.0
        ),
        total_prompt_tokens_actual=session_prompt_tokens_actual + patch_prompt_tokens_actual,
        total_completion_tokens_actual=session_completion_tokens_actual + patch_completion_tokens_actual,
        total_tokens_actual=session_total_tokens_actual + patch_total_tokens_actual,
        chunk_attempted=to_int(chunk_summary.get("attempted", 0)),
        chunk_succeeded=to_int(chunk_summary.get("succeeded", 0)),
        chunk_failed=to_int(chunk_summary.get("failed", 0)),
        chunk_retry_count=to_int(chunk_summary.get("retry_count", 0)),
        chunk_split_seconds=to_int(chunk_split.get("elapsed_seconds", 0)),
        chunk_summary_seconds=to_int(chunk_summary.get("elapsed_seconds", 0)),
        session_stage_seconds=to_int(session_stage.get("elapsed_seconds", 0)),
        patch_stage_seconds=to_int(patch_stage.get("elapsed_seconds", 0)),
        completed_at=completed_at,
        sort_epoch=sort_epoch,
        chunk_rows=chunk_rows,
        chunk_row_failures=chunk_row_failures,
    )


def discover_runs(runs_dir: Path, limit: int, completed_only: bool) -> list[RunSummary]:
    if not runs_dir.is_dir():
        return []
    metrics_paths = [p / "METRICS.json" for p in runs_dir.iterdir() if p.is_dir()]
    existing = [p for p in metrics_paths if p.is_file()]
    summaries = [parse_run(p) for p in existing]
    if completed_only:
        summaries = [summary for summary in summaries if summary.status == "completed"]
    summaries.sort(key=lambda s: (s.sort_epoch, s.run_dir.name), reverse=True)
    if limit <= 0:
        return summaries
    return summaries[:limit]


def recommended_profile(
    runs: list[RunSummary],
    completed_only: bool,
    min_recent_runs_for_chunked: int,
) -> tuple[str, str]:
    if not runs:
        return ("smoke", "No runs found yet.")
    failures = sum(1 for run in runs if run.status != "completed")
    retry_heavy = sum(1 for run in runs if run.chunk_retry_count > 0)
    avg_elapsed = sum(run.total_elapsed_seconds for run in runs) / len(runs)
    recent = runs[0]

    if not completed_only and failures > 0:
        return ("smoke", "Recent failures detected.")
    if retry_heavy > 0:
        return ("smoke", "Chunk retries detected in recent runs.")
    if avg_elapsed > 600:
        return ("smoke", "Recent runs are very slow.")
    if recent.chunked_mode:
        if len(runs) < min_recent_runs_for_chunked:
            return (
                "normal",
                f"Need at least {min_recent_runs_for_chunked} recent runs before recommending chunked as default.",
            )
        if recent.status == "completed" and recent.chunk_failed == 0 and recent.chunk_row_failures == 0:
            return ("chunked", "Recent chunked runs completed without chunk failures.")
        return ("normal", "Recent chunked runs need stabilization before using chunked as default.")
    return ("normal", "Recent runs look stable for normal compact mode.")


def recommendation(runs: list[RunSummary], completed_only: bool, min_recent_runs_for_chunked: int) -> str:
    profile, reason = recommended_profile(runs, completed_only, min_recent_runs_for_chunked)
    settings = PROFILE_SETTINGS[profile]
    setting_text = ", ".join(f"{key}={value}" for key, value in settings.items())
    return f"Recommend {profile} profile: {reason} Suggested settings: {setting_text}."


def build_confidence_signals(runs: list[RunSummary]) -> dict[str, int]:
    return {
        "recent_completed_count": sum(1 for run in runs if run.status == "completed"),
        "recent_failed_count": sum(1 for run in runs if run.status != "completed"),
        "recent_chunk_retry_count": sum(run.chunk_retry_count for run in runs),
    }


def recommendation_confidence(
    runs: list[RunSummary],
    completed_only: bool,
    min_recent_runs_for_chunked: int,
) -> tuple[str, str]:
    if not runs:
        return ("low", "No recent runs available.")
    signals = build_confidence_signals(runs)
    if not completed_only and signals["recent_failed_count"] > 0:
        return ("low", "Recent failures detected in analyzed runs.")
    if signals["recent_chunk_retry_count"] > 0:
        return ("low", "Chunk retries exceed threshold (0).")
    if len(runs) < min_recent_runs_for_chunked:
        return ("medium", f"Only {len(runs)} recent runs available; need {min_recent_runs_for_chunked} for high confidence.")
    recent = runs[0]
    if recent.status == "completed" and recent.chunk_failed == 0 and recent.chunk_row_failures == 0:
        return ("high", "Recent window is stable with completed runs and no chunk failures.")
    return ("medium", "Recent run signals are partially stable.")


def readiness_decision(
    runs: list[RunSummary],
    completed_only: bool,
    min_recent_runs_for_chunked: int,
) -> tuple[str, str, list[str]]:
    if not runs:
        return ("not_ready", "No recent runs available.", ["no_recent_runs"])
    signals = build_confidence_signals(runs)
    blockers: list[str] = []
    if not completed_only and signals["recent_failed_count"] > 0:
        blockers.append("recent_failures")
    if signals["recent_chunk_retry_count"] > 0:
        blockers.append("chunk_retries")
    confidence, confidence_reason = recommendation_confidence(runs, completed_only, min_recent_runs_for_chunked)
    if blockers:
        return ("not_ready", "Blocking run instability signals detected.", blockers)
    if confidence == "high":
        return ("ready", "Recent runs are stable and confidence is high.", blockers)
    blockers.append("insufficient_recent_window")
    return ("needs_review", confidence_reason, blockers)


def lesson_tag_for_run(run: RunSummary) -> str:
    if run.status != "completed":
        return "run_failed"
    if run.chunk_retry_count > 0:
        return "retry_spike"
    if run.total_elapsed_seconds > 600:
        return "slow_backend"
    if run.chunked_mode and run.chunk_failed == 0 and run.chunk_row_failures == 0:
        return "chunk_stable"
    return "run_stable"


def build_ledger_entry(
    run: RunSummary,
    recommended_profile_name: str,
    confidence_level: str,
    readiness: str,
) -> dict[str, Any]:
    observed_profile = run.run_profile
    return {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "run_dir": str(run.run_dir),
        "source_id": run.source_id,
        "short_title": run.short_title,
        "run_profile": run.run_profile,
        "run_purpose": run.run_purpose,
        "recommended_profile": recommended_profile_name,
        "recommendation_confidence": confidence_level,
        "readiness": readiness,
        "actual_status": run.status,
        "observed_profile": observed_profile,
        "delta": "match" if observed_profile == recommended_profile_name else "profile_mismatch",
        "lesson_tag": lesson_tag_for_run(run),
    }


def append_ledger_entries(
    runs_dir: Path,
    runs: list[RunSummary],
    recommended_profile_name: str,
    confidence_level: str,
    readiness: str,
) -> Path:
    ledger_path = runs_dir / "interviewer_ledger.jsonl"
    seen: set[str] = set()
    if ledger_path.is_file():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            run_dir = str(entry.get("run_dir", ""))
            if run_dir:
                seen.add(run_dir)
    additions = [run for run in runs if str(run.run_dir) not in seen]
    if not additions:
        return ledger_path
    with ledger_path.open("a", encoding="utf-8") as handle:
        for run in additions:
            handle.write(json.dumps(build_ledger_entry(run, recommended_profile_name, confidence_level, readiness), sort_keys=True))
            handle.write("\n")
    return ledger_path


def read_ledger_entries(runs_dir: Path, calibration_window: int) -> list[dict[str, Any]]:
    ledger_path = runs_dir / "interviewer_ledger.jsonl"
    if not ledger_path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries[-max(1, calibration_window) :]


def build_calibration_metrics(runs_dir: Path | None, calibration_window: int) -> dict[str, Any]:
    entries = read_ledger_entries(runs_dir, calibration_window) if runs_dir else []
    high_entries = [e for e in entries if e.get("recommendation_confidence") == "high"]
    high_successes = sum(1 for e in high_entries if e.get("actual_status") == "completed")
    low_entries = [e for e in entries if e.get("recommendation_confidence") == "low"]
    false_high_count = sum(1 for e in high_entries if e.get("actual_status") != "completed")
    false_low_count = sum(1 for e in low_entries if e.get("actual_status") == "completed")
    return {
        "window_size": max(1, calibration_window),
        "entries_analyzed": len(entries),
        "confidence_high_success_rate": round((high_successes / len(high_entries)), 4) if high_entries else None,
        "false_high_count": false_high_count,
        "false_low_count": false_low_count,
        "high_confidence_count": len(high_entries),
        "low_confidence_count": len(low_entries),
    }


def load_role_critiques(role_critiques_file: Path | None) -> list[dict[str, Any]]:
    if role_critiques_file is None or not role_critiques_file.is_file():
        return []
    text = role_critiques_file.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            if "critiques" in parsed:
                critiques = parsed.get("critiques", [])
                if isinstance(critiques, list):
                    return [item for item in critiques if isinstance(item, dict)]
                return []
            return [parsed]
    except json.JSONDecodeError:
        pass
    critiques: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed_line = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed_line, dict):
            critiques.append(parsed_line)
    return critiques


def summarize_role_critiques(critiques: list[dict[str, Any]]) -> dict[str, Any]:
    blocking_levels = {"high", "critical", "blocker"}
    unresolved = [item for item in critiques if str(item.get("status", "open")).lower() not in {"resolved", "closed"}]
    blocking = [item for item in unresolved if str(item.get("severity", "")).lower() in blocking_levels]
    focus_areas = sorted({str(item.get("focus_area", "")).strip() for item in unresolved if str(item.get("focus_area", "")).strip()})
    roles = sorted({str(item.get("role", "")).strip() for item in unresolved if str(item.get("role", "")).strip()})
    return {
        "total_count": len(critiques),
        "unresolved_count": len(unresolved),
        "blocking_count": len(blocking),
        "roles": roles,
        "focus_areas": focus_areas,
    }


def interviewer_verdict(
    readiness: str,
    calibration_metrics: dict[str, Any],
    role_critique_summary: dict[str, Any],
    role_critiques_strict: bool,
) -> tuple[str, str]:
    if int(role_critique_summary.get("blocking_count", 0)) > 0:
        return ("hold", "Role critiques include unresolved blocking findings.")
    if role_critiques_strict and int(role_critique_summary.get("unresolved_count", 0)) > 0:
        return ("hold", "Role critiques strict mode requires all findings to be resolved.")
    if readiness == "not_ready":
        return ("hold", "Readiness gate is not_ready.")
    if readiness == "needs_review":
        return ("proceed_with_review", "Readiness gate requires review.")
    if int(role_critique_summary.get("unresolved_count", 0)) > 0:
        return ("proceed_with_review", "Role critiques include unresolved non-blocking findings.")
    high_success_rate = calibration_metrics.get("confidence_high_success_rate")
    false_high_count = int(calibration_metrics.get("false_high_count", 0))
    if isinstance(high_success_rate, (int, float)) and high_success_rate < 0.5:
        return ("hold", "Calibration high-confidence success rate is below 0.5.")
    if false_high_count > 0:
        return ("proceed_with_review", "Calibration recorded false-high outcomes.")
    return ("proceed", "Readiness is ready and calibration has no false-high drift.")


def format_mode(run: RunSummary) -> str:
    if run.chunked_mode and run.compact_mode:
        return "compact+chunked"
    if run.chunked_mode:
        return "chunked"
    if run.compact_mode:
        return "compact"
    return "standard"


def tracked_completion_token_cap(run: RunSummary) -> int:
    return max(run.session_max_tokens, 0) + max(run.patch_max_tokens, 0)


def total_output_estimated_tokens(run: RunSummary) -> int:
    return run.session_estimated_tokens + run.patch_estimated_tokens


def completion_cap_utilization(run: RunSummary) -> float | None:
    if not run.usage_available:
        return None
    return safe_ratio(run.total_completion_tokens_actual, tracked_completion_token_cap(run))


def completion_to_output_estimate_ratio(run: RunSummary) -> float | None:
    if not run.usage_available:
        return None
    return safe_ratio(run.total_completion_tokens_actual, total_output_estimated_tokens(run))


def format_finish_reasons(run: RunSummary) -> str:
    session_reason = run.session_finish_reason or "unknown"
    patch_reason = run.patch_finish_reason or "unknown"
    return f"session={session_reason}, review_patch={patch_reason}"


def budget_tuning_advice(run: RunSummary) -> dict[str, str]:
    if run.status != "completed":
        return {
            "action": "fix_run_stability",
            "reason": "Run did not complete; tune reliability before token budgets.",
        }
    if run.session_finish_reason == "length":
        return {
            "action": "raise_session_budget",
            "reason": "Session generation reached the completion cap and may be clipped.",
        }
    if run.patch_finish_reason == "length":
        return {
            "action": "raise_patch_budget",
            "reason": "Review-patch generation reached the completion cap and may be clipped.",
        }
    if not run.usage_available:
        return {
            "action": "review_finish_reasons",
            "reason": "Finish reasons are available, but model token usage is unavailable.",
        }

    cap_used = completion_cap_utilization(run)
    if run.session_finish_reason == "stop" and run.patch_finish_reason == "stop":
        if cap_used is not None and cap_used < 0.5:
            return {
                "action": "consider_lowering_budget",
                "reason": "Both calls stopped naturally with substantial completion-token headroom.",
            }
        if cap_used is not None and cap_used <= 0.9:
            return {
                "action": "profile_looks_good",
                "reason": "Both calls stopped naturally and used a healthy share of the completion budget.",
            }
        return {
            "action": "monitor_budget_headroom",
            "reason": "Both calls stopped naturally, but completion budget headroom is narrow.",
        }

    return {
        "action": "review_finish_reasons",
        "reason": f"Finish reasons need review: {format_finish_reasons(run)}.",
    }


def serialize_run(run: RunSummary) -> dict[str, Any]:
    return {
        "run_dir": str(run.run_dir),
        "source_id": run.source_id,
        "short_title": run.short_title,
        "status": run.status,
        "failure_stage": run.failure_stage,
        "mode": format_mode(run),
        "run_profile": run.run_profile,
        "run_purpose": run.run_purpose,
        "settings": {
            "chunk_line_size": run.chunk_line_size,
            "chunk_max_tokens": run.chunk_max_tokens,
            "session_max_tokens": run.session_max_tokens,
            "patch_max_tokens": run.patch_max_tokens,
            "call_timeout_seconds": run.call_timeout_seconds,
        },
        "total_elapsed_seconds": run.total_elapsed_seconds,
        "source": {
            "bytes": run.source_bytes,
            "lines": run.source_lines,
            "estimated_tokens": run.source_estimated_tokens,
        },
        "session_prompt": {
            "bytes": run.session_prompt_bytes,
            "lines": run.session_prompt_lines,
            "estimated_tokens": run.session_prompt_estimated_tokens,
        },
        "patch_prompt": {
            "bytes": run.patch_prompt_bytes,
            "lines": run.patch_prompt_lines,
            "estimated_tokens": run.patch_prompt_estimated_tokens,
        },
        "session_output": {
            "bytes": run.session_bytes,
            "lines": run.session_lines,
            "estimated_tokens": run.session_estimated_tokens,
        },
        "patch_output": {
            "bytes": run.patch_bytes,
            "lines": run.patch_lines,
            "estimated_tokens": run.patch_estimated_tokens,
        },
        "model_usage": {
            "available": run.usage_available,
            "session": {
                "finish_reason": run.session_finish_reason,
                "prompt_tokens": run.session_prompt_tokens_actual,
                "completion_tokens": run.session_completion_tokens_actual,
                "total_tokens": run.session_total_tokens_actual,
                "timings": {
                    "prompt_ms": run.session_prompt_ms,
                    "predicted_ms": run.session_predicted_ms,
                    "prompt_per_second": run.session_prompt_per_second,
                    "predicted_per_second": run.session_predicted_per_second,
                },
            },
            "review_patch": {
                "finish_reason": run.patch_finish_reason,
                "prompt_tokens": run.patch_prompt_tokens_actual,
                "completion_tokens": run.patch_completion_tokens_actual,
                "total_tokens": run.patch_total_tokens_actual,
                "timings": {
                    "prompt_ms": run.patch_prompt_ms,
                    "predicted_ms": run.patch_predicted_ms,
                    "prompt_per_second": run.patch_prompt_per_second,
                    "predicted_per_second": run.patch_predicted_per_second,
                },
            },
            "total": {
                "prompt_tokens": run.total_prompt_tokens_actual,
                "completion_tokens": run.total_completion_tokens_actual,
                "total_tokens": run.total_tokens_actual,
            },
            "tracked_completion_cap_tokens": tracked_completion_token_cap(run),
            "completion_cap_utilization": completion_cap_utilization(run),
            "estimated_output_tokens": total_output_estimated_tokens(run),
            "completion_to_output_estimate_ratio": completion_to_output_estimate_ratio(run),
            "finish_reasons": {
                "session": run.session_finish_reason,
                "review_patch": run.patch_finish_reason,
            },
            "budget_tuning": budget_tuning_advice(run),
        },
        "stages": {
            "chunk_split_elapsed_seconds": run.chunk_split_seconds,
            "chunk_summary_elapsed_seconds": run.chunk_summary_seconds,
            "session_elapsed_seconds": run.session_stage_seconds,
            "review_patch_elapsed_seconds": run.patch_stage_seconds,
        },
        "chunk": {
            "attempted": run.chunk_attempted,
            "succeeded": run.chunk_succeeded,
            "failed": run.chunk_failed,
            "retry_count": run.chunk_retry_count,
            "tsv_rows": run.chunk_rows,
            "tsv_failures": run.chunk_row_failures,
        },
        "run_completed_at": run.completed_at,
    }


def build_report_payload(
    runs: list[RunSummary],
    completed_only: bool,
    min_recent_runs_for_chunked: int,
    runs_dir: Path | None = None,
    calibration_window: int = DEFAULT_CALIBRATION_WINDOW,
    role_critique_summary: dict[str, Any] | None = None,
    role_critiques_strict: bool = False,
    filters: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    profile, reason = recommended_profile(runs, completed_only, min_recent_runs_for_chunked)
    confidence, confidence_reason = recommendation_confidence(runs, completed_only, min_recent_runs_for_chunked)
    readiness, readiness_reason, blocking_signals = readiness_decision(runs, completed_only, min_recent_runs_for_chunked)
    calibration = build_calibration_metrics(runs_dir, calibration_window)
    role_summary = role_critique_summary or summarize_role_critiques([])
    verdict, verdict_reason = interviewer_verdict(readiness, calibration, role_summary, role_critiques_strict)
    return {
        "run_count": len(runs),
        "completed_only": completed_only,
        "filters": filters or {"profiles": [], "purposes": [], "excluded_purposes": []},
        "recommendation": recommendation(runs, completed_only, min_recent_runs_for_chunked),
        "recommended_profile": profile,
        "recommended_settings": PROFILE_SETTINGS[profile],
        "recommendation_reason": reason,
        "recommendation_confidence": confidence,
        "confidence_reason": confidence_reason,
        "readiness": readiness,
        "readiness_reason": readiness_reason,
        "blocking_signals": blocking_signals,
        "interviewer_verdict": verdict,
        "interviewer_verdict_reason": verdict_reason,
        "thresholds": {
            "min_recent_runs_for_chunked": min_recent_runs_for_chunked,
        },
        "confidence_signals": build_confidence_signals(runs),
        "role_critique_summary": role_summary,
        "role_critiques_strict": role_critiques_strict,
        "calibration_metrics": calibration,
        "runs": [serialize_run(run) for run in runs],
    }


def build_advisor_payload(
    runs: list[RunSummary],
    completed_only: bool,
    min_recent_runs_for_chunked: int,
    runs_dir: Path | None = None,
    calibration_window: int = DEFAULT_CALIBRATION_WINDOW,
    role_critique_summary: dict[str, Any] | None = None,
    role_critiques_strict: bool = False,
    filters: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    profile, reason = recommended_profile(runs, completed_only, min_recent_runs_for_chunked)
    confidence, confidence_reason = recommendation_confidence(runs, completed_only, min_recent_runs_for_chunked)
    readiness, readiness_reason, blocking_signals = readiness_decision(runs, completed_only, min_recent_runs_for_chunked)
    calibration = build_calibration_metrics(runs_dir, calibration_window)
    role_summary = role_critique_summary or summarize_role_critiques([])
    verdict, verdict_reason = interviewer_verdict(readiness, calibration, role_summary, role_critiques_strict)
    payload: dict[str, Any] = {
        "run_count": len(runs),
        "completed_only": completed_only,
        "filters": filters or {"profiles": [], "purposes": [], "excluded_purposes": []},
        "recommended_profile": profile,
        "recommended_settings": PROFILE_SETTINGS[profile],
        "recommendation_reason": reason,
        "recommendation": recommendation(runs, completed_only, min_recent_runs_for_chunked),
        "recommendation_confidence": confidence,
        "confidence_reason": confidence_reason,
        "readiness": readiness,
        "readiness_reason": readiness_reason,
        "blocking_signals": blocking_signals,
        "interviewer_verdict": verdict,
        "interviewer_verdict_reason": verdict_reason,
        "thresholds": {
            "min_recent_runs_for_chunked": min_recent_runs_for_chunked,
        },
        "confidence_signals": build_confidence_signals(runs),
        "role_critique_summary": role_summary,
        "role_critiques_strict": role_critiques_strict,
        "calibration_metrics": calibration,
    }
    if runs:
        recent = runs[0]
        payload["recent_run"] = {
            "run_dir": str(recent.run_dir),
            "source_id": recent.source_id,
            "short_title": recent.short_title,
            "status": recent.status,
            "mode": format_mode(recent),
            "run_profile": recent.run_profile,
            "run_purpose": recent.run_purpose,
            "total_elapsed_seconds": recent.total_elapsed_seconds,
            "chunk_retry_count": recent.chunk_retry_count,
            "chunk_failed": recent.chunk_failed,
            "chunk_row_failures": recent.chunk_row_failures,
            "finish_reasons": {
                "session": recent.session_finish_reason,
                "review_patch": recent.patch_finish_reason,
            },
            "model_usage_available": recent.usage_available,
            "prompt_tokens": recent.total_prompt_tokens_actual,
            "completion_tokens": recent.total_completion_tokens_actual,
            "total_tokens": recent.total_tokens_actual,
            "tracked_completion_cap_tokens": tracked_completion_token_cap(recent),
            "completion_cap_utilization": completion_cap_utilization(recent),
            "completion_to_output_estimate_ratio": completion_to_output_estimate_ratio(recent),
            "budget_tuning": budget_tuning_advice(recent),
        }
    return payload


def print_report(runs: list[RunSummary], completed_only: bool, min_recent_runs_for_chunked: int) -> None:
    print("Distiller metrics report")
    print()
    for run in runs:
        print(f"Run: {run.run_dir.name}")
        print(f"  Source: {run.source_id} ({run.short_title})")
        print(f"  Mode: {format_mode(run)}")
        print(f"  Profile/purpose: {run.run_profile}/{run.run_purpose}")
        print(f"  Status: {run.status}")
        if run.failure_stage:
            print(f"  Failure stage: {run.failure_stage}")
        print(
            "  Settings (chunk lines/chunk max/session max/patch max/timeout): "
            f"{run.chunk_line_size}/{run.chunk_max_tokens}/{run.session_max_tokens}/"
            f"{run.patch_max_tokens}/{run.call_timeout_seconds}"
        )
        print(f"  Total elapsed: {run.total_elapsed_seconds}s")
        print(
            "  Source size (bytes/lines/tokens est): "
            f"{run.source_bytes}/{run.source_lines}/{run.source_estimated_tokens}"
        )
        print(
            "  Session prompt (bytes/lines/tokens est): "
            f"{run.session_prompt_bytes}/{run.session_prompt_lines}/{run.session_prompt_estimated_tokens}"
        )
        print(
            "  Patch prompt (bytes/lines/tokens est): "
            f"{run.patch_prompt_bytes}/{run.patch_prompt_lines}/{run.patch_prompt_estimated_tokens}"
        )
        print(
            "  Session output (bytes/lines/tokens est): "
            f"{run.session_bytes}/{run.session_lines}/{run.session_estimated_tokens}"
        )
        print(
            "  Patch output (bytes/lines/tokens est): "
            f"{run.patch_bytes}/{run.patch_lines}/{run.patch_estimated_tokens}"
        )
        if run.usage_available:
            print(
                "  Model usage actual (prompt/completion/total): "
                f"{run.total_prompt_tokens_actual}/{run.total_completion_tokens_actual}/{run.total_tokens_actual}"
            )
            print(f"  Finish reasons: {format_finish_reasons(run)}")
            print(
                "  Completion efficiency (cap used/completion-output-est ratio): "
                f"{format_optional_ratio(completion_cap_utilization(run))}/"
                f"{format_optional_ratio(completion_to_output_estimate_ratio(run))}"
            )
            advice = budget_tuning_advice(run)
            print(f"  Budget tuning: {advice['action']} ({advice['reason']})")
        else:
            print("  Model usage actual: unavailable")
        print(
            "  Stage seconds (chunk_split/chunk_summary/session/review_patch): "
            f"{run.chunk_split_seconds}/{run.chunk_summary_seconds}/"
            f"{run.session_stage_seconds}/{run.patch_stage_seconds}"
        )
        print(
            "  Chunk counts (attempted/succeeded/failed/retries): "
            f"{run.chunk_attempted}/{run.chunk_succeeded}/{run.chunk_failed}/{run.chunk_retry_count}"
        )
        if run.chunk_rows > 0:
            print(f"  Chunk TSV rows/failures: {run.chunk_rows}/{run.chunk_row_failures}")
        print()
    print(recommendation(runs, completed_only, min_recent_runs_for_chunked))


def print_advisor_report(
    runs: list[RunSummary],
    completed_only: bool,
    min_recent_runs_for_chunked: int,
    runs_dir: Path,
    calibration_window: int,
    role_critique_summary: dict[str, Any],
    role_critiques_strict: bool,
    filters: dict[str, list[str]] | None = None,
) -> None:
    payload = build_advisor_payload(
        runs,
        completed_only,
        min_recent_runs_for_chunked,
        runs_dir=runs_dir,
        calibration_window=calibration_window,
        role_critique_summary=role_critique_summary,
        role_critiques_strict=role_critiques_strict,
        filters=filters,
    )
    print("Distiller advisor")
    print()
    print(f"Runs analyzed: {payload['run_count']}")
    applied_filters = payload.get("filters", {})
    if isinstance(applied_filters, dict) and any(applied_filters.values()):
        print(
            "Filters: "
            f"profiles={applied_filters.get('profiles', [])}, "
            f"purposes={applied_filters.get('purposes', [])}, "
            f"excluded_purposes={applied_filters.get('excluded_purposes', [])}"
        )
    print(f"Recommended profile: {payload['recommended_profile']}")
    print(f"Reason: {payload['recommendation_reason']}")
    print(f"Recommendation confidence: {payload['recommendation_confidence']} ({payload['confidence_reason']})")
    print(f"Readiness: {payload['readiness']} ({payload['readiness_reason']})")
    if payload["blocking_signals"]:
        print("Blocking signals: " + ", ".join(payload["blocking_signals"]))
    print(f"Interviewer verdict: {payload['interviewer_verdict']} ({payload['interviewer_verdict_reason']})")
    print(f"Threshold min recent runs for chunked: {payload['thresholds']['min_recent_runs_for_chunked']}")
    confidence = payload["confidence_signals"]
    print(
        "Confidence signals: "
        f"completed={confidence['recent_completed_count']}, failed={confidence['recent_failed_count']}, "
        f"chunk_retries={confidence['recent_chunk_retry_count']}"
    )
    settings = ", ".join(f"{key}={value}" for key, value in payload["recommended_settings"].items())
    print(f"Recommended settings: {settings}")
    calibration = payload["calibration_metrics"]
    print(
        "Calibration: "
        f"window={calibration['window_size']}, entries={calibration['entries_analyzed']}, "
        f"high_success_rate={calibration['confidence_high_success_rate']}, "
        f"false_high={calibration['false_high_count']}, false_low={calibration['false_low_count']}"
    )
    role_summary = payload["role_critique_summary"]
    print(
        "Role critiques: "
        f"total={role_summary['total_count']}, unresolved={role_summary['unresolved_count']}, "
        f"blocking={role_summary['blocking_count']}, strict={payload['role_critiques_strict']}"
    )
    recent = payload.get("recent_run")
    if isinstance(recent, dict):
        summary = (
            "Recent run summary: "
            f"profile={recent['run_profile']}, purpose={recent['run_purpose']}, "
            f"mode={recent['mode']}, status={recent['status']}, elapsed={recent['total_elapsed_seconds']}s, "
            f"chunk_retries={recent['chunk_retry_count']}, chunk_failed={recent['chunk_failed']}, "
            f"chunk_tsv_failures={recent['chunk_row_failures']}"
        )
        if recent.get("model_usage_available"):
            finish_reasons = recent.get("finish_reasons", {})
            budget_tuning = recent.get("budget_tuning", {})
            summary += (
                f", tokens={recent['prompt_tokens']}/{recent['completion_tokens']}/{recent['total_tokens']}, "
                f"finish=session:{finish_reasons.get('session') or 'unknown'}/"
                f"patch:{finish_reasons.get('review_patch') or 'unknown'}, "
                f"cap_used={format_optional_ratio(recent['completion_cap_utilization'])}, "
                f"completion_output_ratio={format_optional_ratio(recent['completion_to_output_estimate_ratio'])}, "
                f"budget_tuning={budget_tuning.get('action', 'unknown')}"
            )
        else:
            summary += ", tokens=unavailable"
        print(summary)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report distiller metrics from outputs/run_records.")
    parser.add_argument(
        "--runs-dir",
        default="outputs/run_records",
        help="Directory containing distiller run folders.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=6,
        help="Maximum number of recent runs to include.",
    )
    parser.add_argument(
        "--completed-only",
        action="store_true",
        help="Only include completed runs in report and recommendation.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print report as JSON.",
    )
    parser.add_argument(
        "--advisor-only",
        action="store_true",
        help="Print concise operator advisory summary.",
    )
    parser.add_argument(
        "--profile",
        action="append",
        default=[],
        help="Only include runs with these run_profile labels; repeat or use comma-separated values.",
    )
    parser.add_argument(
        "--purpose",
        action="append",
        default=[],
        help="Only include runs with these run_purpose labels; repeat or use comma-separated values.",
    )
    parser.add_argument(
        "--exclude-purpose",
        action="append",
        default=[],
        help="Exclude runs with these run_purpose labels; repeat or use comma-separated values.",
    )
    parser.add_argument(
        "--min-recent-runs-for-chunked",
        type=int,
        default=DEFAULT_MIN_RECENT_RUNS_FOR_CHUNKED,
        help="Minimum recent runs required before recommending chunked as default.",
    )
    parser.add_argument(
        "--write-ledger",
        action="store_true",
        help="Append unseen run outcomes to interviewer_ledger.jsonl.",
    )
    parser.add_argument(
        "--calibration-window",
        type=int,
        default=DEFAULT_CALIBRATION_WINDOW,
        help="Number of recent ledger entries to use for calibration metrics.",
    )
    parser.add_argument(
        "--role-critiques-file",
        default="",
        help="Optional JSON/JSONL file containing role critique findings.",
    )
    parser.add_argument(
        "--role-critiques-strict",
        action="store_true",
        help="Treat any unresolved role critique finding as hold.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runs_dir = Path(args.runs_dir)
    profile_filters = parse_filter_values(args.profile)
    purpose_filters = parse_filter_values(args.purpose)
    excluded_purpose_filters = parse_filter_values(args.exclude_purpose)
    has_filters = bool(profile_filters or purpose_filters or excluded_purpose_filters)
    runs = discover_runs(runs_dir, 0 if has_filters else max(1, args.limit), args.completed_only)
    if has_filters:
        runs = filter_runs(runs, profile_filters, purpose_filters, excluded_purpose_filters)[: max(1, args.limit)]
    filter_payload = {
        "profiles": sorted(profile_filters),
        "purposes": sorted(purpose_filters),
        "excluded_purposes": sorted(excluded_purpose_filters),
    }
    min_recent_runs_for_chunked = max(1, args.min_recent_runs_for_chunked)
    calibration_window = max(1, args.calibration_window)
    role_critiques_file = Path(args.role_critiques_file) if args.role_critiques_file else None
    role_critique_summary = summarize_role_critiques(load_role_critiques(role_critiques_file))
    profile, _ = recommended_profile(runs, args.completed_only, min_recent_runs_for_chunked)
    confidence, _ = recommendation_confidence(runs, args.completed_only, min_recent_runs_for_chunked)
    readiness, _, _ = readiness_decision(runs, args.completed_only, min_recent_runs_for_chunked)
    if args.write_ledger:
        append_ledger_entries(runs_dir, runs, profile, confidence, readiness)
    if args.advisor_only and args.json:
        print(
            json.dumps(
                build_advisor_payload(
                    runs,
                    args.completed_only,
                    min_recent_runs_for_chunked,
                    runs_dir=runs_dir,
                    calibration_window=calibration_window,
                    role_critique_summary=role_critique_summary,
                    role_critiques_strict=args.role_critiques_strict,
                    filters=filter_payload,
                ),
                indent=2,
            )
        )
    elif args.advisor_only:
        print_advisor_report(
            runs,
            args.completed_only,
            min_recent_runs_for_chunked,
            runs_dir,
            calibration_window,
            role_critique_summary,
            args.role_critiques_strict,
            filters=filter_payload,
        )
    elif args.json:
        print(
            json.dumps(
                build_report_payload(
                    runs,
                    args.completed_only,
                    min_recent_runs_for_chunked,
                    runs_dir=runs_dir,
                    calibration_window=calibration_window,
                    role_critique_summary=role_critique_summary,
                    role_critiques_strict=args.role_critiques_strict,
                    filters=filter_payload,
                ),
                indent=2,
            )
        )
    else:
        print_report(runs, args.completed_only, min_recent_runs_for_chunked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
