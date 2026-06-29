#!/usr/bin/env python3
"""Draft a held LARQL candidate from a reviewed intake artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


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
        "model_call_performed",
        "authority_boundaries_preserved",
        "provenance",
    }
    if review.get("report_type") != "larql_intake_review.v0":
        raise ValueError("unexpected report_type")
    if not required.issubset(review):
        missing = sorted(required - set(review))
        raise ValueError(f"review missing required keys: {', '.join(missing)}")
    if review.get("review_status") != "accepted_for_candidate_drafting":
        raise ValueError("review_status must be accepted_for_candidate_drafting")
    if review.get("review_scope") != "intake candidate scaffold only":
        raise ValueError("unexpected review_scope")
    if review.get("required_next_step") != "draft_larql_candidate_from_reviewed_intake":
        raise ValueError("unexpected required_next_step")
    if review.get("registry_promotion_authorized") is not False:
        raise ValueError("registry promotion must remain false")
    if review.get("runtime_rule_creation_authorized") is not False:
        raise ValueError("runtime rule creation must remain false")
    if review.get("model_call_performed") is not False:
        raise ValueError("model call must remain false")
    if review.get("authority_boundaries_preserved") is not True:
        raise ValueError("authority boundaries must be preserved")
    provenance = review["provenance"]
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be a JSON object")
    if not provenance.get("source_note_path"):
        raise ValueError("missing provenance.source_note_path")
    if not provenance.get("source_note_sha256"):
        raise ValueError("missing provenance.source_note_sha256")


def build_candidate(review: dict[str, Any], review_path: Path) -> dict[str, Any]:
    validate_review(review)
    family = review["proposed_rule_family_id"]
    source_failure_id = review["source_failure_id"]
    candidate_id = review["candidate_id"]
    held_actions = list(review["held_actions"])
    candidate = {
        "report_type": "larql_candidate_from_intake.v0",
        "candidate_status": "held_for_candidate_review",
        "source_review_artifact_path": str(review_path),
        "source_failure_id": source_failure_id,
        "candidate_id": candidate_id,
        "proposed_rule_family_id": family,
        "evidence_boundary": review["evidence_boundary"],
        "allowed_claim": review["allowed_claim"],
        "held_actions": held_actions,
        "required_next_step": "supervised_candidate_review",
        "registry_promotion_authorized": False,
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "model_call_performed": False,
        "candidate_promotion_authorized": False,
        "authority_boundaries_preserved": True,
        "provenance": dict(review["provenance"]),
        "drafted_candidate": {
            "candidate_family_id": family,
            "source_failure_id": source_failure_id,
            "candidate_id": candidate_id,
            "failure_pattern": "allowed_files boundary treated as exclusive authority",
            "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
            "allowed_claim": review["allowed_claim"],
            "held_actions": held_actions,
            "evidence_boundary": review["evidence_boundary"],
            "required_next_step": "supervised_candidate_review",
            "review_status": "held_for_candidate_review",
        },
        "notes": [
            "Independent candidate drafting is model-free.",
            "The drafted candidate remains held for supervised review.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
        ],
    }
    return candidate


def render_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        "# LARQL Candidate From Intake Join Smoke",
        "",
        f"Candidate status: `{candidate['candidate_status']}`",
        f"Required next step: `{candidate['required_next_step']}`",
        "",
        f"Source review artifact: `{candidate['source_review_artifact_path']}`",
        f"Source failure id: `{candidate['source_failure_id']}`",
        f"Candidate id: `{candidate['candidate_id']}`",
        f"Proposed rule family id: `{candidate['proposed_rule_family_id']}`",
        "",
        "## What this join smoke proves",
        "",
        "- a reviewed intake artifact can be converted into a held candidate draft;",
        "- the draft can preserve provenance and explicit authority boundaries;",
        "- the next step can be returned as supervised candidate review;",
        "- the completed registry remains unchanged.",
        "",
        "## What this join smoke does not prove",
        "",
        "- it does not accept the candidate;",
        "- it does not create or install a runtime rule;",
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
        "- no model weights are mutated",
        "- no runtime rules are installed or modified",
        "- no automatic failure-to-curriculum capture is performed",
        "",
        "## Notes",
        "",
        *[f"- {note}" for note in candidate["notes"]],
        "",
        "## Next step",
        "",
        "Subject the drafted candidate to supervised candidate review before any further lifecycle movement.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_candidate(review_path: Path, run_id: str, out_root: Path) -> dict[str, Any]:
    review = load_review(review_path)
    candidate = build_candidate(review, review_path)
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "larql_candidate_draft.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "larql_candidate_draft.md").write_text(render_markdown(candidate), encoding="utf-8")
    return candidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_candidate(args.review, args.run_id, args.out_root)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
