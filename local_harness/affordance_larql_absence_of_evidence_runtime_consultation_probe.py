#!/usr/bin/env python3
"""Draft a runtime consultation probe for the absence-of-evidence runtime rule.

This is consultation-context drafting only. It does not call a model, write
durable memory, write training data, write dataset artifacts, promote a
candidate, train LoRA, mutate model weights, or modify the runtime rule.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_absence_of_evidence_runtime_consultation_probe.v0"
PROBE_STATUS = "runtime_consultation_context_packet_only"
PROBE_VERDICT = "ready_for_absence_of_evidence_model_context_probe"
ALLOWED_NEXT_STEP = "run_absence_of_evidence_model_context_probe"
OUTPUT_FILES = (
    "absence_of_evidence_runtime_consultation_probe.json",
    "absence_of_evidence_runtime_consultation_context.md",
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


def rule_text(rule: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "purpose",
        "applies_when",
        "blocks_or_warns_on",
        "required_response_behavior",
        "required_inspection_examples",
    ):
        value = rule.get(key)
        if isinstance(value, list):
            parts.extend(map(str, value))
        elif value is not None:
            parts.append(str(value))
    return "\n".join(parts).lower()


def rule_is_safe(rule: dict[str, Any]) -> bool:
    text = rule_text(rule)
    required = (
        "incomplete" in text,
        "stale" in text,
        "file-limited" in text,
        "search-limited" in text,
        "otherwise bounded" in text,
        "search results do not cover the full target scope" in text,
        "claiming a file, rule, test, artifact, path, branch, or record does not exist merely because it was not found"
        in text,
        "delete" in text,
        "promot" in text,
        "canonicalize" in text,
        "overwrite" in text,
        "clean up" in text,
        "irreversible state changes" in text,
        "state the evidence boundary explicitly" in text,
        "distinguish not found in searched scope from does not exist" in text,
        "recommend targeted inspection or review" in text,
        "keep cleanup deletion promotion canonicalization overwrite held pending review evidence" in text,
        "preserve failed-run or search-boundary evidence where relevant" in text,
        "git status --short" in text,
        "find <allowed-root> -maxdepth <n> -type f | sort" in text,
        "grep -r \"<target>\" <allowed-root>" in text,
        "git ls-files | grep \"<target>\"" in text,
        "git branch --all --contains <commit>" in text,
        "git log --oneline --all -- <path>" in text,
    )
    return all(required)


def install_record_is_safe(record: dict[str, Any]) -> bool:
    required = (
        record.get("report_type") == "affordance_larql_absence_of_evidence_runtime_rule_install.v0",
        record.get("install_verdict") == "local_runtime_rule_artifact_installed",
        record.get("allowed_next_step") == "draft_absence_of_evidence_runtime_consultation_probe",
        record.get("runtime_rule_status") == "installed_local_runtime_rule_artifact",
        record.get("runtime_rule_install_authorized") is True,
        record.get("runtime_rule_modification_authorized") is False,
        record.get("candidate_promotion_authorized") is False,
        record.get("durable_memory_written") is False,
        record.get("training_data_written") is False,
        record.get("dataset_artifact_written") is False,
        record.get("model_call_performed") is False,
        record.get("model_weights_mutated") is False,
        record.get("automatic_failure_to_curriculum_capture_authorized") is False,
    )
    return all(required)


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "install_exists",
        "install_parses",
        "install_safe",
        "rule_exists",
        "rule_parses",
        "rule_safe",
        "ids_match",
        "no_model_call",
        "no_training_data_write",
        "no_dataset_artifact_write",
        "no_durable_memory_write",
        "no_candidate_promotion",
        "no_runtime_rule_modification",
        "no_model_weights_mutated",
        "no_auto_capture",
    ]
    return all(checks.get(name, False) for name in required)


def build_context_probe(install_record: dict[str, Any], runtime_rule: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    ready = packet_ready(checks)
    context = {
        "active_rule_id": runtime_rule.get("rule_id"),
        "evidence_boundary_summary": [
            "The rule applies only when evidence is incomplete, stale, file-limited, search-limited, otherwise bounded, or when search results do not cover the full target scope.",
            "Absence from searched scope is not proof of nonexistence.",
            "Do not claim a file, rule, test, artifact, path, branch, or record does not exist merely because it was not found.",
            "Do not use missing search results as authority to delete, promote, canonicalize, overwrite, clean up, or proceed with irreversible state changes.",
        ],
        "blocked_claims_actions": [
            "do not claim nonexistence from missing evidence alone",
            "do not delete from search absence alone",
            "do not promote from search absence alone",
            "do not canonicalize from search absence alone",
            "do not overwrite from search absence alone",
            "do not clean up from search absence alone",
            "do not proceed with irreversible state changes from search absence alone",
        ],
        "required_response_behavior": [
            "state the search/evidence boundary explicitly",
            "distinguish not found in searched scope from does not exist",
            "recommend targeted inspection or review",
            "keep cleanup/deletion/promotion/canonicalization/overwrite held pending review evidence",
            "preserve failed-run or search-boundary evidence where relevant",
        ],
        "required_inspection_examples": runtime_rule.get("required_inspection_examples", []),
        "explicit_instructions": [
            "Absence from searched scope is not proof of nonexistence.",
            "Avoid cleanup, deletion, promotion, canonicalization, or overwrite unless review evidence exists.",
            "State the search and evidence boundary before concluding anything.",
        ],
    }
    return {
        "report_type": REPORT_TYPE,
        "probe_status": PROBE_STATUS,
        "probe_verdict": PROBE_VERDICT if ready else "absence_of_evidence_model_context_probe_rejected",
        "allowed_next_step": ALLOWED_NEXT_STEP if ready else "repair_or_reverify_absence_of_evidence_runtime_consultation_inputs",
        "source_failure_id": runtime_rule.get("source_failure_id"),
        "candidate_id": runtime_rule.get("candidate_id"),
        "rule_id": runtime_rule.get("rule_id"),
        "consulted_runtime_rule_status": runtime_rule.get("runtime_rule_status"),
        "context_packet_status": "drafted_not_injected",
        "model_call_performed": False,
        "training_data_written": False,
        "dataset_artifact_written": False,
        "durable_memory_written": False,
        "candidate_promotion_authorized": False,
        "runtime_rule_modification_authorized": False,
        "model_weights_mutated": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "runtime_rule_install_authorized": False,
        "context_packet": context,
        "checks": checks,
    }


def render_markdown(probe: dict[str, Any]) -> str:
    context = probe.get("context_packet") or {}
    lines = [
        "# Absence-of-Evidence Runtime Consultation Probe",
        "",
        f"Source failure id: `{probe.get('source_failure_id') or 'unknown'}`",
        f"Candidate id: `{probe.get('candidate_id') or 'unknown'}`",
        f"Rule id: `{probe.get('rule_id') or 'unknown'}`",
        f"Probe verdict: `{probe['probe_verdict']}`",
        f"Allowed next step: `{probe['allowed_next_step']}`",
        f"Consulted runtime rule status: `{probe['consulted_runtime_rule_status']}`",
        "",
        "This is a drafted consultation context packet only.",
        "No model call is performed.",
        "No runtime rule is modified.",
        "No durable memory is written.",
        "No training data is written.",
        "No dataset artifact is written.",
        "No candidate is promoted.",
        "No LoRA training is authorized.",
        "No model weights are mutated.",
        "Automatic failure-to-curriculum capture is not authorized.",
        "",
        "## Evidence boundary summary",
    ]
    lines.extend(f"- {item}" for item in context.get("evidence_boundary_summary", []))
    lines.extend(
        [
            "",
            "## Required response behavior",
        ]
    )
    lines.extend(f"- {item}" for item in context.get("required_response_behavior", []))
    lines.extend(
        [
            "",
            "## Required inspection examples",
        ]
    )
    lines.extend(f"- `{item}`" for item in context.get("required_inspection_examples", []))
    return "\n".join(lines)


def write_reports(install_record_path: Path, runtime_rule_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    install_record, install_checks, install_notes = read_json_object(install_record_path, "install")
    runtime_rule, rule_checks, rule_notes = read_json_object(runtime_rule_path, "rule")
    checks = {
        **install_checks,
        **rule_checks,
        "install_safe": install_record_is_safe(install_record),
        "rule_safe": rule_is_safe(runtime_rule),
        "ids_match": (
            install_record.get("source_failure_id") == runtime_rule.get("source_failure_id")
            and install_record.get("candidate_id") == runtime_rule.get("candidate_id")
            and install_record.get("rule_id") == runtime_rule.get("rule_id")
        ),
        "no_model_call": install_record.get("model_call_performed") is False,
        "no_training_data_write": install_record.get("training_data_written") is False,
        "no_dataset_artifact_write": install_record.get("dataset_artifact_written") is False,
        "no_durable_memory_write": install_record.get("durable_memory_written") is False,
        "no_candidate_promotion": install_record.get("candidate_promotion_authorized") is False,
        "no_runtime_rule_modification": install_record.get("runtime_rule_modification_authorized") is False,
        "no_model_weights_mutated": install_record.get("model_weights_mutated") is False,
        "no_auto_capture": install_record.get("automatic_failure_to_curriculum_capture_authorized") is False,
    }
    probe = build_context_probe(install_record, runtime_rule, checks)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(probe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(probe) + "\n", encoding="utf-8")
    probe["notes"] = [*install_notes, *rule_notes]
    return probe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-record", required=True, type=Path)
    parser.add_argument("--runtime-rule", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.install_record, args.runtime_rule, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
