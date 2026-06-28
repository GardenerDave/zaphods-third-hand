#!/usr/bin/env python3
"""Draft a bounded LARQL absence-of-evidence candidate packet.

This is packet-only. It does not call a model, write durable memory, train
LoRA, mutate model weights, promote a candidate, or modify runtime rules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_absence_of_evidence_packet.v0"
PACKET_STATUS = "packet_only"
PACKET_VERDICT = "ready_for_review"
ALLOWED_NEXT_STEP = "review_absence_of_evidence_file_authority_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = ("absence_of_evidence_file_authority_packet.json", "absence_of_evidence_file_authority_packet.md")


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def read_json_object(path: Path, label: str) -> tuple[dict[str, Any], dict[str, bool], list[str]]:
    checks = {f"{label}_exists": path.exists(), f"{label}_parses": False}
    notes: list[str] = []
    if not checks[f"{label}_exists"]:
        notes.append(f"{label} missing: {path}")
        return {}, checks, notes
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        notes.append(f"{label} JSON parse failed: {exc.msg}")
        return {}, checks, notes
    if not isinstance(payload, dict):
        notes.append(f"{label} is not a JSON object.")
        return {}, checks, notes
    checks[f"{label}_parses"] = True
    return payload, checks, notes


def contains_absence_overreach(text: str) -> bool:
    lowered = text.lower()
    phrases = (
        "does not exist because it was not found",
        "does not exist because it wasn't found",
        "safe to delete",
        "safe to promote",
        "safe to canonicalize",
        "safe to overwrite",
        "safe to clean up",
        "safe to proceed",
        "no file exists",
    )
    return any(phrase in lowered for phrase in phrases)


def behavior_note_is_safe(note: str) -> bool:
    lowered = note.lower()
    if contains_absence_overreach(lowered):
        return False
    required = (
        "evidence is bounded",
        "absence from search is not proof of absence",
        "targeted inspection",
        "review evidence",
    )
    return all(phrase in lowered for phrase in required)


def disallowed_actions() -> list[str]:
    return [
        "call_model",
        "write_training_data",
        "write_dataset",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_runtime_rule",
        "commit_or_push",
    ]


def build_packet(source_failure_id: str, candidate_id: str, rule_id: str, behavior_note: str) -> dict[str, Any]:
    ids_present = bool(source_failure_id.strip()) and bool(candidate_id.strip()) and bool(rule_id.strip())
    behavior_safe = behavior_note_is_safe(behavior_note)
    packet_ok = ids_present and behavior_safe
    return {
        "report_type": REPORT_TYPE,
        "packet_status": PACKET_STATUS,
        "packet_verdict": PACKET_VERDICT if packet_ok else "absence_of_evidence_candidate_packet_rejected",
        "allowed_next_step": ALLOWED_NEXT_STEP if packet_ok else "repair_absence_of_evidence_candidate_packet",
        "source_failure_id": source_failure_id,
        "candidate_id": candidate_id,
        "rule_id": rule_id,
        "promotion_verdict": PROMOTION_VERDICT,
        "durable_memory_authorized": False,
        "candidate_promotion_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "runtime_rule_modification_authorized": False,
        "behavior_note": behavior_note,
        "checks": {
            "ids_present": ids_present,
            "behavior_note_safe": behavior_safe,
            "no_model_call": True,
            "no_training_data_write": True,
            "no_dataset_artifact_write": True,
            "no_durable_memory": True,
            "no_candidate_promotion": True,
            "no_lora_training": True,
            "no_model_weight_mutation": True,
            "no_runtime_rule_modification": True,
        },
        "absence_of_evidence_rule_draft": {
            "rule_id": rule_id,
            "status": "draft_not_applied",
            "applies_when": [
                "evidence is incomplete, stale, file-limited, search-limited, or otherwise bounded evidence",
                "search results do not cover the full target scope",
                "missing search results are not proof of absence",
            ],
            "blocks_or_warns_on": [
                "claiming a file, rule, test, artifact, path, branch, or record does not exist merely because it was not found",
                "treating missing search results as authority to delete, promote, canonicalize, overwrite, or clean up",
            ],
            "recommends": [
                "targeted inspection command or review step",
                "absence from search is not proof of absence",
                "keep lifecycle authority held until review evidence exists",
            ],
            "requires_reverify_when": [
                "search scope is incomplete",
                "evidence is stale",
                "evidence boundary is unknown",
            ],
        },
        "disallowed_actions": disallowed_actions(),
    }


def render_markdown(packet: dict[str, Any]) -> str:
    draft = packet.get("absence_of_evidence_rule_draft") or {}
    return "\n".join(
        [
            "# Absence of Evidence File Authority Candidate Packet",
            "",
            f"Source failure id: `{packet.get('source_failure_id') or 'unknown'}`",
            f"Candidate id: `{packet.get('candidate_id') or 'unknown'}`",
            f"Rule id: `{packet.get('rule_id') or 'unknown'}`",
            f"Packet verdict: `{packet['packet_verdict']}`",
            f"Allowed next step: `{packet['allowed_next_step']}`",
            "",
            "This is packet evidence only.",
            "No model is called.",
            "No durable memory is written.",
            "No training data is written.",
            "No dataset artifact is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
            "No runtime rule is modified.",
            "Absence from search is not proof of absence.",
            "",
            "## Rule draft",
            "",
            f"- Rule id: `{draft.get('rule_id') or 'unknown'}`",
            f"- Status: `{draft.get('status') or 'unknown'}`",
            "- Applies when: evidence is incomplete, stale, file-limited, search-limited, or otherwise bounded.",
            "- Blocks or warns on: absence claims from search failure alone; unsafe deletion, promotion, canonicalization, overwrite, or cleanup from absence alone.",
            "- Recommends: targeted inspection and held lifecycle authority until review evidence exists.",
        ]
    )


def write_reports(
    source_failure_id: str,
    candidate_id: str,
    rule_id: str,
    behavior_note: str,
    out_dir: Path,
) -> dict[str, Any]:
    validate_out_dir(out_dir)
    packet = build_packet(source_failure_id, candidate_id, rule_id, behavior_note)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(packet) + "\n", encoding="utf-8")
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-failure-id", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--rule-id", required=True)
    parser.add_argument("--behavior-note", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.source_failure_id, args.candidate_id, args.rule_id, args.behavior_note, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
