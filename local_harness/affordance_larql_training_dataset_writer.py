#!/usr/bin/env python3
"""Write a reviewed LARQL training candidate into a local dataset artifact only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ARTIFACT_TYPE = "affordance_larql_training_candidate_artifact.v0"
ARTIFACT_REVIEW_TYPE = "affordance_larql_training_candidate_artifact_review.v0"
DATASET_RECORD_TYPE = "affordance_larql_training_dataset_write_record.v0"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def approval_text_ok(text: str) -> bool:
    lowered = text.lower()
    return all(
        phrase in lowered
        for phrase in (
            "approve writing",
            "local training dataset artifact only",
            "do not train",
            "promote",
            "write durable memory",
            "mutate weights",
            "modify runtime rules",
        )
    )


def same_identity(a: dict[str, Any], b: dict[str, Any], key: str) -> bool:
    return bool(a.get(key)) and a.get(key) == b.get(key)


def build_dataset_row(artifact: dict[str, Any]) -> dict[str, Any]:
    preview = artifact.get("training_example_preview") or {}
    return {
        "messages": preview.get("messages", []),
        "metadata": {
            "format": "larql_supervised_sft_candidate.v0",
            "candidate_id": artifact.get("candidate_id", ""),
            "source_failure_id": artifact.get("source_failure_id", ""),
            "rule_id": artifact.get("rule_id", ""),
            "candidate_digest": artifact.get("candidate_digest", ""),
            "response_sha256": artifact.get("response_sha256", ""),
            "candidate_status": artifact.get("candidate_status", ""),
            "positive_requirements": preview.get("positive_requirements", []),
            "negative_requirements": preview.get("negative_requirements", []),
            "evidence": artifact.get("evidence", {}),
            "training_scope": "local_dataset_artifact_only",
        },
    }


def build_write_record(
    artifact: dict[str, Any],
    artifact_review: dict[str, Any],
    approval_text: str,
    dataset_path: str,
) -> dict[str, Any]:
    checks = {
        "approval_text_ok": approval_text_ok(approval_text),
        "artifact_report_type_ok": artifact.get("report_type") == ARTIFACT_TYPE,
        "artifact_status_ok": artifact.get("candidate_status") == "local_candidate_artifact_only",
        "artifact_training_candidate_written_true": artifact.get("training_candidate_written") is True,
        "artifact_training_dataset_written_false": artifact.get("training_dataset_written") is False,
        "artifact_durable_memory_written_false": artifact.get("durable_memory_written") is False,
        "artifact_lora_training_started_false": artifact.get("lora_training_started") is False,
        "artifact_model_weights_mutated_false": artifact.get("model_weights_mutated") is False,
        "artifact_candidate_promoted_false": artifact.get("candidate_promoted") is False,
        "artifact_runtime_rule_modified_false": artifact.get("runtime_rule_modified") is False,
        "artifact_review_report_type_ok": artifact_review.get("report_type") == ARTIFACT_REVIEW_TYPE,
        "artifact_review_status_ok": artifact_review.get("review_status") == "review_only",
        "artifact_review_verdict_ok": artifact_review.get("review_verdict") == "approved_written_larql_training_candidate_artifact",
        "artifact_review_next_step_ok": artifact_review.get("allowed_next_step") == "hold_for_explicit_larql_training_dataset_write_approval",
        "artifact_review_training_candidate_written_true": artifact_review.get("training_candidate_written") is True,
        "artifact_review_training_dataset_written_false": artifact_review.get("training_dataset_written") is False,
        "artifact_review_durable_memory_written_false": artifact_review.get("durable_memory_written") is False,
        "artifact_review_lora_training_started_false": artifact_review.get("lora_training_started") is False,
        "artifact_review_model_weights_mutated_false": artifact_review.get("model_weights_mutated") is False,
        "artifact_review_candidate_promoted_false": artifact_review.get("candidate_promoted") is False,
        "artifact_review_runtime_rule_modified_false": artifact_review.get("runtime_rule_modified") is False,
        "candidate_id_consistent": same_identity(artifact, artifact_review, "candidate_id"),
        "source_failure_id_consistent": same_identity(artifact, artifact_review, "source_failure_id"),
        "rule_id_consistent": same_identity(artifact, artifact_review, "rule_id"),
        "candidate_digest_consistent": same_identity(artifact, artifact_review, "candidate_digest"),
        "response_sha256_consistent": same_identity(artifact, artifact_review, "response_sha256"),
        "dataset_path_present": bool(dataset_path),
        "dataset_messages_present": bool((artifact.get("training_example_preview") or {}).get("messages")),
    }

    ok = all(checks.values())

    return {
        "report_type": DATASET_RECORD_TYPE,
        "write_status": "completed" if ok else "rejected",
        "write_verdict": (
            "larql_training_dataset_local_artifact_written"
            if ok
            else "larql_training_dataset_local_artifact_write_rejected"
        ),
        "allowed_next_step": (
            "review_written_larql_training_dataset_artifact"
            if ok
            else "repair_larql_training_dataset_write_inputs"
        ),
        "candidate_id": artifact.get("candidate_id", ""),
        "source_failure_id": artifact.get("source_failure_id", ""),
        "rule_id": artifact.get("rule_id", ""),
        "candidate_digest": artifact.get("candidate_digest", ""),
        "response_sha256": artifact.get("response_sha256", ""),
        "dataset_artifact_path": dataset_path if ok else "",
        "dataset_rows_written": 1 if ok else 0,
        "checks": checks,
        "approval_scope": "write_local_training_dataset_artifact_only",
        "training_dataset_write_authorized": ok,
        "training_dataset_written": ok,
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
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--artifact-review", required=True, type=Path)
    parser.add_argument("--approval-text", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    artifact = read_json(args.artifact)
    artifact_review = read_json(args.artifact_review)

    dataset_path = args.out / "larql_training_dataset.jsonl"
    record_path = args.out / "larql_training_dataset_write_record.json"

    record = build_write_record(artifact, artifact_review, args.approval_text, str(dataset_path))
    if record["write_verdict"] == "larql_training_dataset_local_artifact_written":
        write_jsonl(dataset_path, [build_dataset_row(artifact)])

    write_json(record_path, record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
