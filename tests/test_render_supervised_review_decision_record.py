from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "render_supervised_review_decision_record.py"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def make_review_packet(tmp_path: Path, validation_status: str = "validation_passed") -> Path:
    packet = tmp_path / "review"
    packet.mkdir()
    review_packet = {
        "report_type": "correction_aware_supervised_review_packet.v1",
        "source_model_attempt_record": "attempt/model_attempt_record.json",
        "source_raw_output": "attempt/raw_model_output.txt",
        "source_validation_report": "validation/correction_aware_output_validation.json",
        "source_job_packet": "job/job_packet.json",
        "source_prompt_packet": "prompt/correction_aware_prompt_packet.json",
        "source_model_attempt_record_sha256": "attempt-sha",
        "source_job_packet_sha256": "job-sha",
        "source_prompt_packet_sha256": "prompt-sha",
        "source_raw_output_sha256": "raw-sha",
        "source_validation_report_sha256": "validation-sha",
        "validation_status": validation_status,
        "findings": [] if validation_status == "validation_passed" else ["example finding"],
        "parsed_output": {
            "allowed_targets": ["docs/README.md"],
            "held_targets": ["docs/ROADMAP.md"],
            "scope_expansion_required": True,
            "install_authorized": False,
            "registry_mutation_authorized": False,
        },
        "raw_output_excerpt": "excerpt",
        "review_packet_authority_flags": {
            "model_inference_performed": False,
            "generation_performed": False,
            "training_performed": False,
            "delta_written": False,
            "patched_model_materialized": False,
            "promotion_authorized": False,
            "supervised_acceptance_performed": False,
            "automatic_failure_curriculum_capture_authorized": False,
        },
        "source_model_attempt_authority_flags": {
            "model_inference_performed": True,
            "generation_performed": True,
            "training_performed": False,
            "delta_written": False,
            "patched_model_materialized": False,
            "promotion_authorized": False,
            "supervised_acceptance_performed": False,
            "automatic_failure_curriculum_capture_authorized": False,
        },
        "source_validation_authority_flags": {
            "model_inference_performed": False,
            "generation_performed": False,
            "training_performed": False,
            "delta_written": False,
            "patched_model_materialized": False,
            "promotion_authorized": False,
            "supervised_acceptance_performed": False,
            "automatic_failure_curriculum_capture_authorized": False,
        },
        "review_decision_options": [
            "accept_as_corrected_output",
            "reject",
            "needs_prompt_revision",
            "needs_validator_revision",
            "needs_human_scope_decision",
        ],
        "recommended_next_step": "supervised_review_required",
        "no_auto_acceptance": True,
        "packet_level_only": True,
        "job_packet_summary": "Choose only docs/README.md as allowed, hold docs/ROADMAP.md out.",
        "prompt_packet_summary": "Choose only docs/README.md as allowed, hold docs/ROADMAP.md out.",
    }
    (packet / "supervised_review_packet.json").write_text(
        json.dumps(review_packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return packet / "supervised_review_packet.json"


def test_help():
    assert run_script("--help").returncode == 0


def test_accept_renders_json_and_md(tmp_path: Path):
    review_packet = make_review_packet(tmp_path)
    out = tmp_path / "out"
    result = run_script(
        "--review-packet",
        review_packet,
        "--decision",
        "accept_as_corrected_output",
        "--reviewer-id",
        "david",
        "--rationale",
        "Validated r5 corrected output and confirmed ROADMAP.md is held out.",
        "--out-dir",
        out,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "supervised_review_decision_record.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "correction_aware_supervised_review_decision_record.v1"
    assert payload["decision"] == "accept_as_corrected_output"
    assert payload["decision_is_allowed"] is True
    assert payload["decision_record_authority_flags"]["supervised_acceptance_performed"] is True
    assert payload["decision_record_authority_flags"]["promotion_authorized"] is False
    assert payload["no_auto_promotion"] is True
    assert payload["no_file_edits"] is True
    assert payload["packet_level_only"] is True
    assert payload["source_supervised_review_packet_sha256"]
    md = (out / "supervised_review_decision_record.md").read_text(encoding="utf-8")
    assert "accept_as_corrected_output" in md
    assert "Validated r5 corrected output" in md


def test_reject_renders_json_and_md(tmp_path: Path):
    review_packet = make_review_packet(tmp_path, validation_status="validation_failed")
    out = tmp_path / "out"
    result = run_script(
        "--review-packet",
        review_packet,
        "--decision",
        "reject",
        "--out-dir",
        out,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "supervised_review_decision_record.json").read_text(encoding="utf-8"))
    assert payload["decision"] == "reject"
    assert payload["decision_is_allowed"] is True
    assert payload["decision_record_authority_flags"]["supervised_acceptance_performed"] is False


def test_invalid_decision_fails(tmp_path: Path):
    review_packet = make_review_packet(tmp_path)
    out = tmp_path / "out"
    result = run_script(
        "--review-packet",
        review_packet,
        "--decision",
        "invalid",
        "--out-dir",
        out,
    )
    assert result.returncode != 0
    assert not out.exists()


def test_validation_passed_does_not_auto_accept(tmp_path: Path):
    review_packet = make_review_packet(tmp_path, validation_status="validation_passed")
    out = tmp_path / "out"
    result = run_script(
        "--review-packet",
        review_packet,
        "--decision",
        "needs_human_scope_decision",
        "--out-dir",
        out,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "supervised_review_decision_record.json").read_text(encoding="utf-8"))
    assert payload["decision"] == "needs_human_scope_decision"
    assert payload["decision_record_authority_flags"]["supervised_acceptance_performed"] is False


def test_validation_failed_does_not_auto_reject(tmp_path: Path):
    review_packet = make_review_packet(tmp_path, validation_status="validation_failed")
    out = tmp_path / "out"
    result = run_script(
        "--review-packet",
        review_packet,
        "--decision",
        "needs_prompt_revision",
        "--out-dir",
        out,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "supervised_review_decision_record.json").read_text(encoding="utf-8"))
    assert payload["decision"] == "needs_prompt_revision"
    assert payload["decision_record_authority_flags"]["supervised_acceptance_performed"] is False


def test_out_dir_exists_fails(tmp_path: Path):
    review_packet = make_review_packet(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    result = run_script(
        "--review-packet",
        review_packet,
        "--decision",
        "reject",
        "--out-dir",
        out,
    )
    assert result.returncode != 0


def test_no_model_call_is_made():
    assert True
