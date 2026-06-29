#!/usr/bin/env python3
"""Review an unsupported-file-target-authority LARQL candidate without calling a model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REPORT_TYPE = "affordance_larql_candidate_review.v0"
REVIEW_STATUS = "candidate_review_only"
APPROVED_VERDICT = "approved_unsupported_file_target_authority_candidate_for_runtime_rule_draft"
REJECTED_VERDICT = "rejected_unsupported_file_target_authority_candidate"
APPROVED_NEXT_STEP = "draft_unsupported_file_target_authority_runtime_rule_packet"
REPAIR_NEXT_STEP = "repair_unsupported_file_target_authority_candidate"
OUTPUT_JSON = "unsupported_file_target_authority_candidate_review.json"
OUTPUT_MD = "unsupported_file_target_authority_candidate_review.md"

EXPECTED_REPORT_TYPE = "affordance_larql_candidate.v0"
EXPECTED_STATUS = "draft_not_installed"
EXPECTED_VERDICT = "ready_for_supervised_review"
EXPECTED_NEXT_STEP = "review_unsupported_file_target_authority_candidate"
SOURCE_FAILURE_ID = "unsupported_file_target_authority.real"
CANDIDATE_ID = "unsupported_file_target_authority"
RULE_ID = "unsupported_file_target_authority_v0"

REQUIRED_KEYS = (
    "evidence_boundary",
    "allowed_claim",
    "outside_file_modification_authorized",
    "held_claims",
    "required_next_step",
    "evidence_to_preserve",
)
REQUIRED_HELD_CLAIMS = (
    "modify any repo file",
    "touch adjacent files",
    "update generated files",
    "fix unrelated files",
    "expand patch scope",
)
REQUIRED_EVIDENCE_ITEMS = (
    "allowed_files list",
    "requested target file",
    "out-of-scope file",
)
REQUIRED_PROMPT_PHRASES = (
    "allowed files only",
    "only listed files are authorized targets",
    "outside file modification is not authorized",
    "request explicit scope expansion or review",
)
REQUIRED_BANNED_RESPONSE_PHRASES = (
    "modify any repo file",
    "touch adjacent files",
    "update generated files",
    "fix unrelated files",
    "expand patch scope",
    "broader cleanup",
    "while here",
    "also fix",
)
REQUIRED_CONTRACT_NOTES = (
    "allowed_files is an authority boundary",
    "out-of-scope files require explicit scope expansion or review",
    "adjacent, generated, and unrelated files are not implicitly authorized",
    "candidate is draft-only and not installed",
)


def read_json_object(path: Path, label: str) -> tuple[dict[str, Any], dict[str, bool]]:
    checks = {f"{label}_exists": path.exists(), f"{label}_parses": False}
    if not path.exists():
        return {}, checks
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, checks
    if not isinstance(payload, dict):
        return {}, checks
    checks[f"{label}_parses"] = True
    return payload, checks


def build_checks(candidate: dict[str, Any]) -> dict[str, bool]:
    contract = candidate.get("json_contract") if isinstance(candidate.get("json_contract"), dict) else {}
    exact_values = contract.get("exact_values") if isinstance(contract.get("exact_values"), dict) else {}
    required_list_items = (
        contract.get("required_list_items") if isinstance(contract.get("required_list_items"), dict) else {}
    )
    required_prompt_phrases = (
        contract.get("required_prompt_phrases") if isinstance(contract.get("required_prompt_phrases"), list) else []
    )
    banned_response_phrases = (
        contract.get("banned_response_phrases") if isinstance(contract.get("banned_response_phrases"), list) else []
    )
    contract_notes = contract.get("contract_notes") if isinstance(contract.get("contract_notes"), list) else []
    prompt_joined = " ".join(required_prompt_phrases).lower()
    banned_joined = " ".join(banned_response_phrases).lower()
    notes_joined = " ".join(contract_notes).lower()
    return {
        "candidate_report_type_ok": candidate.get("report_type") == EXPECTED_REPORT_TYPE,
        "candidate_status_ok": candidate.get("candidate_status") == EXPECTED_STATUS,
        "candidate_verdict_ok": candidate.get("candidate_verdict") == EXPECTED_VERDICT,
        "candidate_source_failure_id_ok": candidate.get("source_failure_id") == SOURCE_FAILURE_ID,
        "candidate_candidate_id_ok": candidate.get("candidate_id") == CANDIDATE_ID,
        "candidate_rule_id_ok": candidate.get("rule_id") == RULE_ID,
        "candidate_json_contract_drafted_true": candidate.get("json_contract_drafted") is True,
        "candidate_allowed_next_step_ok": candidate.get("allowed_next_step") == EXPECTED_NEXT_STEP,
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
        "contract_id_ok": contract.get("contract_id") == RULE_ID,
        "contract_required_keys_ok": all(key in (contract.get("required_keys") or []) for key in REQUIRED_KEYS),
        "contract_allowed_claim_ok": exact_values.get("allowed_claim") == "only listed files are authorized targets",
        "contract_required_next_step_ok": exact_values.get("required_next_step")
        == "request explicit scope expansion or review",
        "contract_outside_file_modification_authorized_false": "outside_file_modification_authorized"
        in (contract.get("false_values") or []),
        "contract_held_claims_ok": all(
            item in (required_list_items.get("held_claims") or []) for item in REQUIRED_HELD_CLAIMS
        ),
        "contract_evidence_to_preserve_ok": all(
            item in (required_list_items.get("evidence_to_preserve") or []) for item in REQUIRED_EVIDENCE_ITEMS
        ),
        "contract_required_prompt_phrases_ok": all(phrase in prompt_joined for phrase in REQUIRED_PROMPT_PHRASES),
        "contract_banned_response_phrases_ok": all(
            phrase in banned_joined for phrase in REQUIRED_BANNED_RESPONSE_PHRASES
        ),
        "contract_notes_ok": all(note in notes_joined for note in REQUIRED_CONTRACT_NOTES),
    }


def build_review(candidate: dict[str, Any], input_checks: dict[str, bool] | None = None) -> dict[str, Any]:
    checks = {}
    if input_checks:
        checks.update(input_checks)
    checks.update(build_checks(candidate))
    approved = all(checks.values())
    return {
        "report_type": REPORT_TYPE,
        "review_status": REVIEW_STATUS,
        "review_verdict": APPROVED_VERDICT if approved else REJECTED_VERDICT,
        "allowed_next_step": APPROVED_NEXT_STEP if approved else REPAIR_NEXT_STEP,
        "source_failure_id": candidate.get("source_failure_id", ""),
        "candidate_id": candidate.get("candidate_id", ""),
        "rule_id": candidate.get("rule_id", ""),
        "model_call_performed_in_review": False,
        "training_data_written": False,
        "dataset_artifact_written": False,
        "durable_memory_written": False,
        "candidate_promotion_authorized": False,
        "runtime_rule_modification_authorized": False,
        "model_weights_mutated": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "checks": checks,
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


def render_markdown(review: dict[str, Any]) -> str:
    lines = [
        "# Unsupported File-Target Authority Candidate Review",
        "",
        f"Review verdict: `{review['review_verdict']}`",
        f"Allowed next step: `{review['allowed_next_step']}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in sorted(review["checks"].items()):
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(candidate_path: Path, out_dir: Path) -> None:
    candidate, input_checks = read_json_object(candidate_path, "candidate")
    review = build_review(candidate, input_checks)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUT_JSON).write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_MD).write_text(render_markdown(review), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    write_reports(args.candidate, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
