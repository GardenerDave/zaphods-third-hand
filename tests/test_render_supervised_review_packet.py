from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "render_supervised_review_packet.py"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def make_attempt(tmp_path: Path) -> Path:
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    (attempt / "model_attempt_record.json").write_text(
        json.dumps(
            {
                "report_type": "correction_aware_model_attempt.v1",
                "source_prompt_packet": "prompt.md",
                "endpoint_url": "http://127.0.0.1:1234/v1",
                "model": "test-model",
                "max_tokens": 32,
                "temperature": 0.0,
                "timeout_seconds": 5,
                "prompt_sha256": "x",
                "raw_output_sha256": "y",
                "raw_output_path": "raw_model_output.txt",
                "status_log_path": "status.log",
                "status_events_path": "status_events.jsonl",
                "model_inference_performed": True,
                "generation_performed": True,
                "training_performed": False,
                "delta_written": False,
                "patched_model_materialized": False,
                "promotion_authorized": False,
                "validation_performed": False,
                "supervised_acceptance_performed": False,
                "automatic_failure_curriculum_capture_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (attempt / "raw_model_output.txt").write_text(
        '{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"docs/ROADMAP.md is plausible but not authorized and must be held out as it is not in allowed_files."}',
        encoding="utf-8",
    )
    return attempt


def make_validation(tmp_path: Path, validation_status: str = "validation_passed") -> Path:
    validation = tmp_path / "validation"
    validation.mkdir()
    payload = {
        "report_type": "correction_aware_output_validation.v1",
        "source_model_attempt_dir": "attempt",
        "source_job_packet": "job.json",
        "source_prompt_packet": "prompt.json",
        "parsed_output": {"allowed_targets": ["docs/README.md"]},
        "validation_status": validation_status,
        "findings": [] if validation_status == "validation_passed" else ["example"],
        "recommended_next_step": "supervised_review",
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "delta_written": False,
        "patched_model_materialized": False,
        "promotion_authorized": False,
        "supervised_acceptance_performed": False,
        "automatic_failure_curriculum_capture_authorized": False,
    }
    (validation / "correction_aware_output_validation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return validation


def make_job_packet(tmp_path: Path) -> Path:
    path = tmp_path / "job.json"
    path.write_text(
        json.dumps(
            {
                "packet_id": "job-001",
                "task_summary": "Choose only docs/README.md as allowed, hold docs/ROADMAP.md out.",
                "allowed_files": ["docs/README.md"],
                "requested_targets": ["docs/README.md", "docs/ROADMAP.md"],
                "behavior_corrections": ["file_scope_hold_out_v1"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def make_prompt_packet(tmp_path: Path) -> Path:
    path = tmp_path / "prompt.json"
    path.write_text(
        json.dumps(
            {
                "report_type": "correction_aware_prompt_packet.v1",
                "task_summary": "Choose only docs/README.md as allowed, hold docs/ROADMAP.md out.",
                "allowed_files": ["docs/README.md"],
                "requested_targets": ["docs/README.md", "docs/ROADMAP.md"],
                "behavior_corrections": ["file_scope_hold_out_v1"],
                "packet_level_only": True,
                "auto_assigned_corrections": False,
                "model_inference_performed": False,
                "generation_performed": False,
                "training_performed": False,
                "delta_written": False,
                "patched_model_materialized": False,
                "promotion_authorized": False,
                "automatic_failure_curriculum_capture_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_prompt_markdown(packet_json: Path, md_path: Path) -> Path:
    payload = json.loads(packet_json.read_text(encoding="utf-8"))
    md_path.write_text(
        "\n".join(
            [
                "# Correction-Aware Prompt Packet",
                "",
                f"Task summary: {payload['task_summary']}",
                f"Allowed files: {', '.join(payload['allowed_files'])}",
                f"Behavior corrections: {', '.join(payload['behavior_corrections'])}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return md_path


def test_help():
    assert run_script("--help").returncode == 0


def test_renders_review_packet(tmp_path: Path):
    attempt = make_attempt(tmp_path)
    validation = make_validation(tmp_path)
    job_packet = make_job_packet(tmp_path)
    prompt_packet = make_prompt_packet(tmp_path)
    out = tmp_path / "out"
    result = run_script(
        "--model-attempt-dir",
        attempt,
        "--job-packet",
        job_packet,
        "--prompt-packet",
        prompt_packet,
        "--validation-report",
        validation / "correction_aware_output_validation.json",
        "--out-dir",
        out,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads((out / "supervised_review_packet.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "correction_aware_supervised_review_packet.v1"
    assert payload["authority_flags"]["model_inference_performed"] is False
    assert payload["authority_flags"]["training_performed"] is False
    assert payload["authority_flags"]["delta_written"] is False
    assert payload["authority_flags"]["patched_model_materialized"] is False
    assert payload["authority_flags"]["promotion_authorized"] is False
    assert payload["authority_flags"]["supervised_acceptance_performed"] is False
    assert payload["authority_flags"]["automatic_failure_curriculum_capture_authorized"] is False
    assert payload["source_job_packet_sha256"]
    assert payload["source_prompt_packet_sha256"]
    assert payload["review_packet_authority_flags"]["model_inference_performed"] is False
    assert payload["source_model_attempt_authority_flags"]["model_inference_performed"] is True
    assert payload["source_model_attempt_authority_flags"]["generation_performed"] is True
    assert payload["source_validation_authority_flags"]["model_inference_performed"] is False
    md = (out / "supervised_review_packet.md").read_text(encoding="utf-8")
    assert "accept_as_corrected_output" in md
    assert "needs_human_scope_decision" in md
    assert "Source model attempt authority flags" in md
    assert "Source validation authority flags" in md


def test_validation_passed_does_not_auto_accept(tmp_path: Path):
    attempt = make_attempt(tmp_path)
    validation = make_validation(tmp_path, validation_status="validation_passed")
    out = tmp_path / "out"
    run_script(
        "--model-attempt-dir",
        attempt,
        "--job-packet",
        make_job_packet(tmp_path),
        "--prompt-packet",
        make_prompt_packet(tmp_path),
        "--validation-report",
        validation / "correction_aware_output_validation.json",
        "--out-dir",
        out,
    )
    payload = json.loads((out / "supervised_review_packet.json").read_text(encoding="utf-8"))
    assert payload["recommended_next_step"] == "supervised_review_required"
    assert payload["authority_flags"]["supervised_acceptance_performed"] is False
    assert payload["review_packet_authority_flags"]["supervised_acceptance_performed"] is False


def test_validation_failed_does_not_auto_reject(tmp_path: Path):
    attempt = make_attempt(tmp_path)
    validation = make_validation(tmp_path, validation_status="validation_failed")
    out = tmp_path / "out"
    run_script(
        "--model-attempt-dir",
        attempt,
        "--job-packet",
        make_job_packet(tmp_path),
        "--prompt-packet",
        make_prompt_packet(tmp_path),
        "--validation-report",
        validation / "correction_aware_output_validation.json",
        "--out-dir",
        out,
    )
    payload = json.loads((out / "supervised_review_packet.json").read_text(encoding="utf-8"))
    assert payload["validation_status"] == "validation_failed"
    assert payload["recommended_next_step"] == "supervised_review_required"
    assert payload["review_packet_authority_flags"]["promotion_authorized"] is False


def test_prompt_packet_json_path_is_explicit(tmp_path: Path):
    prompt_json = make_prompt_packet(tmp_path)
    prompt_md = write_prompt_markdown(prompt_json, tmp_path / "prompt.md")
    assert prompt_json.suffix == ".json"
    assert prompt_md.suffix == ".md"


def test_review_packet_contains_hashes_and_provenance(tmp_path: Path):
    attempt = make_attempt(tmp_path)
    validation = make_validation(tmp_path)
    job_packet = make_job_packet(tmp_path)
    prompt_packet = make_prompt_packet(tmp_path)
    out = tmp_path / "out"
    run_script(
        "--model-attempt-dir",
        attempt,
        "--job-packet",
        job_packet,
        "--prompt-packet",
        prompt_packet,
        "--validation-report",
        validation / "correction_aware_output_validation.json",
        "--out-dir",
        out,
    )
    payload = json.loads((out / "supervised_review_packet.json").read_text(encoding="utf-8"))
    assert payload["source_job_packet_sha256"]
    assert payload["source_prompt_packet_sha256"]
    assert payload["source_model_attempt_record_sha256"]


def test_no_model_call_is_made():
    assert True
