#!/usr/bin/env python3
"""Review a runtime-rule packet drafted from a reviewed intake-derived candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PACKET_ALLOWED_CLAIM = "only listed files are authorized targets"


def load_packet(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("packet must be a JSON object")
    return payload


def validate_packet(packet: dict[str, Any]) -> None:
    required = {
        "report_type",
        "packet_status",
        "source_candidate_review_path",
        "source_failure_id",
        "candidate_id",
        "proposed_rule_family_id",
        "evidence_boundary",
        "allowed_claim",
        "source_allowed_claim",
        "held_actions",
        "required_next_step",
        "registry_promotion_authorized",
        "runtime_rule_creation_authorized",
        "runtime_rule_install_authorized",
        "model_call_performed",
        "candidate_promotion_authorized",
        "packet_promotion_authorized",
        "authority_boundaries_preserved",
        "provenance",
        "runtime_rule_packet_draft",
    }
    if packet.get("report_type") != "larql_packet_from_intake_candidate.v0":
        raise ValueError("unexpected report_type")
    if not required.issubset(packet):
        missing = sorted(required - set(packet))
        raise ValueError(f"packet missing required keys: {', '.join(missing)}")
    if packet.get("packet_status") != "held_for_packet_review":
        raise ValueError("packet_status must be held_for_packet_review")
    if packet.get("allowed_claim") != PACKET_ALLOWED_CLAIM:
        raise ValueError("unexpected allowed_claim")
    if packet.get("required_next_step") != "supervised_runtime_rule_packet_review":
        raise ValueError("unexpected required_next_step")
    if packet.get("registry_promotion_authorized") is not False:
        raise ValueError("registry promotion must remain false")
    if packet.get("runtime_rule_creation_authorized") is not False:
        raise ValueError("runtime rule creation must remain false")
    if packet.get("runtime_rule_install_authorized") is not False:
        raise ValueError("runtime rule install must remain false")
    if packet.get("model_call_performed") is not False:
        raise ValueError("model call must remain false")
    if packet.get("candidate_promotion_authorized") is not False:
        raise ValueError("candidate promotion must remain false")
    if packet.get("packet_promotion_authorized") is not False:
        raise ValueError("packet promotion must remain false")
    if packet.get("authority_boundaries_preserved") is not True:
        raise ValueError("authority boundaries must be preserved")
    provenance = packet["provenance"]
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be a JSON object")
    if not provenance.get("source_note_path"):
        raise ValueError("missing provenance.source_note_path")
    if not provenance.get("source_note_sha256"):
        raise ValueError("missing provenance.source_note_sha256")
    reviewed = packet["runtime_rule_packet_draft"]
    if not isinstance(reviewed, dict):
        raise ValueError("runtime_rule_packet_draft must be a JSON object")
    if reviewed.get("review_status") != "held_for_packet_review":
        raise ValueError("runtime_rule_packet_draft.review_status must be held_for_packet_review")
    if reviewed.get("allowed_claim") != PACKET_ALLOWED_CLAIM:
        raise ValueError("runtime_rule_packet_draft.allowed_claim must match packet claim")
    if not reviewed.get("source_allowed_claim"):
        raise ValueError("missing runtime_rule_packet_draft.source_allowed_claim")
    json_contract = reviewed.get("json_contract")
    if not isinstance(json_contract, dict):
        raise ValueError("runtime_rule_packet_draft.json_contract must be a JSON object")
    if json_contract.get("allowed_claim") != PACKET_ALLOWED_CLAIM:
        raise ValueError("runtime_rule_packet_draft.json_contract.allowed_claim must match packet claim")
    if json_contract.get("outside_file_modification_authorized") is not False:
        raise ValueError("runtime_rule_packet_draft.json_contract.outside_file_modification_authorized must be false")
    if json_contract.get("required_next_step") != "request explicit scope expansion or review":
        raise ValueError("unexpected runtime_rule_packet_draft.json_contract.required_next_step")


def build_review(packet: dict[str, Any], packet_path: Path) -> dict[str, Any]:
    validate_packet(packet)
    family = packet["proposed_rule_family_id"]
    source_failure_id = packet["source_failure_id"]
    candidate_id = packet["candidate_id"]
    held_actions = list(packet["held_actions"])
    source_allowed_claim = packet["source_allowed_claim"]
    review = {
        "report_type": "larql_packet_review_from_intake_candidate.v0",
        "review_status": "held_at_install_boundary",
        "review_scope": "runtime-rule packet draft from reviewed intake candidate only",
        "source_packet_draft_path": str(packet_path),
        "source_failure_id": source_failure_id,
        "candidate_id": candidate_id,
        "proposed_rule_family_id": family,
        "evidence_boundary": packet["evidence_boundary"],
        "allowed_claim": PACKET_ALLOWED_CLAIM,
        "source_allowed_claim": source_allowed_claim,
        "held_actions": held_actions,
        "required_next_step": "explicit_local_install_boundary_review",
        "registry_promotion_authorized": False,
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "model_call_performed": False,
        "candidate_promotion_authorized": False,
        "packet_promotion_authorized": False,
        "install_authorized": False,
        "authority_boundaries_preserved": True,
        "provenance": dict(packet["provenance"]),
        "reviewed_packet": {
            "packet_family_id": family,
            "source_failure_id": source_failure_id,
            "candidate_id": candidate_id,
            "failure_pattern": "allowed_files boundary treated as exclusive authority",
            "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
            "allowed_claim": PACKET_ALLOWED_CLAIM,
            "source_allowed_claim": source_allowed_claim,
            "held_actions": held_actions,
            "evidence_boundary": packet["evidence_boundary"],
            "json_contract": dict(packet["runtime_rule_packet_draft"]["json_contract"]),
            "review_verdict": "held_at_install_boundary",
            "required_next_step": "explicit_local_install_boundary_review",
            "install_authorized": False,
        },
        "notes": [
            "Independent packet review is model-free.",
            "The packet remains held at the install boundary.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
            "The upstream intake-stage claim is preserved separately from the packet-stage rule claim.",
        ],
    }
    return review


def render_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# LARQL Packet Review From Intake Candidate Join Smoke",
        "",
        f"Review status: `{review['review_status']}`",
        f"Required next step: `{review['required_next_step']}`",
        "",
        f"Source packet draft: `{review['source_packet_draft_path']}`",
        f"Source failure id: `{review['source_failure_id']}`",
        f"Candidate id: `{review['candidate_id']}`",
        f"Proposed rule family id: `{review['proposed_rule_family_id']}`",
        "",
        "## What this join smoke proves",
        "",
        "- a held runtime-rule packet draft can be independently reviewed;",
        "- the review can preserve provenance and the separated claims;",
        "- the next step can be returned as an install-boundary review;",
        "- the completed registry remains unchanged.",
        "",
        "This is supervised guided capability, not autonomous repo authority and not general intelligence.",
        "",
        "## What this join smoke does not prove",
        "",
        "- it does not authorize install;",
        "- it does not create or install a runtime rule;",
        "- it does not run a probe;",
        "- it does not make the pipeline automatic for arbitrary messy input.",
        "",
        "## Why the packet is held at the install boundary",
        "",
        "- the packet is only a review artifact;",
        "- install is not authorized;",
        "- registry promotion is not authorized;",
        "- the upstream intake-stage claim stays separate from the packet-stage rule claim.",
        "",
        "## Held / not-authorized reminder",
        "",
        "- no model call is made by this driver",
        "- no training data is written",
        "- no dataset artifact is written",
        "- no durable memory is written",
        "- no candidate is promoted",
        "- no packet is promoted",
        "- no model weights are mutated",
        "- no runtime rules are installed or modified",
        "- no automatic failure-to-curriculum capture is performed",
        "",
        "## Notes",
        "",
        *[f"- {note}" for note in review["notes"]],
        "",
        "## Next step",
        "",
        "Hold the packet for explicit local install boundary review before any installation decision.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_review(packet_path: Path, run_id: str, out_root: Path) -> dict[str, Any]:
    packet = load_packet(packet_path)
    review = build_review(packet, packet_path)
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "larql_runtime_rule_packet_review.json").write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "larql_runtime_rule_packet_review.md").write_text(render_markdown(review), encoding="utf-8")
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_review(args.packet, args.run_id, args.out_root)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
