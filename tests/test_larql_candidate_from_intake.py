from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_candidate_from_intake.py"


def review_payload() -> dict:
    return {
        "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
        "authority_boundaries_preserved": True,
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "evidence_boundary": "single synthetic noisy note only",
        "held_actions": [
            "promote candidate",
            "modify registry",
            "install runtime rule",
            "run live probe",
            "write training data",
            "write dataset artifact",
            "write durable memory",
            "mutate model weights",
            "modify runtime rules",
            "automatic failure-to-curriculum capture",
        ],
        "model_call_performed": False,
        "notes": [
            "Independent review is model-free.",
            "The intake scaffold remains held for supervised candidate drafting.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
        ],
        "proposed_rule_family_id": "unsupported_file_target_authority",
        "provenance": {
            "source_note_excerpt": "ugh sorry, this is messy: I checked the allowed_files list and it looks like docs/ROADMAP.md is the thing we should probably touch too. While we're here, maybe broaden cleanup to adjacent docs and maybe the generated bits as well. Please keep the scope bounded and do not turn this into repo-wide cleanup.",
            "source_note_path": "tests/fixtures/larql_intake_smoke_noisy_note.txt",
            "source_note_sha256": "fbe869a7d5bb1f2107c14d70584f6db765b2d992a2346bf10eae70aa5e12b227",
        },
        "registry_promotion_authorized": False,
        "required_next_step": "draft_larql_candidate_from_reviewed_intake",
        "report_type": "larql_intake_review.v0",
        "review_scope": "intake candidate scaffold only",
        "review_status": "accepted_for_candidate_drafting",
        "runtime_rule_creation_authorized": False,
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
    }


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_review(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_review_artifact_payload(tmp_path):
    out_root = tmp_path / "out"
    review_path = write_review(tmp_path, review_payload())
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_001", "--out-root", out_root)
    assert result.returncode == 0
    payload = json.loads((out_root / "candidate_from_intake_001/larql_candidate_draft.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "larql_candidate_from_intake.v0"
    assert payload["candidate_status"] == "held_for_candidate_review"
    assert payload["source_review_artifact_path"].endswith("review.json")
    assert payload["source_failure_id"] == "synthetic_unsupported_file_target_authority_noisy_note.real"
    assert payload["candidate_id"] == "larql_intake_smoke_unsupported_file_target_authority_candidate"
    assert payload["proposed_rule_family_id"] == "unsupported_file_target_authority"
    assert payload["required_next_step"] == "supervised_candidate_review"
    assert payload["registry_promotion_authorized"] is False
    assert payload["runtime_rule_creation_authorized"] is False
    assert payload["runtime_rule_install_authorized"] is False
    assert payload["model_call_performed"] is False
    assert payload["candidate_promotion_authorized"] is False
    assert payload["authority_boundaries_preserved"] is True
    assert payload["drafted_candidate"]["review_status"] == "held_for_candidate_review"


def test_writes_candidate_draft_markdown(tmp_path):
    out_root = tmp_path / "out"
    review_path = write_review(tmp_path, review_payload())
    run_script("--review", review_path, "--run-id", "candidate_from_intake_002", "--out-root", out_root)
    assert (out_root / "candidate_from_intake_002/larql_candidate_draft.md").exists()


def test_candidate_draft_includes_provenance(tmp_path):
    out_root = tmp_path / "out"
    review_path = write_review(tmp_path, review_payload())
    run_script("--review", review_path, "--run-id", "candidate_from_intake_003", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_from_intake_003/larql_candidate_draft.json").read_text(encoding="utf-8"))
    provenance = payload["provenance"]
    assert provenance["source_note_path"].endswith("larql_intake_smoke_noisy_note.txt")
    assert isinstance(provenance["source_note_sha256"], str) and provenance["source_note_sha256"]


def test_candidate_draft_keeps_registry_promotion_false(tmp_path):
    out_root = tmp_path / "out"
    review_path = write_review(tmp_path, review_payload())
    run_script("--review", review_path, "--run-id", "candidate_from_intake_004", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_from_intake_004/larql_candidate_draft.json").read_text(encoding="utf-8"))
    assert payload["registry_promotion_authorized"] is False


def test_candidate_draft_keeps_runtime_rule_creation_false(tmp_path):
    out_root = tmp_path / "out"
    review_path = write_review(tmp_path, review_payload())
    run_script("--review", review_path, "--run-id", "candidate_from_intake_005", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_from_intake_005/larql_candidate_draft.json").read_text(encoding="utf-8"))
    assert payload["runtime_rule_creation_authorized"] is False


def test_candidate_draft_keeps_model_call_false(tmp_path):
    out_root = tmp_path / "out"
    review_path = write_review(tmp_path, review_payload())
    run_script("--review", review_path, "--run-id", "candidate_from_intake_006", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_from_intake_006/larql_candidate_draft.json").read_text(encoding="utf-8"))
    assert payload["model_call_performed"] is False


def test_rejects_wrong_report_type(tmp_path):
    payload = review_payload()
    payload["report_type"] = "wrong"
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_007", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_non_accepted_review_status(tmp_path):
    payload = review_payload()
    payload["review_status"] = "rejected"
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_008", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_wrong_required_next_step(tmp_path):
    payload = review_payload()
    payload["required_next_step"] = "something_else"
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_009", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_required_field(tmp_path):
    payload = review_payload()
    del payload["candidate_id"]
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_010", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_provenance_hash(tmp_path):
    payload = review_payload()
    del payload["provenance"]["source_note_sha256"]
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_011", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_registry_promotion_authorization(tmp_path):
    payload = review_payload()
    payload["registry_promotion_authorized"] = True
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_012", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_runtime_rule_creation_authorization(tmp_path):
    payload = review_payload()
    payload["runtime_rule_creation_authorized"] = True
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_013", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_model_call_performed_true(tmp_path):
    payload = review_payload()
    payload["model_call_performed"] = True
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_014", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_review_performs_no_model_call(tmp_path):
    review_path = write_review(tmp_path, review_payload())
    result = run_script("--review", review_path, "--run-id", "candidate_from_intake_015", "--out-root", tmp_path / "out")
    assert result.returncode == 0
    assert "model" not in result.stderr.lower()
