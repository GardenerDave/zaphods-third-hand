#!/usr/bin/env python3
"""Read-only validator for the full front-door chain."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.validate_bounded_task_packet_draft import (  # noqa: E402
    BoundedTaskPacketDraftError,
    validate_bounded_task_packet_draft,
)
from local_harness.validate_bounded_task_review_packet import (  # noqa: E402
    BoundedTaskReviewPacketError,
    validate_bounded_task_review_packet,
)
from local_harness.validate_messy_input_triage_packet import (  # noqa: E402
    MessyInputTriagePacketError,
    validate_messy_input_triage_packet,
)

VALIDATION_SCHEMA = "front_door_chain_validation_v1"


class FrontDoorChainError(ValueError):
    """Raised when the front-door chain is malformed or inconsistent."""


def _read_json(path: Path) -> tuple[Any, Exception | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # noqa: BLE001
        return None, exc


def _load_or_validate(
    path: Path, validator
) -> tuple[Any | None, dict[str, Any], Exception | None]:
    packet, read_exc = _read_json(path)
    if read_exc is not None:
        diagnostics = [f"{path}: {read_exc}"]
        if isinstance(read_exc, json.JSONDecodeError):
            diagnostics = [f"{path}: malformed JSON packet", f"{path}: {read_exc.msg}"]
        return None, {"validation_status": "failed", "diagnostics": diagnostics}, read_exc
    try:
        validator(packet)
        return packet, {"validation_status": "passed", "diagnostics": []}, None
    except (MessyInputTriagePacketError, BoundedTaskPacketDraftError, BoundedTaskReviewPacketError, ValueError) as exc:
        return packet if isinstance(packet, dict) else None, {
            "validation_status": "failed",
            "diagnostics": [str(exc)],
        }, exc


def _path_matches(source: str, expected: str) -> bool:
    if source == expected:
        return True
    if not source.strip() or not expected.strip():
        return False
    if source.endswith(expected) or expected.endswith(source):
        return True
    return Path(source).name == Path(expected).name


_REQUIRED_BOUNDARY_TERMS = [
    "no_unattended_execution",
    "no_repo_mutation_without_review",
    "no_training_capture",
    "no_promotion",
    "no_deployment",
    "no_downstream_use_authority",
]


def _validate_boundary_terms(packet: Any, *, context: str, diagnostics: list[str]) -> str:
    boundaries = packet.get("authority_boundary") if isinstance(packet, dict) else None
    if not isinstance(boundaries, list) or any(
        not isinstance(item, str) or not item.strip() for item in boundaries
    ):
        diagnostics.append(f"{context}: authority_boundary must be a list of strings")
        return "failed"
    status = "passed"
    for term in _REQUIRED_BOUNDARY_TERMS:
        if term not in boundaries:
            diagnostics.append(f"{context}: missing authority boundary term: {term}")
            status = "failed"
    return status


def validate_front_door_chain(
    *,
    triage_packet_path: Path,
    bounded_task_packet_path: Path,
    review_packet_path: Path,
) -> dict[str, Any]:
    diagnostics: list[str] = []

    triage_raw, triage_result, triage_exc = _load_or_validate(
        triage_packet_path, validate_messy_input_triage_packet
    )
    bounded_task_raw, bounded_task_result, bounded_exc = _load_or_validate(
        bounded_task_packet_path, validate_bounded_task_packet_draft
    )
    review_raw, review_result, review_exc = _load_or_validate(
        review_packet_path, validate_bounded_task_review_packet
    )

    if triage_exc is not None:
        diagnostics.extend([f"triage: {item}" for item in triage_result["diagnostics"]])
    if bounded_exc is not None:
        diagnostics.extend([f"bounded_task: {item}" for item in bounded_task_result["diagnostics"]])
    if review_exc is not None:
        diagnostics.extend([f"review: {item}" for item in review_result["diagnostics"]])

    linkage_status = "passed"
    lifecycle_status = "passed"
    authority_boundary_status = "passed"

    if triage_result["validation_status"] != "passed":
        linkage_status = "failed"
    if bounded_task_result["validation_status"] != "passed":
        linkage_status = "failed"
    if review_result["validation_status"] != "passed":
        linkage_status = "failed"

    if triage_result["validation_status"] == "passed" and bounded_task_raw is not None:
        if bounded_task_raw.get("source_packet_schema") != "messy_input_triage_packet_v1":
            linkage_status = "failed"
            diagnostics.append(
                "bounded_task: source_packet_schema must be 'messy_input_triage_packet_v1'"
            )
        source_path = str(bounded_task_raw.get("source_packet_path", ""))
        if not source_path or not _path_matches(source_path, str(triage_packet_path)):
            linkage_status = "failed"
            diagnostics.append(
                "bounded_task: source_packet_path must match or end with the triage packet path"
            )

    if bounded_task_result["validation_status"] == "passed" and review_raw is not None:
        if review_raw.get("source_packet_schema") != "bounded_task_packet_draft_v1":
            linkage_status = "failed"
            diagnostics.append(
                "review: source_packet_schema must be 'bounded_task_packet_draft_v1'"
            )
        source_path = str(review_raw.get("source_packet_path", ""))
        if not source_path or not _path_matches(source_path, str(bounded_task_packet_path)):
            linkage_status = "failed"
            diagnostics.append(
                "review: source_packet_path must match or end with the bounded task packet path"
            )

    if bounded_task_raw is not None:
        for field, expected in {
            "review_required": True,
            "downstream_use_status": "prohibited_until_review",
            "automation_status": "not_automated",
            "queue_handoff_status": "not_inserted",
        }.items():
            if bounded_task_raw.get(field) != expected:
                lifecycle_status = "failed"
                diagnostics.append(f"bounded_task: {field} must be {expected!r}")
        if _validate_boundary_terms(bounded_task_raw, context="bounded_task", diagnostics=diagnostics) == "failed":
            authority_boundary_status = "failed"

    if review_raw is not None:
        for field, expected in {
            "review_status": "review_required",
            "downstream_use_status": "prohibited_until_review",
            "automation_status": "not_automated",
            "queue_handoff_status": "not_inserted",
            "repo_mutation_status": "not_authorized",
        }.items():
            if review_raw.get(field) != expected:
                lifecycle_status = "failed"
                diagnostics.append(f"review: {field} must be {expected!r}")
        if _validate_boundary_terms(review_raw, context="review", diagnostics=diagnostics) == "failed":
            authority_boundary_status = "failed"

    validation_status = "passed" if not diagnostics else "failed"
    return {
        "validation_schema": VALIDATION_SCHEMA,
        "validation_status": validation_status,
        "triage_packet_path": str(triage_packet_path),
        "bounded_task_packet_path": str(bounded_task_packet_path),
        "review_packet_path": str(review_packet_path),
        "triage_validation_status": triage_result["validation_status"],
        "bounded_task_validation_status": bounded_task_result["validation_status"],
        "review_packet_validation_status": review_result["validation_status"],
        "linkage_status": linkage_status,
        "lifecycle_status": lifecycle_status,
        "authority_boundary_status": authority_boundary_status,
        "diagnostics": diagnostics,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triage-packet", required=True, type=Path)
    parser.add_argument("--bounded-task-packet", required=True, type=Path)
    parser.add_argument("--review-packet", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = validate_front_door_chain(
        triage_packet_path=args.triage_packet,
        bounded_task_packet_path=args.bounded_task_packet,
        review_packet_path=args.review_packet,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
