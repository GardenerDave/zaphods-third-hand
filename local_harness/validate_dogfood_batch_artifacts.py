#!/usr/bin/env python3
"""Deterministic structural validator for supervised dogfood batch artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from scripts.overnight_queue_authority import AuthorityValidationError, validate_allowed_targets


class DogfoodBatchArtifactValidationError(ValueError):
    """Raised when dogfood batch evidence is missing or malformed."""


@dataclass(frozen=True)
class QueueRow:
    priority: str
    slug: str
    description: str
    allowed_targets: list[str] | None
    line_no: int


@dataclass(frozen=True)
class StateRow:
    timestamp: str
    slug: str
    status: str
    run_dir: str
    line_no: int


def _parse_tsv_row(parts: list[str], *, expected: int, line_no: int, source: Path) -> list[str]:
    if len(parts) != expected:
        raise DogfoodBatchArtifactValidationError(
            f"{source} line {line_no}: expected {expected} tab-separated fields, found {len(parts)}"
        )
    return parts


def _read_queue(queue_path: Path) -> tuple[list[QueueRow], list[str]]:
    if not queue_path.is_file():
        raise DogfoodBatchArtifactValidationError(f"queue file does not exist: {queue_path}")
    rows: list[QueueRow] = []
    diagnostics: list[str] = []
    schema_version: int | None = None
    for line_no, line in enumerate(queue_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            if line.strip() == "# zth-roadmap-queue-schema: 2":
                schema_version = 2
            continue
        parts = line.split("\t")
        if len(parts) == 3:
            if schema_version == 2:
                raise DogfoodBatchArtifactValidationError(
                    f"{queue_path} line {line_no}: schema 2 queue rows must contain priority, slug, description, and allowed_targets_json"
                )
            priority, slug, description = (item.strip() for item in parts)
            if not priority or not slug or not description:
                raise DogfoodBatchArtifactValidationError(
                    f"{queue_path} line {line_no}: queue rows must contain priority, slug, and description"
                )
            rows.append(QueueRow(priority=priority, slug=slug, description=description, allowed_targets=None, line_no=line_no))
            continue
        if len(parts) != 4:
            raise DogfoodBatchArtifactValidationError(
                f"{queue_path} line {line_no}: expected 3 fields for schema 1 or 4 fields for schema 2"
            )
        if schema_version != 2:
            raise DogfoodBatchArtifactValidationError(
                f"{queue_path} line {line_no}: schema 2 queue rows require the '# zth-roadmap-queue-schema: 2' marker"
            )
        priority, slug, description, raw_targets = (item.strip() for item in parts)
        if not priority or not slug or not description:
            raise DogfoodBatchArtifactValidationError(
                f"{queue_path} line {line_no}: queue rows must contain priority, slug, description, and allowed targets"
            )
        try:
            allowed_targets = validate_allowed_targets(json.loads(raw_targets))
        except (json.JSONDecodeError, AuthorityValidationError) as exc:
            raise DogfoodBatchArtifactValidationError(
                f"{queue_path} line {line_no}: invalid allowed_targets_json: {exc}"
            ) from exc
        rows.append(QueueRow(priority=priority, slug=slug, description=description, allowed_targets=allowed_targets, line_no=line_no))
    return rows, diagnostics


def _read_state(state_path: Path) -> tuple[list[StateRow], list[str]]:
    if not state_path.is_file():
        raise DogfoodBatchArtifactValidationError(f"state file does not exist: {state_path}")
    rows: list[StateRow] = []
    diagnostics: list[str] = []
    for line_no, line in enumerate(state_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = _parse_tsv_row(line.split("\t"), expected=4, line_no=line_no, source=state_path)
        timestamp, slug, status, run_dir = (item.strip() for item in parts)
        if not timestamp or not slug or not status or not run_dir:
            raise DogfoodBatchArtifactValidationError(
                f"{state_path} line {line_no}: state rows must contain timestamp, slug, status, and run_dir"
            )
        rows.append(
            StateRow(
                timestamp=timestamp,
                slug=slug,
                status=status,
                run_dir=run_dir,
                line_no=line_no,
            )
        )
    return rows, diagnostics


def _json_or_error(path: Path) -> str | None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return f"{path.name}: {exc.msg}"
    return None


def _json_object_or_error(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"{path.name}: {exc.msg}"
    if not isinstance(payload, dict):
        return None, f"{path.name}: expected a JSON object"
    return payload, None


def validate_dogfood_batch_artifacts(
    *,
    queue_path: Path,
    state_path: Path,
    runs_dir: Path,
    stage_log_path: Path | None = None,
) -> dict[str, Any]:
    diagnostics: list[str] = []
    missing_artifacts: list[dict[str, Any]] = []
    json_errors: list[dict[str, Any]] = []
    order_mismatches: list[dict[str, Any]] = []
    duplicate_state_slugs: list[str] = []

    try:
        queue_rows, queue_diagnostics = _read_queue(queue_path)
        diagnostics.extend(queue_diagnostics)
    except DogfoodBatchArtifactValidationError as exc:
        return {
            "validation_status": "failed",
            "queue_total": 0,
            "completed_total": 0,
            "remaining_total": 0,
            "duplicate_state_slugs": [],
            "order_mismatches": [],
            "missing_artifacts": [],
            "json_errors": [],
            "exhaustion_visible": False,
            "diagnostics": [str(exc)],
        }

    try:
        state_rows, state_diagnostics = _read_state(state_path)
        diagnostics.extend(state_diagnostics)
    except DogfoodBatchArtifactValidationError as exc:
        return {
            "validation_status": "failed",
            "queue_total": len(queue_rows),
            "completed_total": 0,
            "remaining_total": len(queue_rows),
            "duplicate_state_slugs": [],
            "order_mismatches": [],
            "missing_artifacts": [],
            "json_errors": [],
            "exhaustion_visible": False,
            "diagnostics": [str(exc)],
        }

    queue_slugs = [row.slug for row in queue_rows]
    seen_slugs: set[str] = set()
    for row in state_rows:
        if row.slug in seen_slugs and row.slug not in duplicate_state_slugs:
            duplicate_state_slugs.append(row.slug)
        seen_slugs.add(row.slug)

    for index, state_row in enumerate(state_rows):
        expected_slug = queue_slugs[index] if index < len(queue_slugs) else None
        if expected_slug != state_row.slug:
            order_mismatches.append(
                {
                    "index": index,
                    "expected_slug": expected_slug,
                    "actual_slug": state_row.slug,
                    "state_line": state_row.line_no,
                }
            )

    completed_total = len(state_rows)
    remaining_total = max(len(queue_rows) - completed_total, 0)

    for state_row in state_rows:
        run_path = Path(state_row.run_dir)
        if not run_path.is_absolute():
            run_path = runs_dir / state_row.run_dir
        if not run_path.is_dir():
            missing_artifacts.append(
                {
                    "slug": state_row.slug,
                    "path": str(run_path),
                    "missing": ["run_dir"],
                }
            )
            continue

        if state_row.status != "packet_generated":
            diagnostics.append(
                f"state row for {state_row.slug} has status {state_row.status!r}, expected 'packet_generated'"
            )
            missing_artifacts.append(
                {
                    "slug": state_row.slug,
                    "path": str(run_path),
                    "missing": ["packet_generated_status"],
                }
            )
            continue

        required_files = [
            "stage_packet.md",
            "model_output.raw.json",
            "model_output.redacted.json",
            "model_content.json",
        ]
        missing_files = [name for name in required_files if not (run_path / name).is_file()]
        if missing_files:
            missing_artifacts.append(
                {
                    "slug": state_row.slug,
                    "path": str(run_path),
                    "missing": missing_files,
                }
            )
            continue

        for json_name in ["model_output.raw.json"]:
            json_error = _json_or_error(run_path / json_name)
            if json_error:
                json_errors.append(
                    {
                        "slug": state_row.slug,
                        "path": str(run_path / json_name),
                        "error": json_error,
                    }
                )

        model_content_path = run_path / "model_content.json"
        model_content, content_error = _json_object_or_error(model_content_path)
        if content_error:
            json_errors.append(
                {
                    "slug": state_row.slug,
                    "path": str(model_content_path),
                    "error": content_error,
                }
            )
            continue

        required_content_fields = [
            "task_summary",
            "repo_observations",
            "allowed_targets",
            "held_targets",
            "proposed_next_action",
            "validation_plan",
        ]
        missing_fields = [field for field in required_content_fields if field not in model_content]
        if missing_fields:
            json_errors.append(
                {
                    "slug": state_row.slug,
                    "path": str(model_content_path),
                    "error": "model_content.json missing required fields: " + ", ".join(missing_fields),
                }
            )

    exhaustion_visible = False
    if stage_log_path is not None and stage_log_path.is_file():
        exhaustion_visible = "No remaining dogfood stages." in stage_log_path.read_text(encoding="utf-8")

    if completed_total == len(queue_rows) and stage_log_path is not None and stage_log_path.exists():
        if not exhaustion_visible:
            diagnostics.append("stage.log does not show the exhaustion line")

    validation_status = "passed"
    if duplicate_state_slugs or order_mismatches or missing_artifacts or json_errors:
        validation_status = "failed"
    if completed_total == len(queue_rows) and stage_log_path is not None and not exhaustion_visible:
        validation_status = "failed"

    return {
        "validation_status": validation_status,
        "queue_total": len(queue_rows),
        "completed_total": completed_total,
        "remaining_total": remaining_total,
        "duplicate_state_slugs": duplicate_state_slugs,
        "order_mismatches": order_mismatches,
        "missing_artifacts": missing_artifacts,
        "json_errors": json_errors,
        "exhaustion_visible": exhaustion_visible,
        "diagnostics": diagnostics,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True, type=Path, help="Path to the dogfood queue TSV.")
    parser.add_argument("--state", required=True, type=Path, help="Path to the dogfood state TSV.")
    parser.add_argument("--runs-dir", required=True, type=Path, help="Path to the dogfood runs directory.")
    parser.add_argument(
        "--stage-log",
        type=Path,
        default=None,
        help="Optional path to the stage log for exhaustion checks.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    result = validate_dogfood_batch_artifacts(
        queue_path=args.queue,
        state_path=args.state,
        runs_dir=args.runs_dir,
        stage_log_path=args.stage_log,
    )
    json.dump(result, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0 if result["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
