#!/usr/bin/env python3
"""Run a reviewed bounded fixture set sequentially and emit scorecard evidence.

This is an operator-selected batch driver, not a roadmap queue writer.  It
reuses the capability primitive and the overnight work directory/lock shape.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from local_harness.supervised_capability_loop import (
    aggregate_scorecard,
    load_patch_library,
    load_task_fixture,
    run_capability_loop,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures_dir", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--patch-dir", type=Path)
    parser.add_argument("--existing-patch-id", action="append", default=[])
    parser.add_argument("--max-worker-attempts", type=int, default=2)
    parser.add_argument("--max-teacher-passes", type=int, default=2)
    parser.add_argument("--deterministic-patch-path")
    parser.add_argument("--deterministic-patch-id")
    parser.add_argument("--deterministic-patch-sha256")
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "batch.lock").open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        library = load_patch_library(args.patch_dir)
        deterministic_patch_retry = None
        if any(value is not None for value in (args.deterministic_patch_path, args.deterministic_patch_id, args.deterministic_patch_sha256)):
            deterministic_patch_retry = {
                "patch_path": args.deterministic_patch_path,
                "patch_id": args.deterministic_patch_id,
                "patch_sha256": args.deterministic_patch_sha256,
            }
        fixture_paths = sorted(args.fixtures_dir.glob("*.json"))
        if not fixture_paths:
            raise SystemExit("no reviewed JSON fixtures found")
        trajectories = []
        for fixture_path in fixture_paths:
            task = load_task_fixture(fixture_path)
            task_dir = args.out_dir / task["task_id"]
            run_capability_loop(
                task,
                out_dir=task_dir,
                patch_library=library,
                existing_patch_ids=args.existing_patch_id,
                max_worker_attempts=args.max_worker_attempts,
                max_teacher_passes=args.max_teacher_passes,
                deterministic_patch_retry=deterministic_patch_retry,
            )
            trajectories.append(task_dir / "trajectory.jsonl")
        scorecard = aggregate_scorecard(trajectories)
        scorecard["fixture_set"] = str(args.fixtures_dir)
        scorecard["review_state"] = "ready_for_review"
        scorecard["queue_mutated"] = False
        scorecard["authority_boundaries"] = [
            "No automatic queue insertion or invented work.",
            "No automatic prompt-patch promotion or training.",
            "Deterministic validators remain authoritative.",
        ]
        (args.out_dir / "scorecard.json").write_text(json.dumps(scorecard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(scorecard, indent=2, sort_keys=True))
    return 0 if scorecard["unresolved_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
