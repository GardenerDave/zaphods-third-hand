#!/usr/bin/env python3
"""Write a reviewed LARQL training candidate as a local artifact only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PACKET_TYPE = "affordance_larql_training_candidate_packet.v0"
REVIEW_TYPE = "affordance_larql_training_candidate_review.v0"
CANDIDATE_TYPE = "affordance_larql_training_candidate_artifact.v0"
WRITE_RECORD_TYPE = "affordance_larql_training_candidate_write_record.v0"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def approval_text_ok(text: str) -> bool:
    lowered = text.lower()
    return all(
        phrase in lowered
        for phrase in (
            "approve writing",
            "local candidate artifact only",
            "do not train",
            "promote",
            "write durable memory",
            "mutate weights",
            "modify runtime rules",
        )
    )


def same_identity(packet: dict[str, Any], review: dict[str, Any], key: str) -> bool:
    return bool(packet.get(key)) and packet.get(key) == review.get(key)


def build_candidate_artifact(packet: dict[str, Any], review: dict[str, Any], approval_text: str) -> dict[str, Any]:
    preview = packet.get("training_candidate_preview") or {}

    return {
        "report_type": CANDIDATE_TYPE,
        "candidate_status": "local_candidate_artifact_only",
        "candidate_id": packet.get("candidate_id", ""),
        "source_failure_id": packet.get("source_failure_id", ""),
        "rule_id": packet.get("rule_id", ""),
        "candidate_digest": packet.get("candidate_digest", ""),
        "response_sha256": packet.get("response_sha256", ""),
        "format": preview.get("format", ""),
        "training_example_preview": {
            "messages": [
                {
                    "role": "system",
                    "content": preview.get("local_context_instruction", ""),
                },
                {
                    "role": "user",
                    "content": preview.get("input", ""),
                },
                {
                    "role": "assistant",
                    "content": preview.get("expected_response", ""),
                },
            ],
            "positive_requirements": preview.get("positive_requirements", []),
            "negative_requirements": preview.get("negative_requirements", []),
        },
        "evidence": preview.get("evidence", {}),
        "approval": {
            "approval_scope": "write_local_candidate_artifact_only",
            "approval_text": approval_text,
            "training_candidate_write_authorized": True,
        },
        "training_candidate_written": True,
        "training_dataset_written": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "candidate_promoted": False,
        "runtime_rule_modified": False,
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
    }


def build_write_record(
    packet: dict[str, Any],
    review: dict[str, Any],
    approval_text: str,
    candidate_path: str,
) -> dict[str, Any]:
    checks = {
        "approval_text_ok": approval_text_ok(approval_text),
        "packet_report_type_ok": packet.get("report_type") == PACKET_TYPE,
        "packet_status_ok": packet.get("packet_status") == "packet_only",
        "packet_verdict_ok": packet.get("packet_verdict") == "ready_for_larql_training_candidate_review",
        "packet_next_step_ok": packet.get("allowed_next_step") == "review_larql_training_candidate_packet",
        "packet_training_candidate_written_false": packet.get("training_candidate_written") is False,
        "packet_durable_memory_authorized_false": packet.get("durable_memory_authorized") is False,
        "packet_lora_training_authorized_false": packet.get("lora_training_authorized") is False,
        "packet_model_weight_mutation_authorized_false": packet.get("model_weight_mutation_authorized") is False,
        "packet_candidate_promotion_authorized_false": packet.get("candidate_promotion_authorized") is False,
        "review_report_type_ok": review.get("report_type") == REVIEW_TYPE,
        "review_status_ok": review.get("review_status") == "review_only",
        "review_verdict_ok": review.get("review_verdict") == "approved_for_larql_training_candidate_opt_in_boundary",
        "review_next_step_ok": review.get("allowed_next_step") == "request_explicit_larql_training_candidate_write_approval",
        "review_training_candidate_write_authorized_false": review.get("training_candidate_write_authorized") is False,
        "review_training_candidate_written_false": review.get("training_candidate_written") is False,
        "review_durable_memory_authorized_false": review.get("durable_memory_authorized") is False,
        "review_lora_training_authorized_false": review.get("lora_training_authorized") is False,
        "review_model_weight_mutation_authorized_false": review.get("model_weight_mutation_authorized") is False,
        "review_candidate_promotion_authorized_false": review.get("candidate_promotion_authorized") is False,
        "candidate_id_consistent": same_identity(packet, review, "candidate_id"),
        "source_failure_id_consistent": same_identity(packet, review, "source_failure_id"),
        "rule_id_consistent": same_identity(packet, review, "rule_id"),
        "candidate_digest_consistent": same_identity(packet, review, "candidate_digest"),
        "response_sha256_consistent": same_identity(packet, review, "response_sha256"),
        "candidate_path_present": bool(candidate_path),
    }

    ok = all(checks.values())

    return {
        "report_type": WRITE_RECORD_TYPE,
        "write_status": "completed" if ok else "rejected",
        "write_verdict": (
            "larql_training_candidate_local_artifact_written"
            if ok
            else "larql_training_candidate_local_artifact_write_rejected"
        ),
        "allowed_next_step": (
            "review_written_larql_training_candidate_artifact"
            if ok
            else "repair_larql_training_candidate_write_inputs"
        ),
        "candidate_id": packet.get("candidate_id", ""),
        "source_failure_id": packet.get("source_failure_id", ""),
        "rule_id": packet.get("rule_id", ""),
        "candidate_digest": packet.get("candidate_digest", ""),
        "response_sha256": packet.get("response_sha256", ""),
        "candidate_artifact_path": candidate_path if ok else "",
        "checks": checks,
        "approval_scope": "write_local_candidate_artifact_only",
        "training_candidate_write_authorized": ok,
        "training_candidate_written": ok,
        "training_dataset_written": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "candidate_promoted": False,
        "runtime_rule_modified": False,
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "disallowed_actions": [
            "call_model",
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
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--approval-text", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    packet = read_json(args.packet)
    review = read_json(args.review)

    candidate_path = args.out / "larql_training_candidate_artifact.json"
    record_path = args.out / "larql_training_candidate_write_record.json"

    record = build_write_record(packet, review, args.approval_text, str(candidate_path))
    if record["write_verdict"] == "larql_training_candidate_local_artifact_written":
        candidate = build_candidate_artifact(packet, review, args.approval_text)
        write_json(candidate_path, candidate)

    write_json(record_path, record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
