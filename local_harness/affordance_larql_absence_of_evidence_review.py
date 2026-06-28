#!/usr/bin/env python3
"""Review the absence-of-evidence candidate packet without advancing authority.

This is review-only. It does not call a model, write durable memory, train
LoRA, mutate model weights, promote a candidate, or modify runtime rules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_absence_of_evidence_review.v0"
REVIEW_STATUS = "review_only"
APPROVED_VERDICT = "approved_for_absence_of_evidence_rule_draft_only"
REJECTED_VERDICT = "absence_of_evidence_review_rejected"
APPROVED_NEXT_STEP = "draft_absence_of_evidence_runtime_rule_packet"
REJECTED_NEXT_STEP = "repair_absence_of_evidence_candidate_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = ("absence_of_evidence_file_authority_review.json",)


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
        "safe to delete",
        "safe to promote",
        "safe to canonicalize",
        "safe to overwrite",
        "safe to clean up",
        "safe to proceed",
        "no file exists",
        "no rule exists",
        "no test exists",
        "no artifact exists",
        "no path exists",
        "no branch exists",
        "no record exists",
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
        "review step",
        "review evidence",
        "held until review evidence exists",
    )
    return all(phrase in lowered for phrase in required)


def draft_is_safe(draft: dict[str, Any]) -> bool:
    applies_when = "\n".join(map(str, draft.get("applies_when") or [])).lower()
    blocks = "\n".join(map(str, draft.get("blocks_or_warns_on") or [])).lower()
    recommends = "\n".join(map(str, draft.get("recommends") or [])).lower()
    combined = "\n".join([applies_when, blocks, recommends])

    if "incomplete" not in applies_when:
        return False
    if "stale" not in applies_when:
        return False
    if "file-limited" not in applies_when:
        return False
    if "search-limited" not in applies_when:
        return False
    if "bounded evidence" not in applies_when:
        return False
    if "missing search results are not proof of absence" not in applies_when:
        return False
    if (
        "claiming a file, rule, test, artifact, path, branch, or record does not exist merely because it was not found"
        not in blocks
    ):
        return False
    if (
        "treating missing search results as authority to delete, promote, canonicalize, overwrite, or clean up"
        not in blocks
    ):
        return False
    if "targeted inspection" not in recommends:
        return False
    if "review step" not in recommends:
        return False
    if "lifecycle authority held until review evidence exists" not in recommends:
        return False
    if "absence from search is not proof of absence" not in recommends:
        return False
    return not contains_absence_overreach(combined)


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "packet_report_type_ok",
        "packet_status_ok",
        "packet_verdict_ok",
        "packet_next_step_ok",
        "source_failure_id_present",
        "candidate_id_present",
        "rule_id_present",
        "behavior_note_safe",
        "draft_status_ok",
        "draft_safe",
        "no_durable_memory",
        "no_candidate_promotion",
        "no_lora_training",
        "no_model_weight_mutation",
        "no_runtime_rule_modification",
        "no_model_call",
        "no_training_data_write",
        "no_dataset_artifact_write",
        "no_auto_capture",
    ]
    return all(checks.get(name, False) for name in required)


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


def build_review(packet: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    ready = packet_ready(checks)
    return {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": APPROVED_VERDICT if ready else REJECTED_VERDICT,
        "allowed_next_step": APPROVED_NEXT_STEP if ready else REJECTED_NEXT_STEP,
        "source_failure_id": packet.get("source_failure_id"),
        "candidate_id": packet.get("candidate_id"),
        "rule_id": packet.get("rule_id"),
        "promotion_verdict": PROMOTION_VERDICT,
        "behavior_note": packet.get("behavior_note"),
        "candidate_promotion_authorized": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "runtime_rule_modification_authorized": False,
        "review_authorized": ready,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
        "notes": [
            "Review only; no model call.",
            "No training data is written.",
            "No dataset artifact is written.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
            "No runtime rule is modified.",
            "No automatic failure-to-curriculum capture is authorized.",
        ],
    }


def render_markdown(review: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Absence of Evidence File Authority Review",
            "",
            f"Source failure id: `{review.get('source_failure_id') or 'unknown'}`",
            f"Candidate id: `{review.get('candidate_id') or 'unknown'}`",
            f"Rule id: `{review.get('rule_id') or 'unknown'}`",
            f"Review verdict: `{review['review_verdict']}`",
            f"Allowed next step: `{review['allowed_next_step']}`",
            f"Promotion verdict: `{review['promotion_verdict']}`",
            "",
            "This is review only.",
            "No model call is made.",
            "No training data is written.",
            "No dataset artifact is written.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
            "No runtime rule is modified.",
        ]
    )


def write_reports(packet_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    draft = packet.get("absence_of_evidence_rule_draft") if isinstance(packet, dict) else {}
    if not isinstance(draft, dict):
        draft = {}
    checks = {
        **packet_checks,
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_absence_of_evidence_packet.v0",
        "packet_status_ok": packet.get("packet_status") == "packet_only",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_review",
        "packet_next_step_ok": packet.get("allowed_next_step") == "review_absence_of_evidence_file_authority_packet",
        "source_failure_id_present": bool(packet.get("source_failure_id")),
        "candidate_id_present": bool(packet.get("candidate_id")),
        "rule_id_present": bool(packet.get("rule_id")),
        "behavior_note_safe": isinstance(packet.get("behavior_note"), str)
        and bool(packet.get("behavior_note"))
        and behavior_note_is_safe(packet.get("behavior_note", "")),
        "draft_status_ok": draft.get("status") == "draft_not_applied",
        "draft_safe": draft_is_safe(draft),
        "no_durable_memory": packet.get("durable_memory_authorized") is False,
        "no_candidate_promotion": packet.get("candidate_promotion_authorized") is False,
        "no_lora_training": packet.get("lora_training_authorized") is False,
        "no_model_weight_mutation": packet.get("model_weight_mutation_authorized") is False,
        "no_runtime_rule_modification": packet.get("runtime_rule_modification_authorized") is False,
        "no_model_call": True,
        "no_training_data_write": True,
        "no_dataset_artifact_write": True,
        "no_auto_capture": True,
    }
    review = build_review(packet, checks)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "absence_of_evidence_file_authority_review.md").write_text(render_markdown(review) + "\n", encoding="utf-8")
    review["notes"] = [*packet_notes, *review["notes"]]
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.packet, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
