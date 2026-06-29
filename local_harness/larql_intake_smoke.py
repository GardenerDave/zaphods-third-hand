#!/usr/bin/env python3
"""Build a minimal model-free LARQL intake smoke from one noisy failure note."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_intake_smoke.v0"
OUTPUT_FILE = "larql_intake_smoke_candidate.json"
SOURCE_FAILURE_ID = "synthetic_unsupported_file_target_authority_noisy_note.real"
PROPOSED_RULE_FAMILY_ID = "unsupported_file_target_authority"


def sha256_for_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summarize_note(note_text: str) -> dict[str, Any]:
    lowered = note_text.lower()
    signals: list[str] = []
    if "allowed_files" in lowered or "allowed files" in lowered:
        signals.append("allowed_files_boundary")
    if "docs/roadmap.md" in lowered or "roadmap" in lowered:
        signals.append("requested_target_outside_allowed_files")
    if "while we're here" in lowered or "while here" in lowered:
        signals.append("while_here_cleanup_pressure")
    if "broaden cleanup" in lowered or "broader cleanup" in lowered:
        signals.append("scope_expansion_pressure")
    if "adjacent" in lowered:
        signals.append("adjacent_file_pressure")
    if "generated" in lowered:
        signals.append("generated_file_pressure")
    return {
        "detected_signals": signals,
        "bounded_failure_pattern": "unsupported_file_target_authority",
        "note_summary": "bounded file-target authority failure pattern identified from a noisy note",
    }


def build_smoke(input_path: Path, run_id: str) -> dict[str, Any]:
    note_text = input_path.read_text(encoding="utf-8")
    summary = summarize_note(note_text)
    excerpt = " ".join(note_text.strip().split())[:240]
    return {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "status": "held_for_supervised_review",
        "candidate_status": "held_for_supervised_review",
        "candidate_verdict": "bounded_candidate_scaffold_ready",
        "source_failure_id": SOURCE_FAILURE_ID,
        "candidate_id": f"larql_intake_smoke_{PROPOSED_RULE_FAMILY_ID}_candidate",
        "proposed_rule_family_id": PROPOSED_RULE_FAMILY_ID,
        "evidence_boundary": "single synthetic noisy note only",
        "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
        "held_actions": [
            "promote candidate",
            "modify registry",
            "install runtime rule",
            "run live probe",
            "write training data",
            "write dataset artifact",
            "write durable memory",
            "mutate model weights",
            "modify runtime rules",
            "automatic failure-to-curriculum capture",
        ],
        "required_next_step": "supervised review of the candidate scaffold",
        "registry_promotion_authorized": False,
        "authority_boundaries": {
            "registry_promotion_authorized": False,
            "runtime_rule_creation_authorized": False,
            "runtime_rule_install_authorized": False,
            "model_call_performed": False,
            "training_data_written": False,
            "dataset_artifact_written": False,
            "durable_memory_written": False,
            "candidate_promotion_authorized": False,
            "model_weights_mutated": False,
            "runtime_rule_modification_authorized": False,
            "automatic_failure_to_curriculum_capture_authorized": False,
        },
        "provenance": {
            "source_note_path": str(input_path),
            "source_note_sha256": sha256_for_text(note_text),
            "source_note_excerpt": excerpt,
        },
        "summary": summary,
        "notes": [
            "The smoke only proves that a noisy note can be reduced into a bounded candidate scaffold.",
            "The candidate remains held for supervised review.",
            "Downstream machinery would have structured data to inspect later.",
            "Registry promotion is not authorized.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Noisy source note text file")
    parser.add_argument("--run-id", required=True, help="Smoke run identifier")
    parser.add_argument(
        "--out-root",
        default=Path(".work/larql_intake_smoke"),
        type=Path,
        help="Output root directory under .work",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        out_dir = args.out_root / args.run_id
        write_json(out_dir / OUTPUT_FILE, build_smoke(args.input, args.run_id))
    except (OSError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
