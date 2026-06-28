#!/usr/bin/env python3
"""Review a LARQL training-candidate packet without writing training data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_training_candidate_review.v0"
PACKET_TYPE = "affordance_larql_training_candidate_packet.v0"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def contains_all_true(checks: dict[str, Any]) -> bool:
    return bool(checks) and all(value is True for value in checks.values())


def preview_has_required_content(preview: dict[str, Any]) -> bool:
    all_text = "\n".join(
        [
            str(preview.get("input", "")),
            str(preview.get("local_context_instruction", "")),
            str(preview.get("expected_response", "")),
            "\n".join(preview.get("positive_requirements", [])),
            "\n".join(preview.get("negative_requirements", [])),
        ]
    ).lower()
    expected_response = str(preview.get("expected_response", "")).lower()

    required_anywhere = (
        "rx580",
        "no_cuda",
        "lm studio openai-compatible endpoint",
        "reverify",
        "do not claim cuda is available",
        "do not recommend installing nvidia cuda",
    )
    required_in_expected_response = (
        "rx580",
        "no_cuda",
        "lm studio openai-compatible endpoint",
        "reverify",
        "do not claim cuda is available",
        "do not recommend installing nvidia cuda",
    )

    return all(phrase in all_text for phrase in required_anywhere) and all(
        phrase in expected_response for phrase in required_in_expected_response
    )


def build_review(packet: dict[str, Any]) -> dict[str, Any]:
    preview = packet.get("training_candidate_preview") or {}
    evidence = preview.get("evidence") or {}

    checks = {
        "packet_report_type_ok": packet.get("report_type") == PACKET_TYPE,
        "packet_status_ok": packet.get("packet_status") == "packet_only",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_larql_training_candidate_review",
        "packet_next_step_ok": packet.get("allowed_next_step") == "review_larql_training_candidate_packet",
        "packet_checks_all_true": contains_all_true(packet.get("checks") or {}),
        "candidate_id_present": bool(packet.get("candidate_id")),
        "source_failure_id_present": bool(packet.get("source_failure_id")),
        "rule_id_present": bool(packet.get("rule_id")),
        "candidate_digest_present": bool(packet.get("candidate_digest")),
        "response_sha256_present": bool(packet.get("response_sha256")),
        "training_candidate_written_false": packet.get("training_candidate_written") is False,
        "durable_memory_authorized_false": packet.get("durable_memory_authorized") is False,
        "lora_training_authorized_false": packet.get("lora_training_authorized") is False,
        "model_weight_mutation_authorized_false": packet.get("model_weight_mutation_authorized") is False,
        "candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized") is False,
        "preview_format_ok": preview.get("format") == "larql_supervised_sft_candidate_preview.v0",
        "preview_input_present": bool(str(preview.get("input", "")).strip()),
        "preview_context_instruction_present": bool(str(preview.get("local_context_instruction", "")).strip()),
        "preview_expected_response_present": bool(str(preview.get("expected_response", "")).strip()),
        "preview_positive_requirements_present": bool(preview.get("positive_requirements")),
        "preview_negative_requirements_present": bool(preview.get("negative_requirements")),
        "preview_required_content_present": preview_has_required_content(preview),
        "evidence_probe_pass": evidence.get("probe_verdict") == "larql_model_response_pass",
        "evidence_review_pass": evidence.get("review_verdict") == "larql_model_response_review_pass",
        "evidence_record_pass": evidence.get("record_verdict") == "larql_model_response_pass_recorded",
        "evidence_cuda_block_pass": evidence.get("cuda_block_pass") is True,
        "evidence_model_semantic_failures_empty": evidence.get("model_semantic_failures") == [],
        "evidence_scorer_false_negatives_empty": evidence.get("scorer_false_negatives") == [],
        "evidence_scorer_false_positives_empty": evidence.get("scorer_false_positives") == [],
    }

    approved = all(checks.values())

    return {
        "report_type": REPORT_TYPE,
        "review_status": "review_only",
        "review_verdict": (
            "approved_for_larql_training_candidate_opt_in_boundary"
            if approved
            else "larql_training_candidate_review_rejected"
        ),
        "allowed_next_step": (
            "request_explicit_larql_training_candidate_write_approval"
            if approved
            else "repair_larql_training_candidate_packet"
        ),
        "candidate_id": packet.get("candidate_id", ""),
        "source_failure_id": packet.get("source_failure_id", ""),
        "rule_id": packet.get("rule_id", ""),
        "candidate_digest": packet.get("candidate_digest", ""),
        "response_sha256": packet.get("response_sha256", ""),
        "checks": checks,
        "training_candidate_write_authorized": False,
        "training_candidate_written": False,
        "durable_memory_authorized": False,
        "lora_training_authorized": False,
        "model_weight_mutation_authorized": False,
        "candidate_promotion_authorized": False,
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "disallowed_actions": [
            "call_model",
            "write_training_data",
            "write_durable_memory",
            "promote_candidate",
            "train_lora_adapter",
            "mutate_model_weights",
            "modify_runtime_rule",
            "commit_or_push",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    review = build_review(read_json(args.packet))
    write_json(args.out / "larql_training_candidate_review.json", review)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
