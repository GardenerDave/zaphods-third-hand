"""Draft a model-free LARQL runtime install packet.

This helper consumes a validated LARQL rule artifact and validation report and
writes an inert runtime-install packet. It does not install the rule into
durable memory, train LoRA, mutate model weights, or promote the candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_runtime_install_packet.v0"
PACKET_STATUS = "packet_only"
PACKET_VERDICT = "ready_for_runtime_install_review"
ALLOWED_NEXT_STEP = "review_larql_runtime_install_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"

OUTPUT_FILES = ("larql_runtime_install_packet.json", "larql_runtime_install_packet.md")


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


def build_checks(rule: dict[str, Any], validation: dict[str, Any], rule_checks: dict[str, bool], validation_checks: dict[str, bool]) -> dict[str, bool]:
    checks = {}
    checks.update(rule_checks)
    checks.update(validation_checks)
    payload = validation if isinstance(validation, dict) else {}
    checks.update(
        {
            "rule_report_type_ok": rule.get("report_type") == "affordance_larql_rule.v0",
            "rule_status_ok": rule.get("rule_status") == "applied_as_bounded_artifact",
            "rule_runtime_installation_status_ok": rule.get("runtime_installation_status") == "not_installed",
            "rule_durable_memory_status_ok": rule.get("durable_memory_status") == "not_written",
            "rule_candidate_promotion_status_ok": rule.get("candidate_promotion_status") == "not_promoted",
            "validation_report_type_ok": payload.get("report_type") == "affordance_larql_rule_validation.v0",
            "validation_verdict_ok": payload.get("validation_verdict") == "larql_rule_artifact_validated",
            "validation_next_step_ok": payload.get("allowed_next_step") == "draft_larql_runtime_install_packet",
            "validation_runtime_installation_authorized_false": payload.get("runtime_installation_authorized") is False,
            "validation_durable_memory_authorized_false": payload.get("durable_memory_authorized") is False,
            "validation_candidate_promotion_authorized_false": payload.get("candidate_promotion_authorized") is False,
            "validation_lora_training_authorized_false": payload.get("lora_training_authorized") is False,
            "candidate_id_matches": rule.get("candidate_id") == payload.get("candidate_id"),
            "source_failure_id_matches": rule.get("source_failure_id") == payload.get("source_failure_id"),
            "rule_id_matches": rule.get("rule_id") == payload.get("rule_id"),
            "candidate_digest_matches": rule.get("candidate_digest") == payload.get("candidate_digest"),
        }
    )
    return checks


def packet_ready(checks: dict[str, bool]) -> bool:
    required = [
        "rule_exists",
        "rule_parses",
        "validation_exists",
        "validation_parses",
        "rule_report_type_ok",
        "rule_status_ok",
        "rule_runtime_installation_status_ok",
        "rule_durable_memory_status_ok",
        "rule_candidate_promotion_status_ok",
        "validation_report_type_ok",
        "validation_verdict_ok",
        "validation_next_step_ok",
        "validation_runtime_installation_authorized_false",
        "validation_durable_memory_authorized_false",
        "validation_candidate_promotion_authorized_false",
        "validation_lora_training_authorized_false",
        "candidate_id_matches",
        "source_failure_id_matches",
        "rule_id_matches",
        "candidate_digest_matches",
    ]
    return all(checks.get(name, False) for name in required)


def disallowed_actions() -> list[str]:
    return [
        "install_runtime_rule",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_rule_artifact",
        "modify_validation_report",
        "commit_or_push",
    ]


def build_packet(rule: dict[str, Any], validation: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    verdict = PACKET_VERDICT if packet_ready(checks) else "invalid_input"
    return {
        "report_type": REPORT_TYPE,
        "packet_status": PACKET_STATUS,
        "packet_verdict": verdict,
        "allowed_next_step": ALLOWED_NEXT_STEP if verdict == PACKET_VERDICT else "repair_larql_runtime_install_packet_inputs",
        "rule_id": rule.get("rule_id"),
        "candidate_id": rule.get("candidate_id"),
        "source_failure_id": rule.get("source_failure_id"),
        "candidate_digest": rule.get("candidate_digest"),
        "runtime_installation_authorized": False,
        "durable_memory_authorized": False,
        "candidate_promotion_authorized": False,
        "lora_training_authorized": False,
        "proposed_runtime_action": "install_rule_for_runtime_consultation_only",
        "rule_payload": rule,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
        "notes": [
            "Packet only; runtime rule is not installed.",
            "Durable memory is not written.",
            "Candidate is not promoted.",
            "LoRA is not trained.",
        ],
    }


def render_markdown(packet: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Runtime Install Packet v0",
            "",
            f"Candidate id: `{packet.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{packet.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{packet.get('rule_id') or 'unknown'}`",
            f"Packet verdict: `{packet['packet_verdict']}`",
            f"Allowed next step: `{packet['allowed_next_step']}`",
            "",
            "This is packet only.",
            "The runtime rule is not installed.",
            "Durable memory is not written.",
            "The candidate is not promoted.",
            "LoRA is not trained.",
            "The next step is runtime install packet review.",
        ]
    )


def write_reports(rule_path: Path, validation_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rule, rule_checks, rule_notes = read_json_object(rule_path, "rule")
    validation, validation_checks, validation_notes = read_json_object(validation_path, "validation")
    checks = build_checks(rule, validation, rule_checks, validation_checks)
    packet = build_packet(rule, validation, checks)
    packet["notes"] = [
        *rule_notes,
        *validation_notes,
        *packet["notes"],
    ]
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(packet) + "\n", encoding="utf-8")
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rule", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.rule, args.validation, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
