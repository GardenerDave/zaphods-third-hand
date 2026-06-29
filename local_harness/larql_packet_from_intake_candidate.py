#!/usr/bin/env python3
"""Draft a held runtime-rule packet from a reviewed intake-derived candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PACKET_JSON_CONTRACT = {
    "evidence_boundary": "allowed files only",
    "allowed_claim": "only listed files are authorized targets",
    "outside_file_modification_authorized": False,
    "held_claims": [
        "modify any repo file",
        "touch adjacent files",
        "update generated files",
        "fix unrelated files",
        "expand patch scope",
    ],
    "required_next_step": "request explicit scope expansion or review",
    "evidence_to_preserve": [
        "allowed_files list",
        "requested target file",
        "out-of-scope file",
    ],
}


def load_review(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("review must be a JSON object")
    return payload


def validate_review(review: dict[str, Any]) -> None:
    required = {
        "report_type",
        "review_status",
        "review_scope",
        "source_failure_id",
        "candidate_id",
        "proposed_rule_family_id",
        "evidence_boundary",
        "allowed_claim",
        "held_actions",
        "required_next_step",
        "registry_promotion_authorized",
        "runtime_rule_creation_authorized",
        "runtime_rule_install_authorized",
        "model_call_performed",
        "candidate_promotion_authorized",
        "authority_boundaries_preserved",
        "provenance",
        "reviewed_candidate",
    }
    if review.get("report_type") != "larql_candidate_review_from_intake.v0":
        raise ValueError("unexpected report_type")
    if not required.issubset(review):
        missing = sorted(required - set(review))
        raise ValueError(f"review missing required keys: {', '.join(missing)}")
    if review.get("review_status") != "accepted_for_runtime_rule_packet_drafting":
        raise ValueError("review_status must be accepted_for_runtime_rule_packet_drafting")
    if review.get("review_scope") != "candidate draft from reviewed intake only":
        raise ValueError("unexpected review_scope")
    if review.get("required_next_step") != "draft_runtime_rule_packet_from_reviewed_candidate":
        raise ValueError("unexpected required_next_step")
    if review.get("registry_promotion_authorized") is not False:
        raise ValueError("registry promotion must remain false")
    if review.get("runtime_rule_creation_authorized") is not False:
        raise ValueError("runtime rule creation must remain false")
    if review.get("runtime_rule_install_authorized") is not False:
        raise ValueError("runtime rule install must remain false")
    if review.get("model_call_performed") is not False:
        raise ValueError("model call must remain false")
    if review.get("candidate_promotion_authorized") is not False:
        raise ValueError("candidate promotion must remain false")
    if review.get("authority_boundaries_preserved") is not True:
        raise ValueError("authority boundaries must be preserved")
    provenance = review["provenance"]
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be a JSON object")
    if not provenance.get("source_note_path"):
        raise ValueError("missing provenance.source_note_path")
    if not provenance.get("source_note_sha256"):
        raise ValueError("missing provenance.source_note_sha256")
    reviewed = review["reviewed_candidate"]
    if not isinstance(reviewed, dict):
        raise ValueError("reviewed_candidate must be a JSON object")
    if reviewed.get("review_verdict") != "accepted_for_runtime_rule_packet_drafting":
        raise ValueError("reviewed_candidate.review_verdict must be accepted_for_runtime_rule_packet_drafting")


def build_packet(review: dict[str, Any], review_path: Path) -> dict[str, Any]:
    validate_review(review)
    family = review["proposed_rule_family_id"]
    source_failure_id = review["source_failure_id"]
    candidate_id = review["candidate_id"]
    held_actions = list(review["held_actions"])
    source_allowed_claim = review["allowed_claim"]
    packet = {
        "report_type": "larql_packet_from_intake_candidate.v0",
        "packet_status": "held_for_packet_review",
        "source_candidate_review_path": str(review_path),
        "source_failure_id": source_failure_id,
        "candidate_id": candidate_id,
        "proposed_rule_family_id": family,
        "evidence_boundary": review["evidence_boundary"],
        "allowed_claim": PACKET_JSON_CONTRACT["allowed_claim"],
        "source_allowed_claim": source_allowed_claim,
        "held_actions": held_actions,
        "required_next_step": "supervised_runtime_rule_packet_review",
        "registry_promotion_authorized": False,
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "model_call_performed": False,
        "candidate_promotion_authorized": False,
        "packet_promotion_authorized": False,
        "authority_boundaries_preserved": True,
        "provenance": dict(review["provenance"]),
        "runtime_rule_packet_draft": {
            "packet_family_id": family,
            "source_failure_id": source_failure_id,
            "candidate_id": candidate_id,
            "failure_pattern": "allowed_files boundary treated as exclusive authority",
            "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
            "allowed_claim": PACKET_JSON_CONTRACT["allowed_claim"],
            "source_allowed_claim": source_allowed_claim,
            "held_actions": held_actions,
            "evidence_boundary": review["evidence_boundary"],
            "json_contract": dict(PACKET_JSON_CONTRACT),
            "review_status": "held_for_packet_review",
            "required_next_step": "supervised_runtime_rule_packet_review",
        },
        "notes": [
            "Independent packet drafting is model-free.",
            "The packet draft remains held for supervised packet review.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
            "This packet does not create or install a runtime rule.",
        ],
    }
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# LARQL Packet From Intake Candidate Join Smoke",
        "",
        f"Packet status: `{packet['packet_status']}`",
        f"Required next step: `{packet['required_next_step']}`",
        "",
        f"Source candidate review: `{packet['source_candidate_review_path']}`",
        f"Source failure id: `{packet['source_failure_id']}`",
        f"Candidate id: `{packet['candidate_id']}`",
        f"Proposed rule family id: `{packet['proposed_rule_family_id']}`",
        f"Upstream intake/candidate allowed claim preserved separately: `{packet['source_allowed_claim']}`",
        "",
        "## What this join smoke proves",
        "",
        "- a reviewed candidate can be converted into a held runtime-rule packet draft;",
        "- the packet draft can preserve provenance and explicit authority boundaries;",
        "- the next step can be returned as supervised runtime-rule packet review;",
        "- the completed registry remains unchanged.",
        "",
        "This is supervised guided capability, not autonomous repo authority and not general intelligence.",
        "",
        "## What this join smoke does not prove",
        "",
        "- it does not create or install a runtime rule;",
        "- it does not approve the packet;",
        "- it does not run a probe;",
        "- it does not solve arbitrary messy input generally.",
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
        "## JSON contract",
        "",
        "```json",
        json.dumps(PACKET_JSON_CONTRACT, indent=2, sort_keys=True),
        "```",
        "",
        "## Notes",
        "",
        *[f"- {note}" for note in packet["notes"]],
        "",
        "## Next step",
        "",
        "Subject the packet draft to supervised runtime-rule packet review before any install-boundary movement.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_packet(review_path: Path, run_id: str, out_root: Path) -> dict[str, Any]:
    review = load_review(review_path)
    packet = build_packet(review, review_path)
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "larql_runtime_rule_packet_draft.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "larql_runtime_rule_packet_draft.md").write_text(render_markdown(packet), encoding="utf-8")
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_packet(args.review, args.run_id, args.out_root)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
