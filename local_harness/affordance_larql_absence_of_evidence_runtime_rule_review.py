#!/usr/bin/env python3
"""Review the drafted absence-of-evidence runtime-rule packet.

This is review-only. It does not install a runtime rule, call a model, write
durable memory, train LoRA, mutate model weights, promote a candidate, or
modify runtime rules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_absence_of_evidence_runtime_rule_review.v0"
REVIEW_STATUS = "runtime_rule_review_only"
APPROVED_VERDICT = "approved_for_absence_of_evidence_runtime_rule_install_approval_boundary"
REJECTED_VERDICT = "absence_of_evidence_runtime_rule_review_rejected"
APPROVED_NEXT_STEP = "hold_for_explicit_absence_of_evidence_runtime_rule_install_approval"
REJECTED_NEXT_STEP = "repair_or_reverify_absence_of_evidence_runtime_rule_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = (
    "absence_of_evidence_runtime_rule_review.json",
    "absence_of_evidence_runtime_rule_review.md",
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
        "packet_exists",
        "packet_parses",
        "packet_report_type_ok",
        "packet_status_ok",
        "packet_verdict_ok",
        "packet_next_step_ok",
        "source_failure_id_present",
        "candidate_id_present",
        "rule_id_present",
        "runtime_rule_status_ok",
        "runtime_rule_modification_authorized_false",
        "candidate_promotion_authorized_false",
        "durable_memory_authorized_false",
        "lora_training_authorized_false",
        "model_weight_mutation_authorized_false",
        "no_auto_capture",
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
        "runtime_rule_status": "reviewed_not_installed",
        "promotion_verdict": PROMOTION_VERDICT,
        "runtime_rule_install_authorized": False,
        "runtime_rule_modification_authorized": False,
        "candidate_promotion_authorized": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
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
            "No runtime rule is installed.",
            "No automatic failure-to-curriculum capture is authorized.",
        ],
    }


def render_markdown(review: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Absence of Evidence Runtime Rule Review",
            "",
            f"Source failure id: `{review.get('source_failure_id') or 'unknown'}`",
            f"Candidate id: `{review.get('candidate_id') or 'unknown'}`",
            f"Rule id: `{review.get('rule_id') or 'unknown'}`",
            f"Review verdict: `{review['review_verdict']}`",
            f"Allowed next step: `{review['allowed_next_step']}`",
            f"Runtime rule status: `{review['runtime_rule_status']}`",
            "",
            "This is review only.",
            "No model call is made.",
            "No runtime rule is installed.",
            "No runtime rule is modified.",
            "No training data is written.",
            "No dataset artifact is written.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
        ]
    )


def write_reports(packet_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    draft = packet.get("absence_of_evidence_runtime_rule_draft") if isinstance(packet, dict) else {}
    if not isinstance(draft, dict):
        draft = {}
    checks = {
        **packet_checks,
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_absence_of_evidence_runtime_rule_packet.v0",
        "packet_status_ok": packet.get("packet_status") == "runtime_rule_packet_only",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_absence_of_evidence_runtime_rule_review",
        "packet_next_step_ok": packet.get("allowed_next_step") == "review_absence_of_evidence_runtime_rule_packet",
        "source_failure_id_present": bool(packet.get("source_failure_id")),
        "candidate_id_present": bool(packet.get("candidate_id")),
        "rule_id_present": bool(packet.get("rule_id")),
        "runtime_rule_status_ok": packet.get("runtime_rule_status") == "draft_not_installed",
        "runtime_rule_modification_authorized_false": packet.get("runtime_rule_modification_authorized") is False,
        "candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized") is False,
        "durable_memory_authorized_false": packet.get("durable_memory_authorized") is False,
        "lora_training_authorized_false": packet.get("lora_training_authorized") is False,
        "model_weight_mutation_authorized_false": packet.get("model_weight_mutation_authorized") is False,
        "no_auto_capture": packet.get("no_auto_capture") is True,
        "draft_status_ok": draft.get("status") == "draft_not_installed",
        "draft_safe": draft_is_safe(draft),
    }
    review = build_review(packet, checks)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(review) + "\n", encoding="utf-8")
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
