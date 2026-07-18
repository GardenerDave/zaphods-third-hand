#!/usr/bin/env python3
"""Read-only wrapper that validates and scores the full front-door chain."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.score_front_door_chain import (  # noqa: E402
    score_front_door_chain,
)
from local_harness.validate_front_door_chain import (  # noqa: E402
    validate_front_door_chain,
)

REVIEW_SCHEMA = "front_door_chain_review_v1"


def review_front_door_chain(
    *,
    triage_packet_path: Path,
    bounded_task_packet_path: Path,
    review_packet_path: Path,
) -> dict[str, Any]:
    chain_validation = validate_front_door_chain(
        triage_packet_path=triage_packet_path,
        bounded_task_packet_path=bounded_task_packet_path,
        review_packet_path=review_packet_path,
    )
    scorecard = score_front_door_chain(
        chain_validation,
        chain_result_path=Path("<in-memory-front-door-chain-result>"),
    )
    diagnostics = list(chain_validation.get("diagnostics", []))
    diagnostics.extend(str(item) for item in scorecard.get("diagnostics", []))
    review_status = scorecard.get("scorecard_status", "invalid")
    if review_status not in {"ready_for_review", "blocked", "invalid"}:
        review_status = "invalid"
    return {
        "review_schema": REVIEW_SCHEMA,
        "review_status": review_status,
        "chain_validation": chain_validation,
        "scorecard": scorecard,
        "automation_status": "not_automated",
        "queue_handoff_status": "not_inserted",
        "downstream_use_status": "prohibited_until_review",
        "repo_mutation_status": "not_authorized",
        "diagnostics": diagnostics,
        "required_human_action": scorecard.get("required_human_action")
        if isinstance(scorecard, dict)
        else "Inspect the chain result and decide whether the evidence is sufficient for the next supervised step.",
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triage-packet", required=True, type=Path)
    parser.add_argument("--bounded-task-packet", required=True, type=Path)
    parser.add_argument("--review-packet", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = review_front_door_chain(
        triage_packet_path=args.triage_packet,
        bounded_task_packet_path=args.bounded_task_packet,
        review_packet_path=args.review_packet,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["review_status"] == "ready_for_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
