from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TICK = ROOT / "scripts" / "zth_long_duration_dogfood_tick.sh"
INSTALL = ROOT / "scripts" / "zth_install_long_duration_cron.sh"
UNINSTALL = ROOT / "scripts" / "zth_uninstall_long_duration_cron.sh"
LONG_DURATION_DOC = ROOT / "docs" / "reports" / "model_auditions" / "LONG_DURATION_DOGFOOD_CRON_2026-07-18.md"
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
    for src in [TICK, INSTALL, UNINSTALL, LONG_DURATION_DOC, ROADMAP, README]:
        dest = snapshot / src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    tests_dir = snapshot / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "tests" / "test_long_duration_dogfood_scripts.py", tests_dir / "test_long_duration_dogfood_scripts.py")


def _make_snapshot(tmp_path: Path, *, commit: bool = True) -> Path:
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
    if commit:
        subprocess.run(
            [
                "git",
                "add",
                str(TICK.relative_to(ROOT)),
                str(INSTALL.relative_to(ROOT)),
                str(UNINSTALL.relative_to(ROOT)),
                str(LONG_DURATION_DOC.relative_to(ROOT)),
                str(ROADMAP.relative_to(ROOT)),
                str(README.relative_to(ROOT)),
                str(Path("tests") / "test_long_duration_dogfood_scripts.py"),
            ],
            cwd=snapshot,
            check=True,
        )
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
    for script in [TICK, INSTALL, UNINSTALL]:
        result = _bash_n(script)
        assert result.returncode == 0, result.stderr


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
    assert summary["branch"] == "main"
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


def test_tick_moves_past_completed_script_tests(tmp_path):
    snapshot = _make_snapshot(tmp_path)
    result = _run([str(TICK), "--once"], cwd=snapshot, env={"ZTH_REPO": str(snapshot)})
    assert result.returncode == 0, result.stderr

    run_dir = _latest_run_dir(snapshot)
    summary = _read_json(run_dir / "tick_summary.json")
    assert summary["next_task_category"] == "code_or_validator"
    assert summary["next_task_title"] == "Add queue approval path validator design scaffold."
    assert "Add deterministic tests for scripts/zth_long_duration_dogfood_tick.sh" not in summary["implementation_prompt"]
    assert "review-artifact-only validator scaffold for a future queue approval path" in summary["implementation_prompt"]


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
