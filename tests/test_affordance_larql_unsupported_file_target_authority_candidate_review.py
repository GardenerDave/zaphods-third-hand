from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_file_target_authority_candidate_review.py"
CANDIDATE_PATH = (
    ROOT / ".work/affordance_larql_candidates/unsupported_file_target_authority/unsupported_file_target_authority_candidate.json"
)


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def candidate_payload() -> dict:
    return json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))


def good_candidate(tmp_path: Path) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def build_review(candidate: dict) -> dict:
    from local_harness.affordance_larql_unsupported_file_target_authority_candidate_review import build_review

    return build_review(candidate)


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_candidate(tmp_path):
    candidate = good_candidate(tmp_path)
    result = run_review("--candidate", candidate, "--out", tmp_path / "out")
    assert result.returncode == 0
    payload = json.loads(
        (tmp_path / "out/unsupported_file_target_authority_candidate_review.json").read_text(encoding="utf-8")
    )
    assert payload["report_type"] == "affordance_larql_candidate_review.v0"
    assert payload["review_status"] == "candidate_review_only"
    assert payload["review_verdict"] == "approved_unsupported_file_target_authority_candidate_for_runtime_rule_draft"
    assert payload["allowed_next_step"] == "draft_unsupported_file_target_authority_runtime_rule_packet"
    assert payload["model_call_performed_in_review"] is False
    assert payload["training_data_written"] is False
    assert payload["dataset_artifact_written"] is False
    assert payload["durable_memory_written"] is False
    assert payload["candidate_promotion_authorized"] is False
    assert payload["runtime_rule_modification_authorized"] is False
    assert payload["model_weights_mutated"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert all(payload["checks"].values())


def test_rejects_wrong_top_level_fields():
    payload = candidate_payload()
    fields = {
        "report_type": "wrong",
        "candidate_status": "wrong",
        "candidate_verdict": "wrong",
        "source_failure_id": "wrong.real",
        "candidate_id": "wrong",
        "rule_id": "wrong_v0",
        "allowed_next_step": "wrong",
    }
    expected_checks = {
        "report_type": "candidate_report_type_ok",
        "candidate_status": "candidate_status_ok",
        "candidate_verdict": "candidate_verdict_ok",
        "source_failure_id": "candidate_source_failure_id_ok",
        "candidate_id": "candidate_candidate_id_ok",
        "rule_id": "candidate_rule_id_ok",
        "allowed_next_step": "candidate_allowed_next_step_ok",
    }
    for field, bad_value in fields.items():
        bad = json.loads(json.dumps(payload))
        bad[field] = bad_value
        review = build_review(bad)
        assert review["review_verdict"] == "rejected_unsupported_file_target_authority_candidate"
        assert review["checks"][expected_checks[field]] is False


def test_rejects_authority_flags():
    payload = candidate_payload()
    mapping = {
        "model_call_performed": "candidate_model_call_performed_false",
        "training_data_written": "candidate_training_data_written_false",
        "dataset_artifact_written": "candidate_dataset_artifact_written_false",
        "durable_memory_written": "candidate_durable_memory_written_false",
        "candidate_promotion_authorized": "candidate_candidate_promotion_authorized_false",
        "runtime_rule_modification_authorized": "candidate_runtime_rule_modification_authorized_false",
        "model_weights_mutated": "candidate_model_weights_mutated_false",
        "automatic_failure_to_curriculum_capture_authorized": "candidate_automatic_failure_to_curriculum_capture_authorized_false",
    }
    for field, check_name in mapping.items():
        bad = json.loads(json.dumps(payload))
        bad[field] = True
        review = build_review(bad)
        assert review["review_verdict"] == "rejected_unsupported_file_target_authority_candidate"
        assert review["checks"][check_name] is False


def test_rejects_missing_required_key():
    payload = candidate_payload()
    bad = json.loads(json.dumps(payload))
    bad["json_contract"]["required_keys"].remove("allowed_claim")
    review = build_review(bad)
    assert review["checks"]["contract_required_keys_ok"] is False


def test_rejects_wrong_exact_value():
    payload = candidate_payload()
    bad = json.loads(json.dumps(payload))
    bad["json_contract"]["exact_values"]["allowed_claim"] = "wrong"
    review = build_review(bad)
    assert review["checks"]["contract_allowed_claim_ok"] is False


def test_rejects_missing_false_value_requirement():
    payload = candidate_payload()
    bad = json.loads(json.dumps(payload))
    bad["json_contract"]["false_values"] = []
    review = build_review(bad)
    assert review["checks"]["contract_outside_file_modification_authorized_false"] is False


def test_rejects_missing_held_claim():
    payload = candidate_payload()
    bad = json.loads(json.dumps(payload))
    bad["json_contract"]["required_list_items"]["held_claims"].remove("expand patch scope")
    review = build_review(bad)
    assert review["checks"]["contract_held_claims_ok"] is False


def test_rejects_missing_evidence_to_preserve_item():
    payload = candidate_payload()
    bad = json.loads(json.dumps(payload))
    bad["json_contract"]["required_list_items"]["evidence_to_preserve"].remove("requested target file")
    review = build_review(bad)
    assert review["checks"]["contract_evidence_to_preserve_ok"] is False


def test_rejects_missing_required_prompt_phrase():
    payload = candidate_payload()
    bad = json.loads(json.dumps(payload))
    bad["json_contract"]["required_prompt_phrases"].remove("allowed files only")
    review = build_review(bad)
    assert review["checks"]["contract_required_prompt_phrases_ok"] is False


def test_rejects_missing_banned_response_phrase():
    payload = candidate_payload()
    bad = json.loads(json.dumps(payload))
    bad["json_contract"]["banned_response_phrases"].remove("also fix")
    review = build_review(bad)
    assert review["checks"]["contract_banned_response_phrases_ok"] is False


def test_rejects_missing_boundary_note():
    payload = candidate_payload()
    bad = json.loads(json.dumps(payload))
    bad["json_contract"]["contract_notes"].remove("The candidate is draft-only and not installed.")
    review = build_review(bad)
    assert review["checks"]["contract_notes_ok"] is False


def test_review_performs_no_model_call():
    review = build_review(candidate_payload())
    assert review["model_call_performed_in_review"] is False
