#!/usr/bin/env python3
"""Model-free triage packet schema for normalizing messy input.

A triage packet is the bounded, reviewable form of a messy request. It records
normalized intent, a recommended workflow, allowed and held targets, risk
flags, recommended prompt patches, an output contract, validation hooks, and
provenance. Triage packets are recommendations for supervised review. They
grant no execution, promotion, training, or curriculum-capture authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_PACKET_KEYS = {
    "triage_id",
    "messy_input",
    "normalized_intent",
    "task_type",
    "recommended_workflow",
    "confidence",
    "requires_clarification",
    "bounded_outputs",
    "allowed_targets",
    "held_targets",
    "risk_flags",
    "recommended_prompt_patches",
    "output_contract",
    "validation_hooks",
    "provenance",
}
ALLOWED_CONFIDENCES = {"low", "medium", "high"}
FORBIDDEN_AUTHORITY_KEYS = {
    "execution_authority",
    "auto_promote",
    "auto_train",
    "auto_curriculum_capture",
    "lifecycle_authority",
}
FORBIDDEN_WORKFLOW_TERMS = {
    "execute",
    "auto_execute",
    "autonomous",
    "auto_promote",
    "auto_train",
    "training_execution",
    "auto_curriculum",
}
RISK_TRIGGER_KEYWORDS = {
    "training": "training_pipeline_ambiguity",
    "fine-tune": "training_pipeline_ambiguity",
    "finetune": "training_pipeline_ambiguity",
    "lora": "training_pipeline_ambiguity",
    "adapter": "training_pipeline_ambiguity",
    "prompt injection": "prompt_injection_surface",
    "orchestrat": "orchestration_scope_risk",
    "everything": "scope_creep",
    "all of it": "scope_creep",
    "entire repo": "scope_creep",
    "whole repo": "scope_creep",
}


class TriagePacketError(ValueError):
    """Raised when a triage packet is malformed or claims authority."""


def _require_nonempty_str(packet: dict[str, Any], key: str) -> str:
    value = packet.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TriagePacketError(f"packet field {key!r} must be a non-empty string")
    return value


def _require_str_list(packet: dict[str, Any], key: str, *, allow_empty: bool = False) -> list[str]:
    value = packet.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise TriagePacketError(f"packet field {key!r} must be a list of non-empty strings")
    if not value and not allow_empty:
        raise TriagePacketError(f"packet field {key!r} must not be empty")
    return value


def required_risk_flags_for_input(messy_input: str) -> set[str]:
    """Return risk flags that a packet must carry for this messy input."""
    lowered = messy_input.lower()
    return {
        flag
        for keyword, flag in RISK_TRIGGER_KEYWORDS.items()
        if keyword in lowered
    }


def validate_triage_packet(packet: Any, *, model_facing: bool = False) -> dict[str, Any]:
    """Validate one triage packet dictionary. Returns the packet on success."""
    if not isinstance(packet, dict):
        raise TriagePacketError("triage packet must be a JSON object")
    missing = sorted(REQUIRED_PACKET_KEYS - set(packet))
    if missing:
        raise TriagePacketError(f"packet missing required fields: {', '.join(missing)}")
    forbidden = sorted(FORBIDDEN_AUTHORITY_KEYS & set(packet))
    if forbidden:
        raise TriagePacketError(
            f"packet contains forbidden authority fields: {', '.join(forbidden)}"
        )

    _require_nonempty_str(packet, "triage_id")
    messy_input = _require_nonempty_str(packet, "messy_input")
    _require_nonempty_str(packet, "normalized_intent")
    _require_nonempty_str(packet, "task_type")

    workflow = _require_nonempty_str(packet, "recommended_workflow")
    workflow_lower = workflow.lower()
    for term in sorted(FORBIDDEN_WORKFLOW_TERMS):
        if term in workflow_lower:
            raise TriagePacketError(
                f"recommended_workflow {workflow!r} implies forbidden authority ({term})"
            )

    confidence = _require_nonempty_str(packet, "confidence")
    if confidence not in ALLOWED_CONFIDENCES:
        raise TriagePacketError(
            f"confidence {confidence!r} not in allowed values: {sorted(ALLOWED_CONFIDENCES)}"
        )

    if not isinstance(packet.get("requires_clarification"), bool):
        raise TriagePacketError("packet field 'requires_clarification' must be a boolean")

    _require_str_list(packet, "bounded_outputs")
    allowed_targets = _require_str_list(packet, "allowed_targets")
    held_targets = _require_str_list(packet, "held_targets", allow_empty=True)
    overlap = sorted(set(allowed_targets) & set(held_targets))
    if overlap:
        raise TriagePacketError(
            f"allowed_targets and held_targets overlap: {', '.join(overlap)}"
        )

    risk_flags = _require_str_list(packet, "risk_flags", allow_empty=True)
    missing_flags = sorted(required_risk_flags_for_input(messy_input) - set(risk_flags))
    if missing_flags:
        raise TriagePacketError(
            f"packet missing required risk flags for this input: {', '.join(missing_flags)}"
        )

    _require_str_list(packet, "recommended_prompt_patches", allow_empty=True)
    _require_str_list(packet, "validation_hooks")

    output_contract = packet.get("output_contract")
    if not isinstance(output_contract, dict) or not output_contract:
        raise TriagePacketError("packet field 'output_contract' must be a non-empty object")
    if not isinstance(output_contract.get("format"), str) or not output_contract["format"].strip():
        raise TriagePacketError("output_contract must declare a non-empty 'format'")
    if not isinstance(output_contract.get("requires_reason"), bool):
        raise TriagePacketError("output_contract must declare boolean 'requires_reason'")

    provenance = packet.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise TriagePacketError("packet field 'provenance' must be a non-empty object")
    if not isinstance(provenance.get("source"), str) or not provenance["source"].strip():
        raise TriagePacketError("provenance must declare a non-empty 'source'")

    if model_facing:
        if not output_contract.get("requires_reason"):
            raise TriagePacketError(
                "model-facing packets must set output_contract.requires_reason to true"
            )

    return packet


def load_triage_packet(path: Path, *, model_facing: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_triage_packet(payload, model_facing=model_facing)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--model-facing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        packet = load_triage_packet(args.packet, model_facing=args.model_facing)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    print(json.dumps({"triage_id": packet["triage_id"], "valid": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
