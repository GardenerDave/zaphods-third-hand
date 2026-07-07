from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "run_supervised_chain_smoke.py"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_runs_with_messy_input(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260706T235959Z"
    result = run_script(
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    run_dir = out_dir / ts
    assert run_dir.is_dir()


def test_runs_with_messy_input_file(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260706T235959Z"
    input_file = tmp_path / "messy.txt"
    input_file.write_text("The LoRA and prompt injection work got messy. Build a bounded design packet.\n", encoding="utf-8")
    result = run_script(
        "--messy-input-file",
        input_file,
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert (out_dir / ts / "messy_input.txt").is_file()


def test_creates_timestamped_run_directory(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260706T010203Z"
    result = run_script(
        "--messy-input",
        "Bounded operator smoke input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert (out_dir / ts).is_dir()


def test_writes_expected_artifacts(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260706T111111Z"
    result = run_script(
        "--messy-input",
        "Bounded operator smoke input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    run_dir = out_dir / ts
    assert (run_dir / "messy_input.txt").is_file()
    assert (run_dir / "supervised_chain_smoke.json").is_file()
    assert (run_dir / "supervised_chain_smoke_report.txt").is_file()
    assert (run_dir / "model_prompt_packet.md").is_file()
    assert (run_dir / "handoff_packet.json").is_file()


def test_prints_output_paths_and_status(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260706T121212Z"
    result = run_script(
        "--messy-input",
        "Bounded operator smoke input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert "run_dir:" in result.stdout
    assert "smoke_status: passed" in result.stdout
    assert "report_path:" in result.stdout


def test_supports_deterministic_timestamp(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260706T131313Z"
    result = run_script(
        "--messy-input",
        "Bounded operator smoke input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert f"run_dir: {out_dir / ts}" in result.stdout


def test_refuses_overwrite_existing_run_dir_by_default(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260706T141414Z"
    run_dir = out_dir / ts
    run_dir.mkdir(parents=True)
    result = run_script(
        "--messy-input",
        "Bounded operator smoke input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode != 0
    assert "already exists" in result.stderr


def test_fails_when_no_input_mode_is_supplied(tmp_path: Path):
    out_dir = tmp_path / "runs"
    result = run_script(
        "--out-dir",
        out_dir,
        "--timestamp",
        "20260706T151515Z",
    )
    assert result.returncode != 0
    assert "exactly one of --messy-input or --messy-input-file" in result.stderr


def test_fails_when_both_input_modes_are_supplied(tmp_path: Path):
    out_dir = tmp_path / "runs"
    input_file = tmp_path / "messy.txt"
    input_file.write_text("Bounded operator smoke input.\n", encoding="utf-8")
    result = run_script(
        "--messy-input",
        "Bounded operator smoke input.",
        "--messy-input-file",
        input_file,
        "--out-dir",
        out_dir,
        "--timestamp",
        "20260706T161616Z",
    )
    assert result.returncode != 0
    assert "exactly one of --messy-input or --messy-input-file" in result.stderr


def test_writes_no_files_outside_requested_output_directory(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260706T171717Z"
    result = run_script(
        "--messy-input",
        "Bounded operator smoke input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    created_files = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert created_files
    for path in created_files:
        assert out_dir in path.parents


def test_smoke_record_preserves_no_model_call_and_no_authority_grants(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260706T181818Z"
    result = run_script(
        "--messy-input",
        "Bounded operator smoke input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    record = json.loads((out_dir / ts / "supervised_chain_smoke.json").read_text(encoding="utf-8"))
    assert record["artifacts"]["supervised_model_attempt"]["model_metadata"]["provider"] == "none"
    prohibited = record["artifacts"]["handoff_packet"]["prohibited_downstream_use"]
    assert "no_command_execution" in prohibited
    assert "no_direct_file_modification" in prohibited
    assert "no_patch_application" in prohibited
    assert "no_automatic_patch_promotion" in prohibited
    assert "no_automatic_training" in prohibited
    assert "no_default_failure_to_curriculum_capture" in prohibited
