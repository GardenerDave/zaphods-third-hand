#!/usr/bin/env python3
"""Read-only scorecard for front-door chain validation results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VALIDATION_SCHEMA = "front_door_chain_validation_v1"
SCORECARD_SCHEMA = "front_door_chain_scorecard_v1"

_CHAIN_REQUIRED_FIELDS = {
    "validation_schema",
    "validation_status",
    "triage_validation_status",
    "bounded_task_validation_status",
    "review_packet_validation_status",
    "linkage_status",
    "lifecycle_status",
    "authority_boundary_status",
    "diagnostics",
}

_RESULT_KEYS = {
    "scorecard_schema": SCORECARD_SCHEMA,
    "automation_status": "not_automated",
    "queue_handoff_status": "not_inserted",
    "downstream_use_status": "prohibited_until_review",
    "repo_mutation_status": "not_authorized",
}


class FrontDoorChainScorecardError(ValueError):
    """Raised when the chain result cannot be scored safely."""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FrontDoorChainScorecardError("chain result must be a JSON object")
    return payload


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FrontDoorChainScorecardError(f"chain result field {key!r} must be a non-empty string")
    return value.strip()


def _require_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise FrontDoorChainScorecardError(f"chain result field {key!r} must be a list")
    return value


def _failure_payload(
    *,
    chain_result_path: Path,
    validation_schema: str | None,
    diagnostics: list[str],
) -> dict[str, Any]:
    return {
        "scorecard_schema": SCORECARD_SCHEMA,
        "scorecard_status": "invalid",
        "chain_result_path": str(chain_result_path),
        "chain_validation_status": "failed" if validation_schema == VALIDATION_SCHEMA else "unknown",
        "readiness_level": "malformed",
        "required_human_action": "Inspect the chain result and repair or regenerate the front-door chain evidence.",
        "automation_status": "not_automated",
        "queue_handoff_status": "not_inserted",
        "downstream_use_status": "prohibited_until_review",
        "repo_mutation_status": "not_authorized",
        "diagnostics": diagnostics,
        "evidence_summary": {
            "triage_validation_status": None,
            "bounded_task_validation_status": None,
            "review_packet_validation_status": None,
            "linkage_status": None,
            "lifecycle_status": None,
            "authority_boundary_status": None,
            "diagnostics_count": len(diagnostics),
        },
    }


def score_front_door_chain(chain_result: Any, *, chain_result_path: Path) -> dict[str, Any]:
    diagnostics: list[str] = []
    try:
        payload = _require_object(chain_result)
    except FrontDoorChainScorecardError as exc:
        return _failure_payload(
            chain_result_path=chain_result_path,
            validation_schema=None,
            diagnostics=[str(exc)],
        )

    missing = sorted(_CHAIN_REQUIRED_FIELDS - set(payload))
    if missing:
        return _failure_payload(
            chain_result_path=chain_result_path,
            validation_schema=payload.get("validation_schema")
            if isinstance(payload.get("validation_schema"), str)
            else None,
            diagnostics=[f"chain result missing required fields: {', '.join(missing)}"],
        )

    validation_schema = _require_str(payload, "validation_schema")
    if validation_schema != VALIDATION_SCHEMA:
        return _failure_payload(
            chain_result_path=chain_result_path,
            validation_schema=validation_schema,
            diagnostics=[
                f"chain result validation_schema must be {VALIDATION_SCHEMA!r}, got {validation_schema!r}"
            ],
        )

    validation_status = _require_str(payload, "validation_status")
    triage_status = _require_str(payload, "triage_validation_status")
    bounded_status = _require_str(payload, "bounded_task_validation_status")
    review_status = _require_str(payload, "review_packet_validation_status")
    linkage_status = _require_str(payload, "linkage_status")
    lifecycle_status = _require_str(payload, "lifecycle_status")
    authority_status = _require_str(payload, "authority_boundary_status")
    diagnostics_list = _require_list(payload, "diagnostics")
    if any(not isinstance(item, str) for item in diagnostics_list):
        raise FrontDoorChainScorecardError("chain result diagnostics must be a list of strings")

    all_passed = (
        validation_status == "passed"
        and triage_status == "passed"
        and bounded_status == "passed"
        and review_status == "passed"
        and linkage_status == "passed"
        and lifecycle_status == "passed"
        and authority_status == "passed"
    )

    if all_passed and not diagnostics_list:
        return {
            "scorecard_schema": SCORECARD_SCHEMA,
            "scorecard_status": "ready_for_review",
            "chain_result_path": str(chain_result_path),
            "chain_validation_status": validation_status,
            "readiness_level": "review_ready",
            "required_human_action": "Review the validated chain result and decide whether the evidence is sufficient for the next supervised step.",
            "automation_status": "not_automated",
            "queue_handoff_status": "not_inserted",
            "downstream_use_status": "prohibited_until_review",
            "repo_mutation_status": "not_authorized",
            "diagnostics": [],
            "evidence_summary": {
                "triage_validation_status": triage_status,
                "bounded_task_validation_status": bounded_status,
                "review_packet_validation_status": review_status,
                "linkage_status": linkage_status,
                "lifecycle_status": lifecycle_status,
                "authority_boundary_status": authority_status,
                "diagnostics_count": 0,
            },
        }

    if validation_status == "failed":
        diagnostics.append("chain validation failed; review readiness is blocked")
    else:
        diagnostics.append("chain result is not fully review-ready")

    if triage_status != "passed":
        diagnostics.append(f"triage_validation_status is {triage_status!r}")
    if bounded_status != "passed":
        diagnostics.append(f"bounded_task_validation_status is {bounded_status!r}")
    if review_status != "passed":
        diagnostics.append(f"review_packet_validation_status is {review_status!r}")
    if linkage_status != "passed":
        diagnostics.append(f"linkage_status is {linkage_status!r}")
    if lifecycle_status != "passed":
        diagnostics.append(f"lifecycle_status is {lifecycle_status!r}")
    if authority_status != "passed":
        diagnostics.append(f"authority_boundary_status is {authority_status!r}")
    if diagnostics_list:
        diagnostics.append("chain diagnostics:")
        diagnostics.extend(str(item) for item in diagnostics_list)

    return {
        **_RESULT_KEYS,
        "scorecard_status": "blocked",
        "chain_result_path": str(chain_result_path),
        "chain_validation_status": validation_status,
        "readiness_level": "needs_repair",
        "required_human_action": "Inspect the failing chain layers, preserve the evidence, and repair the underlying packet or validator issue before review.",
        "diagnostics": diagnostics,
        "evidence_summary": {
            "triage_validation_status": triage_status,
            "bounded_task_validation_status": bounded_status,
            "review_packet_validation_status": review_status,
            "linkage_status": linkage_status,
            "lifecycle_status": lifecycle_status,
            "authority_boundary_status": authority_status,
            "diagnostics_count": len(diagnostics_list),
        },
    }


def build_scorecard(chain_result_path: Path) -> dict[str, Any]:
    try:
        payload = _read_json(chain_result_path)
    except Exception as exc:  # noqa: BLE001
        diagnostics = [f"{chain_result_path}: malformed JSON packet" if isinstance(exc, json.JSONDecodeError) else f"{chain_result_path}: {exc}"]
        if isinstance(exc, json.JSONDecodeError):
            diagnostics.append(f"{chain_result_path}: {exc.msg}")
        return _failure_payload(
            chain_result_path=chain_result_path,
            validation_schema=None,
            diagnostics=diagnostics,
        )

    if not isinstance(payload, dict):
        return _failure_payload(
            chain_result_path=chain_result_path,
            validation_schema=None,
            diagnostics=["chain result must be a JSON object"],
        )

    return score_front_door_chain(payload, chain_result_path=chain_result_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain-result", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    scorecard = build_scorecard(args.chain_result)
    print(json.dumps(scorecard, indent=2, sort_keys=True))
    return 0 if scorecard["scorecard_status"] == "ready_for_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
