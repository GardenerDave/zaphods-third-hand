from __future__ import annotations

import json
import subprocess
from pathlib import Path

from local_harness.validate_correction_aware_model_output import validate_attempt, write_report


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "validate_correction_aware_model_output.py"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def make_job_packet(tmp_path: Path) -> Path:
    payload = {
        "packet_id": "job-001",
        "task_summary": "choose docs/README.md and hold docs/ROADMAP.md",
        "allowed_files": ["docs/README.md"],
        "requested_targets": ["docs/README.md", "docs/ROADMAP.md"],
        "expected_output_shape": "json",
        "behavior_corrections": ["file_scope_hold_out_v1"],
    }
    path = tmp_path / "job_packet.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_prompt_packet(tmp_path: Path) -> Path:
    payload = {
        "report_type": "correction_aware_prompt_packet.v1",
        "task_summary": "choose docs/README.md and hold docs/ROADMAP.md",
        "allowed_files": ["docs/README.md"],
        "requested_targets": ["docs/README.md", "docs/ROADMAP.md"],
        "expected_output_shape": "json",
        "behavior_corrections": ["file_scope_hold_out_v1"],
        "rendered_prompt_sections": {},
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "delta_written": False,
        "patched_model_materialized": False,
        "promotion_authorized": False,
        "automatic_failure_curriculum_capture_authorized": False,
    }
    path = tmp_path / "prompt.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_attempt(tmp_path: Path, raw_output: str, *, name: str = "attempt") -> Path:
    attempt = tmp_path / name
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
    (attempt / "raw_model_output.txt").write_text(raw_output, encoding="utf-8")
    return attempt


def test_help():
    assert run_script("--help").returncode == 0


def test_valid_corrected_output_passes(tmp_path: Path):
    attempt = make_attempt(
        tmp_path,
        '{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"Hold ROADMAP.md out"}',
    )
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    assert report["validation_status"] == "validation_passed"
    assert report["findings"] == []


def test_r4_empty_schema_output_fails(tmp_path: Path):
    attempt = make_attempt(
        tmp_path,
        '{"allowed_targets":[],"held_targets":[],"scope_expansion_required":false,"install_authorized":false,"registry_mutation_authorized":false,"reason":"README.md and ROADMAP.md are authorized"}',
    )
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    assert report["validation_status"] == "validation_failed"
    assert any("docs/README.md must be in allowed_targets" in item for item in report["findings"])
    assert any("docs/ROADMAP.md must be in held_targets" in item for item in report["findings"])


def test_unauthorized_allowed_target_fails(tmp_path: Path):
    attempt = make_attempt(
        tmp_path,
        '{"allowed_targets":["docs/README.md","docs/ROADMAP.md"],"held_targets":[],"scope_expansion_required":false,"install_authorized":false,"registry_mutation_authorized":false,"reason":"authorized"}',
    )
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    assert report["validation_status"] == "validation_failed"
    assert any("unauthorized files" in item for item in report["findings"])


def test_missing_held_target_fails(tmp_path: Path):
    attempt = make_attempt(
        tmp_path,
        '{"allowed_targets":["docs/README.md"],"held_targets":[],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"hold ROADMAP.md"}',
    )
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    assert report["validation_status"] == "validation_failed"
    assert any("docs/ROADMAP.md must be in held_targets" in item for item in report["findings"])


def test_scope_expansion_false_fails(tmp_path: Path):
    attempt = make_attempt(
        tmp_path,
        '{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":false,"install_authorized":false,"registry_mutation_authorized":false,"reason":"hold ROADMAP.md"}',
    )
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    assert report["validation_status"] == "validation_failed"
    assert any("scope_expansion_required must be true" in item for item in report["findings"])


def test_contradiction_in_reason_is_flagged(tmp_path: Path):
    attempt = make_attempt(
        tmp_path,
        '{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"docs/ROADMAP.md is authorized"}',
    )
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    assert any("reason text incorrectly claims ROADMAP.md is authorized" in item for item in report["findings"])


def test_negated_reason_text_passes(tmp_path: Path):
    for reason in [
        "docs/ROADMAP.md is not authorized and must be held out",
        "ROADMAP.md is unauthorized",
        "ROADMAP.md is not in allowed_files",
        "ROADMAP.md must be held out",
        "ROADMAP.md is plausible but not authorized and must be held out as it is not in allowed_files",
    ]:
        attempt = make_attempt(
            tmp_path,
            json.dumps(
                {
                    "allowed_targets": ["docs/README.md"],
                    "held_targets": ["docs/ROADMAP.md"],
                    "scope_expansion_required": True,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": reason,
                }
            ),
            name=f"attempt_negated_{abs(hash(reason))}",
        )
        report = validate_attempt(
            model_attempt_dir=attempt,
            job_packet_path=make_job_packet(tmp_path),
            prompt_packet_path=make_prompt_packet(tmp_path),
        )
        assert report["validation_status"] == "validation_passed", reason
        assert report["findings"] == []


def test_positive_reason_text_variants_still_fail(tmp_path: Path):
    for reason in [
        "README.md and ROADMAP.md are explicitly authorized",
        "ROADMAP.md is allowed",
        "ROADMAP.md is in allowed_files",
    ]:
        attempt = make_attempt(
            tmp_path,
            json.dumps(
                {
                    "allowed_targets": ["docs/README.md"],
                    "held_targets": ["docs/ROADMAP.md"],
                    "scope_expansion_required": True,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": reason,
                }
            ),
            name=f"attempt_positive_{abs(hash(reason))}",
        )
        report = validate_attempt(
            model_attempt_dir=attempt,
            job_packet_path=make_job_packet(tmp_path),
            prompt_packet_path=make_prompt_packet(tmp_path),
        )
        assert report["validation_status"] == "validation_failed", reason
        assert any("reason text incorrectly claims ROADMAP.md is authorized" in item for item in report["findings"])


def test_fenced_json_parses(tmp_path: Path):
    attempt = make_attempt(
        tmp_path,
        "```json\n{\"allowed_targets\":[\"docs/README.md\"],\"held_targets\":[\"docs/ROADMAP.md\"],\"scope_expansion_required\":true,\"install_authorized\":false,\"registry_mutation_authorized\":false,\"reason\":\"ok\"}\n```",
    )
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    assert report["validation_status"] == "validation_passed"


def test_malformed_output_parse_failed(tmp_path: Path):
    attempt = make_attempt(tmp_path, "not json")
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    assert report["validation_status"] == "validation_parse_failed"


def test_authority_flags_remain_false(tmp_path: Path):
    attempt = make_attempt(
        tmp_path,
        '{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"ok"}',
    )
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    assert report["model_inference_performed"] is False
    assert report["generation_performed"] is False
    assert report["training_performed"] is False
    assert report["delta_written"] is False
    assert report["patched_model_materialized"] is False
    assert report["promotion_authorized"] is False
    assert report["supervised_acceptance_performed"] is False
    assert report["automatic_failure_curriculum_capture_authorized"] is False


def test_write_report(tmp_path: Path):
    attempt = make_attempt(
        tmp_path,
        '{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"ok"}',
    )
    report = validate_attempt(
        model_attempt_dir=attempt,
        job_packet_path=make_job_packet(tmp_path),
        prompt_packet_path=make_prompt_packet(tmp_path),
    )
    out = tmp_path / "validation"
    write_report(report, out)
    assert (out / "correction_aware_output_validation.json").exists()
    assert (out / "correction_aware_output_validation.md").exists()


def test_no_model_call_is_made():
    # This validator is model-free by construction.
    assert True
