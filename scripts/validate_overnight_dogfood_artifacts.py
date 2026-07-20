#!/usr/bin/env python3
"""Validate durable overnight dogfood controller artifacts.

This validator is intentionally narrow. It checks the overnight lifecycle state,
queue schema, run-directory evidence, terminal marker, closeout manifest, and
status snapshot for internal consistency.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.overnight_queue_authority import AuthorityValidationError, validate_allowed_targets


class OvernightArtifactValidationError(ValueError):
    pass


TERMINAL_STAGE_STATES = {"ready_for_review", "blocked"}


@dataclass(frozen=True)
class QueueRow:
    priority: str
    slug: str
    objective: str
    allowed_targets: list[str]
    line_no: int


@dataclass(frozen=True)
class StateRow:
    run_id: str
    slug: str
    event: str
    run_dir: str
    state: str
    detail: str | None
    timestamp: str
    line_no: int


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_queue(queue_path: Path) -> list[QueueRow]:
    if not queue_path.is_file():
        raise OvernightArtifactValidationError(f"queue file does not exist: {queue_path}")
    rows: list[QueueRow] = []
    schema = None
    slugs: set[str] = set()
    with queue_path.open(encoding="utf-8") as fh:
        for line_no, row in enumerate(csv.reader(fh, delimiter="\t"), start=1):
            if not row:
                continue
            if row[0].startswith("#"):
                if row[0].strip() == "# zth-roadmap-queue-schema: 2":
                    schema = 2
                continue
            if schema != 2:
                raise OvernightArtifactValidationError("unsupported_or_missing_queue_schema")
            if len(row) != 4:
                raise OvernightArtifactValidationError(f"{queue_path} line {line_no}: expected 4 fields")
            priority, slug, objective, raw_targets = (item.strip() for item in row)
            if not priority or not slug or not objective:
                raise OvernightArtifactValidationError(f"{queue_path} line {line_no}: missing required queue field")
            if slug in slugs:
                raise OvernightArtifactValidationError(f"{queue_path} line {line_no}: duplicate queue slug {slug}")
            slugs.add(slug)
            try:
                allowed_targets = validate_allowed_targets(json.loads(raw_targets))
            except (json.JSONDecodeError, AuthorityValidationError) as exc:
                raise OvernightArtifactValidationError(f"{queue_path} line {line_no}: invalid authority: {exc}") from exc
            rows.append(QueueRow(priority=priority, slug=slug, objective=objective, allowed_targets=allowed_targets, line_no=line_no))
    return rows


def _read_state(state_path: Path) -> list[StateRow]:
    if not state_path.is_file():
        raise OvernightArtifactValidationError(f"state file does not exist: {state_path}")
    rows: list[StateRow] = []
    with state_path.open(encoding="utf-8") as fh:
        for line_no, row in enumerate(csv.reader(fh, delimiter="\t"), start=1):
            if not row:
                continue
            if row[0].startswith("#"):
                continue
            if len(row) not in {6, 7}:
                raise OvernightArtifactValidationError(f"{state_path} line {line_no}: expected 6 or 7 fields")
            if len(row) == 6:
                run_id, slug, event, run_dir, state, timestamp = (item.strip() for item in row)
                detail = None
            else:
                run_id, slug, event, run_dir, state, detail, timestamp = (item.strip() for item in row)
            if not all([run_id, slug, event, run_dir, state, timestamp]):
                raise OvernightArtifactValidationError(f"{state_path} line {line_no}: empty lifecycle field")
            rows.append(StateRow(run_id=run_id, slug=slug, event=event, run_dir=run_dir, state=state, detail=detail, timestamp=timestamp, line_no=line_no))
    return rows


def _load_status(status_path: Path) -> dict[str, Any]:
    payload = _load_json(status_path)
    if not isinstance(payload, dict):
        raise OvernightArtifactValidationError("status file must contain a JSON object")
    return payload


def _load_terminal(terminal_path: Path, closeout_path: Path) -> dict[str, Any]:
    terminal = _load_json(terminal_path)
    closeout = _load_json(closeout_path)
    if terminal != closeout:
        raise OvernightArtifactValidationError("terminal marker and closeout manifest differ")
    duplicates = sorted(
        p for p in closeout_path.parent.glob(f"{closeout_path.stem}*.json") if p != closeout_path
    )
    if duplicates:
        raise OvernightArtifactValidationError("duplicate closeout artifacts present")
    return terminal


def validate_overnight_dogfood_artifacts(
    *,
    queue_path: Path,
    state_path: Path,
    runs_dir: Path,
    terminal_path: Path,
    closeout_path: Path,
    status_path: Path,
) -> dict[str, Any]:
    queue_rows = _read_queue(queue_path)
    state_rows = _read_state(state_path)
    status = _load_status(status_path)
    terminal = _load_terminal(terminal_path, closeout_path)

    latest_by_slug: dict[str, StateRow] = {}
    for row in state_rows:
        latest_by_slug[row.slug] = row

    queue_slugs = [row.slug for row in queue_rows]
    terminal_stage_rows = {row.slug for row in state_rows if row.state in TERMINAL_STAGE_STATES}
    unresolved_stage_rows = {row.slug for row in state_rows if row.state not in TERMINAL_STAGE_STATES}
    queue_exhausted_rows = [row for row in state_rows if row.state == "queue_exhausted"]
    ready_rows = [row for row in state_rows if row.state == "ready_for_review"]
    interrupted_rows = [row for row in state_rows if row.event == "interrupted_recovered"]

    for slug in queue_slugs:
        if slug not in latest_by_slug:
            raise OvernightArtifactValidationError(f"queue stage unresolved: {slug}")

    for row in state_rows:
        run_dir = Path(row.run_dir)
        if not run_dir.is_absolute():
            run_dir = runs_dir / row.run_dir
        if row.event == "model_output_captured" and not any(run_dir.glob("model_output.raw.*.json")):
            raise OvernightArtifactValidationError(f"{row.slug}: model_output_captured without raw output artifact")
        if row.event == "interrupted_recovered":
            recovery = run_dir / "recovery_manifest.json"
            expected_recovery = Path(row.detail) if row.detail else recovery
            if row.detail is None:
                raise OvernightArtifactValidationError(f"{row.slug}: interrupted_recovered without recovery manifest")
            if not expected_recovery.is_file():
                raise OvernightArtifactValidationError(f"{row.slug}: interrupted_recovered without recovery manifest")
            payload = _load_json(expected_recovery)
            prior_dir = Path(payload["prior_directory"])
            current_dir = Path(payload["current_directory"])
            if prior_dir == current_dir:
                raise OvernightArtifactValidationError(f"{row.slug}: recovery manifest reused the same directory")
            if not prior_dir.is_dir():
                raise OvernightArtifactValidationError(f"{row.slug}: prior recovery directory missing")
        if row.state == "ready_for_review":
            if not (run_dir / "stage_packet.md").is_file():
                raise OvernightArtifactValidationError(f"{row.slug}: ready_for_review missing stage packet")
            if not any(run_dir.glob("validation.*.json")):
                raise OvernightArtifactValidationError(f"{row.slug}: ready_for_review missing semantic validation evidence")
            if not (run_dir / "model_content.json").is_file():
                raise OvernightArtifactValidationError(f"{row.slug}: ready_for_review missing final content")
        if row.state == "blocked" and row.event == "queue_exhausted":
            raise OvernightArtifactValidationError("queue_exhausted cannot be recorded as a per-stage state")

    queue_remaining = sum(1 for slug in queue_slugs if latest_by_slug[slug].state not in TERMINAL_STAGE_STATES)
    queue_exhausted = bool(terminal.get("queue_exhausted"))
    if queue_exhausted and len(queue_exhausted_rows) != 1:
        raise OvernightArtifactValidationError("queue exhaustion must be recorded exactly once")
    if queue_exhausted and queue_remaining:
        raise OvernightArtifactValidationError("terminal marker claims queue exhaustion while work remains")
    if queue_exhausted and terminal.get("terminal_state") != "queue_exhausted":
        raise OvernightArtifactValidationError("terminal marker state mismatch")
    if len(ready_rows) != int(status.get("queue_stages_ready_for_review", -1)):
        raise OvernightArtifactValidationError("status ready_for_review count disagrees with durable state")
    if len([row for row in state_rows if row.state == "blocked" and row.slug in queue_slugs]) != int(status.get("queue_stages_blocked", -1)):
        raise OvernightArtifactValidationError("status blocked count disagrees with durable state")
    if len([row for row in state_rows if row.state == "semantic_validation_failed" and row.slug in queue_slugs]) != int(status.get("queue_stages_failed_semantic_validation", -1)):
        raise OvernightArtifactValidationError("status semantic failure count disagrees with durable state")
    if len([row for row in state_rows if row.state == "incomplete" and row.slug in queue_slugs]) != int(status.get("incomplete_count", -1)):
        raise OvernightArtifactValidationError("status incomplete count disagrees with durable state")

    status_remaining = status.get("queue_remaining")
    if status_remaining != queue_remaining:
        raise OvernightArtifactValidationError("status queue_remaining disagrees with durable state")
    if bool(status.get("terminal_state_consistent")) != (not queue_remaining or not queue_exhausted or queue_remaining == 0):
        raise OvernightArtifactValidationError("terminal_state_consistent disagrees with durable state")
    if status.get("queue_exhausted") != queue_exhausted:
        raise OvernightArtifactValidationError("status queue_exhausted disagrees with terminal marker")
    if queue_exhausted and status.get("terminal_run_state") != "queue_exhausted":
        raise OvernightArtifactValidationError("status terminal run state disagrees with terminal marker")

    closeout_marker = _load_json(closeout_path)
    if closeout_marker != terminal:
        raise OvernightArtifactValidationError("closeout manifest and terminal marker differ")

    queue_slug_set = set(queue_slugs)
    if len({row.slug for row in state_rows if row.slug in queue_slug_set}) != len(queue_slug_set):
        raise OvernightArtifactValidationError("state slug accounting mismatch")
    if len(interrupted_rows) > len(queue_rows):
        raise OvernightArtifactValidationError("too many interrupted_recovered rows")
    if any(row.state == "ready_for_review" for row in state_rows):
        for row in ready_rows:
            run_dir = Path(row.run_dir)
            if not run_dir.is_absolute():
                run_dir = runs_dir / row.run_dir
            if not (run_dir / "validation.1.json").is_file() and not any(run_dir.glob("validation.*.json")):
                raise OvernightArtifactValidationError(f"{row.slug}: ready_for_review missing semantic validation evidence")

    return {
        "validation_status": "passed",
        "queue_total": len(queue_rows),
        "queue_remaining": queue_remaining,
        "status_queue_remaining": status_remaining,
        "queue_exhausted": queue_exhausted,
        "terminal_state_consistent": status.get("terminal_state_consistent"),
        "terminal_run_state": status.get("terminal_run_state"),
        "queue_slugs": queue_slugs,
        "terminal_stage_slugs": sorted(terminal_stage_rows),
        "unresolved_stage_slugs": sorted(unresolved_stage_rows),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--terminal", required=True)
    parser.add_argument("--closeout", required=True)
    parser.add_argument("--status", required=True)
    args = parser.parse_args(argv)
    try:
        payload = validate_overnight_dogfood_artifacts(
            queue_path=Path(args.queue),
            state_path=Path(args.state),
            runs_dir=Path(args.runs_dir),
            terminal_path=Path(args.terminal),
            closeout_path=Path(args.closeout),
            status_path=Path(args.status),
        )
    except Exception as exc:
        print(json.dumps({"validation_status": "failed", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
