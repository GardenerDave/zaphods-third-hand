#!/usr/bin/env python3
"""Install the reviewed absence-of-evidence runtime rule as a local artifact.

This installs only a local runtime-rule artifact under .work. It does not call
a model, write training data, write dataset artifacts, write durable memory,
promote a candidate, train LoRA, mutate model weights, or perform automatic
failure-to-curriculum capture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_absence_of_evidence_runtime_rule_install.v0"
INSTALL_STATUS = "local_runtime_rule_artifact_install_only"
INSTALL_VERDICT = "local_runtime_rule_artifact_installed"
ALLOWED_NEXT_STEP = "draft_absence_of_evidence_runtime_consultation_probe"
OUTPUT_FILENAMES = (
    "runtime_rule_install_record.json",
    "runtime_rule_install_record.md",
)
RULE_FILENAME = "absence_of_evidence_file_authority_v0.json"


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def approval_text_is_safe(text: str) -> bool:
    lowered = text.lower()
    required = [
        "i approve installing the reviewed absence-of-evidence larql runtime rule as a local runtime rule artifact only",
        "do not call a model",
        "write training data",
        "write dataset artifacts",
        "write durable memory",
        "promote a candidate",
        "mutate model weights",
        "automatic failure-to-curriculum capture",
        "train lora",
    ]
    return all(item in lowered for item in required)


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


def packet_review_ready(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "packet_report_type_ok",
        "packet_status_ok",
        "packet_verdict_ok",
        "packet_next_step_ok",
        "packet_runtime_rule_status_ok",
        "review_exists",
        "review_parses",
        "review_report_type_ok",
        "review_status_ok",
        "review_verdict_ok",
        "review_next_step_ok",
        "review_runtime_rule_status_ok",
        "review_runtime_rule_install_authorized_false",
        "review_runtime_rule_modification_authorized_false",
        "review_candidate_promotion_authorized_false",
        "review_durable_memory_authorized_false",
        "review_lora_training_authorized_false",
        "review_model_weight_mutation_authorized_false",
        "packet_no_auto_capture",
        "packet_runtime_rule_modification_authorized_false",
        "packet_candidate_promotion_authorized_false",
        "packet_durable_memory_authorized_false",
        "packet_lora_training_authorized_false",
        "packet_model_weight_mutation_authorized_false",
        "ids_match",
        "approval_text_present",
        "approval_text_safe",
        "draft_safe",
    ]
    return all(checks.get(name, False) for name in required)


def build_runtime_rule(
    packet: dict[str, Any],
    review: dict[str, Any],
    approval_text: str,
    packet_path: Path,
    review_path: Path,
) -> dict[str, Any]:
    draft = packet["absence_of_evidence_runtime_rule_draft"]
    return {
        "report_type": "affordance_larql_runtime_rule.v0",
        "rule_id": packet["rule_id"],
        "source_failure_id": packet["source_failure_id"],
        "candidate_id": packet["candidate_id"],
        "runtime_rule_status": "installed_local_runtime_rule_artifact",
        "installation_scope": "local_runtime_rule_artifact_only",
        "purpose": draft["purpose"],
        "applies_when": draft["applies_when"],
        "blocks_or_warns_on": draft["blocks_or_warns_on"],
        "required_response_behavior": draft["required_response_behavior"],
        "required_inspection_examples": draft["required_inspection_examples"],
        "provenance": {
            "runtime_rule_packet_path": str(packet_path),
            "runtime_rule_review_path": str(review_path),
            "explicit_user_approval_captured": True,
            "approval_text_sha256": sha256_text(approval_text),
        },
    }


def build_install_record(packet: dict[str, Any], review: dict[str, Any], runtime_rule_path: Path, approval_text: str, checks: dict[str, bool]) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "install_status": INSTALL_STATUS,
        "install_verdict": INSTALL_VERDICT,
        "allowed_next_step": ALLOWED_NEXT_STEP,
        "source_failure_id": packet["source_failure_id"],
        "candidate_id": packet["candidate_id"],
        "rule_id": packet["rule_id"],
        "runtime_rule_status": "installed_local_runtime_rule_artifact",
        "runtime_rule_artifact_path": str(runtime_rule_path),
        "runtime_rule_install_authorized": True,
        "runtime_rule_modification_authorized": False,
        "candidate_promotion_authorized": False,
        "durable_memory_written": False,
        "training_data_written": False,
        "dataset_artifact_written": False,
        "model_call_performed": False,
        "model_weights_mutated": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "approval_basis": "explicit_user_approval",
        "approval_text_sha256": sha256_text(approval_text),
        "checks": checks,
        "disallowed_actions": [
            "write_training_data",
            "write_dataset_artifact",
            "write_durable_memory",
            "promote_candidate",
            "train_lora_adapter",
            "mutate_model_weights",
            "automatic_failure_to_curriculum_capture",
            "modify_runtime_rule",
            "call_model",
        ],
    }


def render_markdown(record: dict[str, Any], runtime_rule: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Absence-of-Evidence Runtime Rule Install Record",
            "",
            f"Source failure id: `{record['source_failure_id']}`",
            f"Candidate id: `{record['candidate_id']}`",
            f"Rule id: `{record['rule_id']}`",
            f"Install verdict: `{record['install_verdict']}`",
            f"Allowed next step: `{record['allowed_next_step']}`",
            "",
            "This is a local runtime rule artifact install only.",
            "The runtime rule is installed for consultation only.",
            "No durable memory is written.",
            "No candidate is promoted.",
            "No LoRA is trained.",
            "No model weights are mutated.",
            "No training data is written.",
            "No dataset artifacts are written.",
            "No model call is performed.",
            "Automatic failure-to-curriculum capture is not authorized.",
            "",
            "## Installed runtime rule",
            "",
            f"- Rule id: `{runtime_rule['rule_id']}`",
            f"- Status: `{runtime_rule['runtime_rule_status']}`",
            f"- Installation scope: `{runtime_rule['installation_scope']}`",
            f"- Purpose: {runtime_rule['purpose']}",
            "- Applies when: evidence is incomplete, stale, file-limited, search-limited, otherwise bounded, or when search results do not cover the full target scope.",
            "- Blocks or warns on: claims of absence from missing evidence alone and irreversible lifecycle/file actions from missing search results alone.",
            "- Required response behavior: state the evidence boundary, distinguish not found from does not exist, and recommend targeted inspection or review.",
        ]
    )


def write_reports(packet_path: Path, review_path: Path, approval_text: str, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    review, review_checks, review_notes = read_json_object(review_path, "review")

    draft = packet.get("absence_of_evidence_runtime_rule_draft") if isinstance(packet, dict) else {}
    if not isinstance(draft, dict):
        draft = {}

    approval_text_present = isinstance(approval_text, str) and bool(approval_text.strip())
    checks = {
        **packet_checks,
        **review_checks,
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_absence_of_evidence_runtime_rule_packet.v0",
        "packet_status_ok": packet.get("packet_status") == "runtime_rule_packet_only",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_absence_of_evidence_runtime_rule_review",
        "packet_next_step_ok": packet.get("allowed_next_step") == "review_absence_of_evidence_runtime_rule_packet",
        "packet_runtime_rule_status_ok": packet.get("runtime_rule_status") == "draft_not_installed",
        "review_report_type_ok": review.get("report_type") == "affordance_larql_absence_of_evidence_runtime_rule_review.v0",
        "review_status_ok": review.get("review_status") == "runtime_rule_review_only",
        "review_verdict_ok": review.get("review_verdict") == "approved_for_absence_of_evidence_runtime_rule_install_approval_boundary",
        "review_next_step_ok": review.get("allowed_next_step") == "hold_for_explicit_absence_of_evidence_runtime_rule_install_approval",
        "review_runtime_rule_status_ok": review.get("runtime_rule_status") == "reviewed_not_installed",
        "review_runtime_rule_install_authorized_false": review.get("runtime_rule_install_authorized") is False,
        "review_runtime_rule_modification_authorized_false": review.get("runtime_rule_modification_authorized") is False,
        "review_candidate_promotion_authorized_false": review.get("candidate_promotion_authorized") is False,
        "review_durable_memory_authorized_false": review.get("durable_memory_authorized") is False,
        "review_lora_training_authorized_false": review.get("lora_training_authorized") is False,
        "review_model_weight_mutation_authorized_false": review.get("model_weight_mutation_authorized") is False,
        "packet_runtime_rule_modification_authorized_false": packet.get("runtime_rule_modification_authorized") is False,
        "packet_candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized") is False,
        "packet_durable_memory_authorized_false": packet.get("durable_memory_authorized") is False,
        "packet_lora_training_authorized_false": packet.get("lora_training_authorized") is False,
        "packet_model_weight_mutation_authorized_false": packet.get("model_weight_mutation_authorized") is False,
        "packet_no_auto_capture": packet.get("no_auto_capture") is True,
        "ids_match": (
            packet.get("source_failure_id") == "absence_of_evidence_file_authority.real"
            and review.get("source_failure_id") == packet.get("source_failure_id")
            and review.get("candidate_id") == packet.get("candidate_id")
            and review.get("rule_id") == packet.get("rule_id")
        ),
        "approval_text_present": approval_text_present,
        "approval_text_safe": approval_text_is_safe(approval_text or ""),
        "draft_safe": draft_is_safe(draft),
    }
    runtime_rule = build_runtime_rule(packet, review, approval_text, packet_path, review_path)
    ready = packet_review_ready(checks)
    runtime_rule_path = out_dir / "runtime_rules" / RULE_FILENAME
    record = build_install_record(packet, review, runtime_rule_path, approval_text, checks)
    record["install_verdict"] = INSTALL_VERDICT if ready else "absence_of_evidence_runtime_rule_install_rejected"
    record["allowed_next_step"] = ALLOWED_NEXT_STEP if ready else "repair_or_reverify_absence_of_evidence_runtime_rule_install_inputs"
    record["runtime_rule_install_authorized"] = True if ready else False
    out_dir.mkdir(parents=True, exist_ok=True)
    if ready:
        runtime_rule_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_rule_path.write_text(json.dumps(runtime_rule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        record_path = out_dir / OUTPUT_FILENAMES[0]
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out_dir / OUTPUT_FILENAMES[1]).write_text(render_markdown(record, runtime_rule) + "\n", encoding="utf-8")
    else:
        (out_dir / OUTPUT_FILENAMES[0]).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out_dir / OUTPUT_FILENAMES[1]).write_text(render_markdown(record, runtime_rule) + "\n", encoding="utf-8")
    record["notes"] = [*packet_notes, *review_notes, "Local runtime rule artifact install only."]
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--approval-text", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.packet, args.review, args.approval_text, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
