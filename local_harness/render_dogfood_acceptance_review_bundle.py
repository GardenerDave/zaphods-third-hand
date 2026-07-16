#!/usr/bin/env python3
"""Model-free renderer for a supervised dogfood acceptance-review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.validate_dogfood_batch_artifacts import (
    validate_dogfood_batch_artifacts,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state_rows(state_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in state_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        timestamp, slug, status, run_dir = (part.strip() for part in parts)
        rows.append(
            {
                "timestamp": timestamp,
                "slug": slug,
                "status": status,
                "run_dir": run_dir,
            }
        )
    return rows


def _artifact_paths(run_path: Path) -> dict[str, str]:
    return {
        "stage_packet.md": str(run_path / "stage_packet.md"),
        "model_output.raw.json": str(run_path / "model_output.raw.json"),
        "model_output.redacted.json": str(run_path / "model_output.redacted.json"),
        "model_content.json": str(run_path / "model_content.json"),
    }


def _artifact_hashes(run_path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in [
        "stage_packet.md",
        "model_output.raw.json",
        "model_output.redacted.json",
        "model_content.json",
    ]:
        path = run_path / name
        if path.is_file():
            hashes[name] = _sha256(path)
    return hashes


def render_dogfood_acceptance_review_bundle(
    *,
    queue_path: Path,
    state_path: Path,
    runs_dir: Path,
    out_dir: Path,
    stage_log_path: Path | None = None,
) -> dict[str, Any]:
    validation_result = validate_dogfood_batch_artifacts(
        queue_path=queue_path,
        state_path=state_path,
        runs_dir=runs_dir,
        stage_log_path=stage_log_path,
    )

    state_rows = _state_rows(state_path) if state_path.is_file() else []
    completed_stages: list[dict[str, Any]] = []
    for row in state_rows:
        run_path = Path(row["run_dir"])
        if not run_path.is_absolute():
            run_path = runs_dir / row["run_dir"]
        completed_stages.append(
            {
                "timestamp": row["timestamp"],
                "slug": row["slug"],
                "status": row["status"],
                "run_dir": str(run_path),
                "artifact_paths": _artifact_paths(run_path),
                "artifact_sha256": _artifact_hashes(run_path),
            }
        )

    evidence_validation_status = validation_result["validation_status"]
    bundle = {
        "bundle_schema": "dogfood_acceptance_review_bundle_v1",
        "generated_at_utc": _utc_now(),
        "evidence_validation_status": evidence_validation_status,
        "acceptance_status": "not_reviewed",
        "review_required": True,
        "downstream_use_status": "prohibited_until_review",
        "authority_boundary": [
            "evidence_only",
            "no_auto_promotion",
            "no_unattended_execution",
            "no_training_capture",
            "no_cleanup_authority",
            "no_merge_authority",
            "no_deployment_authority",
        ],
        "inputs": {
            "queue_path": str(queue_path),
            "state_path": str(state_path),
            "runs_dir": str(runs_dir),
            "stage_log_path": str(stage_log_path) if stage_log_path is not None else None,
        },
        "validation_result": validation_result,
        "completed_stages": completed_stages,
        "diagnostics": list(validation_result.get("diagnostics", [])),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "dogfood_acceptance_review_bundle.json"
    output_path.write_text(json.dumps(bundle, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return bundle


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--runs-dir", required=True, type=Path)
    parser.add_argument("--stage-log", type=Path, default=None)
    parser.add_argument("--out-dir", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    bundle = render_dogfood_acceptance_review_bundle(
        queue_path=args.queue,
        state_path=args.state,
        runs_dir=args.runs_dir,
        out_dir=args.out_dir,
        stage_log_path=args.stage_log,
    )
    json.dump(bundle, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
