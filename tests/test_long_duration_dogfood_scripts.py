from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TICK = ROOT / "scripts" / "zth_long_duration_dogfood_tick.sh"
INSTALL = ROOT / "scripts" / "zth_install_long_duration_cron.sh"
UNINSTALL = ROOT / "scripts" / "zth_uninstall_long_duration_cron.sh"
OVERNIGHT_CONTROLLER = ROOT / "scripts" / "zth_overnight_dogfood_controller.sh"
OVERNIGHT_CONTROLLER_PY = ROOT / "scripts" / "zth_overnight_dogfood_controller.py"
OVERNIGHT_STATUS = ROOT / "scripts" / "zth_overnight_dogfood_status.sh"
OVERNIGHT_INSTALL = ROOT / "scripts" / "zth_install_overnight_dogfood_cron.sh"
OVERNIGHT_UNINSTALL = ROOT / "scripts" / "zth_uninstall_overnight_dogfood_cron.sh"
OVERNIGHT_VALIDATOR = ROOT / "scripts" / "zth_validate_overnight_review_output.py"
LONG_DURATION_DOC = ROOT / "docs" / "reports" / "model_auditions" / "LONG_DURATION_DOGFOOD_CRON_2026-07-18.md"
MILESTONE_MAP_SYNTHESIS = ROOT / "docs" / "reports" / "model_auditions" / "DECLARATIVE_LONG_DURATION_MILESTONE_MAP_CALIBRATION_SYNTHESIS_2026-07-18.md"
LONG_DURATION_CLOSEOUT = ROOT / "docs" / "reports" / "model_auditions" / "LONG_DURATION_DOGFOOD_CLOSEOUT_2026-07-18.md"
ROADMAP = ROOT / "docs" / "ROADMAP.md"
README = ROOT / "docs" / "reports" / "model_auditions" / "README.md"


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=proc_env,
        text=True,
        capture_output=True,
        check=False,
    )


def _bash_n(script: Path) -> subprocess.CompletedProcess[str]:
    return _run(["bash", "-n", str(script)], cwd=ROOT)


def _overlay_snapshot(snapshot: Path) -> None:
    for src in [TICK, INSTALL, UNINSTALL, OVERNIGHT_CONTROLLER, OVERNIGHT_CONTROLLER_PY, OVERNIGHT_STATUS, OVERNIGHT_INSTALL, OVERNIGHT_UNINSTALL, OVERNIGHT_VALIDATOR, LONG_DURATION_DOC, MILESTONE_MAP_SYNTHESIS, LONG_DURATION_CLOSEOUT, ROADMAP, README]:
        dest = snapshot / src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    tests_dir = snapshot / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "tests" / "test_long_duration_dogfood_scripts.py", tests_dir / "test_long_duration_dogfood_scripts.py")


def _make_snapshot(
    tmp_path: Path,
    *,
    commit: bool = True,
    remove_paths: list[str] | None = None,
) -> Path:
    snapshot = tmp_path / "snapshot"
    subprocess.run(
        ["git", "clone", "--local", "--no-hardlinks", str(ROOT), str(snapshot)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    _overlay_snapshot(snapshot)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=snapshot, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=snapshot, check=True)
    for relative_path in remove_paths or []:
        path = snapshot / relative_path
        if path.exists():
            path.unlink()
    if commit:
        subprocess.run(["git", "add", "-A"], cwd=snapshot, check=True)
        diff_cached = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=snapshot,
            text=True,
            capture_output=True,
            check=False,
        )
        if diff_cached.returncode == 0:
            pass
        elif diff_cached.returncode == 1:
            subprocess.run(
                ["git", "commit", "-m", "snapshot for long duration dogfood script tests"],
                cwd=snapshot,
                text=True,
                capture_output=True,
                check=True,
            )
        else:
            raise AssertionError(
                "git diff --cached --quiet failed: "
                f"returncode={diff_cached.returncode} stderr={diff_cached.stderr}"
            )
    return snapshot


def _remove_snapshot_paths(snapshot: Path, *relative_paths: str) -> None:
    for relative_path in relative_paths:
        path = snapshot / relative_path
        if path.is_file():
            path.unlink()


def _latest_run_dir(repo: Path) -> Path:
    runs = sorted((repo / ".work" / "long_duration_dogfood" / "runs").glob("*"))
    assert runs, "expected a tick run directory"
    return runs[-1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _make_crontab_stub(tmp_path: Path, *, initial_lines: list[str] | None = None) -> tuple[Path, Path]:
    state = tmp_path / "crontab.state"
    if initial_lines:
        state.write_text("\n".join(initial_lines) + "\n", encoding="utf-8")
    else:
        state.write_text("", encoding="utf-8")

    bindir = tmp_path / "bin"
    bindir.mkdir()
    stub = bindir / "crontab"
    stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
STATE="${CRONTAB_STATE_FILE:?missing CRONTAB_STATE_FILE}"
if [ "${1:-}" = "-l" ]; then
  if [ -f "$STATE" ]; then
    cat "$STATE"
    exit 0
  fi
  exit 1
fi
if [ "$#" -ne 1 ]; then
  exit 1
fi
cp "$1" "$STATE"
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return bindir, state


def test_bash_n_passes_for_all_three_scripts():
    for script in [TICK, INSTALL, UNINSTALL, OVERNIGHT_CONTROLLER, OVERNIGHT_STATUS, OVERNIGHT_INSTALL, OVERNIGHT_UNINSTALL]:
        result = _bash_n(script)
        assert result.returncode == 0, result.stderr
    assert subprocess.run([sys.executable, "-m", "py_compile", str(OVERNIGHT_CONTROLLER_PY), str(OVERNIGHT_VALIDATOR)], cwd=ROOT, text=True, capture_output=True).returncode == 0


def test_make_snapshot_tolerates_clean_clone(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    status = _run(["git", "status", "--short", "--untracked-files=no"], cwd=snapshot)
    assert status.stdout == ""
    assert (snapshot / "tests" / "test_long_duration_dogfood_scripts.py").is_file()


def test_tick_once_creates_run_dir_and_summary(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    before = _run(["git", "status", "--short", "--untracked-files=no"], cwd=snapshot)
    result = _run([str(TICK), "--once"], cwd=snapshot, env={"ZTH_REPO": str(snapshot)})
    assert result.returncode == 0, result.stderr

    after = _run(["git", "status", "--short", "--untracked-files=no"], cwd=snapshot)
    assert before.stdout == after.stdout

    run_dir = _latest_run_dir(snapshot)
    summary = _read_json(run_dir / "tick_summary.json")
    assert summary["summary_schema"] == "long_duration_dogfood_tick_v1"
    assert summary["branch"] == "dogfood/overnight-20260718"
    assert len(summary["head_commit"]) == 40
    assert summary["next_task_category"] in {"tests_or_fixtures", "code_or_validator", "blocked_needs_review"}
    assert isinstance(summary["implementation_prompt"], str) and summary["implementation_prompt"].strip()
    assert "safe_checks" in summary
    assert summary["safe_checks"]["git_diff_check"]["exit_code"] == 0
    assert summary["safe_checks"]["queue_handoff_validator_tests"]["exit_code"] == 0
    assert summary["safe_checks"]["front_door_tests"]["exit_code"] == 0
    assert summary["window"]["window_schema"] == "long_duration_dogfood_window_v1"
    assert (run_dir / "implementation_prompt.md").is_file()
    assert (run_dir / "git_status_short.txt").is_file()
    assert (run_dir / "git_log_oneline_20.txt").is_file()


@pytest.mark.parametrize(
    ("missing_paths", "expected_category", "expected_title", "unexpected_phrases", "prompt_substring"),
    [
        (
            ["tests/test_long_duration_dogfood_scripts.py"],
            "tests_or_fixtures",
            "Add long-duration dogfood script tests.",
            [],
            "Add deterministic tests for scripts/zth_long_duration_dogfood_tick.sh",
        ),
        (
            [
                "local_harness/validate_queue_approval_path.py",
                "tests/test_validate_queue_approval_path.py",
                "tests/test_queue_approval_path_fixtures.py",
            ],
            "code_or_validator",
            "Add queue approval path validator design scaffold.",
            ["Add long-duration dogfood script tests."],
            "Add a review-artifact-only validator scaffold for a future queue approval path.",
        ),
        (
            ["docs/reports/model_auditions/QUEUE_APPROVAL_PATH_CALIBRATION_SYNTHESIS_2026-07-18.md"],
            "tests_or_fixtures",
            "Add queue approval path calibration synthesis.",
            ["Add long-duration dogfood script tests.", "Add queue approval path validator design scaffold."],
            "Add a queue approval path calibration synthesis report after the validator, pass fixtures, blocked fixtures, and regression tests.",
        ),
        (
            [
                "local_harness/review_queue_approval_path.py",
                "tests/test_review_queue_approval_path.py",
                "docs/reports/model_auditions/QUEUE_APPROVAL_REVIEW_COMMAND_2026-07-18.md",
            ],
            "code_or_validator",
            "Add read-only queue approval review command.",
            [
                "Add long-duration dogfood script tests.",
                "Add queue approval path validator design scaffold.",
                "Add queue approval path calibration synthesis.",
            ],
            "Add a read-only queue approval review command that wraps queue_approval_path_v1 validation and emits a review/report artifact only.",
        ),
        (
            ["docs/reports/model_auditions/QUEUE_APPROVAL_REVIEW_COMMAND_CALIBRATION_SYNTHESIS_2026-07-18.md"],
            "tests_or_fixtures",
            "Add queue approval review command calibration synthesis.",
            [
                "Add long-duration dogfood script tests.",
                "Add queue approval path validator design scaffold.",
                "Add queue approval path calibration synthesis.",
                "Add read-only queue approval review command.",
            ],
            "Add a queue approval review command calibration synthesis report after the read-only command, direct tests, smoke output, and regression slices.",
        ),
        (
            ["docs/reports/model_auditions/DECLARATIVE_LONG_DURATION_MILESTONE_MAP_CALIBRATION_SYNTHESIS_2026-07-18.md"],
            "tests_or_fixtures",
            "Add declarative milestone map calibration synthesis.",
            [
                "Add long-duration dogfood script tests.",
                "Add queue approval path validator design scaffold.",
                "Add queue approval path calibration synthesis.",
                "Add read-only queue approval review command.",
                "Add queue approval review command calibration synthesis.",
            ],
            "Add a calibration synthesis report for the declarative long-duration dogfood milestone map.",
        ),
        (
            ["docs/reports/model_auditions/LONG_DURATION_DOGFOOD_CLOSEOUT_2026-07-18.md"],
            "tests_or_fixtures",
            "Add long-duration dogfood closeout report.",
            [
                "Add long-duration dogfood script tests.",
                "Add queue approval path validator design scaffold.",
                "Add queue approval path calibration synthesis.",
                "Add read-only queue approval review command.",
                "Add queue approval review command calibration synthesis.",
                "Add declarative milestone map calibration synthesis.",
            ],
            "Add a long-duration dogfood closeout report summarizing the supervised cron/tick loop, completed evidence-backed milestones, stale-recommendation fixes, declarative milestone map, validation coverage, remaining unimplemented authority, and recommended stop/next-decision point.",
        ),
    ],
)
def test_tick_recommends_the_first_incomplete_milestone(
    tmp_path,
    missing_paths,
    expected_category,
    expected_title,
    unexpected_phrases,
    prompt_substring,
):
    snapshot = _make_snapshot(tmp_path, remove_paths=missing_paths)
    result = _run([str(TICK), "--once"], cwd=snapshot, env={"ZTH_REPO": str(snapshot)})
    assert result.returncode == 0, result.stderr

    run_dir = _latest_run_dir(snapshot)
    summary = _read_json(run_dir / "tick_summary.json")
    assert summary["next_task_category"] == expected_category
    assert summary["next_task_title"] == expected_title
    for phrase in unexpected_phrases:
        assert phrase not in summary["implementation_prompt"]
    assert prompt_substring in summary["implementation_prompt"]


def test_tick_moves_past_completed_milestones(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    result = _run([str(TICK), "--once"], cwd=snapshot, env={"ZTH_REPO": str(snapshot)})
    assert result.returncode == 0, result.stderr

    run_dir = _latest_run_dir(snapshot)
    summary = _read_json(run_dir / "tick_summary.json")
    assert summary["next_task_category"] == "tests_or_fixtures"
    assert summary["next_task_title"] == "Review long-duration dogfood closeout before selecting next lane."
    assert "Add long-duration dogfood script tests." not in summary["implementation_prompt"]
    assert "Add queue approval path validator design scaffold." not in summary["implementation_prompt"]
    assert "Add queue approval path calibration synthesis." not in summary["implementation_prompt"]
    assert "Add read-only queue approval review command." not in summary["implementation_prompt"]
    assert "Add queue approval review command calibration synthesis." not in summary["implementation_prompt"]
    assert "Add declarative milestone map calibration synthesis." not in summary["implementation_prompt"]
    assert "Add long-duration dogfood closeout report." not in summary["implementation_prompt"]
    assert "LONG_DURATION_DOGFOOD_CLOSEOUT_2026-07-18.md|" not in summary["implementation_prompt"]
    assert "tests/test_validate_queue_approval_path.py|" not in summary["implementation_prompt"]
    assert "tests/test_queue_approval_path_fixtures.py|" not in summary["implementation_prompt"]
    assert "tests/test_review_queue_approval_path.py|" not in summary["implementation_prompt"]
    assert "docs/reports/model_auditions/QUEUE_APPROVAL_REVIEW_COMMAND_CALIBRATION_SYNTHESIS_2026-07-18.md|" not in summary["implementation_prompt"]
    assert summary["implementation_prompt"].startswith("Review the long-duration dogfood closeout evidence and choose the next bounded lane")


def test_tick_moves_to_long_duration_dogfood_closeout_when_all_milestones_complete(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    result = _run([str(TICK), "--once"], cwd=snapshot, env={"ZTH_REPO": str(snapshot)})
    assert result.returncode == 0, result.stderr

    run_dir = _latest_run_dir(snapshot)
    summary = _read_json(run_dir / "tick_summary.json")
    assert summary["next_task_category"] == "tests_or_fixtures"
    assert summary["next_task_title"] == "Review long-duration dogfood closeout before selecting next lane."
    assert summary["implementation_prompt"].startswith("Review the long-duration dogfood closeout evidence and choose the next bounded lane")
    assert "Add declarative milestone map calibration synthesis." not in summary["implementation_prompt"]
    assert "LONG_DURATION_DOGFOOD_CLOSEOUT_2026-07-18.md|" not in summary["implementation_prompt"]


def test_tick_recommends_declarative_milestone_map_synthesis_when_report_missing(tmp_path):
    snapshot = _make_snapshot(tmp_path, remove_paths=[
        "docs/reports/model_auditions/DECLARATIVE_LONG_DURATION_MILESTONE_MAP_CALIBRATION_SYNTHESIS_2026-07-18.md",
    ])
    result = _run([str(TICK), "--once"], cwd=snapshot, env={"ZTH_REPO": str(snapshot)})
    assert result.returncode == 0, result.stderr

    run_dir = _latest_run_dir(snapshot)
    summary = _read_json(run_dir / "tick_summary.json")
    assert summary["next_task_category"] == "tests_or_fixtures"
    assert summary["next_task_title"] == "Add declarative milestone map calibration synthesis."
    assert "DECLARATIVE_LONG_DURATION_MILESTONE_MAP_CALIBRATION_SYNTHESIS_2026-07-18.md|" not in summary["implementation_prompt"]
    assert "Add a calibration synthesis report for the declarative long-duration dogfood milestone map." in summary["implementation_prompt"]


def test_tick_expired_control_window_blocks_useful_work(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    control = snapshot / ".work" / "long_duration_dogfood" / "control"
    control.mkdir(parents=True, exist_ok=True)
    (control / "window.json").write_text(
        json.dumps(
            {
                "window_schema": "long_duration_dogfood_window_v1",
                "source": "manual_bootstrap",
                "installed_at_epoch": 1,
                "installed_at_utc": "1970-01-01T00:00:01+00:00",
                "expires_at_epoch": 2,
                "expires_at_utc": "1970-01-01T00:00:02+00:00",
                "cadence_minutes": 20,
                "max_duration_hours": 8,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    before = sorted((snapshot / ".work" / "long_duration_dogfood" / "runs").glob("*"))
    result = _run([str(TICK), "--once"], cwd=snapshot, env={"ZTH_REPO": str(snapshot)})
    assert result.returncode != 0
    after = sorted((snapshot / ".work" / "long_duration_dogfood" / "runs").glob("*"))
    assert len(after) == len(before) + 1
    run_dir = after[-1]
    summary = _read_json(run_dir / "tick_summary.json")
    assert summary["summary_status"] == "blocked_needs_review"
    assert summary["next_task_category"] == "blocked_needs_review"
    assert summary["window"]["expires_at_epoch"] == 2
    assert summary["safe_checks"]["git_diff_check"]["exit_code"] is None
    assert summary["safe_checks"]["queue_handoff_validator_tests"]["exit_code"] is None
    assert summary["safe_checks"]["front_door_tests"]["exit_code"] is None


def test_tick_refuses_dirty_tracked_tree(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    road = snapshot / "docs" / "ROADMAP.md"
    road.write_text(road.read_text(encoding="utf-8") + "\n# dirty test marker\n", encoding="utf-8")
    result = _run([str(TICK), "--once"], cwd=snapshot, env={"ZTH_REPO": str(snapshot)})
    assert result.returncode != 0
    assert "tracked modifications present" in result.stderr
    assert "dirty test marker" in road.read_text(encoding="utf-8")


def test_tick_lock_contention_exits_cleanly(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    lock = snapshot / ".work" / "long_duration_dogfood" / "tick.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import fcntl, pathlib, time; "
                f"path = pathlib.Path(r'{lock}'); "
                "path.parent.mkdir(parents=True, exist_ok=True); "
                "fh = path.open('w'); "
                "fcntl.flock(fh, fcntl.LOCK_EX); "
                "time.sleep(5)"
            ),
        ],
        cwd=snapshot,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        before = sorted((snapshot / ".work" / "long_duration_dogfood" / "runs").glob("*"))
        result = _run([str(TICK), "--once"], cwd=snapshot, env={"ZTH_REPO": str(snapshot)})
        assert result.returncode == 0
        after = sorted((snapshot / ".work" / "long_duration_dogfood" / "runs").glob("*"))
        assert after == before
    finally:
        holder.terminate()
        holder.wait(timeout=10)


def test_install_helper_with_stubbed_crontab(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    bindir, state = _make_crontab_stub(tmp_path, initial_lines=["0 * * * * echo unrelated # keep-me"])
    env = {
        "ZTH_REPO": str(snapshot),
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "CRONTAB_STATE_FILE": str(state),
    }

    result = _run([str(INSTALL)], cwd=snapshot, env=env)
    assert result.returncode == 0, result.stderr
    payload = state.read_text(encoding="utf-8")
    assert payload.count("ZTH_LONG_DURATION_DOGFOOD") == 1
    assert "echo unrelated # keep-me" in payload
    control = _read_json(snapshot / ".work" / "long_duration_dogfood" / "control" / "window.json")
    assert control["window_schema"] == "long_duration_dogfood_window_v1"
    assert control["cadence_minutes"] == 20
    assert control["max_duration_hours"] == 8
    assert "installed cron line:" in result.stdout
    assert "uninstall command:" in result.stdout

    result_again = _run([str(INSTALL)], cwd=snapshot, env=env)
    assert result_again.returncode == 0, result_again.stderr
    payload_again = state.read_text(encoding="utf-8")
    assert payload_again.count("ZTH_LONG_DURATION_DOGFOOD") == 1


def test_uninstall_helper_with_stubbed_crontab(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    bindir, state = _make_crontab_stub(
        tmp_path,
        initial_lines=[
            "0 * * * * echo unrelated # keep-me",
            "*/20 * * * * cd /repo && /repo/scripts/zth_long_duration_dogfood_tick.sh --once # ZTH_LONG_DURATION_DOGFOOD",
        ],
    )
    env = {
        "ZTH_REPO": str(snapshot),
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "CRONTAB_STATE_FILE": str(state),
    }

    result = _run([str(UNINSTALL)], cwd=snapshot, env=env)
    assert result.returncode == 0, result.stderr
    payload = state.read_text(encoding="utf-8")
    assert "ZTH_LONG_DURATION_DOGFOOD" not in payload
    assert "echo unrelated # keep-me" in payload
    assert "remaining tagged cron lines:" in result.stdout


def test_overnight_status_reports_deadline_and_queue(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    result = _run([str(OVERNIGHT_STATUS)], cwd=snapshot, env={"ZTH_REPO": str(snapshot), "ZTH_OVERNIGHT_DEADLINE": "2099-01-01T08:00:00-05:00"})
    assert result.returncode == 0, result.stderr
    payload = _read_json(snapshot / ".work" / "dogfood" / "overnight" / "status.json")
    assert payload["deadline_local"].startswith("2099-01-01T08:00:00")
    assert payload["queue_path"].endswith(".work/dogfood/roadmap_queue.tsv")
    assert payload["state_path"].endswith(".work/dogfood/overnight/state.tsv")
    assert payload["attempted_unique_stages"] == 0
    assert payload["queue_exhausted"] is False
    assert payload["terminal_run_state"] is None


def test_overnight_validator_rejects_invalid_schema_and_deadline_contradiction(tmp_path):
    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {
                "verdict": "pass",
                "review_state": "complete",
                "changed_paths": [],
                "verification": {
                    "raw_output_structure": "pass",
                    "changed_files_against_allowlist": "pass",
                    "narrowest_relevant_local_checks": "pass",
                },
                "evidence": [{"path": "docs/ROADMAP.md", "observation": "evidence"}],
                "notes": "deadline reached and complete",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    result = _run([str(OVERNIGHT_VALIDATOR), str(sample), "false", ".work/dogfood/overnight"], cwd=ROOT)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["state"] == "semantic_validation_failed"
    assert "deadline_contradiction" in payload["errors"]


def test_overnight_validator_rejects_pending_schema_and_invented_keys(tmp_path):
    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {
                "verdict": "incomplete",
                "review_state": "incomplete",
                "changed_paths": [".work/dogfood/overnight/ok.json"],
                "verification": {
                    "raw_output_structure": "pass",
                    "changed_files_against_allowlist": "pass",
                    "narrowest_relevant_local_checks": "not_run",
                    "invented": "nope",
                },
                "evidence": [{"path": "docs/ROADMAP.md", "observation": "evidence"}],
                "notes": "pending work",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    result = _run([str(OVERNIGHT_VALIDATOR), str(sample), "false", ".work/dogfood/overnight"], cwd=ROOT)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["state"] == "structure_valid"


def test_overnight_install_and_uninstall_helpers_with_stubbed_crontab(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    bindir, state = _make_crontab_stub(tmp_path)
    env = {
        "ZTH_REPO": str(snapshot),
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "CRONTAB_STATE_FILE": str(state),
    }

    result = _run([str(OVERNIGHT_INSTALL)], cwd=snapshot, env=env)
    assert result.returncode == 0, result.stderr
    payload = state.read_text(encoding="utf-8")
    assert "ZTH_OVERNIGHT_DOGFOOD_20260718" in payload
    assert "*/5 * * * *" in payload
    assert "zth_overnight_dogfood_controller.sh" in payload

    result = _run([str(OVERNIGHT_UNINSTALL)], cwd=snapshot, env=env)
    assert result.returncode == 0, result.stderr
    assert "ZTH_OVERNIGHT_DOGFOOD_20260718" not in state.read_text(encoding="utf-8")


def test_overnight_queue_exhaustion_is_terminal_and_idempotent(tmp_path):
    snapshot = _make_snapshot(tmp_path, remove_paths=[
        "docs/reports/model_auditions/QUEUE_APPROVAL_REVIEW_COMMAND_CALIBRATION_SYNTHESIS_2026-07-18.md",
        "docs/reports/model_auditions/DECLARATIVE_LONG_DURATION_MILESTONE_MAP_CALIBRATION_SYNTHESIS_2026-07-18.md",
        "docs/reports/model_auditions/LONG_DURATION_DOGFOOD_CLOSEOUT_2026-07-18.md",
    ])
    queue = snapshot / ".work" / "dogfood" / "roadmap_queue.tsv"
    queue.parent.mkdir(parents=True, exist_ok=True)
    queue.write_text("1\tone-stage\tOne stage\n", encoding="utf-8")
    response = snapshot / "model_response.json"
    response.write_text(
        json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "verdict": "pass",
                                    "review_state": "complete",
                                    "changed_paths": [],
                                    "verification": {
                                        "raw_output_structure": "pass",
                                        "changed_files_against_allowlist": "not_applicable",
                                        "narrowest_relevant_local_checks": "not_run",
                                    },
                                    "evidence": [{"path": "docs/ROADMAP.md", "observation": "ok"}],
                                    "notes": "evidence-based review",
                                }
                            )
                        }
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    env = {
        "ZTH_REPO": str(snapshot),
        "ZTH_OVERNIGHT_MODEL_RESPONSE_FILE": str(response),
        "ZTH_PUBLIC_HOST_ALIAS": "LOCAL_STUB",
        "ZTH_OVERNIGHT_DEADLINE": "2099-01-01T08:00:00-05:00",
    }

    try:
        first = _run([str(OVERNIGHT_CONTROLLER), "--tick"], cwd=snapshot, env=env)
        assert first.returncode == 0, first.stderr
        runs = sorted((snapshot / ".work" / "dogfood" / "overnight" / "runs").glob("*"))
        assert len(runs) == 1
        terminal = snapshot / ".work" / "dogfood" / "overnight" / "terminal_state.json"
        assert terminal.is_file()
        second = _run([str(OVERNIGHT_CONTROLLER), "--tick"], cwd=snapshot, env=env)
        assert second.returncode == 0, second.stderr
        runs_after = sorted((snapshot / ".work" / "dogfood" / "overnight" / "runs").glob("*"))
        assert runs_after == runs
    finally:
        pass


def test_overnight_dry_run_does_not_modify_state(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    queue_src = ROOT / ".work" / "dogfood" / "roadmap_queue.tsv"
    queue_dest = snapshot / ".work" / "dogfood" / "roadmap_queue.tsv"
    queue_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(queue_src, queue_dest)
    before = _run(["git", "status", "--short", "--untracked-files=no"], cwd=snapshot)
    result = _run([str(OVERNIGHT_CONTROLLER), "--dry-run"], cwd=snapshot, env={"ZTH_REPO": str(snapshot), "ZTH_OVERNIGHT_DEADLINE": "2099-01-01T08:00:00-05:00"})
    assert result.returncode == 0, result.stderr
    after = _run(["git", "status", "--short", "--untracked-files=no"], cwd=snapshot)
    assert before.stdout == after.stdout
    json_start = result.stdout.index("{")
    payload = json.loads(result.stdout[json_start:])
    assert payload["attempted_unique_stages"] == 0


def test_no_private_address_literals_in_tracked_overnight_artifacts():
    paths = [
        ROOT / "docs" / "reports" / "model_auditions" / "OVERNIGHT_DOGFOOD_RUN_2026-07-19.md",
        ROOT / "docs" / "reports" / "model_auditions" / "OVERNIGHT_DOGFOOD_CALIBRATION_2026-07-20.md",
        ROOT / "scripts" / "zth_overnight_dogfood_controller.py",
        ROOT / "scripts" / "zth_validate_overnight_review_output.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists())
    patterns = [
        r"\b192\.168\.\d{1,3}\.\d{1,3}\b",
        r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        r"\b172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}\b",
        r"\b127\.0\.0\.1\b",
    ]
    for pattern in patterns:
        assert not re.search(pattern, text)
    assert "http://" not in text
    assert "https://" not in text


def test_authority_boundary_text_remains_present():
    text = "".join(
        path.read_text(encoding="utf-8")
        for path in [TICK, INSTALL, UNINSTALL, LONG_DURATION_DOC, ROADMAP, README]
    )
    for phrase in [
        "auto-commit",
        "auto-push",
        "queue-write",
        "mutate main unattended",
    ]:
        assert phrase in text
