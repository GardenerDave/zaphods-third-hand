#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


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
    metrics_paths = [p / "METRICS.json" for p in runs_dir.iterdir() if p.is_dir()]
    existing = [p for p in metrics_paths if p.is_file()]
    summaries = [parse_run(p) for p in existing]
    if completed_only:
        summaries = [summary for summary in summaries if summary.status == "completed"]
    summaries.sort(key=lambda s: (s.sort_epoch, s.run_dir.name), reverse=True)
    return summaries[:limit]


def recommendation(runs: list[RunSummary], completed_only: bool) -> str:
    if not runs:
        return "No runs found. Start with a smoke profile first."
    failures = sum(1 for run in runs if run.status != "completed")
    avg_elapsed = sum(run.total_elapsed_seconds for run in runs) / len(runs)
    retry_heavy = sum(1 for run in runs if run.chunk_retry_count > 0)
    if not completed_only and failures > 0:
        return "Recommend smoke profile: recent failures detected."
    if retry_heavy > 0:
        return "Recommend smoke profile: retries detected in recent runs."
    if avg_elapsed > 240:
        return "Recommend smoke profile: recent runs are slow."
    return "Recommend full-distill profile: recent runs look stable."


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


def build_report_payload(runs: list[RunSummary], completed_only: bool) -> dict[str, Any]:
    return {
        "run_count": len(runs),
        "completed_only": completed_only,
        "recommendation": recommendation(runs, completed_only),
        "runs": [serialize_run(run) for run in runs],
    }


def print_report(runs: list[RunSummary], completed_only: bool) -> None:
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
    print(recommendation(runs, completed_only))


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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runs_dir = Path(args.runs_dir)
    if not runs_dir.is_dir():
        print(f"Run directory not found: {runs_dir}")
        return 1
    runs = discover_runs(runs_dir, max(1, args.limit), args.completed_only)
    if args.json:
        print(json.dumps(build_report_payload(runs, args.completed_only), indent=2))
    else:
        print_report(runs, args.completed_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
