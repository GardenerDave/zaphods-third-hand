#!/usr/bin/env python3
"""Review the full LARQL intake-to-install-boundary chain as one bounded proof artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_PACKET_CLAIM = "only listed files are authorized targets"


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def require(value: Any, message: str) -> Any:
    if value is None or value == "":
        raise ValueError(message)
    return value


def validate_chain(intake_candidate: dict[str, Any], intake_review: dict[str, Any], candidate_draft: dict[str, Any], candidate_review: dict[str, Any], packet_draft: dict[str, Any], packet_review: dict[str, Any]) -> None:
    source_failure_id = require(intake_candidate.get("source_failure_id"), "missing intake candidate source_failure_id")
    candidate_id = require(intake_candidate.get("candidate_id"), "missing intake candidate candidate_id")
    rule_family = require(intake_candidate.get("proposed_rule_family_id"), "missing intake candidate proposed_rule_family_id")
    provenance = intake_candidate.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("intake candidate provenance must be a JSON object")
    require(provenance.get("source_note_path"), "missing intake candidate provenance.source_note_path")
    require(provenance.get("source_note_sha256"), "missing intake candidate provenance.source_note_sha256")

    # Stage coherence
    if intake_review.get("source_failure_id") != source_failure_id:
        raise ValueError("mismatched source_failure_id between intake candidate and intake review")
    if intake_review.get("candidate_id") != candidate_id:
        raise ValueError("mismatched candidate_id between intake candidate and intake review")
    if intake_review.get("proposed_rule_family_id") != rule_family:
        raise ValueError("mismatched proposed_rule_family_id between intake candidate and intake review")
    if intake_review.get("provenance", {}).get("source_note_path") != provenance.get("source_note_path"):
        raise ValueError("mismatched provenance.source_note_path between intake candidate and intake review")
    if intake_review.get("provenance", {}).get("source_note_sha256") != provenance.get("source_note_sha256"):
        raise ValueError("mismatched provenance.source_note_sha256 between intake candidate and intake review")
    if intake_review.get("allowed_claim") != intake_candidate.get("allowed_claim"):
        raise ValueError("mismatched allowed_claim between intake candidate and intake review")
    if intake_review.get("required_next_step") != "draft_larql_candidate_from_reviewed_intake":
        raise ValueError("unexpected intake review required_next_step")

    if candidate_draft.get("source_failure_id") != source_failure_id:
        raise ValueError("mismatched source_failure_id between intake candidate and candidate draft")
    if candidate_draft.get("candidate_id") != candidate_id:
        raise ValueError("mismatched candidate_id between intake candidate and candidate draft")
    if candidate_draft.get("proposed_rule_family_id") != rule_family:
        raise ValueError("mismatched proposed_rule_family_id between intake candidate and candidate draft")
    if candidate_draft.get("provenance", {}).get("source_note_path") != provenance.get("source_note_path"):
        raise ValueError("mismatched provenance.source_note_path between intake candidate and candidate draft")
    if candidate_draft.get("provenance", {}).get("source_note_sha256") != provenance.get("source_note_sha256"):
        raise ValueError("mismatched provenance.source_note_sha256 between intake candidate and candidate draft")
    if candidate_draft.get("allowed_claim") != intake_review.get("allowed_claim"):
        raise ValueError("mismatched allowed_claim between candidate draft and intake review")
    if candidate_draft.get("required_next_step") != "supervised_candidate_review":
        raise ValueError("unexpected candidate draft required_next_step")

    if candidate_review.get("source_failure_id") != source_failure_id:
        raise ValueError("mismatched source_failure_id between candidate draft and candidate review")
    if candidate_review.get("candidate_id") != candidate_id:
        raise ValueError("mismatched candidate_id between candidate draft and candidate review")
    if candidate_review.get("proposed_rule_family_id") != rule_family:
        raise ValueError("mismatched proposed_rule_family_id between candidate draft and candidate review")
    if candidate_review.get("provenance", {}).get("source_note_path") != provenance.get("source_note_path"):
        raise ValueError("mismatched provenance.source_note_path between candidate draft and candidate review")
    if candidate_review.get("provenance", {}).get("source_note_sha256") != provenance.get("source_note_sha256"):
        raise ValueError("mismatched provenance.source_note_sha256 between candidate draft and candidate review")
    if candidate_review.get("reviewed_candidate", {}).get("review_verdict") != "accepted_for_runtime_rule_packet_drafting":
        raise ValueError("unexpected candidate review verdict")

    if packet_draft.get("source_failure_id") != source_failure_id:
        raise ValueError("mismatched source_failure_id between candidate review and packet draft")
    if packet_draft.get("candidate_id") != candidate_id:
        raise ValueError("mismatched candidate_id between candidate review and packet draft")
    if packet_draft.get("proposed_rule_family_id") != rule_family:
        raise ValueError("mismatched proposed_rule_family_id between candidate review and packet draft")
    if packet_draft.get("source_allowed_claim") != intake_candidate.get("allowed_claim"):
        raise ValueError("mismatched source_allowed_claim on packet draft")
    if packet_draft.get("allowed_claim") != ALLOWED_PACKET_CLAIM:
        raise ValueError("unexpected packet draft allowed_claim")
    if packet_draft.get("required_next_step") != "supervised_runtime_rule_packet_review":
        raise ValueError("unexpected packet draft required_next_step")
    if packet_draft.get("registry_promotion_authorized") is not False:
        raise ValueError("packet draft registry promotion must remain false")
    if packet_draft.get("runtime_rule_creation_authorized") is not False:
        raise ValueError("packet draft runtime rule creation must remain false")
    if packet_draft.get("runtime_rule_install_authorized") is not False:
        raise ValueError("packet draft runtime rule install must remain false")
    if packet_draft.get("model_call_performed") is not False:
        raise ValueError("packet draft model call must remain false")
    if packet_draft.get("candidate_promotion_authorized") is not False:
        raise ValueError("packet draft candidate promotion must remain false")
    if packet_draft.get("packet_promotion_authorized") is not False:
        raise ValueError("packet draft packet promotion must remain false")
    if packet_draft.get("authority_boundaries_preserved") is not True:
        raise ValueError("packet draft authority boundaries must be preserved")
    packet_provenance = packet_draft.get("provenance")
    if not isinstance(packet_provenance, dict):
        raise ValueError("packet draft provenance must be a JSON object")
    if packet_provenance.get("source_note_path") != provenance.get("source_note_path"):
        raise ValueError("mismatched provenance.source_note_path on packet draft")
    if packet_provenance.get("source_note_sha256") != provenance.get("source_note_sha256"):
        raise ValueError("mismatched provenance.source_note_sha256 on packet draft")
    draft = packet_draft.get("runtime_rule_packet_draft")
    if not isinstance(draft, dict):
        raise ValueError("runtime_rule_packet_draft must be a JSON object")
    if draft.get("review_status") != "held_for_packet_review":
        raise ValueError("packet draft review_status must be held_for_packet_review")
    if draft.get("allowed_claim") != ALLOWED_PACKET_CLAIM:
        raise ValueError("packet draft allowed_claim must match packet claim")
    if draft.get("source_allowed_claim") != intake_candidate.get("allowed_claim"):
        raise ValueError("packet draft source_allowed_claim must preserve upstream claim")
    if draft.get("json_contract", {}).get("allowed_claim") != ALLOWED_PACKET_CLAIM:
        raise ValueError("packet draft json_contract.allowed_claim must match packet claim")
    if draft.get("json_contract", {}).get("outside_file_modification_authorized") is not False:
        raise ValueError("packet draft json_contract.outside_file_modification_authorized must be false")
    if draft.get("json_contract", {}).get("required_next_step") != "request explicit scope expansion or review":
        raise ValueError("packet draft json_contract.required_next_step must match contract")
    if packet_review.get("source_failure_id") != source_failure_id:
        raise ValueError("mismatched source_failure_id between packet draft and packet review")
    if packet_review.get("candidate_id") != candidate_id:
        raise ValueError("mismatched candidate_id between packet draft and packet review")
    if packet_review.get("proposed_rule_family_id") != rule_family:
        raise ValueError("mismatched proposed_rule_family_id between packet draft and packet review")
    if packet_review.get("allowed_claim") != ALLOWED_PACKET_CLAIM:
        raise ValueError("unexpected packet review allowed_claim")
    if packet_review.get("source_allowed_claim") != intake_candidate.get("allowed_claim"):
        raise ValueError("packet review must preserve upstream claim separately")
    if packet_review.get("required_next_step") != "explicit_local_install_boundary_review":
        raise ValueError("unexpected packet review required_next_step")
    if packet_review.get("install_authorized") is not False:
        raise ValueError("packet review install authorization must remain false")
    if packet_review.get("registry_promotion_authorized") is not False:
        raise ValueError("packet review registry promotion must remain false")
    if packet_review.get("runtime_rule_creation_authorized") is not False:
        raise ValueError("packet review runtime rule creation must remain false")
    if packet_review.get("runtime_rule_install_authorized") is not False:
        raise ValueError("packet review runtime rule install must remain false")
    if packet_review.get("model_call_performed") is not False:
        raise ValueError("packet review model call must remain false")
    if packet_review.get("candidate_promotion_authorized") is not False:
        raise ValueError("packet review candidate promotion must remain false")
    if packet_review.get("packet_promotion_authorized") is not False:
        raise ValueError("packet review packet promotion must remain false")
    if packet_review.get("authority_boundaries_preserved") is not True:
        raise ValueError("packet review authority boundaries must be preserved")
    packet_review_provenance = packet_review.get("provenance")
    if not isinstance(packet_review_provenance, dict):
        raise ValueError("packet review provenance must be a JSON object")
    if packet_review_provenance.get("source_note_path") != provenance.get("source_note_path"):
        raise ValueError("mismatched provenance.source_note_path on packet review")
    if packet_review_provenance.get("source_note_sha256") != provenance.get("source_note_sha256"):
        raise ValueError("mismatched provenance.source_note_sha256 on packet review")
    reviewed = packet_review.get("reviewed_packet")
    if not isinstance(reviewed, dict):
        raise ValueError("reviewed_packet must be a JSON object")
    if reviewed.get("review_verdict") != "held_at_install_boundary":
        raise ValueError("unexpected reviewed_packet review_verdict")
    if reviewed.get("required_next_step") != "explicit_local_install_boundary_review":
        raise ValueError("unexpected reviewed_packet required_next_step")
    if reviewed.get("allowed_claim") != ALLOWED_PACKET_CLAIM:
        raise ValueError("reviewed_packet allowed_claim must match packet claim")
    if reviewed.get("source_allowed_claim") != intake_candidate.get("allowed_claim"):
        raise ValueError("reviewed_packet must preserve upstream claim separately")
    if reviewed.get("json_contract", {}).get("allowed_claim") != ALLOWED_PACKET_CLAIM:
        raise ValueError("reviewed_packet json_contract.allowed_claim must match packet claim")
    if reviewed.get("json_contract", {}).get("outside_file_modification_authorized") is not False:
        raise ValueError("reviewed_packet json_contract.outside_file_modification_authorized must be false")
    if reviewed.get("install_authorized") is not False:
        raise ValueError("reviewed_packet install_authorized must remain false")


def summarize_stage(name: str, payload: dict[str, Any], status_fields: list[str]) -> dict[str, Any]:
    summary = {"stage": name}
    for key in status_fields:
        if key in payload:
            summary[key] = payload[key]
    for key in ("source_failure_id", "candidate_id", "proposed_rule_family_id"):
        if key in payload:
            summary[key] = payload[key]
    if "allowed_claim" in payload:
        summary["allowed_claim"] = payload["allowed_claim"]
    if "source_allowed_claim" in payload:
        summary["source_allowed_claim"] = payload["source_allowed_claim"]
    if "required_next_step" in payload:
        summary["required_next_step"] = payload["required_next_step"]
    if "review_status" in payload:
        summary["review_status"] = payload["review_status"]
    if "candidate_status" in payload:
        summary["candidate_status"] = payload["candidate_status"]
    if "packet_status" in payload:
        summary["packet_status"] = payload["packet_status"]
    return summary


def build_review(
    intake_candidate: dict[str, Any],
    intake_review: dict[str, Any],
    candidate_draft: dict[str, Any],
    candidate_review: dict[str, Any],
    packet_draft: dict[str, Any],
    packet_review: dict[str, Any],
) -> dict[str, Any]:
    validate_chain(intake_candidate, intake_review, candidate_draft, candidate_review, packet_draft, packet_review)
    source_failure_id = intake_candidate["source_failure_id"]
    candidate_id = intake_candidate["candidate_id"]
    rule_family = intake_candidate["proposed_rule_family_id"]
    provenance = dict(intake_candidate["provenance"])
    stages = [
        summarize_stage("intake_candidate", intake_candidate, ["candidate_status"]),
        summarize_stage("intake_review", intake_review, ["review_status"]),
        summarize_stage("candidate_draft", candidate_draft, ["candidate_status"]),
        summarize_stage("candidate_review", candidate_review, ["review_status"]),
        summarize_stage("packet_draft", packet_draft, ["packet_status"]),
        summarize_stage("packet_review", packet_review, ["review_status", "install_authorized"]),
    ]
    return {
        "report_type": "larql_intake_to_install_boundary_chain_review.v0",
        "review_status": "chain_reviewed_install_boundary_hold",
        "review_scope": "intake-to-install-boundary smoke chain only",
        "chain_status": "held_at_install_boundary",
        "source_failure_id": source_failure_id,
        "candidate_id": candidate_id,
        "proposed_rule_family_id": rule_family,
        "stage_count": 6,
        "stages": stages,
        "packet_allowed_claim": ALLOWED_PACKET_CLAIM,
        "source_allowed_claim": intake_candidate["allowed_claim"],
        "final_required_next_step": "explicit_local_install_boundary_review",
        "install_authorized": False,
        "registry_promotion_authorized": False,
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "model_call_performed": False,
        "candidate_promotion_authorized": False,
        "packet_promotion_authorized": False,
        "authority_boundaries_preserved": True,
        "provenance": provenance,
        "proof_claims": [
            "one synthetic noisy note was reduced into a held candidate scaffold",
            "the held candidate scaffold moved through model-free review gates",
            "the reviewed candidate became a held packet draft",
            "the held packet draft reached an install-boundary hold",
            "no registry mutation, runtime-rule creation, runtime-rule install, probe, model call, training data, durable memory, or automatic failure-to-curriculum capture was authorized",
        ],
        "non_claims": [
            "this does not prove arbitrary messy input is solved generally",
            "this does not prove the candidate is correct",
            "this does not prove the runtime rule should be installed",
            "this does not prove the completed registry should change",
            "this does not prove the process is autonomous",
            "this does not prove the system has general intelligence",
        ],
        "notes": [
            "The chain is model-free from intake smoke through install-boundary hold.",
            "The packet-stage allowed claim is distinct from the upstream intake-stage claim.",
            "The completed registry remains unchanged.",
            "No automatic failure-to-curriculum capture was performed.",
        ],
    }


def render_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# LARQL Intake to Install Boundary Chain Review",
        "",
        "Date: 2026-06-29",
        "",
        f"Review status: `{review['review_status']}`",
        f"Chain status: `{review['chain_status']}`",
        f"Final next step: `{review['final_required_next_step']}`",
        "",
        "## What this full-chain review proves",
        "",
        "- one synthetic noisy note can be reduced into a held candidate scaffold;",
        "- the scaffold can move through model-free review gates;",
        "- the reviewed candidate can become a held packet draft;",
        "- the held packet draft can reach an install-boundary hold;",
        "- the completed registry remains unchanged.",
        "",
        "This is supervised guided capability, not autonomous repo authority and not general intelligence.",
        "",
        "## What this full-chain review does not prove",
        "",
        "- it does not prove arbitrary messy input is solved generally;",
        "- it does not prove the candidate is correct;",
        "- it does not prove the runtime rule should be installed;",
        "- it does not prove the completed registry should change;",
        "- it does not prove the process is autonomous;",
        "- it does not prove the system has general intelligence.",
        "",
        "## Why the chain stops at install-boundary hold",
        "",
        "The final packet review records a hold only. It does not authorize install.",
        "",
        "## Why this is not runtime-rule creation or install",
        "",
        "- no runtime rule is created;",
        "- no runtime rule is installed;",
        "- no install authorization is granted;",
        "- no probe is run.",
        "",
        "## Why the completed registry remains unchanged",
        "",
        "The chain is an evidence artifact only. It does not mutate the registry or any completed rule artifact.",
        "",
        "## Why the allowed_claim / source_allowed_claim separation matters",
        "",
        "- `allowed_claim` at the packet stage is the rule claim: `only listed files are authorized targets`;",
        "- `source_allowed_claim` preserves the upstream intake-stage claim separately;",
        "- keeping them distinct prevents intake-language from being mistaken for packet-stage authority.",
        "",
        "## Chain stages",
        "",
        "| Stage | Status / note |",
        "| --- | --- |",
    ]
    for stage in review["stages"]:
        note = stage.get("review_status") or stage.get("candidate_status") or stage.get("packet_status") or ""
        lines.append(f"| {stage['stage']} | {note} |")
    lines.extend(
        [
            "",
            "## Proof claims",
            "",
            *[f"- {claim}" for claim in review["proof_claims"]],
            "",
            "## Non-claims",
            "",
            *[f"- {claim}" for claim in review["non_claims"]],
            "",
            "## Held / not-authorized reminder",
            "",
            "- no model call is made by this driver",
            "- no training data is written",
            "- no dataset artifact is written",
            "- no durable memory is written",
            "- no candidate is promoted",
            "- no packet is promoted",
            "- no install is authorized",
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
            "Stop and review before any install-boundary decision.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_review(
    intake_candidate_path: Path,
    intake_review_path: Path,
    candidate_draft_path: Path,
    candidate_review_path: Path,
    packet_draft_path: Path,
    packet_review_path: Path,
    run_id: str,
    out_root: Path,
) -> dict[str, Any]:
    intake_candidate = load_json_object(intake_candidate_path)
    intake_review = load_json_object(intake_review_path)
    candidate_draft = load_json_object(candidate_draft_path)
    candidate_review = load_json_object(candidate_review_path)
    packet_draft = load_json_object(packet_draft_path)
    packet_review = load_json_object(packet_review_path)
    review = build_review(intake_candidate, intake_review, candidate_draft, candidate_review, packet_draft, packet_review)
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "larql_intake_to_install_boundary_chain_review.json").write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "larql_intake_to_install_boundary_chain_review.md").write_text(render_markdown(review), encoding="utf-8")
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake-candidate", required=True, type=Path)
    parser.add_argument("--intake-review", required=True, type=Path)
    parser.add_argument("--candidate-draft", required=True, type=Path)
    parser.add_argument("--candidate-review", required=True, type=Path)
    parser.add_argument("--packet-draft", required=True, type=Path)
    parser.add_argument("--packet-review", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_review(
            args.intake_candidate,
            args.intake_review,
            args.candidate_draft,
            args.candidate_review,
            args.packet_draft,
            args.packet_review,
            args.run_id,
            args.out_root,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
