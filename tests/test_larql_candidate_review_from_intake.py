from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_candidate_review_from_intake.py"


def candidate_payload() -> dict:
    return {
        "report_type": "larql_candidate_from_intake.v0",
        "candidate_status": "held_for_candidate_review",
        "source_review_artifact_path": ".work/larql_intake_reviews/intake_review_001/larql_intake_review.json",
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "proposed_rule_family_id": "unsupported_file_target_authority",
        "evidence_boundary": "single synthetic noisy note only",
        "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
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
        "required_next_step": "supervised_candidate_review",
        "registry_promotion_authorized": False,
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "model_call_performed": False,
        "candidate_promotion_authorized": False,
        "authority_boundaries_preserved": True,
        "provenance": {
            "source_note_excerpt": (
                "ugh sorry, this is messy: I checked the allowed_files list and it looks like "
                "docs/ROADMAP.md is the thing we should probably touch too. While we're here, "
                "maybe broaden cleanup to adjacent docs and maybe the generated bits as well. "
                "Please keep the scope bounded and do not turn this into repo-wide cleanup."
            ),
            "source_note_path": "tests/fixtures/larql_intake_smoke_noisy_note.txt",
            "source_note_sha256": "fbe869a7d5bb1f2107c14d70584f6db765b2d992a2346bf10eae70aa5e12b227",
        },
        "drafted_candidate": {
            "candidate_family_id": "unsupported_file_target_authority",
            "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
            "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
            "failure_pattern": "allowed_files boundary treated as exclusive authority",
            "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
            "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
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
            "evidence_boundary": "single synthetic noisy note only",
            "required_next_step": "supervised_candidate_review",
            "review_status": "held_for_candidate_review",
        },
        "notes": [
            "Independent candidate drafting is model-free.",
            "The drafted candidate remains held for supervised review.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
        ],
    }


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_candidate(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_candidate_draft_payload(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_001", "--out-root", out_root)
    assert result.returncode == 0
    payload = json.loads((out_root / "candidate_review_from_intake_001/larql_candidate_review.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "larql_candidate_review_from_intake.v0"
    assert payload["review_status"] == "accepted_for_runtime_rule_packet_drafting"
    assert payload["review_scope"] == "candidate draft from reviewed intake only"
    assert payload["source_failure_id"] == "synthetic_unsupported_file_target_authority_noisy_note.real"
    assert payload["candidate_id"] == "larql_intake_smoke_unsupported_file_target_authority_candidate"
    assert payload["proposed_rule_family_id"] == "unsupported_file_target_authority"
    assert payload["required_next_step"] == "draft_runtime_rule_packet_from_reviewed_candidate"
    assert payload["registry_promotion_authorized"] is False
    assert payload["runtime_rule_creation_authorized"] is False
    assert payload["runtime_rule_install_authorized"] is False
    assert payload["model_call_performed"] is False
    assert payload["candidate_promotion_authorized"] is False
    assert payload["authority_boundaries_preserved"] is True
    assert payload["reviewed_candidate"]["review_verdict"] == "accepted_for_runtime_rule_packet_drafting"


def test_writes_candidate_review_markdown(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_002", "--out-root", out_root)
    assert (out_root / "candidate_review_from_intake_002/larql_candidate_review.md").exists()


def test_review_artifact_includes_provenance(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_003", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_review_from_intake_003/larql_candidate_review.json").read_text(encoding="utf-8"))
    provenance = payload["provenance"]
    assert provenance["source_note_path"].endswith("larql_intake_smoke_noisy_note.txt")
    assert isinstance(provenance["source_note_sha256"], str) and provenance["source_note_sha256"]


def test_review_keeps_registry_promotion_false(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_004", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_review_from_intake_004/larql_candidate_review.json").read_text(encoding="utf-8"))
    assert payload["registry_promotion_authorized"] is False


def test_review_keeps_runtime_rule_creation_false(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_005", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_review_from_intake_005/larql_candidate_review.json").read_text(encoding="utf-8"))
    assert payload["runtime_rule_creation_authorized"] is False


def test_review_keeps_runtime_rule_install_false(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_006", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_review_from_intake_006/larql_candidate_review.json").read_text(encoding="utf-8"))
    assert payload["runtime_rule_install_authorized"] is False


def test_review_keeps_model_call_false(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_007", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_review_from_intake_007/larql_candidate_review.json").read_text(encoding="utf-8"))
    assert payload["model_call_performed"] is False


def test_review_keeps_candidate_promotion_false(tmp_path):
    out_root = tmp_path / "out"
    candidate_path = write_candidate(tmp_path, candidate_payload())
    run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_008", "--out-root", out_root)
    payload = json.loads((out_root / "candidate_review_from_intake_008/larql_candidate_review.json").read_text(encoding="utf-8"))
    assert payload["candidate_promotion_authorized"] is False


def test_rejects_wrong_report_type(tmp_path):
    payload = candidate_payload()
    payload["report_type"] = "wrong"
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_009", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_non_held_candidate_status(tmp_path):
    payload = candidate_payload()
    payload["candidate_status"] = "draft_not_installed"
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_010", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_wrong_required_next_step(tmp_path):
    payload = candidate_payload()
    payload["required_next_step"] = "something_else"
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_011", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_required_field(tmp_path):
    payload = candidate_payload()
    del payload["candidate_id"]
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_012", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_provenance_hash(tmp_path):
    payload = candidate_payload()
    del payload["provenance"]["source_note_sha256"]
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_013", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_registry_promotion_authorization(tmp_path):
    payload = candidate_payload()
    payload["registry_promotion_authorized"] = True
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_014", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_runtime_rule_creation_authorization(tmp_path):
    payload = candidate_payload()
    payload["runtime_rule_creation_authorized"] = True
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_015", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_runtime_rule_install_authorization(tmp_path):
    payload = candidate_payload()
    payload["runtime_rule_install_authorized"] = True
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_016", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_model_call_performed_true(tmp_path):
    payload = candidate_payload()
    payload["model_call_performed"] = True
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_017", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_candidate_promotion_authorization(tmp_path):
    payload = candidate_payload()
    payload["candidate_promotion_authorized"] = True
    candidate_path = write_candidate(tmp_path, payload)
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_018", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_review_performs_no_model_call(tmp_path):
    candidate_path = write_candidate(tmp_path, candidate_payload())
    result = run_review("--candidate", candidate_path, "--run-id", "candidate_review_from_intake_019", "--out-root", tmp_path / "out")
    assert result.returncode == 0
    assert "model" not in result.stderr.lower()
