"""Split curriculum candidates by review status."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable

from .common import read_jsonl, write_jsonl


CONTROLLED_REVIEW_STATUSES = (
    "candidate",
    "accepted",
    "rejected",
    "holdout_locked",
    "needs_revision",
)

DEFAULT_REVIEW_STATUS = "needs_revision"


def normalized_review_status(candidate: dict[str, Any]) -> str:
    value = candidate.get("review_status")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in CONTROLLED_REVIEW_STATUSES:
            return normalized
    return DEFAULT_REVIEW_STATUS


def split_candidates_by_review_status(
    candidates: Iterable[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    splits: dict[str, list[dict[str, Any]]] = {
        status: [] for status in CONTROLLED_REVIEW_STATUSES
    }

    for candidate in candidates:
        normalized = normalized_review_status(candidate)
        row = dict(candidate)
        row["review_status"] = normalized
        splits[normalized].append(row)

    return splits


def review_summary_markdown(splits: dict[str, list[dict[str, Any]]]) -> str:
    lines = [
        "# Curriculum Review Summary",
        "",
        "| review_status | count | trainable |",
        "| --- | ---: | --- |",
    ]

    for status in CONTROLLED_REVIEW_STATUSES:
        trainable = "yes" if status == "accepted" else "no"
        lines.append(f"| {status} | {len(splits.get(status, []))} | {trainable} |")

    lines.extend(
        [
            "",
            "Only `accepted` candidates are eligible for training export.",
            "`holdout_locked` candidates are reserved for evaluation/proof sets.",
            "`candidate`, `needs_revision`, and `rejected` candidates must not be used for training.",
            "",
        ]
    )
    return "\n".join(lines)


def write_review_splits(
    candidates: Iterable[dict[str, Any]],
    output_dir: str | Path,
) -> dict[str, list[dict[str, Any]]]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    splits = split_candidates_by_review_status(candidates)

    for status, rows in splits.items():
        write_jsonl(out / f"{status}.jsonl", rows)

    (out / "review_summary.md").write_text(
        review_summary_markdown(splits),
        encoding="utf-8",
    )

    return splits


def split_review_jsonl(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict[str, list[dict[str, Any]]]:
    return write_review_splits(read_jsonl(input_path), output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Curriculum candidates JSONL")
    parser.add_argument("--output-dir", required=True, help="Review split output directory")
    args = parser.parse_args(argv)

    split_review_jsonl(args.input, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
