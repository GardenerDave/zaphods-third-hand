from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_intake_review.py"
SMOKE_PATH = ROOT / ".work/larql_intake_smoke/intake_smoke_001/larql_intake_smoke_candidate.json"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_candidate(tmp_path: Path, payload: dict) -> Path:
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return candidate_path


def candidate_payload() -> dict:
    return json.loads(SMOKE_PATH.read_text(encoding="utf-8"))


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_real_intake_smoke_candidate_shape_using_temp_copy(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    result = run_review("--candidate", candidate_path, "--run-id", "review-001", "--out-root", out_root)
    assert result.returncode == 0
    payload = json.loads((out_root / "review-001/larql_intake_review.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "larql_intake_review.v0"
    assert payload["review_status"] == "accepted_for_candidate_drafting"
    assert payload["review_scope"] == "intake candidate scaffold only"
    assert payload["source_failure_id"] == "synthetic_unsupported_file_target_authority_noisy_note.real"
    assert payload["candidate_id"] == "larql_intake_smoke_unsupported_file_target_authority_candidate"
    assert payload["proposed_rule_family_id"] == "unsupported_file_target_authority"
    assert payload["required_next_step"] == "draft_larql_candidate_from_reviewed_intake"
    assert payload["registry_promotion_authorized"] is False
    assert payload["runtime_rule_creation_authorized"] is False
    assert payload["model_call_performed"] is False
    assert payload["authority_boundaries_preserved"] is True


def test_review_artifact_includes_provenance(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "review-002", "--out-root", out_root)
    payload = json.loads((out_root / "review-002/larql_intake_review.json").read_text(encoding="utf-8"))
    provenance = payload["provenance"]
    assert provenance["source_note_path"].endswith("larql_intake_smoke_noisy_note.txt")
    assert isinstance(provenance["source_note_sha256"], str) and provenance["source_note_sha256"]
    assert "source_note_excerpt" in provenance


def test_review_keeps_registry_promotion_false(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "review-003", "--out-root", out_root)
    payload = json.loads((out_root / "review-003/larql_intake_review.json").read_text(encoding="utf-8"))
    assert payload["registry_promotion_authorized"] is False


def test_review_keeps_model_call_false(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "review-004", "--out-root", out_root)
    payload = json.loads((out_root / "review-004/larql_intake_review.json").read_text(encoding="utf-8"))
    assert payload["model_call_performed"] is False


def test_rejects_wrong_report_type(tmp_path):
    payload = candidate_payload()
    payload["report_type"] = "wrong"
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "review-005", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_non_held_candidate_status(tmp_path):
    payload = candidate_payload()
    payload["candidate_status"] = "draft_not_installed"
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "review-006", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_required_field(tmp_path):
    payload = candidate_payload()
    del payload["proposed_rule_family_id"]
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "review-007", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_provenance_hash(tmp_path):
    payload = candidate_payload()
    del payload["provenance"]["source_note_sha256"]
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "review-008", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_authority_boundary_that_authorizes_registry_promotion(tmp_path):
    payload = candidate_payload()
    payload["authority_boundaries"]["registry_promotion_authorized"] = True
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "review-009", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_authority_boundary_that_indicates_model_call_performed(tmp_path):
    payload = candidate_payload()
    payload["authority_boundaries"]["model_call_performed"] = True
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "review-010", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_review_performs_no_model_call(tmp_path):
    candidate_path = write_candidate(tmp_path, candidate_payload())
    result = run_review("--candidate", candidate_path, "--run-id", "review-011", "--out-root", tmp_path / "out")
    assert result.returncode == 0
    assert "model" not in result.stderr.lower()
