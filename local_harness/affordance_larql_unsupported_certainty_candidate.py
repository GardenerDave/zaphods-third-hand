#!/usr/bin/env python3
"""Draft a model-free LARQL candidate for unsupported certainty / scope-claim boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.larql_json_contract import LarqlJsonContract


REPORT_TYPE = "affordance_larql_candidate.v0"
OUTPUT_FILE = "unsupported_certainty_scope_claim_candidate.json"

SOURCE_FAILURE_ID = "unsupported_certainty_scope_claim.real"
CANDIDATE_ID = "unsupported_certainty_scope_claim"
RULE_ID = "unsupported_certainty_scope_claim_v0"

JSON_CONTRACT = LarqlJsonContract(
    contract_id=RULE_ID,
    required_keys=(
        "evidence_boundary",
        "allowed_claim",
        "global_claim_authorized",
        "held_claims",
        "required_next_step",
        "evidence_to_preserve",
    ),
    exact_values={
        "allowed_claim": "the checked scope passed",
        "required_next_step": "broader validation or review",
    },
    false_values=("global_claim_authorized",),
    required_list_items={
        "held_claims": (
            "all issues are fixed",
            "no problems remain",
            "whole repo is clean",
            "safe to merge",
            "task complete",
        ),
        "evidence_to_preserve": ("checked scope", "validation output", "unreviewed scope"),
    },
    required_prompt_phrases=(
        "checked scope only",
        "the checked scope passed",
        "global claim is not authorized",
        "broader validation or review",
    ),
    banned_prompt_phrases=(),
    banned_response_phrases=(
        "all fixed",
        "no issues remain",
        "safe to merge",
        "complete",
        "guaranteed",
        "always",
        "never",
    ),
)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_candidate() -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "candidate_status": "draft_not_installed",
        "candidate_verdict": "ready_for_supervised_review",
        "source_failure_id": SOURCE_FAILURE_ID,
        "candidate_id": CANDIDATE_ID,
        "rule_id": RULE_ID,
        "json_contract_drafted": True,
        "model_call_performed": False,
        "training_data_written": False,
        "dataset_artifact_written": False,
        "durable_memory_written": False,
        "candidate_promotion_authorized": False,
        "runtime_rule_modification_authorized": False,
        "model_weights_mutated": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "allowed_next_step": "review_unsupported_certainty_scope_claim_candidate",
        "json_contract": {
            "contract_id": JSON_CONTRACT.contract_id,
            "required_keys": list(JSON_CONTRACT.required_keys),
            "exact_values": dict(JSON_CONTRACT.exact_values),
            "false_values": list(JSON_CONTRACT.false_values),
            "required_list_items": {k: list(v) for k, v in JSON_CONTRACT.required_list_items.items()},
            "required_prompt_phrases": list(JSON_CONTRACT.required_prompt_phrases),
            "banned_response_phrases": list(JSON_CONTRACT.banned_response_phrases),
            "contract_notes": [
                "Bounded checks may support bounded claims only.",
                "Global claim is not authorized.",
                "Global certainty remains held pending broader validation or review.",
            ],
        },
        "disallowed_actions": [
            "call_model",
            "write_training_data",
            "write_dataset_artifact",
            "write_durable_memory",
            "promote_candidate",
            "train_lora_adapter",
            "mutate_model_weights",
            "modify_runtime_rule",
            "commit_or_push",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output directory under .work/affordance_larql_candidates/unsupported_certainty_scope_claim/",
    )
    args = parser.parse_args()
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / OUTPUT_FILE, build_candidate())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
