#!/usr/bin/env python3
"""Deterministic baseline router: messy input -> bounded triage packet.

The router uses conservative keyword rules to classify messy input into a
reviewable triage packet. It produces recommendations, not authority. It never
emits execution commands, arbitrary file modification, adapter training,
automatic curriculum capture, automatic promotion, or repo-wide certainty
claims. Ambiguous broad input routes to a design packet, not an
implementation packet.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.triage_packet_schema import (  # noqa: E402
    required_risk_flags_for_input,
    validate_triage_packet,
)


BASE_VALIDATION_HOOKS = [
    "allowed_held_target_separation",
    "required_reason",
    "no_execution_authority",
]
BASE_HELD_TARGETS = [
    "production automation",
    "automatic curriculum capture",
    "automatic promotion",
]
FORBIDDEN_OUTPUT_TERMS = (
    "execute this command",
    "modify arbitrary files",
    "train an adapter",
    "auto-add failure to curriculum",
    "promote a patch automatically",
)

ROUTE_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "route_training_design",
        "keywords": ["lora", "fine-tune", "finetune", "fine tune", "training", "adapter"],
        "task_type": "training_design",
        "recommended_workflow": "training_design_packet",
        "bounded_outputs": ["training_design_packet"],
        "allowed_targets": ["docs/reports/"],
        "extra_held_targets": ["training execution", "adapter training runs"],
        "risk_flags": ["training_pipeline_ambiguity"],
        "recommended_prompt_patches": [
            "scope_boundary_v1",
            "unsupported_certainty_v1",
            "output_contract_v1",
        ],
    },
    {
        "rule_id": "route_prompt_patch_library",
        "keywords": ["prompt injection", "prompt patch", "failure mode"],
        "task_type": "prompt_patch_curation",
        "recommended_workflow": "prompt_patch_library_workflow",
        "bounded_outputs": ["prompt_patch_candidates", "validator_expectations"],
        "allowed_targets": ["docs/PROMPT_PATCH_LIBRARY.md", "examples/prompt_patches/"],
        "extra_held_targets": ["automatic patch promotion"],
        "risk_flags": ["prompt_injection_surface"],
        "recommended_prompt_patches": [
            "scope_boundary_v1",
            "output_contract_v1",
            "reason_required_v1",
        ],
    },
    {
        "rule_id": "route_triage_router",
        "keywords": ["router", "triage", "messy input", "orchestration", "orchestrator"],
        "task_type": "triage_routing",
        "recommended_workflow": "triage_router_workflow",
        "bounded_outputs": ["triage_packet"],
        "allowed_targets": ["docs/TRIAGE_ROUTER.md", "examples/triage_packets/"],
        "extra_held_targets": ["autonomous orchestration"],
        "risk_flags": ["orchestration_scope_risk"],
        "recommended_prompt_patches": [
            "scope_boundary_v1",
            "output_contract_v1",
            "stop_condition_quality_v1",
        ],
    },
    {
        "rule_id": "route_presentation_outline",
        "keywords": ["presentation", "demo", "talk", "slides"],
        "task_type": "presentation_outline",
        "recommended_workflow": "presentation_outline_workflow",
        "bounded_outputs": ["presentation_outline"],
        "allowed_targets": ["docs/reports/"],
        "extra_held_targets": [],
        "risk_flags": [],
        "recommended_prompt_patches": [
            "output_contract_v1",
            "placeholder_leakage_v1",
        ],
    },
    {
        "rule_id": "route_repo_patch",
        "keywords": ["bug", "fix", "code", "test", "regression"],
        "task_type": "repo_patch",
        "recommended_workflow": "repo_patch_packet",
        "bounded_outputs": ["repo_patch_packet"],
        "allowed_targets": ["local_harness/", "tests/"],
        "extra_held_targets": ["unrelated files"],
        "risk_flags": [],
        "recommended_prompt_patches": [
            "scope_boundary_v1",
            "reason_required_v1",
            "stop_condition_quality_v1",
        ],
    },
    {
        "rule_id": "route_docs_update",
        "keywords": ["docs", "readme", "roadmap", "documentation"],
        "task_type": "docs_update",
        "recommended_workflow": "documentation_planning_workflow",
        "bounded_outputs": ["docs_update_packet"],
        "allowed_targets": ["docs/"],
        "extra_held_targets": [],
        "risk_flags": [],
        "recommended_prompt_patches": [
            "scope_boundary_v1",
            "placeholder_leakage_v1",
            "output_contract_v1",
        ],
    },
]

FALLBACK_RULE: dict[str, Any] = {
    "rule_id": "route_design_packet_fallback",
    "keywords": [],
    "task_type": "design_planning",
    "recommended_workflow": "design_packet",
    "bounded_outputs": ["design_packet"],
    "allowed_targets": ["docs/reports/"],
    "extra_held_targets": ["implementation_packet"],
    "risk_flags": ["scope_creep"],
    "recommended_prompt_patches": [
        "scope_boundary_v1",
        "unsupported_certainty_v1",
        "output_contract_v1",
    ],
}

BROAD_INPUT_MARKERS = [
    "everything",
    "all of it",
    "entire repo",
    "whole repo",
    "tie it back together",
    "got messy",
    "somehow",
]


def _match_rule(messy_input: str) -> tuple[dict[str, Any], list[str]]:
    lowered = messy_input.lower()
    matches: list[tuple[dict[str, Any], list[str]]] = []
    for rule in ROUTE_RULES:
        hits = [kw for kw in rule["keywords"] if kw in lowered]
        if hits:
            matches.append((rule, hits))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # Multiple domains in one messy request: conservative design packet.
        combined_hits = sorted({hit for _, hits in matches for hit in hits})
        return FALLBACK_RULE, combined_hits
    return FALLBACK_RULE, []


def _is_broad(messy_input: str, matched_hits: list[str]) -> bool:
    lowered = messy_input.lower()
    if any(marker in lowered for marker in BROAD_INPUT_MARKERS):
        return True
    return not matched_hits


def route_messy_input(messy_input: str, *, triage_id: str, source: str = "deterministic_router") -> dict[str, Any]:
    """Classify messy input into a validated, bounded triage packet."""
    if not isinstance(messy_input, str) or not messy_input.strip():
        raise ValueError("messy_input must be a non-empty string")
    if not isinstance(triage_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", triage_id):
        raise ValueError("triage_id must match [A-Za-z0-9_.-]+")

    rule, hits = _match_rule(messy_input)
    broad = _is_broad(messy_input, hits)
    if broad and rule["rule_id"] != "route_design_packet_fallback":
        # Broad ambiguous phrasing downgrades to design packet routing.
        downgraded_hits = hits
        rule, hits = FALLBACK_RULE, downgraded_hits

    risk_flags = sorted(
        set(rule["risk_flags"])
        | required_risk_flags_for_input(messy_input)
        | ({"scope_creep"} if broad else set())
    )

    held_targets = list(dict.fromkeys(BASE_HELD_TARGETS + rule["extra_held_targets"]))
    allowed_targets = [t for t in rule["allowed_targets"] if t not in held_targets]

    packet = {
        "triage_id": triage_id,
        "messy_input": messy_input,
        "normalized_intent": (
            f"Deterministic routing of messy input to {rule['recommended_workflow']}"
            f" (matched keywords: {', '.join(hits) if hits else 'none'})."
        ),
        "task_type": rule["task_type"],
        "recommended_workflow": rule["recommended_workflow"],
        "confidence": "medium" if hits and not broad else "low",
        "requires_clarification": broad,
        "bounded_outputs": list(rule["bounded_outputs"]),
        "allowed_targets": allowed_targets,
        "held_targets": held_targets,
        "risk_flags": risk_flags,
        "recommended_prompt_patches": list(rule["recommended_prompt_patches"]),
        "output_contract": {"format": "json", "requires_reason": True},
        "validation_hooks": list(BASE_VALIDATION_HOOKS),
        "provenance": {
            "source": source,
            "router_rule_id": rule["rule_id"],
            "matched_keywords": hits,
        },
        "reason": (
            "Deterministic keyword routing produced a bounded recommendation for"
            " supervised review. No execution, promotion, training, or curriculum"
            " authority is granted."
        ),
    }

    rendered = json.dumps(packet).lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        if term in rendered:
            raise ValueError(f"router produced forbidden authority term: {term}")

    validate_triage_packet(packet, model_facing=True)
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--messy-input", required=True)
    parser.add_argument("--triage-id", required=True)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        packet = route_messy_input(args.messy_input, triage_id=args.triage_id)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    text = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
