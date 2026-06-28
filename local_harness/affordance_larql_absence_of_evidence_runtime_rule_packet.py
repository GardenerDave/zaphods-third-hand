#!/usr/bin/env python3
"""Draft a bounded runtime-rule packet for the absence-of-evidence candidate.

This is packet-only. It does not install a runtime rule, call a model, write
durable memory, train LoRA, mutate model weights, promote a candidate, or
modify a runtime rule.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_absence_of_evidence_runtime_rule_packet.v0"
PACKET_STATUS = "runtime_rule_packet_only"
PACKET_VERDICT = "ready_for_absence_of_evidence_runtime_rule_review"
ALLOWED_NEXT_STEP = "review_absence_of_evidence_runtime_rule_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = (
    "absence_of_evidence_runtime_rule_packet.json",
    "absence_of_evidence_runtime_rule_packet.md",
)


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


def behavior_note_is_safe(note: str) -> bool:
    lowered = note.lower()
    required = (
        "absence from search is not proof of absence" in lowered,
        "targeted inspection" in lowered,
        "review evidence" in lowered,
        "held until review evidence exists" in lowered,
    )
    forbidden = (
        "safe to delete" in lowered,
        "safe to promote" in lowered,
        "safe to canonicalize" in lowered,
        "safe to overwrite" in lowered,
        "safe to clean up" in lowered,
        "does not exist merely because it was not found" in lowered,
    )
    return all(required) and not any(forbidden)


def draft_is_safe(draft: dict[str, Any]) -> bool:
    applies_when = "\n".join(map(str, draft.get("applies_when") or [])).lower()
    blocks = "\n".join(map(str, draft.get("blocks_or_warns_on") or [])).lower()
    required_response_behavior = "\n".join(map(str, draft.get("required_response_behavior") or [])).lower()
    inspection_examples = "\n".join(map(str, draft.get("required_inspection_examples") or [])).lower()

    required = (
        "incomplete" in applies_when,
        "stale" in applies_when,
        "file-limited" in applies_when,
        "search-limited" in applies_when,
        "otherwise bounded" in applies_when,
        "search results do not cover the full target scope" in applies_when,
        "claiming a file, rule, test, artifact, path, branch, or record does not exist merely because it was not found"
        in blocks,
        "delete" in blocks,
        "promot" in blocks,
        "canonicalize" in blocks,
        "overwrite" in blocks,
        "clean up" in blocks,
        "irreversible state changes" in blocks,
        "state the evidence boundary explicitly" in required_response_behavior,
        "distinguish not found in searched scope from does not exist" in required_response_behavior,
        "recommend targeted inspection or review" in required_response_behavior,
        "keep cleanup deletion promotion canonicalization overwrite held pending review evidence" in required_response_behavior,
        "preserve failed-run or search-boundary evidence where relevant" in required_response_behavior,
        "git status --short" in inspection_examples,
        "find <allowed-root> -maxdepth <n> -type f | sort" in inspection_examples,
        "grep -r \"<target>\" <allowed-root>" in inspection_examples,
        "git ls-files | grep \"<target>\"" in inspection_examples,
        "git branch --all --contains <commit>" in inspection_examples,
        "git log --oneline --all -- <path>" in inspection_examples,
    )
    return all(required)


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "review_exists",
        "review_parses",
        "review_report_type_ok",
        "review_status_ok",
        "review_verdict_ok",
        "review_next_step_ok",
        "source_failure_id_present",
        "candidate_id_present",
        "rule_id_present",
        "review_behavior_note_safe",
        "review_candidate_promotion_authorized_false",
        "review_durable_memory_authorized_false",
        "review_lora_training_authorized_false",
        "review_model_weight_mutation_authorized_false",
        "review_runtime_rule_modification_authorized_false",
        "review_no_model_call",
        "review_no_training_data_write",
        "review_no_dataset_artifact_write",
        "review_no_auto_capture",
        "draft_status_ok",
        "draft_safe",
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
        "install_runtime_rule",
        "commit_or_push",
    ]


def build_packet(review: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    ready = packet_ready(checks)
    draft = build_runtime_rule_draft(review)
    return {
        "report_type": REPORT_TYPE,
        "packet_status": PACKET_STATUS,
        "packet_verdict": PACKET_VERDICT if ready else "absence_of_evidence_runtime_rule_packet_rejected",
        "allowed_next_step": ALLOWED_NEXT_STEP if ready else "repair_or_reverify_absence_of_evidence_runtime_rule_inputs",
        "source_failure_id": review.get("source_failure_id"),
        "candidate_id": review.get("candidate_id"),
        "rule_id": review.get("rule_id"),
        "promotion_verdict": PROMOTION_VERDICT,
        "runtime_rule_status": draft["status"],
        "runtime_rule_modification_authorized": False,
        "candidate_promotion_authorized": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "no_auto_capture": True,
        "absence_of_evidence_runtime_rule_draft": draft,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
}


def build_runtime_rule_draft(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": review.get("rule_id"),
        "status": "draft_not_installed",
        "purpose": "Prevent treating missing or incomplete evidence as authority to assert absence or proceed with irreversible lifecycle/file actions.",
        "applies_when": [
            "evidence is incomplete",
            "evidence is stale",
            "evidence is file-limited",
            "evidence is search-limited",
            "evidence is otherwise bounded",
            "search results do not cover the full target scope",
        ],
        "blocks_or_warns_on": [
            "claiming a file, rule, test, artifact, path, branch, or record does not exist merely because it was not found",
            "treating missing search results as authority to delete",
            "treating missing search results as authority to promote",
            "treating missing search results as authority to canonicalize",
            "treating missing search results as authority to overwrite",
            "treating missing search results as authority to clean up",
            "treating missing search results as authority to proceed with irreversible state changes",
        ],
        "required_response_behavior": [
            "state the evidence boundary explicitly",
            "distinguish not found in searched scope from does not exist",
            "recommend targeted inspection or review",
            "keep cleanup deletion promotion canonicalization overwrite held pending review evidence",
            "preserve failed-run or search-boundary evidence where relevant",
        ],
        "required_inspection_examples": [
            "git status --short",
            "find <allowed-root> -maxdepth <n> -type f | sort",
            "grep -r \"<target>\" <allowed-root>",
            "git ls-files | grep \"<target>\"",
            "git branch --all --contains <commit>",
            "git log --oneline --all -- <path>",
        ],
    }


def render_markdown(packet: dict[str, Any]) -> str:
    draft = packet.get("absence_of_evidence_runtime_rule_draft") or {}
    return "\n".join(
        [
            "# Absence of Evidence Runtime Rule Packet",
            "",
            f"Source failure id: `{packet.get('source_failure_id') or 'unknown'}`",
            f"Candidate id: `{packet.get('candidate_id') or 'unknown'}`",
            f"Rule id: `{packet.get('rule_id') or 'unknown'}`",
            f"Packet verdict: `{packet['packet_verdict']}`",
            f"Allowed next step: `{packet['allowed_next_step']}`",
            f"Runtime rule status: `{packet['runtime_rule_status']}`",
            "",
            "This is packet evidence only.",
            "No runtime rule is installed.",
            "No runtime rule is modified.",
            "No model is called.",
            "No training data is written.",
            "No dataset artifact is written.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
            "",
            "## Drafted runtime rule",
            "",
            f"- Rule id: `{draft.get('rule_id') or 'unknown'}`",
            f"- Status: `{draft.get('status') or 'unknown'}`",
            f"- Purpose: {draft.get('purpose') or 'unknown'}",
            "- Applies when: evidence is incomplete, stale, file-limited, search-limited, or otherwise bounded.",
            "- Blocks or warns on: absence claims from missing evidence alone; unsafe deletion, promotion, canonicalization, overwrite, or cleanup.",
            "- Required response behavior: state the evidence boundary, distinguish not found from does not exist, and recommend targeted inspection or review.",
        ]
    )


def write_reports(review_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    review, review_checks, review_notes = read_json_object(review_path, "review")
    draft = build_runtime_rule_draft(review)
    checks = {
        **review_checks,
        "review_report_type_ok": review.get("report_type") == "affordance_larql_absence_of_evidence_review.v0",
        "review_status_ok": review.get("review_status") == "review_only",
        "review_verdict_ok": review.get("review_verdict") == "approved_for_absence_of_evidence_rule_draft_only",
        "review_next_step_ok": review.get("allowed_next_step") == "draft_absence_of_evidence_runtime_rule_packet",
        "source_failure_id_present": bool(review.get("source_failure_id")),
        "candidate_id_present": bool(review.get("candidate_id")),
        "rule_id_present": bool(review.get("rule_id")),
        "review_behavior_note_safe": behavior_note_is_safe(str(review.get("behavior_note", ""))),
        "review_candidate_promotion_authorized_false": review.get("candidate_promotion_authorized") is False,
        "review_durable_memory_authorized_false": review.get("durable_memory_authorized") is False,
        "review_lora_training_authorized_false": review.get("lora_training_authorized") is False,
        "review_model_weight_mutation_authorized_false": review.get("model_weight_mutation_authorized") is False,
        "review_runtime_rule_modification_authorized_false": review.get("runtime_rule_modification_authorized") is False,
        "review_no_model_call": True,
        "review_no_training_data_write": True,
        "review_no_dataset_artifact_write": True,
        "review_no_auto_capture": True,
        "draft_status_ok": draft.get("status") == "draft_not_installed",
        "draft_safe": draft_is_safe(draft),
    }
    packet = build_packet(review, checks)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(packet) + "\n", encoding="utf-8")
    packet["notes"] = [*review_notes, "Review only; no runtime rule is installed."]
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.review, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
