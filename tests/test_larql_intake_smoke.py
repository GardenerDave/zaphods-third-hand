from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_intake_smoke.py"
FIXTURE = ROOT / "tests/fixtures/larql_intake_smoke_noisy_note.txt"


def run_smoke(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_smoke("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_smoke_writes_candidate_scaffold(tmp_path):
    out_root = tmp_path / "out"
    result = run_smoke("--input", FIXTURE, "--run-id", "smoke-001", "--out-root", out_root)
    assert result.returncode == 0
    payload = json.loads((out_root / "smoke-001/larql_intake_smoke_candidate.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "larql_intake_smoke.v0"
    assert payload["status"] == "held_for_supervised_review"
    assert payload["candidate_status"] == "held_for_supervised_review"
    assert payload["source_failure_id"] == "synthetic_unsupported_file_target_authority_noisy_note.real"
    assert payload["candidate_id"] == "larql_intake_smoke_unsupported_file_target_authority_candidate"
    assert payload["proposed_rule_family_id"] == "unsupported_file_target_authority"
    assert payload["evidence_boundary"] == "single synthetic noisy note only"
    assert payload["allowed_claim"] == "the noisy note can be reduced into a bounded candidate scaffold"
    assert payload["required_next_step"] == "supervised review of the candidate scaffold"
    assert payload["registry_promotion_authorized"] is False
    assert payload["authority_boundaries"]["registry_promotion_authorized"] is False
    assert payload["authority_boundaries"]["runtime_rule_creation_authorized"] is False
    assert payload["authority_boundaries"]["runtime_rule_install_authorized"] is False
    assert payload["authority_boundaries"]["model_call_performed"] is False
    assert payload["authority_boundaries"]["training_data_written"] is False
    assert payload["authority_boundaries"]["dataset_artifact_written"] is False
    assert payload["authority_boundaries"]["durable_memory_written"] is False
    assert payload["authority_boundaries"]["candidate_promotion_authorized"] is False
    assert payload["authority_boundaries"]["model_weights_mutated"] is False
    assert payload["authority_boundaries"]["runtime_rule_modification_authorized"] is False
    assert payload["authority_boundaries"]["automatic_failure_to_curriculum_capture_authorized"] is False
    assert "noisy note" in payload["notes"][0].lower()


def test_smoke_records_provenance(tmp_path):
    out_root = tmp_path / "out"
    run_smoke("--input", FIXTURE, "--run-id", "smoke-002", "--out-root", out_root)
    payload = json.loads((out_root / "smoke-002/larql_intake_smoke_candidate.json").read_text(encoding="utf-8"))
    provenance = payload["provenance"]
    assert provenance["source_note_path"].endswith("larql_intake_smoke_noisy_note.txt")
    assert isinstance(provenance["source_note_sha256"], str) and provenance["source_note_sha256"]
    assert "allowed_files" in provenance["source_note_excerpt"]


def test_smoke_identifies_bounded_failure_pattern(tmp_path):
    out_root = tmp_path / "out"
    run_smoke("--input", FIXTURE, "--run-id", "smoke-003", "--out-root", out_root)
    payload = json.loads((out_root / "smoke-003/larql_intake_smoke_candidate.json").read_text(encoding="utf-8"))
    summary = payload["summary"]
    assert summary["bounded_failure_pattern"] == "unsupported_file_target_authority"
    assert "allowed_files_boundary" in summary["detected_signals"]
    assert "requested_target_outside_allowed_files" in summary["detected_signals"]
    assert "while_here_cleanup_pressure" in summary["detected_signals"]
    assert "scope_expansion_pressure" in summary["detected_signals"]


def test_smoke_does_not_call_a_model(tmp_path):
    out_root = tmp_path / "out"
    result = run_smoke("--input", FIXTURE, "--run-id", "smoke-004", "--out-root", out_root)
    assert result.returncode == 0
    assert "model" not in result.stderr.lower()
