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
        "ZTH_DISTILLER_SESSION_MAX_TOKENS": 1200,
        "ZTH_DISTILLER_PATCH_MAX_TOKENS": 900,
        "ZTH_DISTILLER_TIMEOUT": 600,
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


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip() == "1"


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
    completed_at = str(data.get("run_completed_at", ""))
    sort_epoch = parse_sort_epoch(completed_at)
    if sort_epoch == 0.0:
        sort_epoch = metrics_path.stat().st_mtime
    chunk_metrics_file = str(chunk_summary.get("chunk_metrics_file", ""))
    chunk_rows, chunk_row_failures = parse_chunk_metrics(chunk_metrics_file, metrics_path.parent)

    return RunSummary(
        run_dir=metrics_path.parent,
        source_id=str(data.get("source_id", "")),
        short_title=str(data.get("short_title", "")),
        status=str(data.get("status", "unknown")),
        failure_stage=str(data.get("failure_stage", "")),
        compact_mode=to_bool(data.get("compact_mode", "0")),
        chunked_mode=to_bool(data.get("chunked_mode", "0")),
        chunk_line_size=to_int(data.get("chunk_line_size", 0)),
        chunk_max_tokens=to_int(data.get("chunk_max_tokens", 0)),
        session_max_tokens=to_int(data.get("session_max_tokens", 0)),
        patch_max_tokens=to_int(data.get("patch_max_tokens", 0)),
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
    observed_profile = "chunked" if run.chunked_mode else "normal"
    return {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "run_dir": str(run.run_dir),
        "source_id": run.source_id,
        "short_title": run.short_title,
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


def interviewer_verdict(readiness: str, calibration_metrics: dict[str, Any]) -> tuple[str, str]:
    if readiness == "not_ready":
        return ("hold", "Readiness gate is not_ready.")
    if readiness == "needs_review":
        return ("proceed_with_review", "Readiness gate requires review.")
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


def serialize_run(run: RunSummary) -> dict[str, Any]:
    return {
        "run_dir": str(run.run_dir),
        "source_id": run.source_id,
        "short_title": run.short_title,
        "status": run.status,
        "failure_stage": run.failure_stage,
        "mode": format_mode(run),
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
) -> dict[str, Any]:
    profile, reason = recommended_profile(runs, completed_only, min_recent_runs_for_chunked)
    confidence, confidence_reason = recommendation_confidence(runs, completed_only, min_recent_runs_for_chunked)
    readiness, readiness_reason, blocking_signals = readiness_decision(runs, completed_only, min_recent_runs_for_chunked)
    calibration = build_calibration_metrics(runs_dir, calibration_window)
    verdict, verdict_reason = interviewer_verdict(readiness, calibration)
    return {
        "run_count": len(runs),
        "completed_only": completed_only,
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
        "calibration_metrics": calibration,
        "runs": [serialize_run(run) for run in runs],
    }


def build_advisor_payload(
    runs: list[RunSummary],
    completed_only: bool,
    min_recent_runs_for_chunked: int,
    runs_dir: Path | None = None,
    calibration_window: int = DEFAULT_CALIBRATION_WINDOW,
) -> dict[str, Any]:
    profile, reason = recommended_profile(runs, completed_only, min_recent_runs_for_chunked)
    confidence, confidence_reason = recommendation_confidence(runs, completed_only, min_recent_runs_for_chunked)
    readiness, readiness_reason, blocking_signals = readiness_decision(runs, completed_only, min_recent_runs_for_chunked)
    calibration = build_calibration_metrics(runs_dir, calibration_window)
    verdict, verdict_reason = interviewer_verdict(readiness, calibration)
    payload: dict[str, Any] = {
        "run_count": len(runs),
        "completed_only": completed_only,
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
        "calibration_metrics": calibration,
    }
    if runs:
        recent = runs[0]
        payload["recent_run"] = {
            "run_dir": str(recent.run_dir),
            "status": recent.status,
            "mode": format_mode(recent),
            "total_elapsed_seconds": recent.total_elapsed_seconds,
            "chunk_retry_count": recent.chunk_retry_count,
            "chunk_failed": recent.chunk_failed,
            "chunk_row_failures": recent.chunk_row_failures,
        }
    return payload


def print_report(runs: list[RunSummary], completed_only: bool, min_recent_runs_for_chunked: int) -> None:
    print("Distiller metrics report")
    print()
    for run in runs:
        print(f"Run: {run.run_dir.name}")
        print(f"  Source: {run.source_id} ({run.short_title})")
        print(f"  Mode: {format_mode(run)}")
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


def print_advisor_report(runs: list[RunSummary], completed_only: bool, min_recent_runs_for_chunked: int, runs_dir: Path, calibration_window: int) -> None:
    payload = build_advisor_payload(runs, completed_only, min_recent_runs_for_chunked, runs_dir=runs_dir, calibration_window=calibration_window)
    print("Distiller advisor")
    print()
    print(f"Runs analyzed: {payload['run_count']}")
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
    recent = payload.get("recent_run")
    if isinstance(recent, dict):
        print(
            "Recent run summary: "
            f"mode={recent['mode']}, status={recent['status']}, elapsed={recent['total_elapsed_seconds']}s, "
            f"chunk_retries={recent['chunk_retry_count']}, chunk_failed={recent['chunk_failed']}, "
            f"chunk_tsv_failures={recent['chunk_row_failures']}"
        )


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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runs_dir = Path(args.runs_dir)
    runs = discover_runs(runs_dir, max(1, args.limit), args.completed_only)
    min_recent_runs_for_chunked = max(1, args.min_recent_runs_for_chunked)
    calibration_window = max(1, args.calibration_window)
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
                ),
                indent=2,
            )
        )
    elif args.advisor_only:
        print_advisor_report(runs, args.completed_only, min_recent_runs_for_chunked, runs_dir, calibration_window)
    elif args.json:
        print(
            json.dumps(
                build_report_payload(
                    runs,
                    args.completed_only,
                    min_recent_runs_for_chunked,
                    runs_dir=runs_dir,
                    calibration_window=calibration_window,
                ),
                indent=2,
            )
        )
    else:
        print_report(runs, args.completed_only, min_recent_runs_for_chunked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
