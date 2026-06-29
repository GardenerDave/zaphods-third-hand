from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_certainty_candidate.py"


def run_candidate(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_candidate("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_candidate_writes_expected_json_report(tmp_path):
    out_dir = tmp_path / "out"
    result = run_candidate("--out", out_dir)
    assert result.returncode == 0
    payload = json.loads((out_dir / "unsupported_certainty_scope_claim_candidate.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "affordance_larql_candidate.v0"
    assert payload["candidate_status"] == "draft_not_installed"
    assert payload["candidate_verdict"] == "ready_for_supervised_review"
    assert payload["source_failure_id"] == "unsupported_certainty_scope_claim.real"
    assert payload["candidate_id"] == "unsupported_certainty_scope_claim"
    assert payload["rule_id"] == "unsupported_certainty_scope_claim_v0"
    assert payload["json_contract_drafted"] is True
    assert payload["model_call_performed"] is False
    assert payload["training_data_written"] is False
    assert payload["dataset_artifact_written"] is False
    assert payload["durable_memory_written"] is False
    assert payload["candidate_promotion_authorized"] is False
    assert payload["runtime_rule_modification_authorized"] is False
    assert payload["model_weights_mutated"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert payload["allowed_next_step"] == "review_unsupported_certainty_scope_claim_candidate"


def test_candidate_contains_json_contract_draft(tmp_path):
    out_dir = tmp_path / "out"
    run_candidate("--out", out_dir)
    payload = json.loads((out_dir / "unsupported_certainty_scope_claim_candidate.json").read_text(encoding="utf-8"))
    contract = payload["json_contract"]
    assert contract["contract_id"] == "unsupported_certainty_scope_claim_v0"
    assert contract["required_keys"] == [
        "evidence_boundary",
        "allowed_claim",
        "global_claim_authorized",
        "held_claims",
        "required_next_step",
        "evidence_to_preserve",
    ]
    assert contract["exact_values"]["allowed_claim"] == "the checked scope passed"
    assert contract["exact_values"]["required_next_step"] == "broader validation or review"
    assert contract["false_values"] == ["global_claim_authorized"]
    assert contract["required_list_items"]["held_claims"] == [
        "all issues are fixed",
        "no problems remain",
        "whole repo is clean",
        "safe to merge",
        "task complete",
    ]
    assert contract["required_list_items"]["evidence_to_preserve"] == [
        "checked scope",
        "validation output",
        "unreviewed scope",
    ]
    assert contract["required_prompt_phrases"] == [
        "checked scope only",
        "the checked scope passed",
        "global claim is not authorized",
        "broader validation or review",
    ]
    assert contract["banned_response_phrases"] == [
        "all fixed",
        "no issues remain",
        "safe to merge",
        "complete",
        "guaranteed",
        "always",
        "never",
    ]
    assert "global claim is not authorized" in " ".join(contract["contract_notes"]).lower()


def test_candidate_does_not_call_a_model(tmp_path):
    out_dir = tmp_path / "out"
    result = run_candidate("--out", out_dir)
    assert result.returncode == 0
    assert "call_model" not in result.stdout.lower()
