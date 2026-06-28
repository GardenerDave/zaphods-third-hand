#!/usr/bin/env python3
"""Review a written local LARQL training-candidate artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_TYPE = "affordance_larql_training_candidate_artifact_review.v0"
WRITE_RECORD_TYPE = "affordance_larql_training_candidate_write_record.v0"
ARTIFACT_TYPE = "affordance_larql_training_candidate_artifact.v0"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def same_identity(a: dict[str, Any], b: dict[str, Any], key: str) -> bool:
    return bool(a.get(key)) and a.get(key) == b.get(key)


def messages_by_role(artifact: dict[str, Any]) -> dict[str, str]:
    messages = artifact.get("training_example_preview", {}).get("messages", [])
    return {
        str(message.get("role", "")): str(message.get("content", ""))
        for message in messages
        if isinstance(message, dict)
    }


def artifact_has_required_training_shape(artifact: dict[str, Any]) -> bool:
    by_role = messages_by_role(artifact)
    system = by_role.get("system", "").lower()
    user = by_role.get("user", "").lower()
    assistant = by_role.get("assistant", "").lower()

    return all(
        (
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


def build_review(write_record: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    evidence = artifact.get("evidence") or {}

    checks = {
        "write_record_report_type_ok": write_record.get("report_type") == WRITE_RECORD_TYPE,
        "write_record_status_completed": write_record.get("write_status") == "completed",
        "write_record_verdict_ok": write_record.get("write_verdict") == "larql_training_candidate_local_artifact_written",
        "write_record_next_step_ok": write_record.get("allowed_next_step") == "review_written_larql_training_candidate_artifact",
        "write_record_training_candidate_write_authorized_true": write_record.get("training_candidate_write_authorized") is True,
        "write_record_training_candidate_written_true": write_record.get("training_candidate_written") is True,
        "write_record_training_dataset_written_false": write_record.get("training_dataset_written") is False,
        "write_record_durable_memory_written_false": write_record.get("durable_memory_written") is False,
        "write_record_lora_training_started_false": write_record.get("lora_training_started") is False,
        "write_record_model_weights_mutated_false": write_record.get("model_weights_mutated") is False,
        "write_record_candidate_promoted_false": write_record.get("candidate_promoted") is False,
        "write_record_runtime_rule_modified_false": write_record.get("runtime_rule_modified") is False,
        "artifact_report_type_ok": artifact.get("report_type") == ARTIFACT_TYPE,
        "artifact_status_ok": artifact.get("candidate_status") == "local_candidate_artifact_only",
        "artifact_training_candidate_written_true": artifact.get("training_candidate_written") is True,
        "artifact_training_dataset_written_false": artifact.get("training_dataset_written") is False,
        "artifact_durable_memory_written_false": artifact.get("durable_memory_written") is False,
        "artifact_lora_training_started_false": artifact.get("lora_training_started") is False,
        "artifact_model_weights_mutated_false": artifact.get("model_weights_mutated") is False,
        "artifact_candidate_promoted_false": artifact.get("candidate_promoted") is False,
        "artifact_runtime_rule_modified_false": artifact.get("runtime_rule_modified") is False,
        "candidate_id_consistent": same_identity(write_record, artifact, "candidate_id"),
        "source_failure_id_consistent": same_identity(write_record, artifact, "source_failure_id"),
        "rule_id_consistent": same_identity(write_record, artifact, "rule_id"),
        "candidate_digest_consistent": same_identity(write_record, artifact, "candidate_digest"),
        "response_sha256_consistent": same_identity(write_record, artifact, "response_sha256"),
        "approval_scope_ok": artifact.get("approval", {}).get("approval_scope") == "write_local_candidate_artifact_only",
        "artifact_training_shape_ok": artifact_has_required_training_shape(artifact),
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
            "approved_written_larql_training_candidate_artifact"
            if approved
            else "written_larql_training_candidate_artifact_rejected"
        ),
        "allowed_next_step": (
            "hold_for_explicit_larql_training_dataset_write_approval"
            if approved
            else "repair_written_larql_training_candidate_artifact"
        ),
        "candidate_id": artifact.get("candidate_id", ""),
        "source_failure_id": artifact.get("source_failure_id", ""),
        "rule_id": artifact.get("rule_id", ""),
        "candidate_digest": artifact.get("candidate_digest", ""),
        "response_sha256": artifact.get("response_sha256", ""),
        "checks": checks,
        "training_candidate_written": artifact.get("training_candidate_written") is True,
        "training_dataset_written": False,
        "durable_memory_written": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "candidate_promoted": False,
        "runtime_rule_modified": False,
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "disallowed_actions": [
            "call_model",
            "write_training_dataset",
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
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    review = build_review(read_json(args.write_record), read_json(args.artifact))
    write_json(args.out / "larql_training_candidate_artifact_review.json", review)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
