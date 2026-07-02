from __future__ import annotations

import json
import subprocess
from pathlib import Path

from local_harness.run_correction_aware_model_attempt import run_attempt


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "run_correction_aware_model_attempt.py"
PROMPT_PACKET = ROOT / ".work" / "behavior_correction_prompt_packet_dogfood" / "file_scope_hold_out_v1_20260702" / "correction_aware_prompt_packet.md"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def make_prompt_packet(tmp_path: Path, *, json_packet: bool = False) -> Path:
    packet_json = {
        "report_type": "correction_aware_prompt_packet.v1",
        "source_job_packet": "job.json",
        "source_correction_scaffold": "scaffold.json",
        "task_summary": "hold out docs/ROADMAP.md",
        "allowed_files": ["docs/README.md"],
        "requested_targets": ["docs/README.md", "docs/ROADMAP.md"],
        "expected_output_shape": "json",
        "behavior_corrections": ["file_scope_hold_out_v1"],
        "rendered_prompt_sections": {"task": {"task_summary": "hold out docs/ROADMAP.md"}},
        "auto_assigned_corrections": False,
        "packet_level_only": True,
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "delta_written": False,
        "patched_model_materialized": False,
        "promotion_authorized": False,
        "automatic_failure_curriculum_capture_authorized": False,
    }
    if json_packet:
        path = tmp_path / "packet.json"
        path.write_text(json.dumps(packet_json, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path = tmp_path / "packet.md"
        path.write_text("# Prompt\ncorrection-aware prompt packet", encoding="utf-8")
    return path


def test_help():
    assert run_script("--help").returncode == 0


def test_missing_authorization_fails_before_model_call(tmp_path: Path):
    packet = make_prompt_packet(tmp_path)
    out = tmp_path / "out"
    result = run_script(
        "--prompt-packet",
        packet,
        "--out-dir",
        out,
        "--endpoint-url",
        "http://127.0.0.1:1234/v1",
        "--model",
        "test-model",
    )
    assert result.returncode != 0
    assert not out.exists()


def test_missing_prompt_packet_fails(tmp_path: Path):
    out = tmp_path / "out"
    result = run_script(
        "--prompt-packet",
        tmp_path / "missing.md",
        "--out-dir",
        out,
        "--endpoint-url",
        "http://127.0.0.1:1234/v1",
        "--model",
        "test-model",
        "--authorize-model-attempt",
    )
    assert result.returncode != 0


def test_output_dir_exists_fails(tmp_path: Path):
    packet = make_prompt_packet(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    result = run_script(
        "--prompt-packet",
        packet,
        "--out-dir",
        out,
        "--endpoint-url",
        "http://127.0.0.1:1234/v1",
        "--model",
        "test-model",
        "--authorize-model-attempt",
    )
    assert result.returncode != 0


def test_mocked_endpoint_success_writes_artifacts(tmp_path: Path):
    packet = make_prompt_packet(tmp_path, json_packet=True)
    out = tmp_path / "out"

    def fake_client(**kwargs):
        assert kwargs["endpoint_url"] == "http://user:secret@127.0.0.1:1234/v1"
        return {"choices": [{"message": {"content": "{" + '"ok": true' + "}"}}]}

    result = run_attempt(
        prompt_packet=packet,
        out_dir=out,
        endpoint_url="http://user:secret@127.0.0.1:1234/v1",
        model="test-model",
        max_tokens=32,
        temperature=0.0,
        timeout_seconds=5,
        authorized=True,
        client=fake_client,
    )
    assert result["raw_output"] == '{"ok": true}'
    record = json.loads((out / "model_attempt_record.json").read_text(encoding="utf-8"))
    summary = json.loads((out / "model_attempt_summary.json").read_text(encoding="utf-8"))
    assert (out / "raw_model_output.txt").read_text(encoding="utf-8") == '{"ok": true}'
    assert (out / "status.log").exists()
    assert (out / "status_events.jsonl").exists()
    assert record["model_inference_performed"] is True
    assert record["generation_performed"] is True
    assert record["training_performed"] is False
    assert record["delta_written"] is False
    assert record["patched_model_materialized"] is False
    assert record["promotion_authorized"] is False
    assert record["validation_performed"] is False
    assert record["supervised_acceptance_performed"] is False
    assert record["automatic_failure_curriculum_capture_authorized"] is False
    assert summary["recommended_next_step"] == "supervised_validation_or_review"
    assert summary["output_excerpt"] == '{"ok": true}'
    assert record["endpoint_url"] == "http://127.0.0.1:1234/v1"


def test_json_prompt_packet_authority_flags_are_checked(tmp_path: Path):
    packet = make_prompt_packet(tmp_path, json_packet=True)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["promotion_authorized"] = True
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    try:
        run_attempt(
            prompt_packet=packet,
            out_dir=out,
            endpoint_url="http://127.0.0.1:1234/v1",
            model="test-model",
            max_tokens=32,
            temperature=0.0,
            timeout_seconds=5,
            authorized=True,
            client=lambda **kwargs: {"choices": [{"message": {"content": "ok"}}]},
        )
    except ValueError as exc:
        assert "prompt packet promotion_authorized must be false" in str(exc)
    else:
        raise AssertionError("expected authorization validation failure")

