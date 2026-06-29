from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_certainty_candidate_review.py"
CANDIDATE_PATH = ROOT / ".work/affordance_larql_candidates/unsupported_certainty_scope_claim/unsupported_certainty_scope_claim_candidate.json"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def good_candidate(tmp_path: Path) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_candidate(tmp_path):
    candidate = good_candidate(tmp_path)
    review = run_review("--candidate", candidate, "--out", tmp_path / "out")
    assert review.returncode == 0
    payload = json.loads((tmp_path / "out/unsupported_certainty_scope_claim_candidate_review.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "affordance_larql_candidate_review.v0"
    assert payload["review_status"] == "candidate_review_only"
    assert payload["review_verdict"] == "approved_unsupported_certainty_scope_claim_candidate_for_runtime_rule_draft"
    assert payload["allowed_next_step"] == "draft_unsupported_certainty_scope_claim_runtime_rule_packet"
    assert payload["model_call_performed_in_review"] is False
    assert payload["training_data_written"] is False
    assert payload["dataset_artifact_written"] is False
    assert payload["durable_memory_written"] is False
    assert payload["candidate_promotion_authorized"] is False
    assert payload["runtime_rule_modification_authorized"] is False
    assert payload["model_weights_mutated"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert all(payload["checks"].values())


def test_rejects_wrong_report_type(tmp_path):
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    candidate["report_type"] = "wrong"
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    from local_harness.affordance_larql_unsupported_certainty_candidate_review import build_review

    review = build_review(candidate)
    assert review["review_verdict"] == "rejected_unsupported_certainty_scope_claim_candidate"
    assert review["checks"]["candidate_report_type_ok"] is False


def test_rejects_wrong_verdict_and_next_step(tmp_path):
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    candidate["candidate_verdict"] = "wrong"
    review = __import__("local_harness.affordance_larql_unsupported_certainty_candidate_review", fromlist=["build_review"]).build_review(candidate)
    assert review["review_verdict"] == "rejected_unsupported_certainty_scope_claim_candidate"
    assert review["checks"]["candidate_verdict_ok"] is False
    candidate["candidate_verdict"] = "ready_for_supervised_review"
    candidate["allowed_next_step"] = "wrong"
    review = __import__("local_harness.affordance_larql_unsupported_certainty_candidate_review", fromlist=["build_review"]).build_review(candidate)
    assert review["checks"]["candidate_allowed_next_step_ok"] is False


def test_rejects_authority_flags_and_missing_content():
    from local_harness.affordance_larql_unsupported_certainty_candidate_review import build_review

    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    for key in (
        "model_call_performed",
        "training_data_written",
        "dataset_artifact_written",
        "durable_memory_written",
        "candidate_promotion_authorized",
        "runtime_rule_modification_authorized",
        "model_weights_mutated",
        "automatic_failure_to_curriculum_capture_authorized",
    ):
        bad = json.loads(json.dumps(candidate))
        bad[key] = True
        assert build_review(bad)["review_verdict"] == "rejected_unsupported_certainty_scope_claim_candidate"

    bad = json.loads(json.dumps(candidate))
    bad["json_contract"]["required_keys"].remove("allowed_claim")
    assert build_review(bad)["checks"]["contract_required_keys_ok"] is False

    bad = json.loads(json.dumps(candidate))
    bad["json_contract"]["exact_values"]["allowed_claim"] = "wrong"
    assert build_review(bad)["checks"]["contract_allowed_claim_ok"] is False

    bad = json.loads(json.dumps(candidate))
    bad["json_contract"]["false_values"] = []
    assert build_review(bad)["checks"]["contract_global_claim_authorized_false"] is False

    bad = json.loads(json.dumps(candidate))
    bad["json_contract"]["required_list_items"]["held_claims"].remove("task complete")
    assert build_review(bad)["checks"]["contract_held_claims_ok"] is False

    bad = json.loads(json.dumps(candidate))
    bad["json_contract"]["required_list_items"]["evidence_to_preserve"].remove("validation output")
    assert build_review(bad)["checks"]["contract_evidence_to_preserve_ok"] is False

    bad = json.loads(json.dumps(candidate))
    bad["json_contract"]["required_prompt_phrases"].remove("checked scope only")
    assert build_review(bad)["checks"]["contract_required_prompt_phrases_ok"] is False

    bad = json.loads(json.dumps(candidate))
    bad["json_contract"]["banned_response_phrases"].remove("safe to merge")
    assert build_review(bad)["checks"]["contract_banned_response_phrases_ok"] is False


def test_review_does_not_call_model():
    from local_harness.affordance_larql_unsupported_certainty_candidate_review import build_review

    review = build_review(json.loads(CANDIDATE_PATH.read_text(encoding="utf-8")))
    assert review["model_call_performed_in_review"] is False
