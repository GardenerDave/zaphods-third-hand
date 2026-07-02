#!/usr/bin/env python3
"""Render a supervised decision record for a correction-aware review packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence


OUTPUT_JSON = "supervised_review_decision_record.json"
OUTPUT_MD = "supervised_review_decision_record.md"
REPORT_TYPE = "correction_aware_supervised_review_decision_record.v1"
ALLOWED_DECISIONS = {
    "accept_as_corrected_output",
    "reject",
    "needs_prompt_revision",
    "needs_validator_revision",
    "needs_human_scope_decision",
}


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def short_excerpt(text: str, limit: int = 320) -> str:
    return " ".join(text.split())[:limit]


def build_decision_record(
    *,
    review_packet: dict[str, Any],
    review_packet_path: Path,
    decision: str,
    reviewer_id: str | None,
    rationale: str | None,
) -> dict[str, Any]:
    if decision not in ALLOWED_DECISIONS:
        raise ValueError("decision must be one of: " + ", ".join(sorted(ALLOWED_DECISIONS)))

    decision_options = list(review_packet.get("review_decision_options") or [])
    decision_is_allowed = decision in decision_options
    decision_record_authority_flags = {
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "delta_written": False,
        "patched_model_materialized": False,
        "promotion_authorized": False,
        "supervised_acceptance_performed": decision == "accept_as_corrected_output",
        "automatic_failure_curriculum_capture_authorized": False,
    }
    source_review_packet_authority_flags = dict(
        review_packet.get("review_packet_authority_flags") or decision_record_authority_flags
    )
    record = {
        "report_type": REPORT_TYPE,
        "source_supervised_review_packet": str(review_packet_path),
        "source_supervised_review_packet_sha256": sha256_path(review_packet_path),
        "source_validation_status": review_packet.get("validation_status"),
        "source_findings": review_packet.get("findings") or [],
        "source_parsed_output": review_packet.get("parsed_output"),
        "decision": decision,
        "decision_options": decision_options,
        "decision_is_allowed": decision_is_allowed,
        "no_auto_promotion": True,
        "no_file_edits": True,
        "packet_level_only": True,
        "decision_record_authority_flags": decision_record_authority_flags,
        "authority_flags": decision_record_authority_flags,
        "source_review_packet_authority_flags": source_review_packet_authority_flags,
        "review_packet_summary": review_packet.get("review_packet_summary"),
        "review_packet_excerpt": short_excerpt(
            json.dumps(review_packet.get("parsed_output"), sort_keys=True, default=str)
        ),
    }
    if reviewer_id is not None:
        record["reviewer_id"] = reviewer_id
    if rationale is not None:
        record["rationale"] = rationale
    return record


def render_markdown(record: dict[str, Any]) -> str:
    lines = [
        "# Correction-Aware Supervised Review Decision Record",
        "",
        "## Sources",
        f"- supervised review packet: `{record['source_supervised_review_packet']}`",
        f"- source sha256: `{record['source_supervised_review_packet_sha256']}`",
        f"- validation status: `{record['source_validation_status']}`",
        "",
        "## Decision",
        f"- decision: `{record['decision']}`",
        f"- decision is allowed: `{record['decision_is_allowed']}`",
        f"- no auto promotion: `{record['no_auto_promotion']}`",
        f"- no file edits: `{record['no_file_edits']}`",
        f"- packet level only: `{record['packet_level_only']}`",
    ]
    if record.get("reviewer_id") is not None:
        lines.append(f"- reviewer id: `{record['reviewer_id']}`")
    if record.get("rationale") is not None:
        lines.append(f"- rationale: {record['rationale']}")
    lines.extend(["", "## Review decision options"])
    lines.extend(f"- {item}" for item in record["decision_options"])
    lines.extend(
        [
            "",
            "## Parsed output",
            f"```json\n{json.dumps(record.get('source_parsed_output'), indent=2, sort_keys=True)}\n```",
            "",
            "## Source findings",
        ]
    )
    findings = record.get("source_findings") or []
    lines.extend(f"- {finding}" for finding in findings) if findings else lines.append("- <none>")
    lines.extend(
        [
            "",
            "## Authority flags",
            "### Decision record authority flags",
        ]
    )
    for key, value in record["decision_record_authority_flags"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "### Source review packet authority flags"])
    for key, value in record["source_review_packet_authority_flags"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Required posture",
            "- this record does not promote outputs",
            "- this record does not edit files",
            "- this record does not train",
            "- this record does not write deltas",
            "- this record does not materialize models",
            "- this record does not capture failures for curriculum",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_decision_record(
    *,
    review_packet_path: Path,
    out_dir: Path,
    decision: str,
    reviewer_id: str | None,
    rationale: str | None,
) -> dict[str, Any]:
    if out_dir.exists():
        raise ValueError(f"output directory already exists: {out_dir}")
    review_packet = load_json(review_packet_path, "supervised review packet")
    if review_packet.get("report_type") != "correction_aware_supervised_review_packet.v1":
        raise ValueError("review packet report_type must be correction_aware_supervised_review_packet.v1")

    record = build_decision_record(
        review_packet=review_packet,
        review_packet_path=review_packet_path,
        decision=decision,
        reviewer_id=reviewer_id,
        rationale=rationale,
    )
    if not record["decision_is_allowed"]:
        raise ValueError("decision must be one of the review packet decision options")

    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / OUTPUT_JSON).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / OUTPUT_MD).write_text(render_markdown(record), encoding="utf-8")
    return record


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a supervised decision record for a correction-aware review packet."
    )
    parser.add_argument("--review-packet", required=True, type=Path)
    parser.add_argument("--decision", required=True, choices=sorted(ALLOWED_DECISIONS))
    parser.add_argument("--reviewer-id")
    parser.add_argument("--rationale")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        write_decision_record(
            review_packet_path=args.review_packet,
            out_dir=args.out_dir,
            decision=args.decision,
            reviewer_id=args.reviewer_id,
            rationale=args.rationale,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
