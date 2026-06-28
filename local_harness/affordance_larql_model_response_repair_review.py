"""Review a LARQL model response repair packet without applying it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_model_response_repair_review.v0"
REVIEW_STATUS = "review_only"
APPROVAL_VERDICT = "approved_for_larql_model_response_repair_application_only"
REJECTION_VERDICT = "larql_model_response_repair_review_rejected"
APPROVAL_NEXT_STEP = "apply_larql_model_response_repair"
REJECTION_NEXT_STEP = "repair_or_rewrite_larql_model_response_repair_packet"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = ("larql_model_response_repair_review.json", "larql_model_response_repair_review.md")

ALLOWED_FILES = {
    "local_harness/affordance_larql_model_context_packet.py",
    "local_harness/affordance_larql_model_response_review.py",
}


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


def repair_ready(packet: dict[str, Any]) -> bool:
    return all(
        [
            packet.get("report_type") == "affordance_larql_model_response_repair_packet.v0",
            packet.get("packet_status") == "packet_only",
            packet.get("packet_verdict") == "ready_for_larql_model_response_repair_review",
            packet.get("allowed_next_step") == "review_larql_model_response_repair_packet",
            bool(packet.get("candidate_id")),
            bool(packet.get("candidate_digest")),
            bool(packet.get("rule_id")),
            bool(packet.get("source_failure_id")),
            packet.get("durable_memory_authorized") is False,
            packet.get("candidate_promotion_authorized") is False,
            packet.get("lora_training_authorized") is False,
            packet.get("model_weight_mutation_authorized") is False,
            tuple(packet.get("allowed_files") or ()) == (
                "local_harness/affordance_larql_model_context_packet.py",
                "local_harness/affordance_larql_model_response_review.py",
            ),
        ]
    )


def proposed_repairs_ok(packet: dict[str, Any]) -> bool:
    repairs = packet.get("proposed_repairs") or []
    if len(repairs) != 2:
        return False
    if any(not isinstance(rep, dict) for rep in repairs):
        return False
    by_target = {rep.get("target_file"): rep for rep in repairs}
    if set(by_target) != ALLOWED_FILES:
        return False
    context = "\n".join(by_target["local_harness/affordance_larql_model_context_packet.py"].get("required_changes") or []).lower()
    review = "\n".join(by_target["local_harness/affordance_larql_model_response_review.py"].get("required_changes") or []).lower()
    return all(
        [
            "lm studio openai-compatible endpoint" in context,
            "openai inference api" in context,
            "hugging face inference api" in context,
            "generic cloud" in context,
            "host/profile/gpu/endpoint/digest evidence" in context,
            "reverify if host, gpu, driver, profile, endpoint, or digest evidence changes" in context,
            "cloud-based service" in review,
            "compatible gpu" in review,
            "pytorch with a compatible gpu" in review,
            "endpoint/path drift" in review,
        ]
    )


def build_checks(packet: dict[str, Any]) -> dict[str, bool]:
    return {
        "packet_report_type_ok": packet.get("report_type") == "affordance_larql_model_response_repair_packet.v0",
        "packet_status_ok": packet.get("packet_status") == "packet_only",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_larql_model_response_repair_review",
        "packet_next_step_ok": packet.get("allowed_next_step") == "review_larql_model_response_repair_packet",
        "candidate_id_present": bool(packet.get("candidate_id")),
        "candidate_digest_present": bool(packet.get("candidate_digest")),
        "rule_id_present": bool(packet.get("rule_id")),
        "source_failure_id_present": bool(packet.get("source_failure_id")),
        "allowed_files_exact": tuple(packet.get("allowed_files") or ()) == (
            "local_harness/affordance_larql_model_context_packet.py",
            "local_harness/affordance_larql_model_response_review.py",
        ),
        "repair_targets_exact": set((item or {}).get("target_file") for item in (packet.get("proposed_repairs") or []) if isinstance(item, dict))
        == ALLOWED_FILES,
        "proposed_repairs_ok": proposed_repairs_ok(packet),
        "durable_memory_authorized_false": packet.get("durable_memory_authorized") is False,
        "candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized") is False,
        "lora_training_authorized_false": packet.get("lora_training_authorized") is False,
        "model_weight_mutation_authorized_false": packet.get("model_weight_mutation_authorized") is False,
    }


def review_ready_to_approve(checks: dict[str, bool]) -> bool:
    required = [
        "packet_exists",
        "packet_parses",
        "packet_report_type_ok",
        "packet_status_ok",
        "packet_verdict_ok",
        "packet_next_step_ok",
        "candidate_id_present",
        "candidate_digest_present",
        "rule_id_present",
        "source_failure_id_present",
        "allowed_files_exact",
        "repair_targets_exact",
        "proposed_repairs_ok",
        "durable_memory_authorized_false",
        "candidate_promotion_authorized_false",
        "lora_training_authorized_false",
        "model_weight_mutation_authorized_false",
    ]
    return all(checks.get(name, False) for name in required)


def disallowed_actions() -> list[str]:
    return [
        "call_model",
        "apply_repair",
        "write_durable_memory",
        "promote_candidate",
        "train_lora_adapter",
        "mutate_model_weights",
        "modify_runtime_rule",
        "commit_or_push",
    ]


def build_report(packet: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    approved = review_ready_to_approve(checks)
    return {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": APPROVAL_VERDICT if approved else REJECTION_VERDICT,
        "allowed_next_step": APPROVAL_NEXT_STEP if approved else REJECTION_NEXT_STEP,
        "candidate_id": packet.get("candidate_id"),
        "source_failure_id": packet.get("source_failure_id"),
        "rule_id": packet.get("rule_id"),
        "candidate_digest": packet.get("candidate_digest"),
        "repair_application_authorized": bool(approved),
        "durable_memory_authorized": False,
        "candidate_promotion_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "promotion_verdict": PROMOTION_VERDICT,
        "checks": checks,
        "disallowed_actions": disallowed_actions(),
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Model Response Repair Review v0",
            "",
            f"Candidate id: `{report.get('candidate_id') or 'unknown'}`",
            f"Source failure id: `{report.get('source_failure_id') or 'unknown'}`",
            f"Rule id: `{report.get('rule_id') or 'unknown'}`",
            f"Review verdict: `{report['review_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            "",
            "This is review evidence only.",
            "No repair is applied.",
            "No durable memory is written.",
            "No candidate promotion is granted.",
            "No LoRA training is authorized.",
            "No model weights are mutated.",
        ]
    )


def write_reports(packet_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    packet, packet_checks, packet_notes = read_json_object(packet_path, "packet")
    checks = {**build_checks(packet), **packet_checks}
    report = build_report(packet, checks)
    if report["review_verdict"] in {APPROVAL_VERDICT, REJECTION_VERDICT}:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(report) + "\n", encoding="utf-8")
        report["notes"] = packet_notes
    return report


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
