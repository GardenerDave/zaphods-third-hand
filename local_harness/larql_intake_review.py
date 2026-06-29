#!/usr/bin/env python3
"""Review a held LARQL intake smoke candidate without promoting it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_AUTHORITY_BOUNDARIES = {
    "model_call_performed",
    "registry_promotion_authorized",
    "runtime_rule_creation_authorized",
    "runtime_rule_install_authorized",
    "training_data_written",
    "dataset_artifact_written",
    "durable_memory_written",
    "candidate_promotion_authorized",
    "model_weights_mutated",
    "runtime_rule_modification_authorized",
    "automatic_failure_to_curriculum_capture_authorized",
}


def load_candidate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("candidate must be a JSON object")
    return payload


def validate_candidate(candidate: dict[str, Any]) -> None:
    required = {
        "report_type",
        "status",
        "candidate_status",
        "source_failure_id",
        "candidate_id",
        "proposed_rule_family_id",
        "evidence_boundary",
        "allowed_claim",
        "held_actions",
        "required_next_step",
        "provenance",
        "authority_boundaries",
    }
    if candidate.get("report_type") != "larql_intake_smoke.v0":
        raise ValueError("unexpected report_type")
    if not required.issubset(candidate):
        missing = sorted(required - set(candidate))
        raise ValueError(f"candidate missing required keys: {', '.join(missing)}")
    if candidate.get("status") != "held_for_supervised_review":
        raise ValueError("candidate status must be held_for_supervised_review")
    if candidate.get("candidate_status") != "held_for_supervised_review":
        raise ValueError("candidate_status must be held_for_supervised_review")
    provenance = candidate["provenance"]
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be a JSON object")
    if not provenance.get("source_note_path"):
        raise ValueError("missing provenance.source_note_path")
    if not provenance.get("source_note_sha256"):
        raise ValueError("missing provenance.source_note_sha256")
    authority = candidate["authority_boundaries"]
    if not isinstance(authority, dict):
        raise ValueError("authority_boundaries must be a JSON object")
    if not REQUIRED_AUTHORITY_BOUNDARIES.issubset(authority):
        missing = sorted(REQUIRED_AUTHORITY_BOUNDARIES - set(authority))
        raise ValueError(f"authority_boundaries missing required keys: {', '.join(missing)}")
    if any(bool(authority.get(key)) for key in REQUIRED_AUTHORITY_BOUNDARIES):
        raise ValueError("authority boundary must remain false")


def build_review(candidate: dict[str, Any], candidate_path: Path) -> dict[str, Any]:
    validate_candidate(candidate)
    review = {
        "report_type": "larql_intake_review.v0",
        "review_status": "accepted_for_candidate_drafting",
        "review_scope": "intake candidate scaffold only",
        "source_intake_candidate_path": str(candidate_path),
        "source_failure_id": candidate["source_failure_id"],
        "candidate_id": candidate["candidate_id"],
        "proposed_rule_family_id": candidate["proposed_rule_family_id"],
        "evidence_boundary": candidate["evidence_boundary"],
        "allowed_claim": candidate["allowed_claim"],
        "held_actions": list(candidate["held_actions"]),
        "required_next_step": "draft_larql_candidate_from_reviewed_intake",
        "registry_promotion_authorized": False,
        "runtime_rule_creation_authorized": False,
        "model_call_performed": False,
        "authority_boundaries_preserved": True,
        "provenance": dict(candidate["provenance"]),
        "notes": [
            "Independent review is model-free.",
            "The intake scaffold remains held for supervised candidate drafting.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
        ],
    }
    return review


def render_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# LARQL Intake Review Join Smoke",
        "",
        f"Review status: `{review['review_status']}`",
        f"Required next step: `{review['required_next_step']}`",
        "",
        f"Source intake candidate: `{review['source_intake_candidate_path']}`",
        f"Source failure id: `{review['source_failure_id']}`",
        f"Candidate id: `{review['candidate_id']}`",
        f"Proposed rule family id: `{review['proposed_rule_family_id']}`",
        "",
        "## What this join smoke proves",
        "",
        "- a held intake scaffold can be independently reviewed;",
        "- the review can preserve provenance and authority boundaries;",
        "- the next step can be returned as an explicit candidate-drafting handoff;",
        "- the completed registry does not need to change to support this join.",
        "",
        "## What this join smoke does not prove",
        "",
        "- it does not promote the candidate;",
        "- it does not create or install a runtime rule;",
        "- it does not run a probe;",
        "- it does not make the pipeline automatic for arbitrary messy input.",
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
        *[f"- {note}" for note in review["notes"]],
        "",
        "## Next step",
        "",
        "Draft a LARQL candidate from the reviewed intake scaffold, using supervised review to decide whether that candidate should move forward.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_review(candidate_path: Path, run_id: str, out_root: Path) -> dict[str, Any]:
    candidate = load_candidate(candidate_path)
    review = build_review(candidate, candidate_path)
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "larql_intake_review.json").write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "larql_intake_review.md").write_text(render_markdown(review), encoding="utf-8")
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_review(args.candidate, args.run_id, args.out_root)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
