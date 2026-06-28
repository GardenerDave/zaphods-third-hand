#!/usr/bin/env python3
"""Record a reviewed LARQL model-response pass without promoting or training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_model_response_pass_record.v0"
REQUIRED_REVIEW_TYPE = "affordance_larql_model_response_review.v0"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_record(review: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "review_exists": True,
        "review_parses": True,
        "review_report_type_ok": review.get("report_type") == REQUIRED_REVIEW_TYPE,
        "review_verdict_pass": review.get("review_verdict") == "larql_model_response_review_pass",
        "review_next_step_ok": review.get("allowed_next_step") == "record_larql_model_response_pass",
        "cuda_block_pass": review.get("cuda_block_pass") is True,
        "model_semantic_failures_empty": review.get("model_semantic_failures") == [],
        "scorer_false_negatives_empty": review.get("scorer_false_negatives") == [],
        "scorer_false_positives_empty": review.get("scorer_false_positives") == [],
        "candidate_promoted_false": review.get("candidate_promoted") is False,
        "durable_memory_written_false": review.get("durable_memory_written") is False,
        "lora_training_started_false": review.get("lora_training_started") is False,
        "model_weights_mutated_false": review.get("model_weights_mutated") is False,
        "candidate_id_present": bool(review.get("candidate_id")),
        "source_failure_id_present": bool(review.get("source_failure_id")),
        "rule_id_present": bool(review.get("rule_id")),
        "candidate_digest_present": bool(review.get("candidate_digest")),
        "response_sha256_present": bool(review.get("response_sha256")),
    }

    pass_ok = all(checks.values())

    return {
        "report_type": REPORT_TYPE,
        "record_status": "record_only",
        "record_verdict": (
            "larql_model_response_pass_recorded"
            if pass_ok
            else "larql_model_response_pass_record_rejected"
        ),
        "allowed_next_step": (
            "draft_larql_training_candidate_packet"
            if pass_ok
            else "repair_larql_model_response_pass_record_inputs"
        ),
        "candidate_id": review.get("candidate_id", ""),
        "source_failure_id": review.get("source_failure_id", ""),
        "rule_id": review.get("rule_id", ""),
        "candidate_digest": review.get("candidate_digest", ""),
        "response_sha256": review.get("response_sha256", ""),
        "checks": checks,
        "evidence_summary": {
            "model_response_review_passed": review.get("review_verdict") == "larql_model_response_review_pass",
            "cuda_block_pass": review.get("cuda_block_pass") is True,
            "model_semantic_failures": review.get("model_semantic_failures", []),
            "scorer_false_negatives": review.get("scorer_false_negatives", []),
            "scorer_false_positives": review.get("scorer_false_positives", []),
        },
        "candidate_promoted": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "training_candidate_written": False,
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
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    review = read_json(args.review)
    record = build_record(review)
    write_json(args.out / "larql_model_response_pass_record.json", record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
