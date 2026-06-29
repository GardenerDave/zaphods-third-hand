from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_file_target_authority_runtime_rule_packet.py"
CANDIDATE_PATH = (
    ROOT / ".work/affordance_larql_candidates/unsupported_file_target_authority/unsupported_file_target_authority_candidate.json"
)
REVIEW_PATH = (
    ROOT
    / ".work/affordance_larql_candidate_reviews/unsupported_file_target_authority/unsupported_file_target_authority_candidate_review.json"
)


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


def load_packet_module():
    from local_harness.affordance_larql_unsupported_file_target_authority_runtime_rule_packet import build_packet

    return build_packet


def test_help_works():
    result = run_packet("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_writes_expected_packet_json_and_markdown(tmp_path):
    candidate, review = good_inputs(tmp_path)
    result = run_packet("--candidate", candidate, "--candidate-review", review, "--out", tmp_path / "out")
    assert result.returncode == 0
    payload = json.loads(
        (tmp_path / "out/unsupported_file_target_authority_runtime_rule_packet.json").read_text(encoding="utf-8")
    )
    assert (tmp_path / "out/unsupported_file_target_authority_runtime_rule_packet.md").exists()
    assert payload["report_type"] == "affordance_larql_runtime_rule_packet.v0"
    assert payload["packet_status"] == "draft_not_installed"
    assert payload["packet_verdict"] == "ready_for_runtime_rule_packet_review"
    assert payload["allowed_next_step"] == "review_unsupported_file_target_authority_runtime_rule_packet"
    assert payload["source_failure_id"] == "unsupported_file_target_authority.real"
    assert payload["candidate_id"] == "unsupported_file_target_authority"
    assert payload["rule_id"] == "unsupported_file_target_authority_v0"
    assert payload["runtime_rule_install_authorized"] is False
    assert payload["runtime_rule_modification_authorized"] is False
    assert payload["model_call_performed"] is False
    assert payload["training_data_written"] is False
    assert payload["dataset_artifact_written"] is False
    assert payload["durable_memory_written"] is False
    assert payload["candidate_promotion_authorized"] is False
    assert payload["model_weights_mutated"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert payload["candidate_sha256"]
    assert payload["candidate_review_sha256"]


def test_rejects_missing_candidate(tmp_path):
    review = tmp_path / "review.json"
    review.write_text(REVIEW_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    result = run_packet("--candidate", tmp_path / "missing.json", "--candidate-review", review, "--out", tmp_path / "out")
    assert result.returncode == 0
    payload = json.loads(
        (tmp_path / "out/unsupported_file_target_authority_runtime_rule_packet.json").read_text(encoding="utf-8")
    )
    assert payload["checks"]["candidate_exists"] is False
    assert payload["packet_verdict"] == "runtime_rule_packet_rejected"


def test_rejects_missing_candidate_review(tmp_path):
    candidate = tmp_path / "candidate.json"
    candidate.write_text(CANDIDATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    result = run_packet("--candidate", candidate, "--candidate-review", tmp_path / "missing.json", "--out", tmp_path / "out")
    assert result.returncode == 0
    payload = json.loads(
        (tmp_path / "out/unsupported_file_target_authority_runtime_rule_packet.json").read_text(encoding="utf-8")
    )
    assert payload["checks"]["review_exists"] is False
    assert payload["packet_verdict"] == "runtime_rule_packet_rejected"


def test_rejects_wrong_candidate_fields():
    build_packet = load_packet_module()
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    bad_map = {
        "report_type": "wrong",
        "candidate_status": "wrong",
        "candidate_verdict": "wrong",
        "allowed_next_step": "wrong",
        "source_failure_id": "wrong.real",
        "candidate_id": "wrong",
        "rule_id": "wrong_v0",
    }
    for field, value in bad_map.items():
        bad = json.loads(json.dumps(candidate))
        bad[field] = value
        packet = build_packet(bad, review, candidate_sha256="a", candidate_review_sha256="b")
        assert packet["packet_verdict"] == "runtime_rule_packet_rejected"


def test_rejects_wrong_review_fields():
    build_packet = load_packet_module()
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    bad_map = {
        "report_type": "wrong",
        "review_status": "wrong",
        "review_verdict": "wrong",
        "allowed_next_step": "wrong",
        "source_failure_id": "wrong.real",
        "candidate_id": "wrong",
        "rule_id": "wrong_v0",
    }
    for field, value in bad_map.items():
        bad = json.loads(json.dumps(review))
        bad[field] = value
        packet = build_packet(candidate, bad, candidate_sha256="a", candidate_review_sha256="b")
        assert packet["packet_verdict"] == "runtime_rule_packet_rejected"


def test_rejects_authority_or_model_flags():
    build_packet = load_packet_module()
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    candidate_flags = (
        "model_call_performed",
        "training_data_written",
        "dataset_artifact_written",
        "durable_memory_written",
        "candidate_promotion_authorized",
        "runtime_rule_modification_authorized",
        "model_weights_mutated",
        "automatic_failure_to_curriculum_capture_authorized",
    )
    for field in candidate_flags:
        bad = json.loads(json.dumps(candidate))
        bad[field] = True
        packet = build_packet(bad, review, candidate_sha256="a", candidate_review_sha256="b")
        assert packet["packet_verdict"] == "runtime_rule_packet_rejected"
    review_flags = (
        "model_call_performed_in_review",
        "training_data_written",
        "dataset_artifact_written",
        "durable_memory_written",
        "candidate_promotion_authorized",
        "runtime_rule_modification_authorized",
        "model_weights_mutated",
        "automatic_failure_to_curriculum_capture_authorized",
    )
    for field in review_flags:
        bad = json.loads(json.dumps(review))
        bad[field] = True
        packet = build_packet(candidate, bad, candidate_sha256="a", candidate_review_sha256="b")
        assert packet["packet_verdict"] == "runtime_rule_packet_rejected"


def test_draft_runtime_rule_contains_expected_content():
    build_packet = load_packet_module()
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    packet = build_packet(candidate, review, candidate_sha256="a", candidate_review_sha256="b")
    draft = packet["draft_runtime_rule"]
    assert (
        draft["summary"]
        == "An allowed_files list authorizes only listed target files; it does not authorize modifying adjacent, generated, unrelated, or any other repo files."
    )
    assert draft["applies_when"] == [
        "allowed_files list is present",
        "a patch packet names allowed files",
        "a checklist names target files",
        "a requested target file is not in allowed_files",
        "a model response proposes adjacent file edits",
        "a workflow is tempted to do broader cleanup while here",
    ]
    assert draft["blocks"] == [
        "modify any repo file",
        "touch adjacent files",
        "update generated files",
        "fix unrelated files",
        "expand patch scope",
        "broader cleanup",
        "while here",
        "also fix",
        "any out-of-scope file modification unsupported by allowed_files",
    ]
    assert draft["required_response_behavior"] == [
        "state the allowed_files boundary",
        "state only listed files are authorized targets",
        "outside file modification is not authorized",
        "set outside_file_modification_authorized to false",
        "hold adjacent generated unrelated file modifications",
        "request explicit scope expansion or review before out-of-scope edits",
        "preserve allowed_files list, requested target file, and out-of-scope file",
    ]
    assert draft["json_contract"] == {
        "evidence_boundary": "allowed files only",
        "allowed_claim": "only listed files are authorized targets",
        "outside_file_modification_authorized": False,
        "held_claims": [
            "modify any repo file",
            "touch adjacent files",
            "update generated files",
            "fix unrelated files",
            "expand patch scope",
        ],
        "required_next_step": "request explicit scope expansion or review",
        "evidence_to_preserve": [
            "allowed_files list",
            "requested target file",
            "out-of-scope file",
        ],
    }


def test_packet_remains_draft_and_no_model_call(tmp_path):
    candidate, review = good_inputs(tmp_path)
    result = run_packet("--candidate", candidate, "--candidate-review", review, "--out", tmp_path / "out")
    assert result.returncode == 0
    payload = json.loads(
        (tmp_path / "out/unsupported_file_target_authority_runtime_rule_packet.json").read_text(encoding="utf-8")
    )
    assert payload["packet_status"] == "draft_not_installed"
    assert payload["runtime_rule_install_authorized"] is False
    assert payload["runtime_rule_modification_authorized"] is False
    assert payload["model_call_performed"] is False
