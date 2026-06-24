"""Finalize reviewed curriculum candidates into datasets and SFT exports."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import read_jsonl, write_jsonl
from .export_sft import write_sft_exports
from .review_curriculum import write_review_splits
from .split_curriculum import write_dataset_splits


def finalize_reviewed_curriculum(
    *,
    reviewed_candidates_path: str | Path,
    output_dir: str | Path,
    validation_ratio: float = 0.2,
    include_metadata: bool = True,
) -> dict[str, Any]:
    """Split reviewed candidates and write dataset/SFT artifacts."""

    out = Path(output_dir)
    review_dir = out / "review"
    datasets_dir = out / "datasets"
    sft_dir = datasets_dir / "sft"

    reviewed_candidates = read_jsonl(reviewed_candidates_path)
    review_splits = write_review_splits(reviewed_candidates, review_dir)

    dataset_manifest = write_dataset_splits(
        accepted_path=review_dir / "accepted.jsonl",
        holdout_locked_path=review_dir / "holdout_locked.jsonl",
        output_dir=datasets_dir,
        validation_ratio=validation_ratio,
    )

    sft_manifest = write_sft_exports(
        train_path=datasets_dir / "train.jsonl",
        validation_path=datasets_dir / "validation.jsonl",
        output_dir=sft_dir,
        include_metadata=include_metadata,
    )

    manifest = {
        "reviewed_candidates_count": len(reviewed_candidates),
        "candidate_count": len(review_splits["candidate"]),
        "accepted_count": len(review_splits["accepted"]),
        "rejected_count": len(review_splits["rejected"]),
        "holdout_locked_count": len(review_splits["holdout_locked"]),
        "needs_revision_count": len(review_splits["needs_revision"]),
        "train_count": dataset_manifest["train_count"],
        "validation_count": dataset_manifest["validation_count"],
        "holdout_count": dataset_manifest["holdout_count"],
        "sft_train_count": sft_manifest["train_count"],
        "sft_validation_count": sft_manifest["validation_count"],
        "include_metadata": include_metadata,
        "artifact_paths": {
            "review_dir": "review",
            "datasets_dir": "datasets",
            "sft_dir": "datasets/sft",
            "finalize_manifest": "finalize_manifest.jsonl",
        },
    }

    write_jsonl(out / "finalize_manifest.jsonl", [manifest])
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed-candidates", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--validation-ratio", type=float, default=0.2)
    parser.add_argument("--strip-metadata", action="store_true")
    args = parser.parse_args(argv)

    manifest = finalize_reviewed_curriculum(
        reviewed_candidates_path=args.reviewed_candidates,
        output_dir=args.output_dir,
        validation_ratio=args.validation_ratio,
        include_metadata=not args.strip_metadata,
    )

    print(
        "Finalized reviewed curriculum: "
        f"accepted={manifest['accepted_count']} "
        f"holdout_locked={manifest['holdout_locked_count']} "
        f"train={manifest['train_count']} "
        f"validation={manifest['validation_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
