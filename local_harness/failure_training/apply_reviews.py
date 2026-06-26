"""Apply explicit review decisions to curriculum candidates."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import read_jsonl, write_jsonl
from .review_curriculum import CONTROLLED_REVIEW_STATUSES, DEFAULT_REVIEW_STATUS


REVIEW_DECISION_STATUSES = {
    "accepted",
    "rejected",
    "holdout_locked",
    "needs_revision",
}


def normalize_decision_status(value: Any) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in REVIEW_DECISION_STATUSES:
            return normalized
    raise ValueError(f"unsupported review decision status: {value!r}")


def decisions_by_candidate_id(decisions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}

    for decision in decisions:
        candidate_id = decision.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise ValueError("review decision missing candidate_id")

        status = normalize_decision_status(decision.get("review_status"))
        row = dict(decision)
        row["candidate_id"] = candidate_id.strip()
        row["review_status"] = status
        indexed[row["candidate_id"]] = row

    return indexed


def apply_review_decisions(
    candidates: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    indexed = decisions_by_candidate_id(decisions)
    reviewed: list[dict[str, Any]] = []

    for candidate in candidates:
        row = dict(candidate)
        candidate_id = row.get("id")
        if not isinstance(candidate_id, str):
            row["review_status"] = DEFAULT_REVIEW_STATUS
            reviewed.append(row)
            continue

        decision = indexed.get(candidate_id)
        if decision is None:
            if row.get("review_status") not in CONTROLLED_REVIEW_STATUSES:
                row["review_status"] = DEFAULT_REVIEW_STATUS
            reviewed.append(row)
            continue

        row["review_status"] = decision["review_status"]
        row["review"] = {
            "reviewer": decision.get("reviewer", ""),
            "review_notes": decision.get("review_notes", ""),
            "decision_source": "review_decisions_jsonl",
        }
        reviewed.append(row)

    return reviewed


def apply_review_decisions_jsonl(
    *,
    candidates_path: str | Path,
    decisions_path: str | Path,
    output_path: str | Path,
) -> list[dict[str, Any]]:
    reviewed = apply_review_decisions(
        read_jsonl(candidates_path),
        read_jsonl(decisions_path),
    )
    write_jsonl(output_path, reviewed)
    return reviewed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, help="Input candidates.jsonl")
    parser.add_argument("--decisions", required=True, help="Review decisions JSONL")
    parser.add_argument("--output", required=True, help="Reviewed candidates JSONL")
    args = parser.parse_args(argv)

    reviewed = apply_review_decisions_jsonl(
        candidates_path=args.candidates,
        decisions_path=args.decisions,
        output_path=args.output,
    )
    accepted = sum(1 for row in reviewed if row.get("review_status") == "accepted")
    holdout = sum(1 for row in reviewed if row.get("review_status") == "holdout_locked")
    rejected = sum(1 for row in reviewed if row.get("review_status") == "rejected")
    needs_revision = sum(1 for row in reviewed if row.get("review_status") == "needs_revision")

    print(
        f"Reviewed candidates: total={len(reviewed)} "
        f"accepted={accepted} holdout_locked={holdout} "
        f"rejected={rejected} needs_revision={needs_revision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
