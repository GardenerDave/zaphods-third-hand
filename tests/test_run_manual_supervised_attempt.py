from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "run_manual_supervised_attempt.py"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _valid_raw_output_json() -> str:
    return json.dumps(
        {
            "allowed_targets": ["docs/reports/"],
            "held_targets": [
                "production automation",
                "automatic curriculum capture",
                "automatic promotion",
                "implementation_packet",
            ],
            "scope_expansion_required": False,
            "claims": [
                "The request is a design-planning task involving LoRA and prompt injection.",
                "docs/reports/ is the only allowed target in this packet.",
            ],
            "evidence_basis": [
                "Task summary mentions matched keywords: lora, prompt injection.",
                "Allowed Targets lists docs/reports/.",
            ],
            "unverified_claims": [],
            "format": "json",
            "required_fields_present": True,
            "reason": "The output remains bounded and supervised.",
        }
    )


def _prepare_run(tmp_path: Path, *, timestamp: str = "20260707T010101Z") -> Path:
    out_dir = tmp_path / "runs"
    result = run_script(
        "prepare",
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        out_dir,
        "--timestamp",
        timestamp,
    )
    assert result.returncode == 0
    return out_dir / timestamp


def _session_run(
    tmp_path: Path,
    *,
    timestamp: str = "20260707T010101Z",
    print_prompt: bool = False,
    write_prompt_copy: bool = False,
) -> tuple[Path, subprocess.CompletedProcess[str]]:
    out_dir = tmp_path / "runs"
    command: list[str | Path] = [
        "session",
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        out_dir,
        "--timestamp",
        timestamp,
    ]
    if print_prompt:
        command.append("--print-prompt")
    if write_prompt_copy:
        command.append("--write-prompt-copy")
    result = run_script(*command)
    assert result.returncode == 0
    return out_dir / timestamp, result


def test_prepare_from_messy_input_writes_required_artifacts(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T020202Z"
    result = run_script(
        "prepare",
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
    assert (run_dir / "messy_input.txt").is_file()
    assert (run_dir / "model_prompt_packet.md").is_file()
    assert (run_dir / "operator_instructions.txt").is_file()
    assert (run_dir / "run_manifest.json").is_file()
    assert (run_dir / "output_contract.json").is_file()


def test_prepare_from_messy_input_file(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T030303Z"
    messy_path = tmp_path / "messy.txt"
    messy_path.write_text("The LoRA and prompt injection work got messy. Build a bounded design packet.\n", encoding="utf-8")
    result = run_script(
        "prepare",
        "--messy-input-file",
        messy_path,
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert (out_dir / ts / "messy_input.txt").is_file()


def test_prepare_stores_tightened_output_contract(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T040404Z")
    contract = json.loads((run_dir / "output_contract.json").read_text(encoding="utf-8"))
    assert contract["format"] == "json"
    assert contract["requires_reason"] is True
    assert contract["required_fields"] == [
        "allowed_targets",
        "held_targets",
        "scope_expansion_required",
        "claims",
        "evidence_basis",
        "unverified_claims",
        "format",
        "required_fields_present",
        "reason",
    ]


def test_prepare_refuses_overwrite_by_default(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T050505Z"
    (out_dir / ts).mkdir(parents=True)
    result = run_script(
        "prepare",
        "--messy-input",
        "Bounded operator input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode != 0
    assert "already exists" in result.stderr


def test_prepare_supports_deterministic_timestamp(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T060606Z"
    result = run_script(
        "prepare",
        "--messy-input",
        "Bounded operator input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert f"run_dir: {out_dir / ts}" in result.stdout


def test_prepare_rejects_missing_messy_input(tmp_path: Path):
    result = run_script(
        "prepare",
        "--out-dir",
        tmp_path / "runs",
    )
    assert result.returncode != 0
    assert "exactly one of --messy-input or --messy-input-file" in result.stderr


def test_prepare_rejects_both_messy_input_variants(tmp_path: Path):
    messy_path = tmp_path / "messy.txt"
    messy_path.write_text("bounded input\n", encoding="utf-8")
    result = run_script(
        "prepare",
        "--messy-input",
        "bounded input",
        "--messy-input-file",
        messy_path,
        "--out-dir",
        tmp_path / "runs",
    )
    assert result.returncode != 0
    assert "exactly one of --messy-input or --messy-input-file" in result.stderr


def test_session_mode_writes_required_artifacts_and_prompt_copy(tmp_path: Path):
    run_dir, result = _session_run(tmp_path, timestamp="20260707T171717Z")
    assert run_dir.is_dir()
    assert (run_dir / "messy_input.txt").is_file()
    assert (run_dir / "model_prompt_packet.md").is_file()
    assert (run_dir / "prompt_to_paste.md").is_file()
    assert (run_dir / "raw_model_output.txt").is_file()
    assert (run_dir / "operator_instructions.txt").is_file()
    assert (run_dir / "run_manifest.json").is_file()
    assert (run_dir / "output_contract.json").is_file()

    prompt_packet = (run_dir / "model_prompt_packet.md").read_text(encoding="utf-8")
    prompt_copy = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    assert prompt_copy == prompt_packet
    assert "Manual Supervised Attempt Instructions" not in prompt_copy

    assert f"run_dir: {run_dir}" in result.stdout
    assert f"prompt_to_paste: {run_dir / 'prompt_to_paste.md'}" in result.stdout
    assert f"raw_output_file: {run_dir / 'raw_model_output.txt'}" in result.stdout
    assert (
        f"python3 local_harness/run_manual_supervised_attempt.py ingest --run-dir {run_dir} "
        f"--raw-output-file {run_dir / 'raw_model_output.txt'}"
    ) in result.stdout


def test_session_mode_print_prompt_uses_markers_and_excludes_operator_instructions(tmp_path: Path):
    run_dir, result = _session_run(tmp_path, timestamp="20260707T181818Z", print_prompt=True)
    assert "----- BEGIN MODEL PROMPT PACKET -----" in result.stdout
    assert "----- END MODEL PROMPT PACKET -----" in result.stdout
    begin = result.stdout.index("----- BEGIN MODEL PROMPT PACKET -----")
    end = result.stdout.index("----- END MODEL PROMPT PACKET -----")
    prompt_block = result.stdout[begin:end]
    assert "# ZTH Model Prompt Packet" in prompt_block
    assert "Manual Supervised Attempt Instructions" not in prompt_block
    assert str(run_dir / "prompt_to_paste.md") in result.stdout


def test_session_mode_supports_deterministic_timestamp(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T191919Z"
    result = run_script(
        "session",
        "--messy-input",
        "Bounded operator input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert f"run_dir: {out_dir / ts}" in result.stdout


def test_session_mode_rejects_missing_messy_input(tmp_path: Path):
    result = run_script(
        "session",
        "--out-dir",
        tmp_path / "runs",
    )
    assert result.returncode != 0
    assert "exactly one of --messy-input or --messy-input-file" in result.stderr


def test_session_mode_accepts_write_prompt_copy_flag(tmp_path: Path):
    run_dir, result = _session_run(tmp_path, timestamp="20260707T202020Z", write_prompt_copy=True)
    assert result.returncode == 0
    prompt_packet = (run_dir / "model_prompt_packet.md").read_text(encoding="utf-8")
    prompt_copy = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    assert prompt_copy == prompt_packet


def test_ingest_valid_output_writes_attempt_validation_and_preserves_raw_output(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T070707Z")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert result.returncode == 0
    assert (run_dir / "supervised_model_attempt.json").is_file()
    assert (run_dir / "output_validation.json").is_file()
    assert (run_dir / "output_validation_report.txt").is_file()
    assert (run_dir / "raw_model_output.txt").read_text(encoding="utf-8") == raw_text
    assert "validation_status: passed" in result.stdout


def test_ingest_without_review_keeps_not_reviewed_and_prints_review_required(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T080808Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert result.returncode == 0
    assert "review_required: explicit review decision is required before downstream use" in result.stdout

    attempt = json.loads((run_dir / "supervised_model_attempt.json").read_text(encoding="utf-8"))
    validation = json.loads((run_dir / "output_validation.json").read_text(encoding="utf-8"))
    assert attempt["acceptance_status"] == "not_reviewed"
    assert validation["acceptance_status"] == "not_reviewed"
    assert not (run_dir / "review_decision.json").exists()
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


def test_ingest_validation_fails_when_required_field_missing(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T090909Z")
    source_raw = tmp_path / "raw_model_output.txt"
    payload = json.loads(_valid_raw_output_json())
    del payload["scope_expansion_required"]
    source_raw.write_text(json.dumps(payload), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert result.returncode == 0
    assert "validation_status: failed" in result.stdout
    validation = json.loads((run_dir / "output_validation.json").read_text(encoding="utf-8"))
    assert validation["validation_status"] == "failed"


def test_ingest_with_explicit_accepted_review_writes_decision_gate_handoff(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T101010Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "accepted",
        "--decision-reason",
        "Output satisfies the required contract and remains within scope.",
        "--operator",
        "manual",
    )
    assert result.returncode == 0
    assert (run_dir / "review_decision.json").is_file()
    assert (run_dir / "downstream_use_gate.json").is_file()
    assert (run_dir / "handoff_packet.json").is_file()


def test_ingest_rejects_explicit_accepted_review_when_validation_failed(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T111111Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text('{"reason":"ok"}', encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "accepted",
        "--decision-reason",
        "accept anyway",
        "--operator",
        "manual",
    )
    assert result.returncode != 0
    assert "accepted decision requires validation_status 'passed'" in result.stderr


def test_ingest_rejected_decision_keeps_gate_and_handoff_blocked(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T121212Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "rejected",
        "--decision-reason",
        "Needs revisions.",
        "--operator",
        "manual",
    )
    assert result.returncode == 0
    gate = json.loads((run_dir / "downstream_use_gate.json").read_text(encoding="utf-8"))
    handoff = json.loads((run_dir / "handoff_packet.json").read_text(encoding="utf-8"))
    assert gate["gate_status"] == "blocked"
    assert handoff["handoff_status"] == "blocked"
    prohibited = handoff["prohibited_downstream_use"]
    assert "no_command_execution" in prohibited
    assert "no_direct_file_modification" in prohibited
    assert "no_patch_application" in prohibited
    assert "no_automatic_patch_promotion" in prohibited
    assert "no_automatic_training" in prohibited
    assert "no_default_failure_to_curriculum_capture" in prohibited


def test_ingest_revision_requested_decision_keeps_gate_and_handoff_blocked(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T131313Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "revision_requested",
        "--decision-reason",
        "Clarify evidence basis.",
        "--operator",
        "manual",
    )
    assert result.returncode == 0
    gate = json.loads((run_dir / "downstream_use_gate.json").read_text(encoding="utf-8"))
    handoff = json.loads((run_dir / "handoff_packet.json").read_text(encoding="utf-8"))
    assert gate["gate_status"] == "blocked"
    assert handoff["handoff_status"] == "blocked"


def test_ingest_marks_manual_operator_provenance_and_no_endpoint_usage_fields(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T141414Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert result.returncode == 0
    attempt = json.loads((run_dir / "supervised_model_attempt.json").read_text(encoding="utf-8"))
    assert attempt["provenance"]["source"] == "manual_operator_pasted_model_output"
    assert attempt["model_metadata"]["provider"] == "manual_operator"
    assert "endpoint_url" not in attempt
    assert "raw_model_output" in attempt


def test_prepare_prints_run_dir_and_ingest_prints_validation_status(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T151515Z"
    prepare_result = run_script(
        "prepare",
        "--messy-input",
        "Bounded input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert prepare_result.returncode == 0
    assert "run_dir:" in prepare_result.stdout

    run_dir = out_dir / ts
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")
    ingest_result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert ingest_result.returncode == 0
    assert "validation_status:" in ingest_result.stdout


def test_ingest_invalid_cli_combination_requires_decision_reason(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T161616Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "accepted",
    )
    assert result.returncode != 0
    assert "--decision-reason is required" in result.stderr
