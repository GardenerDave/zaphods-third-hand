"""Apply a bounded LARQL runtime installation for consultation only.

This helper consumes a validated runtime-install packet and approved runtime
install review, then writes a runtime-consultation artifact plus install
report. It does not write durable memory, train LoRA, mutate model weights, or
promote the candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_runtime_install_report.v0"
RULE_STATUS = "installed_for_runtime_consultation"
RUNTIME_SCOPE = "consultation_only"
REPORT_STATUS = "completed"
INSTALL_VERDICT = "runtime_rule_installed_for_consultation"
ALLOWED_NEXT_STEP = "validate_larql_runtime_install"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"

RULE_OUTPUT = "runtime_rules/navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json"
OUTPUT_FILES = ("larql_runtime_install_report.json", "larql_runtime_install_report.md")


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


def build_checks(packet: dict[str, Any], review: dict[str, Any], packet_checks: dict[str, bool], review_checks: dict[str, bool]) -> dict[str, bool]:
    checks = {}
    checks.update(packet_checks)
    checks.update(review_checks)
    rule_payload = packet.get("rule_payload")
    if not isinstance(rule_payload, dict):
        rule_payload = {}
    checks.update(
        {
            "packet_report_type_ok": packet.get("report_type") == "affordance_larql_runtime_install_packet.v0",
            "packet_status_ok": packet.get("packet_status") == "packet_only",
            "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_runtime_install_review",
            "packet_next_step_ok": packet.get("allowed_next_step") == "review_larql_runtime_install_packet",
            "packet_rule_payload_present": bool(rule_payload),
            "packet_rule_payload_status_ok": rule_payload.get("rule_status") == "applied_as_bounded_artifact",
            "packet_rule_payload_runtime_status_ok": rule_payload.get("runtime_installation_status")
            == "not_installed",
            "review_report_type_ok": review.get("report_type") == "affordance_larql_runtime_install_review.v0",
            "review_status_ok": review.get("review_status") == "review_only",
            "review_verdict_ok": review.get("review_verdict") == "approved_for_runtime_installation_only",
            "review_next_step_ok": review.get("allowed_next_step")
            == "install_larql_runtime_rule_from_reviewed_packet",
            "review_runtime_installation_authorized_true": review.get("runtime_installation_authorized")
            is True,
            "review_durable_memory_authorized_false": review.get("durable_memory_authorized") is False,
            "review_candidate_promotion_authorized_false": review.get("candidate_promotion_authorized")
            is False,
            "review_lora_training_authorized_false": review.get("lora_training_authorized") is False,
            "review_model_weight_mutation_authorized_false": review.get(
                "model_weight_mutation_authorized"
            )
            is False,
            "candidate_id_matches": packet.get("candidate_id") == review.get("candidate_id"),
            "source_failure_id_matches": packet.get("source_failure_id") == review.get("source_failure_id"),
            "rule_id_matches": packet.get("rule_id") == review.get("rule_id"),
            "candidate_digest_matches": packet.get("candidate_digest") == review.get("candidate_digest"),
        }
    )
    return checks


def install_ready(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "review_exists",
        "review_parses",
        "packet_report_type_ok",
        "packet_status_ok",
        "packet_verdict_ok",
        "packet_next_step_ok",
        "packet_rule_payload_present",
        "packet_rule_payload_status_ok",
        "packet_rule_payload_runtime_status_ok",
        "review_report_type_ok",
        "review_status_ok",
        "review_verdict_ok",
        "review_next_step_ok",
        "review_runtime_installation_authorized_true",
        "review_durable_memory_authorized_false",
        "review_candidate_promotion_authorized_false",
        "review_lora_training_authorized_false",
        "review_model_weight_mutation_authorized_false",
        "candidate_id_matches",
        "source_failure_id_matches",
        "rule_id_matches",
        "candidate_digest_matches",
    ]
    return all(checks.get(name, False) for name in required)


def disallowed_actions() -> list[str]:
    return [
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_packet",
        "modify_review",
        "commit_or_push",
    ]


def installed_rule(rule_payload: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    installed = dict(rule_payload)
    installed["runtime_installation_status"] = RULE_STATUS
    installed["durable_memory_status"] = "not_written"
    installed["candidate_promotion_status"] = "not_promoted"
    installed["runtime_scope"] = RUNTIME_SCOPE
    installed["installed_from_review"] = review.get("review_verdict")
    return installed


def install_report(packet: dict[str, Any], review: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    verdict = INSTALL_VERDICT if install_ready(checks) else "invalid_input"
    return {
        "report_type": REPORT_TYPE,
        "install_status": REPORT_STATUS,
        "install_verdict": verdict,
        "allowed_next_step": ALLOWED_NEXT_STEP if verdict == INSTALL_VERDICT else "repair_larql_runtime_install_inputs",
        "rule_id": packet.get("rule_id"),
        "candidate_id": packet.get("candidate_id"),
        "source_failure_id": packet.get("source_failure_id"),
        "candidate_digest": packet.get("candidate_digest"),
        "promotion_verdict": PROMOTION_VERDICT,
        "runtime_rule_written": verdict == INSTALL_VERDICT,
        "durable_memory_written": False,
        "candidate_promoted": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
        "notes": [
            "Runtime rule installed for consultation only.",
            "Durable memory not written.",
            "Candidate not promoted.",
            "LoRA not trained.",
            "Model weights not mutated.",
        ],
    }


def render_markdown(report: dict[str, Any], rule: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Runtime Install Report v0",
            "",
            f"Candidate id: `{report.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{report.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{report.get('rule_id') or 'unknown'}`",
            f"Install verdict: `{report['install_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            "",
            "This is packet only.",
            "The runtime rule is installed for consultation only.",
            "Durable memory is not written.",
            "The candidate is not promoted.",
            "LoRA is not trained.",
            "Model weights are not mutated.",
            "",
            "## Installed Rule",
            "",
            f"- Rule status: `{rule.get('runtime_installation_status')}`",
            f"- Runtime scope: `{rule.get('runtime_scope')}`",
            f"- Installed from review: `{rule.get('installed_from_review')}`",
        ]
    )


def write_reports(packet_path: Path, review_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    review, review_checks, review_notes = read_json_object(review_path, "review")
    checks = build_checks(packet, review, packet_checks, review_checks)
    rule_payload = packet.get("rule_payload")
    if not isinstance(rule_payload, dict):
        rule_payload = {}
    rule = installed_rule(rule_payload, review)
    report = install_report(packet, review, checks)
    report["notes"] = [
        *packet_notes,
        *review_notes,
        *report["notes"],
    ]
    (out_dir / RULE_OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (out_dir / RULE_OUTPUT).write_text(json.dumps(rule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(report, rule) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.packet, args.review, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
