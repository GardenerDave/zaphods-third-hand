"""Run the failure curriculum data loop for one cycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .build_curriculum import build_curriculum_jsonl
from .classify_failures import classify_failures_jsonl
from .collect_failures import collect_failures_from_jsonl
from .export_sft import write_sft_exports
from .paths import ensure_cycle_tree
from .review_curriculum import split_review_jsonl
from .split_curriculum import write_dataset_splits
from .status import StatusWriter, utc_now_iso


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(path: Path, base: Path) -> str:
    return str(path.relative_to(base))


def run_cycle(
    *,
    input_path: str | Path,
    work_root: str | Path,
    cycle_id: str,
    source_run_id: str,
    target_capability: str,
    validation_ratio: float = 0.2,
    include_metadata: bool = True,
) -> dict[str, Any]:
    """Run the deterministic failure curriculum data loop."""

    root = Path(work_root)
    base = ensure_cycle_tree(root, cycle_id)
    writer = StatusWriter(base, cycle_id)

    failure_events_path = base / "failures" / "failure_events.jsonl"
    classified_path = base / "failures" / "classified_failure_events.jsonl"
    candidates_path = base / "curriculum" / "candidates.jsonl"
    review_dir = base / "curriculum" / "review"
    datasets_dir = base / "datasets"
    sft_dir = datasets_dir / "sft"
    manifest_path = base / "cycle_manifest.json"

    writer.event("cycle", "START", status="running", source_run_id=source_run_id)

    writer.event("collect", "START", status="running")
    failure_events = collect_failures_from_jsonl(
        input_path,
        failure_events_path,
        cycle_id=cycle_id,
        source_run_id=source_run_id,
    )
    writer.event("collect", "COMPLETE", status="completed", count=len(failure_events))

    writer.event("classify", "START", status="running")
    classified = classify_failures_jsonl(failure_events_path, classified_path)
    writer.event("classify", "COMPLETE", status="completed", count=len(classified))

    writer.event("curriculum", "START", status="running")
    candidates = build_curriculum_jsonl(classified_path, candidates_path)
    writer.event("curriculum", "COMPLETE", status="completed", count=len(candidates))

    writer.event("review_split", "START", status="running")
    review_splits = split_review_jsonl(candidates_path, review_dir)
    writer.event(
        "review_split",
        "COMPLETE",
        status="completed",
        accepted=len(review_splits["accepted"]),
        holdout_locked=len(review_splits["holdout_locked"]),
        needs_revision=len(review_splits["needs_revision"]),
    )

    writer.event("dataset_split", "START", status="running")
    dataset_manifest = write_dataset_splits(
        accepted_path=review_dir / "accepted.jsonl",
        holdout_locked_path=review_dir / "holdout_locked.jsonl",
        output_dir=datasets_dir,
        validation_ratio=validation_ratio,
    )
    writer.event(
        "dataset_split",
        "COMPLETE",
        status="completed",
        train_count=dataset_manifest["train_count"],
        validation_count=dataset_manifest["validation_count"],
        holdout_count=dataset_manifest["holdout_count"],
    )

    writer.event("sft_export", "START", status="running")
    sft_manifest = write_sft_exports(
        train_path=datasets_dir / "train.jsonl",
        validation_path=datasets_dir / "validation.jsonl",
        output_dir=sft_dir,
        include_metadata=include_metadata,
    )
    writer.event(
        "sft_export",
        "COMPLETE",
        status="completed",
        train_count=sft_manifest["train_count"],
        validation_count=sft_manifest["validation_count"],
    )

    manifest = {
        "cycle_id": cycle_id,
        "created_at": utc_now_iso(),
        "source_run_id": source_run_id,
        "target_capability": target_capability,
        "status": "completed",
        "failure_modes": sorted(
            {
                str(event.get("failure_mode"))
                for event in classified
                if event.get("failure_mode")
            }
        ),
        "counts": {
            "failure_events": len(failure_events),
            "classified_failures": len(classified),
            "curriculum_candidates": len(candidates),
            "accepted": len(review_splits["accepted"]),
            "holdout_locked": len(review_splits["holdout_locked"]),
            "needs_revision": len(review_splits["needs_revision"]),
            "train": dataset_manifest["train_count"],
            "validation": dataset_manifest["validation_count"],
            "holdout": dataset_manifest["holdout_count"],
        },
        "artifact_paths": {
            "failure_events": rel(failure_events_path, base),
            "classified_failures": rel(classified_path, base),
            "curriculum_candidates": rel(candidates_path, base),
            "review_dir": rel(review_dir, base),
            "datasets_dir": rel(datasets_dir, base),
            "sft_dir": rel(sft_dir, base),
            "status_log": "status.log",
            "status_events": "status_events.jsonl",
        },
    }

    write_json(manifest_path, manifest)
    writer.event("cycle", "COMPLETE", status="completed")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Raw audition/probe rows JSONL")
    parser.add_argument("--work-root", default=".work/failure_training")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--target-capability", required=True)
    parser.add_argument("--validation-ratio", type=float, default=0.2)
    parser.add_argument("--strip-metadata", action="store_true")
    args = parser.parse_args(argv)

    run_cycle(
        input_path=args.input,
        work_root=args.work_root,
        cycle_id=args.cycle_id,
        source_run_id=args.source_run_id,
        target_capability=args.target_capability,
        validation_ratio=args.validation_ratio,
        include_metadata=not args.strip_metadata,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
