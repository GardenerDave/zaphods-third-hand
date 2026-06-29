from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_certainty_runtime_rule_packet.py"
CANDIDATE_PATH = ROOT / ".work/affordance_larql_candidates/unsupported_certainty_scope_claim/unsupported_certainty_scope_claim_candidate.json"
REVIEW_PATH = ROOT / ".work/affordance_larql_candidate_reviews/unsupported_certainty_scope_claim/unsupported_certainty_scope_claim_candidate_review.json"


def run_packet(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def good_inputs(tmp_path: Path) -> tuple[Path, Path]:
    candidate = tmp_path / "candidate.json"
    review = tmp_path / "review.json"
    candidate.write_text(CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    review.write_text(REVIEW_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return candidate, review


def test_help_works():
    result = run_packet("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_script_writes_expected_packet_json(tmp_path):
    candidate, review = good_inputs(tmp_path)
    result = run_packet("--candidate", candidate, "--candidate-review", review, "--out", tmp_path / "out")
    assert result.returncode == 0
    payload = json.loads((tmp_path / "out/unsupported_certainty_scope_claim_runtime_rule_packet.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "affordance_larql_runtime_rule_packet.v0"
    assert payload["packet_status"] == "draft_not_installed"
    assert payload["packet_verdict"] == "ready_for_runtime_rule_packet_review"
    assert payload["source_failure_id"] == "unsupported_certainty_scope_claim.real"
    assert payload["candidate_id"] == "unsupported_certainty_scope_claim"
    assert payload["rule_id"] == "unsupported_certainty_scope_claim_v0"
    assert payload["candidate_review_verdict"] == "approved_unsupported_certainty_scope_claim_candidate_for_runtime_rule_draft"
    assert payload["runtime_rule_status"] == "draft_not_installed"
    assert payload["runtime_rule_install_authorized"] is False
    assert payload["runtime_rule_modification_authorized"] is False
    assert payload["model_call_performed"] is False
    assert payload["training_data_written"] is False
    assert payload["dataset_artifact_written"] is False
    assert payload["durable_memory_written"] is False
    assert payload["candidate_promotion_authorized"] is False
    assert payload["model_weights_mutated"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert payload["allowed_next_step"] == "review_unsupported_certainty_scope_claim_runtime_rule_packet"
    assert payload["draft_runtime_rule"]["rule_id"] == "unsupported_certainty_scope_claim_v0"
    assert payload["draft_runtime_rule"]["status"] == "draft_not_installed"


def test_packet_contains_draft_runtime_rule_content(tmp_path):
    candidate, review = good_inputs(tmp_path)
    from local_harness.affordance_larql_unsupported_certainty_runtime_rule_packet import build_packet

    packet = build_packet(json.loads(candidate.read_text(encoding="utf-8")), json.loads(review.read_text(encoding="utf-8")))
    draft = packet["draft_runtime_rule"]
    assert draft["summary"].startswith("A bounded check may support a bounded claim")
    assert "a validation command checked only part of the repo" in draft["applies_when"]
    assert "a test suite checked only a specific subset" in draft["applies_when"]
    assert "search results covered only a limited scope" in draft["applies_when"]
    assert "all issues are fixed" in draft["blocks"]
    assert "safe to merge" in draft["blocks"]
    assert "state the checked scope" in draft["required_response_behavior"]
    assert "preserve checked scope, validation output, and unreviewed scope" in draft["required_response_behavior"]


def test_packet_preserves_json_contract_requirements(tmp_path):
    candidate, review = good_inputs(tmp_path)
    from local_harness.affordance_larql_unsupported_certainty_runtime_rule_packet import build_packet

    packet = build_packet(json.loads(candidate.read_text(encoding="utf-8")), json.loads(review.read_text(encoding="utf-8")))
    contract = packet["json_contract"]
    assert contract == {
        "evidence_boundary": "checked scope only",
        "allowed_claim": "the checked scope passed",
        "global_claim_authorized": False,
        "held_claims": [
            "all issues are fixed",
            "no problems remain",
            "whole repo is clean",
            "safe to merge",
            "task complete",
        ],
        "required_next_step": "broader validation or review",
        "evidence_to_preserve": ["checked scope", "validation output", "unreviewed scope"],
    }


def test_packet_rejects_bad_candidate_or_review():
    from local_harness.affordance_larql_unsupported_certainty_runtime_rule_packet import build_packet

    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))

    bad = json.loads(json.dumps(candidate))
    bad["candidate_id"] = "wrong"
    packet = build_packet(bad, review)
    assert packet["packet_verdict"] == "runtime_rule_packet_rejected"

    bad_review = json.loads(json.dumps(review))
    bad_review["review_verdict"] = "wrong"
    packet = build_packet(candidate, bad_review)
    assert packet["packet_verdict"] == "runtime_rule_packet_rejected"

    bad_review = json.loads(json.dumps(review))
    bad_review["allowed_next_step"] = "wrong"
    packet = build_packet(candidate, bad_review)
    assert packet["checks"]["review_next_step_ok"] is False


def test_packet_does_not_call_model(tmp_path):
    candidate, review = good_inputs(tmp_path)
    result = run_packet("--candidate", candidate, "--candidate-review", review, "--out", tmp_path / "out")
    assert result.returncode == 0
    assert "call_model" not in result.stdout.lower()
