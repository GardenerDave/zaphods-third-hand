#!/usr/bin/env python3
"""Draft a LARQL training-candidate packet from a recorded model-response pass.

This is packet-only. It does not write durable training data, train LoRA,
mutate model weights, promote candidates, or modify runtime rules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_training_candidate_packet.v0"

PASS_RECORD_TYPE = "affordance_larql_model_response_pass_record.v0"
CONTEXT_PACKET_TYPE = "affordance_larql_model_context_packet.v0"
PROBE_TYPE = "affordance_larql_model_response_probe.v0"
REVIEW_TYPE = "affordance_larql_model_response_review.v0"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    """Hash canonical response text using the probe/review convention."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def same_identity(*items: dict[str, Any], key: str) -> bool:
    values = [item.get(key) for item in items]
    return bool(values[0]) and all(value == values[0] for value in values)


def build_packet(
    pass_record: dict[str, Any],
    context_packet: dict[str, Any],
    probe: dict[str, Any],
    review: dict[str, Any],
    model_response_text: str,
) -> dict[str, Any]:
    response_sha256 = sha256_text(model_response_text)

    checks = {
        "pass_record_report_type_ok": pass_record.get("report_type") == PASS_RECORD_TYPE,
        "pass_record_verdict_ok": pass_record.get("record_verdict") == "larql_model_response_pass_recorded",
        "pass_record_next_step_ok": pass_record.get("allowed_next_step") == "draft_larql_training_candidate_packet",
        "pass_record_training_candidate_written_false": pass_record.get("training_candidate_written") is False,
        "pass_record_candidate_promoted_false": pass_record.get("candidate_promoted") is False,
        "pass_record_durable_memory_written_false": pass_record.get("durable_memory_written") is False,
        "pass_record_lora_training_started_false": pass_record.get("lora_training_started") is False,
        "pass_record_model_weights_mutated_false": pass_record.get("model_weights_mutated") is False,
        "context_packet_report_type_ok": context_packet.get("report_type") == CONTEXT_PACKET_TYPE,
        "context_packet_verdict_ok": context_packet.get("packet_verdict") == "ready_for_larql_model_response_probe",
        "context_packet_next_step_ok": context_packet.get("allowed_next_step") == "run_larql_model_response_probe",
        "context_packet_model_instruction_present": bool(context_packet.get("model_instruction")),
        "context_packet_user_input_present": bool(context_packet.get("user_input")),
        "probe_report_type_ok": probe.get("report_type") == PROBE_TYPE,
        "probe_verdict_pass": probe.get("probe_verdict") == "larql_model_response_pass",
        "probe_next_step_ok": probe.get("allowed_next_step") == "review_larql_model_response_probe",
        "probe_candidate_promoted_false": probe.get("candidate_promoted") is False,
        "probe_durable_memory_written_false": probe.get("durable_memory_written") is False,
        "probe_lora_training_started_false": probe.get("lora_training_started") is False,
        "probe_model_weights_mutated_false": probe.get("model_weights_mutated") is False,
        "review_report_type_ok": review.get("report_type") == REVIEW_TYPE,
        "review_verdict_pass": review.get("review_verdict") == "larql_model_response_review_pass",
        "review_next_step_ok": review.get("allowed_next_step") == "record_larql_model_response_pass",
        "review_cuda_block_pass": review.get("cuda_block_pass") is True,
        "review_model_semantic_failures_empty": review.get("model_semantic_failures") == [],
        "review_scorer_false_negatives_empty": review.get("scorer_false_negatives") == [],
        "review_scorer_false_positives_empty": review.get("scorer_false_positives") == [],
        "review_candidate_promoted_false": review.get("candidate_promoted") is False,
        "review_durable_memory_written_false": review.get("durable_memory_written") is False,
        "review_lora_training_started_false": review.get("lora_training_started") is False,
        "review_model_weights_mutated_false": review.get("model_weights_mutated") is False,
        "candidate_id_consistent": same_identity(pass_record, context_packet, probe, review, key="candidate_id"),
        "source_failure_id_consistent": same_identity(pass_record, context_packet, probe, review, key="source_failure_id"),
        "rule_id_consistent": same_identity(pass_record, context_packet, probe, review, key="rule_id"),
        "candidate_digest_consistent": same_identity(pass_record, context_packet, probe, review, key="candidate_digest"),
        "response_sha256_matches_review": review.get("response_sha256") == response_sha256,
        "response_sha256_matches_probe": probe.get("response_sha256") == response_sha256,
        "response_sha256_matches_pass_record": pass_record.get("response_sha256") == response_sha256,
        "model_response_nonempty": bool(model_response_text.strip()),
    }

    packet_ok = all(checks.values())

    return {
        "report_type": REPORT_TYPE,
        "packet_status": "packet_only",
        "packet_verdict": (
            "ready_for_larql_training_candidate_review"
            if packet_ok
            else "larql_training_candidate_packet_rejected"
        ),
        "allowed_next_step": (
            "review_larql_training_candidate_packet"
            if packet_ok
            else "repair_larql_training_candidate_packet_inputs"
        ),
        "candidate_id": pass_record.get("candidate_id", ""),
        "source_failure_id": pass_record.get("source_failure_id", ""),
        "rule_id": pass_record.get("rule_id", ""),
        "candidate_digest": pass_record.get("candidate_digest", ""),
        "response_sha256": response_sha256,
        "checks": checks,
        "training_candidate_preview": {
            "format": "larql_supervised_sft_candidate_preview.v0",
            "input": context_packet.get("user_input", ""),
            "local_context_instruction": context_packet.get("model_instruction", ""),
            "expected_response": model_response_text,
            "positive_requirements": [
                "Reject NVIDIA CUDA installation on RX580/no_cuda host.",
                "Recommend the LM Studio OpenAI-compatible endpoint.",
                "Scope the recommendation to current host/profile/GPU/endpoint/digest evidence.",
                "Require reverify if host, GPU, driver, profile, endpoint, or digest evidence changes.",
            ],
            "negative_requirements": [
                "Do not claim CUDA is available.",
                "Do not recommend installing NVIDIA CUDA.",
                "Do not recommend OpenAI Inference API as the primary answer.",
                "Do not recommend Hugging Face Inference API as the primary answer.",
                "Do not recommend generic cloud services as the primary answer.",
                "Do not recommend PyTorch with a different compatible GPU as the primary answer.",
                "Do not recommend replacing hardware as the primary answer.",
            ],
            "evidence": {
                "probe_verdict": probe.get("probe_verdict"),
                "review_verdict": review.get("review_verdict"),
                "record_verdict": pass_record.get("record_verdict"),
                "cuda_block_pass": review.get("cuda_block_pass"),
                "model_semantic_failures": review.get("model_semantic_failures", []),
                "scorer_false_negatives": review.get("scorer_false_negatives", []),
                "scorer_false_positives": review.get("scorer_false_positives", []),
            },
        },
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
    parser.add_argument("--pass-record", required=True, type=Path)
    parser.add_argument("--context-packet", required=True, type=Path)
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--model-response", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    packet = build_packet(
        read_json(args.pass_record),
        read_json(args.context_packet),
        read_json(args.probe),
        read_json(args.review),
        args.model_response.read_text(encoding="utf-8"),
    )
    write_json(args.out / "larql_training_candidate_packet.json", packet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
