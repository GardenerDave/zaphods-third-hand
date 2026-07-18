#!/usr/bin/env python3
"""Deterministic validator for bounded task packet drafts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

VALIDATION_SCHEMA = "bounded_task_packet_draft_validation_v1"
PACKET_SCHEMA = "bounded_task_packet_draft_v1"
SOURCE_PACKET_SCHEMA = "messy_input_triage_packet_v1"
REQUIRED_PACKET_KEYS = {
    "packet_schema",
    "source_packet_schema",
    "source_packet_path",
    "task_summary",
    "allowed_targets",
    "held_targets",
    "evidence_needed",
    "proposed_action",
    "validation_plan",
    "stop_conditions",
    "authority_boundary",
    "review_required",
    "downstream_use_status",
    "automation_status",
    "queue_handoff_status",
}
REQUIRED_AUTHORITY_BOUNDARY = {
    "no_unattended_execution",
    "no_repo_mutation_without_review",
    "no_training_capture",
    "no_promotion",
    "no_deployment",
    "no_downstream_use_authority",
}
REQUIRED_STATUS_VALUES = {
    "downstream_use_status": "prohibited_until_review",
    "automation_status": "not_automated",
    "queue_handoff_status": "not_inserted",
}
UNSAFE_PROPOSED_ACTION_PATTERNS = [
    r"\bcomplete\b",
    r"\bcompletion\b",
    r"\bpromot(?:e|ion)\b",
    r"\bdeploy(?:ment|ing)?\b",
    r"\btrain(?:ing|ed|s)?\b",
    r"\bcleanup\b",
    r"\bclean up\b",
    r"\bimport\b",
    r"\bmerge\b",
    r"\bexecute\b",
    r"\bunattended\b",
    r"\bdownstream use\b",
    r"\bqueue insertion\b",
    r"\binsert into queue\b",
    r"\bgrant authority\b",
]


class BoundedTaskPacketDraftError(ValueError):
    """Raised when a bounded task packet draft is malformed or unsafe."""


def _require_object(packet: Any) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise BoundedTaskPacketDraftError("packet must be a JSON object")
    return packet


def _require_nonempty_str(packet: dict[str, Any], key: str) -> str:
    value = packet.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BoundedTaskPacketDraftError(f"packet field {key!r} must be a non-empty string")
    return value.strip()


def _require_str_list(packet: dict[str, Any], key: str) -> list[str]:
    value = packet.get(key)
    if not isinstance(value, list):
        raise BoundedTaskPacketDraftError(f"packet field {key!r} must be a list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise BoundedTaskPacketDraftError(f"packet field {key!r} must be a list of non-empty strings")
    return [item.strip() for item in value]


def _contains_unsafe_proposed_action(text: str) -> str | None:
    lowered = text.lower()
    for pattern in UNSAFE_PROPOSED_ACTION_PATTERNS:
        if re.search(pattern, lowered):
            return pattern
    return None


def validate_bounded_task_packet_draft(packet: Any) -> dict[str, Any]:
    packet_obj = _require_object(packet)
    missing = sorted(REQUIRED_PACKET_KEYS - set(packet_obj))
    if missing:
        raise BoundedTaskPacketDraftError(
            f"packet missing required fields: {', '.join(missing)}"
        )

    packet_schema = _require_nonempty_str(packet_obj, "packet_schema")
    if packet_schema != PACKET_SCHEMA:
        raise BoundedTaskPacketDraftError(
            f"packet_schema must be {PACKET_SCHEMA!r}, got {packet_schema!r}"
        )

    source_packet_schema = _require_nonempty_str(packet_obj, "source_packet_schema")
    if source_packet_schema != SOURCE_PACKET_SCHEMA:
        raise BoundedTaskPacketDraftError(
            f"source_packet_schema must be {SOURCE_PACKET_SCHEMA!r}, got {source_packet_schema!r}"
        )

    source_packet_path = _require_nonempty_str(packet_obj, "source_packet_path")
    task_summary = _require_nonempty_str(packet_obj, "task_summary")
    allowed_targets = _require_str_list(packet_obj, "allowed_targets")
    held_targets = _require_str_list(packet_obj, "held_targets")
    evidence_needed = _require_str_list(packet_obj, "evidence_needed")
    proposed_action = _require_nonempty_str(packet_obj, "proposed_action")
    validation_plan = _require_str_list(packet_obj, "validation_plan")
    stop_conditions = _require_str_list(packet_obj, "stop_conditions")
    authority_boundary = _require_str_list(packet_obj, "authority_boundary")

    if packet_obj.get("review_required") is not True:
        raise BoundedTaskPacketDraftError("packet field 'review_required' must be true")

    for field, expected in REQUIRED_STATUS_VALUES.items():
        value = packet_obj.get(field)
        if value != expected:
            raise BoundedTaskPacketDraftError(
                f"packet field {field!r} must be {expected!r}"
            )

    missing_boundaries = sorted(REQUIRED_AUTHORITY_BOUNDARY - set(authority_boundary))
    if missing_boundaries:
        raise BoundedTaskPacketDraftError(
            "packet missing required authority boundary terms: "
            + ", ".join(missing_boundaries)
        )

    unsafe_pattern = _contains_unsafe_proposed_action(proposed_action)
    if unsafe_pattern is not None:
        raise BoundedTaskPacketDraftError(
            "proposed_action claims unsafe authority or lifecycle movement: "
            f"{unsafe_pattern}"
        )

    return {
        "validation_schema": VALIDATION_SCHEMA,
        "validation_status": "passed",
        "packet_schema": packet_schema,
        "source_packet_schema": source_packet_schema,
        "source_packet_path": source_packet_path,
        "allowed_targets_count": len(allowed_targets),
        "held_targets_count": len(held_targets),
        "evidence_needed_count": len(evidence_needed),
        "validation_plan_count": len(validation_plan),
        "stop_conditions_count": len(stop_conditions),
        "diagnostics": [],
    }


def _count_list(packet: Any, key: str) -> int:
    if isinstance(packet, dict) and isinstance(packet.get(key), list):
        return len(packet[key])
    return 0


def _failure_result(path: Path, packet: Any, exc: Exception) -> dict[str, Any]:
    diagnostics = [str(exc)]
    if isinstance(exc, json.JSONDecodeError):
        diagnostics.insert(0, "malformed JSON packet")
    packet_schema = packet.get("packet_schema") if isinstance(packet, dict) else None
    return {
        "validation_schema": VALIDATION_SCHEMA,
        "validation_status": "failed",
        "packet_path": str(path),
        "packet_schema": packet_schema,
        "allowed_targets_count": _count_list(packet, "allowed_targets"),
        "held_targets_count": _count_list(packet, "held_targets"),
        "evidence_needed_count": _count_list(packet, "evidence_needed"),
        "validation_plan_count": _count_list(packet, "validation_plan"),
        "stop_conditions_count": _count_list(packet, "stop_conditions"),
        "diagnostics": diagnostics,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = None
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
        result = validate_bounded_task_packet_draft(packet)
        result = {**result, "packet_path": str(args.packet)}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = _failure_result(args.packet, packet, exc)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
