"""Split reviewed curriculum rows into train, validation, and holdout datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import read_jsonl, write_jsonl


def candidate_to_training_row(candidate: dict[str, Any]) -> dict[str, Any]:
    """Convert an accepted curriculum candidate into a training row."""

    return {
        "messages": candidate["messages"],
        "metadata": {
            "candidate_id": candidate.get("id", ""),
            "failure_event_id": candidate.get("failure_event_id", ""),
            "cycle_id": candidate.get("cycle_id", ""),
            "task_type": candidate.get("task_type", ""),
            "failure_modes_targeted": candidate.get("failure_modes_targeted", []),
            "provenance": candidate.get("provenance", {}),
        },
    }


def training_rows_from_accepted(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return trainable rows from accepted candidates only."""

    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("review_status") == "accepted":
            rows.append(candidate_to_training_row(candidate))
    return rows


def split_train_validation(
    rows: list[dict[str, Any]],
    *,
    validation_ratio: float = 0.2,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministically split rows into train and validation sets."""

    if not rows:
        return [], []

    if len(rows) == 1:
        return rows, []

    validation_count = max(1, round(len(rows) * validation_ratio))
    validation_count = min(validation_count, len(rows) - 1)

    validation = rows[-validation_count:]
    train = rows[:-validation_count]
    return train, validation


def dataset_manifest(
    *,
    train_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    holdout_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "train_count": len(train_rows),
        "validation_count": len(validation_rows),
        "holdout_count": len(holdout_rows),
        "holdout_policy": "holdout_locked rows are evaluation-only and must not be used for training",
    }


def write_dataset_splits(
    *,
    accepted_path: str | Path,
    holdout_locked_path: str | Path,
    output_dir: str | Path,
    validation_ratio: float = 0.2,
) -> dict[str, Any]:
    """Write train, validation, holdout, and manifest files."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    accepted_candidates = read_jsonl(accepted_path)
    holdout_rows = read_jsonl(holdout_locked_path)

    trainable_rows = training_rows_from_accepted(accepted_candidates)
    train_rows, validation_rows = split_train_validation(
        trainable_rows,
        validation_ratio=validation_ratio,
    )

    write_jsonl(out / "train.jsonl", train_rows)
    write_jsonl(out / "validation.jsonl", validation_rows)
    write_jsonl(out / "holdout.jsonl", holdout_rows)

    manifest = dataset_manifest(
        train_rows=train_rows,
        validation_rows=validation_rows,
        holdout_rows=holdout_rows,
    )
    write_jsonl(out / "dataset_manifest.jsonl", [manifest])

    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted", required=True, help="accepted.jsonl from review split")
    parser.add_argument("--holdout-locked", required=True, help="holdout_locked.jsonl from review split")
    parser.add_argument("--output-dir", required=True, help="Dataset output directory")
    parser.add_argument("--validation-ratio", type=float, default=0.2)
    args = parser.parse_args(argv)

    write_dataset_splits(
        accepted_path=args.accepted,
        holdout_locked_path=args.holdout_locked,
        output_dir=args.output_dir,
        validation_ratio=args.validation_ratio,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
