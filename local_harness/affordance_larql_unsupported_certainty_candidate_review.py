#!/usr/bin/env python3
"""Review an unsupported-certainty / scope-claim LARQL candidate without calling a model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.larql_json_contract import (
    LarqlJsonContract,
    check_json_contract_prompt,
)


REPORT_TYPE = "affordance_larql_candidate_review.v0"
REVIEW_STATUS = "candidate_review_only"
APPROVED_VERDICT = "approved_unsupported_certainty_scope_claim_candidate_for_runtime_rule_draft"
REJECTED_VERDICT = "rejected_unsupported_certainty_scope_claim_candidate"
APPROVED_NEXT_STEP = "draft_unsupported_certainty_scope_claim_runtime_rule_packet"
REPAIR_NEXT_STEP = "repair_unsupported_certainty_scope_claim_candidate"
PROMOTION_VERDICT = "hold_pending_explicit_experiment_approval"
OUTPUT_FILES = (
    "unsupported_certainty_scope_claim_candidate_review.json",
    "unsupported_certainty_scope_claim_candidate_review.md",
)

EXPECTED_REPORT_TYPE = "affordance_larql_candidate.v0"
EXPECTED_STATUS = "draft_not_installed"
EXPECTED_VERDICT = "ready_for_supervised_review"
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


def check_contract_prompt(contract: LarqlJsonContract) -> dict[str, bool]:
    prompt = "\n".join(
        [
            "Use checked scope only.",
            "The checked scope passed.",
            "Global claim is not authorized.",
            "Broader validation or review is required.",
        ]
    )
    return check_json_contract_prompt(prompt, contract)


def prompt_ready(prompt_text: str) -> dict[str, bool]:
    helper = check_json_contract_prompt(prompt_text, JSON_CONTRACT)
    lowered = prompt_text.lower()
    return {
        "prompt_has_checked_scope_only": "checked scope only" in lowered,
        "prompt_has_checked_scope_passed": "the checked scope passed" in lowered,
        "prompt_has_global_claim_not_authorized": "global claim is not authorized" in lowered,
        "prompt_has_broader_validation_or_review": "broader validation or review" in lowered,
        "prompt_has_required_phrase_checked_scope_only": helper["prompt_has_required_phrase_checked_scope_only"],
        "prompt_has_required_phrase_the_checked_scope_passed": helper["prompt_has_required_phrase_the_checked_scope_passed"],
        "prompt_has_required_phrase_global_claim_is_not_authorized": helper[
            "prompt_has_required_phrase_global_claim_is_not_authorized"
        ],
        "prompt_has_required_phrase_broader_validation_or_review": helper[
            "prompt_has_required_phrase_broader_validation_or_review"
        ],
    }


def contract_ready(contract: dict[str, Any]) -> dict[str, bool]:
    exact_values = contract.get("exact_values") if isinstance(contract.get("exact_values"), dict) else {}
    required_list_items = (
        contract.get("required_list_items") if isinstance(contract.get("required_list_items"), dict) else {}
    )
    required_prompt_phrases = contract.get("required_prompt_phrases") if isinstance(contract.get("required_prompt_phrases"), list) else []
    banned_response_phrases = contract.get("banned_response_phrases") if isinstance(contract.get("banned_response_phrases"), list) else []
    return {
        "contract_id_ok": contract.get("contract_id") == RULE_ID,
        "contract_required_keys_ok": all(
            key in (contract.get("required_keys") or [])
            for key in (
                "evidence_boundary",
                "allowed_claim",
                "global_claim_authorized",
                "held_claims",
                "required_next_step",
                "evidence_to_preserve",
            )
        ),
        "contract_allowed_claim_ok": exact_values.get("allowed_claim") == "the checked scope passed",
        "contract_required_next_step_ok": exact_values.get("required_next_step") == "broader validation or review",
        "contract_global_claim_authorized_false": "global_claim_authorized" in (contract.get("false_values") or []),
        "contract_held_claims_ok": all(
            item in (required_list_items.get("held_claims") or [])
            for item in (
                "all issues are fixed",
                "no problems remain",
                "whole repo is clean",
                "safe to merge",
                "task complete",
            )
        ),
        "contract_evidence_to_preserve_ok": all(
            item in (required_list_items.get("evidence_to_preserve") or [])
            for item in ("checked scope", "validation output", "unreviewed scope")
        ),
        "contract_required_prompt_phrases_ok": all(
            phrase in " ".join(required_prompt_phrases)
            for phrase in (
                "checked scope only",
                "the checked scope passed",
                "global claim is not authorized",
                "broader validation or review",
            )
        ),
        "contract_banned_response_phrases_ok": all(
            phrase in " ".join(banned_response_phrases)
            for phrase in ("all fixed", "no issues remain", "safe to merge", "complete", "guaranteed", "always", "never")
        ),
    }


def build_review(candidate: dict[str, Any]) -> dict[str, Any]:
    contract = candidate.get("json_contract") if isinstance(candidate.get("json_contract"), dict) else {}
    checks = {
        "candidate_report_type_ok": candidate.get("report_type") == EXPECTED_REPORT_TYPE,
        "candidate_status_ok": candidate.get("candidate_status") == EXPECTED_STATUS,
        "candidate_verdict_ok": candidate.get("candidate_verdict") == EXPECTED_VERDICT,
        "candidate_source_failure_id_ok": candidate.get("source_failure_id") == SOURCE_FAILURE_ID,
        "candidate_candidate_id_ok": candidate.get("candidate_id") == CANDIDATE_ID,
        "candidate_rule_id_ok": candidate.get("rule_id") == RULE_ID,
        "candidate_json_contract_drafted_true": candidate.get("json_contract_drafted") is True,
        "candidate_allowed_next_step_ok": candidate.get("allowed_next_step")
        == "review_unsupported_certainty_scope_claim_candidate",
        "candidate_model_call_performed_false": candidate.get("model_call_performed") is False,
        "candidate_training_data_written_false": candidate.get("training_data_written") is False,
        "candidate_dataset_artifact_written_false": candidate.get("dataset_artifact_written") is False,
        "candidate_durable_memory_written_false": candidate.get("durable_memory_written") is False,
        "candidate_candidate_promotion_authorized_false": candidate.get("candidate_promotion_authorized") is False,
        "candidate_runtime_rule_modification_authorized_false": candidate.get("runtime_rule_modification_authorized")
        is False,
        "candidate_model_weights_mutated_false": candidate.get("model_weights_mutated") is False,
        "candidate_automatic_failure_to_curriculum_capture_authorized_false": candidate.get(
            "automatic_failure_to_curriculum_capture_authorized"
        )
        is False,
        **contract_ready(contract),
        **prompt_ready(
            "\n".join(
                [
                    "Checked scope only.",
                    "The checked scope passed.",
                    "Global claim is not authorized.",
                    "Broader validation or review.",
                ]
            )
        ),
    }
    approved = all(checks.values())
    return {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": APPROVED_VERDICT if approved else REJECTED_VERDICT,
        "allowed_next_step": APPROVED_NEXT_STEP if approved else REPAIR_NEXT_STEP,
        "source_failure_id": candidate.get("source_failure_id", ""),
        "candidate_id": candidate.get("candidate_id", ""),
        "rule_id": candidate.get("rule_id", ""),
        "reviewed_candidate_verdict": candidate.get("candidate_verdict"),
        "model_call_performed_in_review": False,
        "training_data_written": False,
        "dataset_artifact_written": False,
        "durable_memory_written": False,
        "candidate_promotion_authorized": False,
        "runtime_rule_modification_authorized": False,
        "model_weights_mutated": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "checks": checks,
        "promotion_verdict": PROMOTION_VERDICT,
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


def render_markdown(review: dict[str, Any], candidate: dict[str, Any]) -> str:
    lines = [
        "# Unsupported Certainty / Scope-Claim Candidate Review",
        "",
        f"Review verdict: `{review['review_verdict']}`",
        f"Allowed next step: `{review['allowed_next_step']}`",
        "",
        "## Candidate reviewed",
        "",
        json.dumps(candidate, indent=2, sort_keys=True),
        "",
        "## Checks",
        "",
    ]
    for key, value in sorted(review["checks"].items()):
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(candidate_path: Path, out_dir: Path) -> dict[str, Any]:
    candidate, checks, notes = read_json_object(candidate_path, "candidate")
    review = build_review(candidate)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(review, candidate), encoding="utf-8")
    review["notes"] = notes
    review["input_checks"] = checks
    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.candidate, args.out)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
