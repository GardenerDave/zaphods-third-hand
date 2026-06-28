#!/usr/bin/env python3
"""Review a written local LARQL training dataset artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_training_dataset_artifact_review.v0"
WRITE_RECORD_TYPE = "affordance_larql_training_dataset_write_record.v0"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def messages_by_role(row: dict[str, Any]) -> dict[str, str]:
    messages = row.get("messages", [])
    return {
        str(message.get("role", "")): str(message.get("content", ""))
        for message in messages
        if isinstance(message, dict)
    }


def dataset_row_shape_ok(row: dict[str, Any]) -> bool:
    messages = row.get("messages", [])
    metadata = row.get("metadata") or {}
    by_role = messages_by_role(row)

    system = by_role.get("system", "").lower()
    user = by_role.get("user", "").lower()
    assistant = by_role.get("assistant", "").lower()

    return all(
        (
            isinstance(messages, list),
            len(messages) == 3,
            [m.get("role") for m in messages] == ["system", "user", "assistant"],
            metadata.get("format") == "larql_supervised_sft_candidate.v0",
            metadata.get("training_scope") == "local_dataset_artifact_only",
            bool(metadata.get("candidate_id")),
            bool(metadata.get("source_failure_id")),
            bool(metadata.get("rule_id")),
            bool(metadata.get("candidate_digest")),
            bool(metadata.get("response_sha256")),
            "bounded advisory constraint" in system,
            "navigator_desktop" in system,
            "no_cuda" in system,
            "lm studio openai-compatible endpoint" in system,
            "rx580" in user,
            "install nvidia cuda" in user,
            "no, do not install nvidia cuda" in assistant,
            "rx580/no_cuda" in assistant,
            "lm studio openai-compatible endpoint" in assistant,
            "reverify" in assistant,
            "do not claim cuda is available" in assistant,
        )
    )


def metadata_matches_record(row: dict[str, Any], record: dict[str, Any]) -> bool:
    metadata = row.get("metadata") or {}
    return all(
        metadata.get(key) == record.get(key)
        for key in (
            "candidate_id",
            "source_failure_id",
            "rule_id",
            "candidate_digest",
            "response_sha256",
        )
    )


def evidence_ok(row: dict[str, Any]) -> bool:
    evidence = (row.get("metadata") or {}).get("evidence") or {}
    return all(
        (
            evidence.get("probe_verdict") == "larql_model_response_pass",
            evidence.get("review_verdict") == "larql_model_response_review_pass",
            evidence.get("record_verdict") == "larql_model_response_pass_recorded",
            evidence.get("cuda_block_pass") is True,
            evidence.get("model_semantic_failures") == [],
            evidence.get("scorer_false_negatives") == [],
            evidence.get("scorer_false_positives") == [],
        )
    )


def build_review(write_record: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    row = rows[0] if rows else {}

    checks = {
        "write_record_report_type_ok": write_record.get("report_type") == WRITE_RECORD_TYPE,
        "write_record_status_completed": write_record.get("write_status") == "completed",
        "write_record_verdict_ok": write_record.get("write_verdict") == "larql_training_dataset_local_artifact_written",
        "write_record_next_step_ok": write_record.get("allowed_next_step") == "review_written_larql_training_dataset_artifact",
        "write_record_training_dataset_write_authorized_true": write_record.get("training_dataset_write_authorized") is True,
        "write_record_training_dataset_written_true": write_record.get("training_dataset_written") is True,
        "write_record_durable_memory_written_false": write_record.get("durable_memory_written") is False,
        "write_record_lora_training_started_false": write_record.get("lora_training_started") is False,
        "write_record_model_weights_mutated_false": write_record.get("model_weights_mutated") is False,
        "write_record_candidate_promoted_false": write_record.get("candidate_promoted") is False,
        "write_record_runtime_rule_modified_false": write_record.get("runtime_rule_modified") is False,
        "dataset_rows_present": bool(rows),
        "dataset_row_count_matches_record": len(rows) == write_record.get("dataset_rows_written"),
        "dataset_single_row_for_candidate": len(rows) == 1,
        "dataset_row_shape_ok": dataset_row_shape_ok(row),
        "dataset_metadata_matches_record": metadata_matches_record(row, write_record),
        "dataset_evidence_ok": evidence_ok(row),
    }

    approved = all(checks.values())

    return {
        "report_type": REPORT_TYPE,
        "review_status": "review_only",
        "review_verdict": (
            "approved_written_larql_training_dataset_artifact"
            if approved
            else "written_larql_training_dataset_artifact_rejected"
        ),
        "allowed_next_step": (
            "hold_for_explicit_larql_training_run_approval"
            if approved
            else "repair_written_larql_training_dataset_artifact"
        ),
        "candidate_id": write_record.get("candidate_id", ""),
        "source_failure_id": write_record.get("source_failure_id", ""),
        "rule_id": write_record.get("rule_id", ""),
        "candidate_digest": write_record.get("candidate_digest", ""),
        "response_sha256": write_record.get("response_sha256", ""),
        "dataset_rows_reviewed": len(rows),
        "checks": checks,
        "training_dataset_written": write_record.get("training_dataset_written") is True,
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
    parser.add_argument("--write-record", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    review = build_review(read_json(args.write_record), read_jsonl(args.dataset))
    write_json(args.out / "larql_training_dataset_artifact_review.json", review)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
