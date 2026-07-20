from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_overnight_dogfood_artifacts import OvernightArtifactValidationError, validate_overnight_dogfood_artifacts


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "validate_dogfood_batch_artifacts.py"
OVERNIGHT_VALIDATOR = ROOT / "scripts" / "validate_overnight_dogfood_artifacts.py"


def _write_queue(path: Path, rows: list[tuple[str, str, str, list[str]]]) -> None:
    lines = ["# zth-roadmap-queue-schema: 2"]
    lines.extend("\t".join((priority, slug, objective, json.dumps(targets))) for priority, slug, objective, targets in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_state(path: Path, rows: list[tuple[str, str, str, str, str, str]]) -> None:
    lines = ["# run_id\tslug\tevent\trun_dir\tstate\ttimestamp"]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_run(run_dir: Path, *, with_raw: bool = True, with_content: bool = True, with_validation: bool = True, with_recovery: dict | None = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    if with_raw:
        (run_dir / "model_output.raw.1.json").write_text('{"choices": []}\n', encoding="utf-8")
    if with_content:
        (run_dir / "model_content.json").write_text('{"verdict":"pass"}\n', encoding="utf-8")
    if with_validation:
        (run_dir / "validation.1.json").write_text('{"state":"ready_for_review","errors":[]}\n', encoding="utf-8")
    if with_recovery is not None:
        (run_dir / "recovery_manifest.json").write_text(json.dumps(with_recovery, indent=2) + "\n", encoding="utf-8")


def _write_status(path: Path, *, queue_remaining: int, ready: int, blocked: int = 0, semantic_failed: int = 0, incomplete: int = 0, queue_exhausted: bool = True, terminal_state_consistent: bool = True) -> None:
    payload = {
        "queue_stage_total": 1,
        "queue_stages_attempted": 1,
        "queue_stages_ready_for_review": ready,
        "queue_stages_failed_semantic_validation": semantic_failed,
        "queue_stages_blocked": blocked,
        "queue_remaining": queue_remaining,
        "queue_exhausted": queue_exhausted,
        "terminal_state_consistent": terminal_state_consistent,
        "terminal_run_state": "queue_exhausted" if queue_exhausted else None,
        "incomplete_count": incomplete,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_terminal(path: Path, closeout: Path) -> None:
    payload = {"terminal_state": "queue_exhausted", "queue_exhausted": True}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    closeout.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _prepare_tree(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    queue = tmp_path / "roadmap_queue.tsv"
    state = tmp_path / "state.tsv"
    runs_dir = tmp_path / "runs"
    terminal = tmp_path / "terminal_state.json"
    closeout = tmp_path / "overnight_closeout_manifest.json"
    status = tmp_path / "status.json"
    return queue, state, runs_dir, terminal, closeout, status


def test_direct_wrapper_executes_from_outside_repo_workdir(tmp_path: Path) -> None:
    queue = tmp_path / "batch_queue.tsv"
    state = tmp_path / "batch_state.tsv"
    runs_dir = tmp_path / "runs"
    stage_log = tmp_path / "stage.log"
    queue.write_text("# priority\tslug\tdescription\n1\talpha\tAlpha\n", encoding="utf-8")
    state.write_text("# timestamp\tslug\tstatus\trun_dir\n2026-07-20T00:00:00Z\talpha\tpacket_generated\talpha\n", encoding="utf-8")
    run_dir = runs_dir / "alpha"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    (run_dir / "model_output.raw.json").write_text('{"allowed_targets": []}\n', encoding="utf-8")
    (run_dir / "model_output.redacted.json").write_text('{"redacted": true}\n', encoding="utf-8")
    (run_dir / "model_content.json").write_text('{"task_summary":"ok","repo_observations":[],"allowed_targets":[],"held_targets":[],"proposed_next_action":"ok","validation_plan":[]}\n', encoding="utf-8")
    stage_log.write_text("No remaining dogfood stages.\n", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = ""
    result = subprocess.run(
        [
            sys.executable,
            str(WRAPPER),
            "--queue",
            str(queue),
            "--state",
            str(state),
            "--runs-dir",
            str(runs_dir),
            "--stage-log",
            str(stage_log),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "validation_status" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr


def test_overnight_validator_executes_from_outside_repo_workdir(tmp_path: Path) -> None:
    queue, state, runs_dir, terminal, closeout, status = _prepare_tree(tmp_path)
    _write_queue(queue, [("1", "alpha", "Alpha", ["docs/ROADMAP.md"])])
    run_dir = runs_dir / "alpha"
    _write_run(run_dir)
    _write_state(
        state,
        [
            ("r1", "alpha", "ready_for_review", str(run_dir), "ready_for_review", "2026-07-20T00:00:00-04:00"),
            ("r1", "queue_exhausted", "queue_exhausted", str(tmp_path / "overnight"), "queue_exhausted", "2026-07-20T00:00:01-04:00"),
        ],
    )
    _write_terminal(terminal, closeout)
    _write_status(status, queue_remaining=0, ready=1, queue_exhausted=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = ""
    result = subprocess.run(
        [
            sys.executable,
            str(OVERNIGHT_VALIDATOR),
            "--queue",
            str(queue),
            "--state",
            str(state),
            "--runs-dir",
            str(runs_dir),
            "--terminal",
            str(terminal),
            "--closeout",
            str(closeout),
            "--status",
            str(status),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "validation_status" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr


def test_successful_interrupted_and_recovered_run(tmp_path: Path) -> None:
    queue, state, runs_dir, terminal, closeout, status = _prepare_tree(tmp_path)
    _write_queue(queue, [("1", "worker-loop-001-roadmap-grounding-01", "Roadmap grounding", ["docs/ROADMAP.md"])])
    interrupted = runs_dir / "20260720_040133_487736-worker-loop-001-roadmap-grounding-01"
    recovered = runs_dir / "20260720_040149_023113-worker-loop-001-roadmap-grounding-01"
    _write_run(interrupted, with_validation=False)
    _write_run(
        recovered,
        with_recovery={
            "stage_slug": "worker-loop-001-roadmap-grounding-01",
            "prior_directory": str(interrupted),
            "prior_lifecycle_state": "model_output_captured",
            "recovery_timestamp": "2026-07-20T04:01:49.024198-04:00",
            "current_directory": str(recovered),
            "next_attempt_number": 2,
        },
    )
    _write_state(
        state,
        [
            ("r1", "worker-loop-001-roadmap-grounding-01", "started", str(interrupted), "started", "2026-07-20T04:01:33.488588-04:00"),
            ("r1", "worker-loop-001-roadmap-grounding-01", "model_call_attempted", str(interrupted), "model_call_attempted", "2026-07-20T04:01:33.488630-04:00"),
            ("r1", "worker-loop-001-roadmap-grounding-01", "model_output_captured", str(interrupted), "model_output_captured", "2026-07-20T04:01:33.488813-04:00"),
            ("r2", "worker-loop-001-roadmap-grounding-01", "interrupted_recovered", str(recovered), "interrupted_recovered", str(recovered / "recovery_manifest.json"), "2026-07-20T04:01:49.024324-04:00"),
            ("r2", "worker-loop-001-roadmap-grounding-01", "started", str(recovered), "started", "2026-07-20T04:01:49.024351-04:00"),
            ("r2", "worker-loop-001-roadmap-grounding-01", "model_call_attempted", str(recovered), "model_call_attempted", "2026-07-20T04:01:49.024367-04:00"),
            ("r2", "worker-loop-001-roadmap-grounding-01", "model_output_captured", str(recovered), "model_output_captured", "2026-07-20T04:01:49.024570-04:00"),
            ("r2", "worker-loop-001-roadmap-grounding-01", "structure_valid", str(recovered), "structure_valid", "2026-07-20T04:01:49.024649-04:00"),
            ("r2", "worker-loop-001-roadmap-grounding-01", "semantic_validation_passed", str(recovered), "semantic_validation_passed", "2026-07-20T04:01:49.051156-04:00"),
            ("r2", "worker-loop-001-roadmap-grounding-01", "ready_for_review", str(recovered), "ready_for_review", "2026-07-20T04:01:49.051272-04:00"),
            ("r2", "queue_exhausted", "queue_exhausted", str(tmp_path / "overnight"), "queue_exhausted", "2026-07-20T04:01:49.052187-04:00"),
        ],
    )
    _write_terminal(terminal, closeout)
    _write_status(status, queue_remaining=0, ready=1, queue_exhausted=True)

    result = validate_overnight_dogfood_artifacts(
        queue_path=queue,
        state_path=state,
        runs_dir=runs_dir,
        terminal_path=terminal,
        closeout_path=closeout,
        status_path=status,
    )

    assert result["validation_status"] == "passed"
    assert result["queue_remaining"] == 0
    assert result["queue_exhausted"] is True


def test_missing_raw_output_after_model_output_captured_fails(tmp_path: Path) -> None:
    queue, state, runs_dir, terminal, closeout, status = _prepare_tree(tmp_path)
    _write_queue(queue, [("1", "worker-loop-001-roadmap-grounding-01", "Roadmap grounding", ["docs/ROADMAP.md"])])
    run_dir = runs_dir / "20260720_040133_487736-worker-loop-001-roadmap-grounding-01"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    _write_state(state, [("r1", "worker-loop-001-roadmap-grounding-01", "model_output_captured", str(run_dir), "model_output_captured", "2026-07-20T04:01:33.488813-04:00")])
    _write_terminal(terminal, closeout)
    _write_status(status, queue_remaining=1, ready=0, queue_exhausted=False, terminal_state_consistent=False)

    with pytest.raises(OvernightArtifactValidationError):
        validate_overnight_dogfood_artifacts(
            queue_path=queue,
            state_path=state,
            runs_dir=runs_dir,
            terminal_path=terminal,
            closeout_path=closeout,
            status_path=status,
        )


def test_missing_recovery_manifest_fails(tmp_path: Path) -> None:
    queue, state, runs_dir, terminal, closeout, status = _prepare_tree(tmp_path)
    _write_queue(queue, [("1", "worker-loop-001-roadmap-grounding-01", "Roadmap grounding", ["docs/ROADMAP.md"])])
    interrupted = runs_dir / "20260720_040133_487736-worker-loop-001-roadmap-grounding-01"
    recovered = runs_dir / "20260720_040149_023113-worker-loop-001-roadmap-grounding-01"
    _write_run(interrupted, with_validation=False)
    _write_run(recovered, with_recovery={
        "stage_slug": "worker-loop-001-roadmap-grounding-01",
        "prior_directory": str(interrupted),
        "prior_lifecycle_state": "model_output_captured",
        "recovery_timestamp": "2026-07-20T04:01:49.024198-04:00",
        "current_directory": str(recovered),
        "next_attempt_number": 2,
    })
    (recovered / "recovery_manifest.json").unlink()
    _write_state(state, [
        ("r1", "worker-loop-001-roadmap-grounding-01", "started", str(interrupted), "started", "2026-07-20T04:01:33.488588-04:00"),
        ("r2", "worker-loop-001-roadmap-grounding-01", "interrupted_recovered", str(recovered), "interrupted_recovered", str(recovered / "recovery_manifest.json"), "2026-07-20T04:01:49.024324-04:00"),
        ("r2", "worker-loop-001-roadmap-grounding-01", "ready_for_review", str(recovered), "ready_for_review", "2026-07-20T04:01:49.051272-04:00"),
        ("r2", "queue_exhausted", "queue_exhausted", str(tmp_path / "overnight"), "queue_exhausted", "2026-07-20T04:01:49.052187-04:00"),
    ])
    _write_terminal(terminal, closeout)
    _write_status(status, queue_remaining=0, ready=1, queue_exhausted=True)

    with pytest.raises(OvernightArtifactValidationError):
        validate_overnight_dogfood_artifacts(queue_path=queue, state_path=state, runs_dir=runs_dir, terminal_path=terminal, closeout_path=closeout, status_path=status)


def test_recovery_same_directory_fails(tmp_path: Path) -> None:
    queue, state, runs_dir, terminal, closeout, status = _prepare_tree(tmp_path)
    _write_queue(queue, [("1", "worker-loop-001-roadmap-grounding-01", "Roadmap grounding", ["docs/ROADMAP.md"])])
    interrupted = runs_dir / "20260720_040133_487736-worker-loop-001-roadmap-grounding-01"
    recovered = runs_dir / "20260720_040149_023113-worker-loop-001-roadmap-grounding-01"
    _write_run(interrupted, with_validation=False)
    _write_run(recovered, with_recovery={
        "stage_slug": "worker-loop-001-roadmap-grounding-01",
        "prior_directory": str(recovered),
        "prior_lifecycle_state": "model_output_captured",
        "recovery_timestamp": "2026-07-20T04:01:49.024198-04:00",
        "current_directory": str(recovered),
        "next_attempt_number": 2,
    })
    _write_state(state, [
        ("r1", "worker-loop-001-roadmap-grounding-01", "started", str(interrupted), "started", "2026-07-20T04:01:33.488588-04:00"),
        ("r2", "worker-loop-001-roadmap-grounding-01", "interrupted_recovered", str(recovered), "interrupted_recovered", str(recovered / "recovery_manifest.json"), "2026-07-20T04:01:49.024324-04:00"),
        ("r2", "worker-loop-001-roadmap-grounding-01", "ready_for_review", str(recovered), "ready_for_review", "2026-07-20T04:01:49.051272-04:00"),
        ("r2", "queue_exhausted", "queue_exhausted", str(tmp_path / "overnight"), "queue_exhausted", "2026-07-20T04:01:49.052187-04:00"),
    ])
    _write_terminal(terminal, closeout)
    _write_status(status, queue_remaining=0, ready=1, queue_exhausted=True)

    with pytest.raises(OvernightArtifactValidationError):
        validate_overnight_dogfood_artifacts(queue_path=queue, state_path=state, runs_dir=runs_dir, terminal_path=terminal, closeout_path=closeout, status_path=status)


def test_unresolved_stage_with_terminal_marker_fails(tmp_path: Path) -> None:
    queue, state, runs_dir, terminal, closeout, status = _prepare_tree(tmp_path)
    _write_queue(queue, [("1", "worker-loop-001-roadmap-grounding-01", "Roadmap grounding", ["docs/ROADMAP.md"])])
    run_dir = runs_dir / "20260720_040133_487736-worker-loop-001-roadmap-grounding-01"
    _write_run(run_dir, with_validation=False)
    _write_state(state, [("r1", "worker-loop-001-roadmap-grounding-01", "started", str(run_dir), "started", "2026-07-20T04:01:33.488588-04:00")])
    _write_terminal(terminal, closeout)
    _write_status(status, queue_remaining=1, ready=0, queue_exhausted=True, terminal_state_consistent=False)

    with pytest.raises(OvernightArtifactValidationError):
        validate_overnight_dogfood_artifacts(queue_path=queue, state_path=state, runs_dir=runs_dir, terminal_path=terminal, closeout_path=closeout, status_path=status)


def test_duplicate_closeout_fails(tmp_path: Path) -> None:
    queue, state, runs_dir, terminal, closeout, status = _prepare_tree(tmp_path)
    _write_queue(queue, [("1", "worker-loop-001-roadmap-grounding-01", "Roadmap grounding", ["docs/ROADMAP.md"])])
    run_dir = runs_dir / "20260720_040149_023113-worker-loop-001-roadmap-grounding-01"
    _write_run(run_dir)
    _write_state(state, [
        ("r1", "worker-loop-001-roadmap-grounding-01", "ready_for_review", str(run_dir), "ready_for_review", "2026-07-20T04:01:49.051272-04:00"),
        ("r1", "queue_exhausted", "queue_exhausted", str(tmp_path / "overnight"), "queue_exhausted", "2026-07-20T04:01:50.000000-04:00"),
    ])
    _write_terminal(terminal, closeout)
    (closeout.parent / "overnight_closeout_manifest.duplicate.json").write_text(closeout.read_text(encoding="utf-8"), encoding="utf-8")
    _write_status(status, queue_remaining=0, ready=1, queue_exhausted=True)

    with pytest.raises(OvernightArtifactValidationError):
        validate_overnight_dogfood_artifacts(queue_path=queue, state_path=state, runs_dir=runs_dir, terminal_path=terminal, closeout_path=closeout, status_path=status)


def test_status_disagreement_fails(tmp_path: Path) -> None:
    queue, state, runs_dir, terminal, closeout, status = _prepare_tree(tmp_path)
    _write_queue(queue, [("1", "worker-loop-001-roadmap-grounding-01", "Roadmap grounding", ["docs/ROADMAP.md"])])
    run_dir = runs_dir / "20260720_040149_023113-worker-loop-001-roadmap-grounding-01"
    _write_run(run_dir)
    _write_state(state, [
        ("r1", "worker-loop-001-roadmap-grounding-01", "ready_for_review", str(run_dir), "ready_for_review", "2026-07-20T04:01:49.051272-04:00"),
        ("r1", "queue_exhausted", "queue_exhausted", str(tmp_path / "overnight"), "queue_exhausted", "2026-07-20T04:01:50.000000-04:00"),
    ])
    _write_terminal(terminal, closeout)
    _write_status(status, queue_remaining=1, ready=1, queue_exhausted=True, terminal_state_consistent=False)

    with pytest.raises(OvernightArtifactValidationError):
        validate_overnight_dogfood_artifacts(queue_path=queue, state_path=state, runs_dir=runs_dir, terminal_path=terminal, closeout_path=closeout, status_path=status)


def test_ready_for_review_without_semantic_validation_fails(tmp_path: Path) -> None:
    queue, state, runs_dir, terminal, closeout, status = _prepare_tree(tmp_path)
    _write_queue(queue, [("1", "worker-loop-001-roadmap-grounding-01", "Roadmap grounding", ["docs/ROADMAP.md"])])
    run_dir = runs_dir / "20260720_040149_023113-worker-loop-001-roadmap-grounding-01"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stage_packet.md").write_text("# packet\n", encoding="utf-8")
    (run_dir / "model_output.raw.1.json").write_text('{"choices": []}\n', encoding="utf-8")
    (run_dir / "model_content.json").write_text('{"verdict":"pass"}\n', encoding="utf-8")
    _write_state(state, [
        ("r1", "worker-loop-001-roadmap-grounding-01", "ready_for_review", str(run_dir), "ready_for_review", "2026-07-20T04:01:49.051272-04:00"),
        ("r1", "queue_exhausted", "queue_exhausted", str(tmp_path / "overnight"), "queue_exhausted", "2026-07-20T04:01:50.000000-04:00"),
    ])
    _write_terminal(terminal, closeout)
    _write_status(status, queue_remaining=0, ready=1, queue_exhausted=True)

    with pytest.raises(OvernightArtifactValidationError):
        validate_overnight_dogfood_artifacts(queue_path=queue, state_path=state, runs_dir=runs_dir, terminal_path=terminal, closeout_path=closeout, status_path=status)
