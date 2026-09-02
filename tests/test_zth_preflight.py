from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

from local_harness.zth_preflight import (
    DEFAULT_TIMEOUT_SECONDS,
    PREFLIGHT_BOUNDARIES,
    PREFLIGHT_SCHEMA,
    REPO_ROOT,
    RUNNER_SCRIPT,
    main,
    run_preflight,
)
from local_harness.zth_preflight_historian_runner import (
    RUNNER_SCHEMA,
    main as runner_main,
)


try:
    import numpy as _np
except ImportError:
    _np = None

requires_numpy = pytest.mark.skipif(
    _np is None, reason="numpy is required to write embeddings fixtures"
)

ZTH_HEAD = "ab" * 20
HIST_HEAD = "cd" * 20
CANONICAL_COUNT = 7
PROJECTED_COUNT = 7


def _cp(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _git_ok(repo_kind: str) -> dict[str, SimpleNamespace]:
    head = ZTH_HEAD if repo_kind == "zth" else HIST_HEAD
    return {
        "git_dir": _cp(0, b".git\n"),
        "head": _cp(0, head.encode() + b"\n"),
        "status": _cp(0, b""),
    }


def make_git_side_effect(
    zth_repo: Path,
    historian_repo: Path,
    *,
    zth: dict[str, SimpleNamespace] | None = None,
    historian: dict[str, SimpleNamespace] | None = None,
    launch_error: Exception | None = None,
):
    """Build a subprocess.run side effect that answers only git commands."""
    responses = {
        str(zth_repo): {**_git_ok("zth"), **(zth or {})},
        str(historian_repo): {**_git_ok("historian"), **(historian or {})},
    }

    def side_effect(command, **kwargs):
        if launch_error is not None:
            raise launch_error
        repo = command[2]
        subcommand = tuple(command[3:])
        repo_responses = responses.get(repo)
        if repo_responses is None:
            return _cp(128, b"", f"not a git repository: {repo}".encode())
        if subcommand == ("rev-parse", "--git-dir"):
            return repo_responses["git_dir"]
        if subcommand == ("rev-parse", "HEAD"):
            return repo_responses["head"]
        if subcommand == ("status", "--porcelain=v1", "-z", "--no-renames"):
            return repo_responses["status"]
        raise AssertionError(f"unexpected git command: {command}")

    return side_effect


def _runner_report(
    *,
    canonical: int | None = CANONICAL_COUNT,
    canonical_error: str | None = None,
    projected: int | None = PROJECTED_COUNT,
    projection_error: str | None = None,
    retrieval: str = "current",
    retrieval_error: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": RUNNER_SCHEMA,
        "historian_root": "stub",
        "runtime_python": "stub-python",
        "canonical": {"count": canonical, "error": canonical_error},
        "projection": {"count": projected, "error": projection_error},
        "retrieval": {"state": retrieval, "error": retrieval_error},
    }


def _runner_response(value: Any):
    if value is None:
        raise AssertionError("the Historian runner should not have been invoked")
    if isinstance(value, BaseException):
        raise value
    if isinstance(value, dict):
        return _cp(0, (json.dumps(value) + "\n").encode())
    return value


def _patch_subprocess(git_side_effect, runner: Any = None):
    """Patch subprocess.run: git goes to the fake, everything else to runner.

    ``runner`` may be a report dict, a SimpleNamespace return value, an
    exception instance to raise, the string sentinel ``"real"`` (non-git
    subprocess calls execute for real, used with stub-runtime fixtures), or
    ``None`` to assert the runner is never invoked.
    """
    real_run = subprocess.run

    def side_effect(command, **kwargs):
        if command[0] == "git":
            return git_side_effect(command, **kwargs)
        if runner == "real":
            return real_run(command, **kwargs)
        if runner is None:
            raise AssertionError("the Historian runner should not have been invoked")
        return _runner_response(runner)

    return mock.patch.object(subprocess, "run", side_effect=side_effect)


def _make_repos(tmp_path: Path) -> tuple[Path, Path]:
    zth_repo = tmp_path / "zaphods-third-hand"
    historian_repo = tmp_path / "project-historian-v1"
    zth_repo.mkdir(parents=True, exist_ok=True)
    historian_repo.mkdir(parents=True, exist_ok=True)
    (zth_repo / "README.md").write_text("stub ZTH repository\n", encoding="utf-8")
    (historian_repo / "README.md").write_text(
        "stub Historian repository\n", encoding="utf-8"
    )
    return zth_repo, historian_repo


def _run(
    zth_repo: Path,
    historian_repo: Path,
    *,
    runner: Any,
    git: dict[str, SimpleNamespace] | None = None,
    historian_git: dict[str, SimpleNamespace] | None = None,
    launch_error: Exception | None = None,
    **preflight_kwargs: Any,
):
    git_side_effect = make_git_side_effect(
        zth_repo, historian_repo, zth=git, historian=historian_git,
        launch_error=launch_error,
    )
    with _patch_subprocess(git_side_effect, runner=runner):
        return run_preflight(
            zth_repo=zth_repo,
            historian_repo=historian_repo,
            historian_python=Path(sys.executable),
            **preflight_kwargs,
        )


def _check_names(result) -> list[str]:
    return [check["name"] for check in result.checks]


def _check(result, name: str) -> dict[str, Any]:
    matching = [check for check in result.checks if check["name"] == name]
    assert len(matching) == 1, f"expected exactly one {name} check"
    return matching[0]


# ---------------------------------------------------------------------------
# Clean happy path, output formats, exit codes
# ---------------------------------------------------------------------------


def test_clean_baseline_passes(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(zth_repo, historian_repo, runner=_runner_report())
    assert result.status == "pass"
    assert result.errors == ()
    assert _check_names(result) == [
        "zth_repo_exists",
        "zth_git_repo",
        "zth_head",
        "zth_clean",
        "historian_repo_exists",
        "historian_git_repo",
        "historian_head",
        "historian_clean",
        "historian_runtime",
        "historian_canonical",
        "historian_projection",
        "historian_counts_agree",
        "historian_retrieval",
    ]
    assert result.zth.head == ZTH_HEAD
    assert result.historian.head == HIST_HEAD
    assert result.historian_baseline.canonical_count == CANONICAL_COUNT
    assert result.historian_baseline.projected_count == PROJECTED_COUNT
    assert result.historian_baseline.counts_agree is True
    assert result.historian_baseline.retrieval_state == "current"


def test_clean_baseline_human_output(tmp_path: Path, capsys) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    git_side_effect = make_git_side_effect(zth_repo, historian_repo)
    with _patch_subprocess(git_side_effect, runner=_runner_report()):
        exit_code = main(
            [
                "--zth-repo",
                str(zth_repo),
                "--historian-repo",
                str(historian_repo),
                "--historian-python",
                sys.executable,
            ]
        )
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "ZTH" in output
    assert f"  head: {ZTH_HEAD}" in output
    assert "  worktree: clean" in output
    assert "Historian" in output
    assert f"  head: {HIST_HEAD}" in output
    assert f"  canonical: {CANONICAL_COUNT}" in output
    assert f"  projected: {PROJECTED_COUNT}" in output
    assert "  counts: agree" in output
    assert "  retrieval: current" in output
    assert "PREFLIGHT: PASS" in output
    assert "Failures" not in output
    for boundary in PREFLIGHT_BOUNDARIES:
        assert boundary in output


def test_json_output_is_structured(tmp_path: Path, capsys) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    git_side_effect = make_git_side_effect(zth_repo, historian_repo)
    with _patch_subprocess(git_side_effect, runner=_runner_report()):
        exit_code = main(
            [
                "--zth-repo",
                str(zth_repo),
                "--historian-repo",
                str(historian_repo),
                "--historian-python",
                sys.executable,
                "--json",
            ]
        )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["schema_version"] == PREFLIGHT_SCHEMA
    assert payload["status"] == "pass"
    assert payload["zth"] == {
        "repo": str(zth_repo),
        "exists": True,
        "git_repo": True,
        "head": ZTH_HEAD,
        "clean": True,
        "changed_paths": [],
        "git_error": None,
        "head_error": None,
        "status_error": None,
    }
    historian = payload["historian"]
    assert historian["head"] == HIST_HEAD
    assert historian["clean"] is True
    assert historian["canonical_count"] == CANONICAL_COUNT
    assert historian["projected_count"] == PROJECTED_COUNT
    assert historian["counts_agree"] is True
    assert historian["retrieval_state"] == "current"
    assert historian["canonical_error"] is None
    assert historian["retrieval_error"] is None
    assert historian["runtime"] == sys.executable
    assert isinstance(payload["checks"], list)
    assert all(
        {"name", "status"} <= set(check) and check["status"] == "pass"
        for check in payload["checks"]
    )
    assert payload["errors"] == []
    assert payload["boundaries"] == list(PREFLIGHT_BOUNDARIES)


def test_failure_exits_nonzero(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(),
        git={"status": _cp(0, b"?? notes.txt\x00")},
    )
    assert result.status == "fail"
    git_side_effect = make_git_side_effect(
        zth_repo, historian_repo, zth={"status": _cp(0, b"?? notes.txt\x00")}
    )
    with _patch_subprocess(git_side_effect, runner=_runner_report()):
        exit_code = main(
            [
                "--zth-repo",
                str(zth_repo),
                "--historian-repo",
                str(historian_repo),
                "--historian-python",
                sys.executable,
            ]
        )
    assert exit_code == 1


# ---------------------------------------------------------------------------
# Git observation fail-closed cases
# ---------------------------------------------------------------------------


def test_missing_zth_repo_fails_closed(tmp_path: Path) -> None:
    _, historian_repo = _make_repos(tmp_path)
    missing = tmp_path / "no-such-zth"
    result = _run(missing, historian_repo, runner=_runner_report())
    assert result.status == "fail"
    assert any("does not exist" in error for error in result.errors)
    assert _check(result, "zth_repo_exists")["status"] == "fail"
    assert "zth_head" not in _check_names(result)
    assert result.zth.exists is False
    assert result.historian_baseline.canonical_count == CANONICAL_COUNT


def test_missing_historian_repo_fails_closed(tmp_path: Path) -> None:
    zth_repo, _ = _make_repos(tmp_path)
    missing = tmp_path / "no-such-historian"
    result = _run(zth_repo, missing, runner=None)
    assert result.status == "fail"
    assert any("does not exist" in error for error in result.errors)
    assert _check(result, "historian_repo_exists")["status"] == "fail"
    assert "historian_canonical" not in _check_names(result)
    assert result.historian_baseline.canonical_count is None


def test_non_git_zth_repo_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(),
        git={"git_dir": _cp(128, b"", b"fatal: not a git repository\n")},
    )
    assert result.status == "fail"
    assert any("not a usable Git repository" in error for error in result.errors)
    assert _check(result, "zth_git_repo")["status"] == "fail"
    assert "zth_head" not in _check_names(result)
    assert "zth_clean" not in _check_names(result)


def test_non_git_historian_repo_skips_baseline_checks(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=None,
        historian_git={"git_dir": _cp(128, b"", b"fatal: not a git repository\n")},
    )
    assert result.status == "fail"
    assert _check(result, "historian_git_repo")["status"] == "fail"
    for name in (
        "historian_runtime",
        "historian_canonical",
        "historian_projection",
        "historian_counts_agree",
        "historian_retrieval",
    ):
        assert name not in _check_names(result)
    assert result.historian_baseline.runtime is None


def test_dirty_zth_surfaces_exact_changed_paths(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    dirty_status = _cp(
        0,
        b"?? notes.txt\x00 M local_harness/zth_preflight.py\x00"
        b"D  gone.md\x00",
    )
    result = _run(
        zth_repo, historian_repo, runner=_runner_report(), git={"status": dirty_status}
    )
    assert result.status == "fail"
    check = _check(result, "zth_clean")
    assert check["status"] == "fail"
    assert check["changed_paths"] == [
        {"status": "??", "path": "notes.txt"},
        {"status": " M", "path": "local_harness/zth_preflight.py"},
        {"status": "D ", "path": "gone.md"},
    ]
    assert result.zth.clean is False
    error = next(
        error for error in result.errors if "ZTH worktree is dirty" in error
    )
    assert "notes.txt" in error
    assert "local_harness/zth_preflight.py" in error
    assert "gone.md" in error
    assert _check(result, "historian_retrieval")["status"] == "pass"


def test_dirty_historian_still_validates_records(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(),
        historian_git={"status": _cp(0, b"?? stray.txt\x00")},
    )
    assert result.status == "fail"
    assert _check(result, "historian_clean")["status"] == "fail"
    assert any("stray.txt" in error for error in result.errors)
    assert _check(result, "historian_canonical")["status"] == "pass"
    assert _check(result, "historian_retrieval")["status"] == "pass"


def test_unborn_head_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(),
        git={
            "head": _cp(
                128,
                b"",
                b"fatal: ambiguous argument 'HEAD': unknown revision\n",
            )
        },
    )
    assert result.status == "fail"
    assert _check(result, "zth_head")["status"] == "fail"
    assert any("no commits on HEAD" in error for error in result.errors)
    assert result.zth.head is None
    assert _check(result, "zth_clean")["status"] == "pass"


def test_git_status_failure_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(),
        git={"status": _cp(1, b"", b"fatal: this operation must be run in a work tree\n")},
    )
    assert result.status == "fail"
    assert _check(result, "zth_clean")["status"] == "fail"
    assert any("git status failed" in error for error in result.errors)


def test_unparseable_git_status_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo, historian_repo, runner=_runner_report(),
        git={"status": _cp(0, b"absolute garbage without nul terminators")},
    )
    assert result.status == "fail"
    check = _check(result, "zth_clean")
    assert check["status"] == "fail"
    assert "cannot parse" in (check.get("error") or "")


def test_git_launch_oserror_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(),
        launch_error=OSError("git binary unavailable"),
    )
    assert result.status == "fail"
    assert any("could not be launched" in error for error in result.errors)
    assert _check(result, "zth_git_repo")["status"] == "fail"


# ---------------------------------------------------------------------------
# Historian runtime and runner fail-closed cases
# ---------------------------------------------------------------------------


def test_missing_bundled_runtime_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    git_side_effect = make_git_side_effect(zth_repo, historian_repo)
    with _patch_subprocess(git_side_effect, runner=None):
        result = run_preflight(
            zth_repo=zth_repo, historian_repo=historian_repo
        )
    assert result.status == "fail"
    check = _check(result, "historian_runtime")
    assert check["status"] == "fail"
    assert "--historian-python" in (check.get("error") or "")
    assert result.historian_baseline.runtime is None
    assert "historian_canonical" not in _check_names(result)


def test_non_executable_historian_python_override_fails_closed(
    tmp_path: Path,
) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    not_executable = tmp_path / "plain-python.txt"
    not_executable.write_text("not executable\n", encoding="utf-8")
    git_side_effect = make_git_side_effect(zth_repo, historian_repo)
    with _patch_subprocess(git_side_effect, runner=None):
        result = run_preflight(
            zth_repo=zth_repo,
            historian_repo=historian_repo,
            historian_python=not_executable,
        )
    assert result.status == "fail"
    check = _check(result, "historian_runtime")
    assert check["status"] == "fail"
    assert "not an executable file" in (check.get("error") or "")


def test_runner_nonzero_exit_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_cp(3, b"", b"traceback: simulated runner crash\n"),
    )
    assert result.status == "fail"
    for name in (
        "historian_canonical",
        "historian_projection",
        "historian_counts_agree",
        "historian_retrieval",
    ):
        check = _check(result, name)
        assert check["status"] == "fail"
        assert "exited 3" in (check.get("error") or "")
    assert any("exited 3" in error for error in result.errors)


def test_runner_non_json_output_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(zth_repo, historian_repo, runner=_cp(0, b"not json at all"))
    assert result.status == "fail"
    assert any("did not return JSON" in error for error in result.errors)


def test_runner_non_object_output_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(zth_repo, historian_repo, runner=_cp(0, b"[1, 2, 3]"))
    assert result.status == "fail"
    assert any("did not return a JSON object" in error for error in result.errors)


def test_runner_timeout_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=subprocess.TimeoutExpired(
            cmd="runner", timeout=DEFAULT_TIMEOUT_SECONDS
        ),
    )
    assert result.status == "fail"
    assert any("timed out" in error for error in result.errors)


def test_runner_launch_failure_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo, historian_repo, runner=OSError("no such interpreter")
    )
    assert result.status == "fail"
    assert any("failed to launch Historian runtime" in error for error in result.errors)


def test_runner_invocation_shape(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    git_side_effect = make_git_side_effect(zth_repo, historian_repo)
    with mock.patch.object(
        subprocess, "run", side_effect=lambda command, **kwargs: (
            git_side_effect(command, **kwargs)
            if command[0] == "git"
            else _runner_response(_runner_report())
        )
    ) as runner_mock:
        result = run_preflight(
            zth_repo=zth_repo,
            historian_repo=historian_repo,
            historian_python=Path(sys.executable),
        )
    assert result.status == "pass"
    runner_calls = [
        call for call in runner_mock.call_args_list
        if call.args[0][0] != "git"
    ]
    assert len(runner_calls) == 1
    call = runner_calls[0]
    command = call.args[0]
    assert isinstance(command, list)
    assert command[0] == sys.executable
    assert command[1] == str(RUNNER_SCRIPT)
    assert command[2] == str(historian_repo)
    assert call.kwargs["cwd"] == str(historian_repo)
    assert call.kwargs["capture_output"] is True
    assert "shell" not in call.kwargs or call.kwargs["shell"] is False
    pythonpath = call.kwargs["env"]["PYTHONPATH"]
    assert pythonpath.split(os.pathsep)[0] == str(historian_repo)
    assert call.kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert call.kwargs["timeout"] == DEFAULT_TIMEOUT_SECONDS


@pytest.mark.parametrize(
    "report",
    [
        {},
        {"canonical": {"count": "7", "error": None}},
        {"canonical": {"count": 7, "error": 5}},
        {"canonical": {"count": 7, "error": None}, "projection": None},
        {
            "canonical": {"count": 7, "error": None},
            "projection": {"count": 7, "error": None},
            "retrieval": {"state": "bogus", "error": None},
        },
        {
            "canonical": {"count": 7, "error": None},
            "projection": {"count": 7, "error": None},
            "retrieval": {"state": "current", "error": 5},
        },
    ],
)
def test_malformed_runner_reports_fail_closed(
    tmp_path: Path, report: dict[str, Any]
) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(zth_repo, historian_repo, runner=report)
    assert result.status == "fail"
    assert result.errors
    if "retrieval" in report and isinstance(report["retrieval"], dict):
        if report["retrieval"].get("state") == "bogus":
            assert result.historian_baseline.retrieval_state == "invalid"


# ---------------------------------------------------------------------------
# Historian baseline content fail-closed cases
# ---------------------------------------------------------------------------


def test_canonical_validation_failure_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(
            canonical=None, canonical_error="canonical corpus is inconsistent: DEC-1"
        ),
    )
    assert result.status == "fail"
    check = _check(result, "historian_canonical")
    assert check["status"] == "fail"
    assert "DEC-1" in (check.get("error") or "")
    assert any("canonical validation failed" in error for error in result.errors)
    assert _check(result, "historian_retrieval")["status"] == "pass"
    assert result.historian_baseline.counts_agree is None
    counts_check = _check(result, "historian_counts_agree")
    assert counts_check["status"] == "fail"
    assert "could not be verified" in (counts_check.get("error") or "")


def test_projection_validation_failure_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(
            projected=None,
            projection_error="retrieval projection is incomplete or stale",
        ),
    )
    assert result.status == "fail"
    check = _check(result, "historian_projection")
    assert check["status"] == "fail"
    assert "incomplete or stale" in (check.get("error") or "")
    assert any("projection validation failed" in error for error in result.errors)


def test_count_mismatch_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(projected=PROJECTED_COUNT - 1),
    )
    assert result.status == "fail"
    check = _check(result, "historian_counts_agree")
    assert check["status"] == "fail"
    assert check["canonical"] == CANONICAL_COUNT
    assert check["projected"] == PROJECTED_COUNT - 1
    assert result.historian_baseline.counts_agree is False
    assert any(
        f"canonical={CANONICAL_COUNT}" in error
        and f"projected={PROJECTED_COUNT - 1}" in error
        for error in result.errors
    )
    assert _check(result, "historian_canonical")["status"] == "pass"
    assert _check(result, "historian_projection")["status"] == "pass"


@pytest.mark.parametrize(
    ("state", "expected_error_fragment"),
    [
        ("stale", "explicitly rebuild"),
        ("missing", "manifest not found"),
        ("invalid", "malformed manifest"),
    ],
)
def test_retrieval_non_current_states_fail_closed(
    tmp_path: Path, state: str, expected_error_fragment: str
) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(
            retrieval=state,
            retrieval_error=f"simulated: {expected_error_fragment}",
        ),
    )
    assert result.status == "fail"
    check = _check(result, "historian_retrieval")
    assert check["status"] == "fail"
    assert check["retrieval_state"] == state
    assert expected_error_fragment in (check.get("error") or "")
    assert any(
        f"retrieval state is {state}" in error for error in result.errors
    )
    assert _check(result, "historian_canonical")["status"] == "pass"


# ---------------------------------------------------------------------------
# Optional explicit expectations
# ---------------------------------------------------------------------------


def test_expected_heads_and_record_count_pass_when_matching(
    tmp_path: Path,
) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(),
        expect_zth_head=ZTH_HEAD,
        expect_historian_head=HIST_HEAD,
        expect_record_count=CANONICAL_COUNT,
    )
    assert result.status == "pass"
    assert _check(result, "zth_head")["expected"] == ZTH_HEAD
    assert _check(result, "historian_head")["expected"] == HIST_HEAD
    assert _check(result, "historian_record_count")["status"] == "pass"


@pytest.mark.parametrize(
    ("expectation", "check_name", "expected_in_error"),
    [
        ("expect_zth_head", "zth_head", "ZTH HEAD is"),
        ("expect_historian_head", "historian_head", "Historian HEAD is"),
    ],
)
def test_expected_head_mismatch_fails_closed(
    tmp_path: Path, expectation: str, check_name: str, expected_in_error: str
) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(),
        **{expectation: "ef" * 20},
    )
    assert result.status == "fail"
    check = _check(result, check_name)
    assert check["status"] == "fail"
    assert check["expected"] == "ef" * 20
    assert any(expected_in_error in error for error in result.errors)


def test_expected_record_count_mismatch_fails_closed(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(
        zth_repo,
        historian_repo,
        runner=_runner_report(),
        expect_record_count=CANONICAL_COUNT + 1,
    )
    assert result.status == "fail"
    check = _check(result, "historian_record_count")
    assert check["status"] == "fail"
    assert check["actual"] == CANONICAL_COUNT
    assert check["expected"] == CANONICAL_COUNT + 1
    assert any("expected" in error for error in result.errors)


def test_record_count_check_absent_without_expectation(tmp_path: Path) -> None:
    zth_repo, historian_repo = _make_repos(tmp_path)
    result = _run(zth_repo, historian_repo, runner=_runner_report())
    assert "historian_record_count" not in _check_names(result)
    assert result.status == "pass"


# ---------------------------------------------------------------------------
# Read-only behavior, CLI end-to-end with a real runner subprocess
# ---------------------------------------------------------------------------


DEFAULT_CLI_SOURCE = (
    "def validate():\n"
    f"    return {CANONICAL_COUNT}\n"
    "\n"
    "def validate_projection():\n"
    f"    return {PROJECTED_COUNT}\n"
)
DEFAULT_RETRIEVAL_SOURCE = (
    "class RetrievalStateMismatch(RuntimeError):\n"
    "    pass\n"
    "\n"
    "def load_documents(corpus):\n"
    "    return []\n"
    "\n"
    "def validate_state(manifest, docs):\n"
    "    return None\n"
)


def _write_stub_historian_package(
    repo: Path,
    *,
    cli_source: str = DEFAULT_CLI_SOURCE,
    retrieval_source: str = DEFAULT_RETRIEVAL_SOURCE,
) -> None:
    package = repo / "historian"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli.py").write_text(cli_source, encoding="utf-8")
    (package / "retrieval.py").write_text(retrieval_source, encoding="utf-8")


def _write_retrieval_state(
    repo: Path,
    *,
    manifest: dict[str, Any] | None = None,
    embeddings_shape: tuple[int, int] = (2, 4),
    write_manifest: bool = True,
    write_embeddings: bool = True,
    embeddings_bytes: bytes | None = None,
) -> None:
    state = repo / "interfaces" / "retrieval" / "state"
    state.mkdir(parents=True, exist_ok=True)
    if write_manifest:
        payload = (
            manifest
            if manifest is not None
            else {
                "corpus_sha256": "0" * 64,
                "corpus_files": ["records/EVT-a.md"],
                "dimensionality": 4,
                "document_count": 2,
                "encoder_revision": "stub-revision",
                "record_ids": ["EVT-a"],
            }
        )
        (state / "manifest.json").write_text(
            json.dumps(payload) + "\n", encoding="utf-8"
        )
    if write_embeddings:
        if embeddings_bytes is not None:
            (state / "embeddings.npy").write_bytes(embeddings_bytes)
        else:
            assert _np is not None
            _np.save(
                state / "embeddings.npy",
                _np.zeros(embeddings_shape, dtype=_np.float32),
            )


def _make_stub_historian_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "stub-historian"
    repo.mkdir(parents=True, exist_ok=True)
    _write_stub_historian_package(repo)
    _write_retrieval_state(repo)
    (repo / "interfaces" / "khoj" / "corpus" / "records").mkdir(
        parents=True, exist_ok=True
    )
    (repo / "interfaces" / "khoj" / "corpus" / "records" / "EVT-a.md").write_text(
        "corpus record\n", encoding="utf-8"
    )
    return repo


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _run_real_runner(repo: Path, *, pythonpath: Path | None = None) -> dict[str, Any]:
    environment = dict(os.environ)
    prefix = str(pythonpath if pythonpath is not None else repo)
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = os.pathsep.join(
        [prefix] + [part for part in existing.split(os.pathsep) if part]
    )
    completed = subprocess.run(
        [sys.executable, str(RUNNER_SCRIPT), str(repo)],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@requires_numpy
def test_preflight_mutates_neither_repo(tmp_path: Path) -> None:
    zth_repo = tmp_path / "zaphods-third-hand"
    zth_repo.mkdir()
    (zth_repo / "README.md").write_text("stub ZTH repository\n", encoding="utf-8")
    historian_repo = _make_stub_historian_repo(tmp_path)
    before = (_tree_digest(zth_repo), _tree_digest(historian_repo))
    git_side_effect = make_git_side_effect(zth_repo, historian_repo)
    with _patch_subprocess(git_side_effect, runner="real") as patched:
        exit_code = main(
            [
                "--zth-repo",
                str(zth_repo),
                "--historian-repo",
                str(historian_repo),
                "--historian-python",
                sys.executable,
            ]
        )
    assert exit_code == 0
    non_git_calls = [
        call for call in patched.call_args_list if call.args[0][0] != "git"
    ]
    assert len(non_git_calls) == 1
    assert non_git_calls[0].args[0][0] == sys.executable
    after = (_tree_digest(zth_repo), _tree_digest(historian_repo))
    assert before == after


@requires_numpy
def test_cli_end_to_end_pass_with_stub_historian(tmp_path: Path, capsys) -> None:
    zth_repo, _ = _make_repos(tmp_path)
    historian_repo = _make_stub_historian_repo(tmp_path)
    git_side_effect = make_git_side_effect(zth_repo, historian_repo)
    with _patch_subprocess(git_side_effect, runner="real"):
        exit_code = main(
            [
                "--zth-repo",
                str(zth_repo),
                "--historian-repo",
                str(historian_repo),
                "--historian-python",
                sys.executable,
            ]
        )
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PREFLIGHT: PASS" in output
    assert f"  canonical: {CANONICAL_COUNT}" in output
    assert "  retrieval: current" in output


@requires_numpy
def test_cli_end_to_end_json_with_stub_historian(tmp_path: Path, capsys) -> None:
    zth_repo, _ = _make_repos(tmp_path)
    historian_repo = _make_stub_historian_repo(tmp_path)
    git_side_effect = make_git_side_effect(zth_repo, historian_repo)
    with _patch_subprocess(git_side_effect, runner="real"):
        exit_code = main(
            [
                "--zth-repo",
                str(zth_repo),
                "--historian-repo",
                str(historian_repo),
                "--historian-python",
                sys.executable,
                "--json",
            ]
        )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "pass"
    assert payload["historian"]["canonical_count"] == CANONICAL_COUNT
    assert payload["historian"]["retrieval_state"] == "current"
    assert payload["historian"]["runtime"] == sys.executable


@requires_numpy
def test_cli_end_to_end_fails_nonzero_on_dirty_zth(tmp_path: Path, capsys) -> None:
    zth_repo, _ = _make_repos(tmp_path)
    historian_repo = _make_stub_historian_repo(tmp_path)
    git_side_effect = make_git_side_effect(
        zth_repo, historian_repo, zth={"status": _cp(0, b"?? draft.md\x00")}
    )
    with _patch_subprocess(git_side_effect, runner="real"):
        exit_code = main(
            [
                "--zth-repo",
                str(zth_repo),
                "--historian-repo",
                str(historian_repo),
                "--historian-python",
                sys.executable,
            ]
        )
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "PREFLIGHT: FAIL" in output
    assert "draft.md" in output


def test_cli_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0


# ---------------------------------------------------------------------------
# Runner module: real subprocess against stub Historian packages
# ---------------------------------------------------------------------------


@requires_numpy
def test_runner_reports_current_baseline(tmp_path: Path) -> None:
    repo = _make_stub_historian_repo(tmp_path)
    report = _run_real_runner(repo)
    assert report["schema_version"] == RUNNER_SCHEMA
    assert report["canonical"] == {"count": CANONICAL_COUNT, "error": None}
    assert report["projection"] == {"count": PROJECTED_COUNT, "error": None}
    assert report["retrieval"] == {"state": "current", "error": None}
    assert report["historian_root"] == str(repo.resolve())


@requires_numpy
def test_runner_reports_stale_on_state_mismatch(tmp_path: Path) -> None:
    repo = tmp_path / "stub-historian"
    repo.mkdir(parents=True, exist_ok=True)
    _write_stub_historian_package(
        repo,
        retrieval_source=(
            "class RetrievalStateMismatch(RuntimeError):\n"
            "    pass\n"
            "\n"
            "def load_documents(corpus):\n"
            "    return []\n"
            "\n"
            "def validate_state(manifest, docs):\n"
            "    raise RetrievalStateMismatch(\n"
            "        'retrieval state is stale; rebuild state explicitly'\n"
            "    )\n"
        ),
    )
    _write_retrieval_state(repo)
    report = _run_real_runner(repo)
    assert report["retrieval"]["state"] == "stale"
    assert "rebuild state explicitly" in report["retrieval"]["error"]
    assert report["canonical"]["count"] == CANONICAL_COUNT


def test_runner_reports_canonical_and_projection_failures(tmp_path: Path) -> None:
    repo = tmp_path / "stub-historian"
    repo.mkdir(parents=True, exist_ok=True)
    _write_stub_historian_package(
        repo,
        cli_source=(
            "def validate():\n"
            "    raise AssertionError('canonical corpus is inconsistent: DEC-9')\n"
            "\n"
            "def validate_projection():\n"
            f"    return {PROJECTED_COUNT}\n"
        ),
    )
    _write_retrieval_state(repo)
    report = _run_real_runner(repo)
    assert report["canonical"]["count"] is None
    assert "DEC-9" in report["canonical"]["error"]
    assert report["projection"] == {"count": PROJECTED_COUNT, "error": None}
    assert report["retrieval"]["state"] == "current"


def test_runner_reports_stale_when_corpus_drift_breaks_projection(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "stub-historian"
    repo.mkdir(parents=True, exist_ok=True)
    _write_stub_historian_package(
        repo,
        cli_source=(
            "def validate():\n"
            f"    return {CANONICAL_COUNT}\n"
            "\n"
            "def validate_projection():\n"
            "    raise AssertionError('retrieval projection is stale')\n"
        ),
    )
    _write_retrieval_state(repo)
    report = _run_real_runner(repo)
    assert report["projection"]["count"] is None
    assert "retrieval projection is stale" in report["projection"]["error"]


@pytest.mark.parametrize("missing", ["manifest", "embeddings"])
def test_runner_reports_missing_retrieval_artifacts(
    tmp_path: Path, missing: str
) -> None:
    repo = tmp_path / "stub-historian"
    repo.mkdir(parents=True, exist_ok=True)
    _write_stub_historian_package(repo)
    _write_retrieval_state(
        repo,
        write_manifest=missing != "manifest",
        write_embeddings=missing != "embeddings",
    )
    report = _run_real_runner(repo)
    assert report["retrieval"]["state"] == "missing"
    assert missing in report["retrieval"]["error"]
    assert report["canonical"]["count"] == CANONICAL_COUNT


@pytest.mark.parametrize(
    ("manifest_text", "fragment"),
    [
        ('{"corpus_sha256": "0"*64,}', "not valid JSON"),
        ("[1, 2, 3]", "must be a JSON object"),
        (
            json.dumps({"corpus_sha256": "0" * 64}),
            "missing required keys",
        ),
    ],
)
def test_runner_reports_invalid_on_malformed_manifest(
    tmp_path: Path, manifest_text: str, fragment: str
) -> None:
    repo = tmp_path / "stub-historian"
    repo.mkdir(parents=True, exist_ok=True)
    _write_stub_historian_package(repo)
    _write_retrieval_state(repo, write_manifest=False)
    state = repo / "interfaces" / "retrieval" / "state"
    (state / "manifest.json").write_text(manifest_text, encoding="utf-8")
    report = _run_real_runner(repo)
    assert report["retrieval"]["state"] == "invalid"
    assert fragment in report["retrieval"]["error"]
    assert report["canonical"]["count"] == CANONICAL_COUNT


@requires_numpy
def test_runner_reports_invalid_on_embeddings_shape_mismatch(tmp_path: Path) -> None:
    repo = tmp_path / "stub-historian"
    repo.mkdir(parents=True, exist_ok=True)
    _write_stub_historian_package(repo)
    _write_retrieval_state(repo, embeddings_shape=(2, 3))
    report = _run_real_runner(repo)
    assert report["retrieval"]["state"] == "invalid"
    error = report["retrieval"]["error"]
    assert "(2, 3)" in error
    assert "(2, 4)" in error


@requires_numpy
def test_runner_reports_invalid_on_corrupt_embeddings(tmp_path: Path) -> None:
    repo = tmp_path / "stub-historian"
    repo.mkdir(parents=True, exist_ok=True)
    _write_stub_historian_package(repo)
    _write_retrieval_state(repo, embeddings_bytes=b"definitely not an npy file")
    report = _run_real_runner(repo)
    assert report["retrieval"]["state"] == "invalid"
    assert "cannot load retrieval embeddings" in report["retrieval"]["error"]


def test_runner_reports_import_failure_on_repo_without_historian_package(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "empty-historian"
    repo.mkdir(parents=True, exist_ok=True)
    report = _run_real_runner(repo)
    assert report["canonical"]["count"] is None
    assert "cannot import historian.cli" in report["canonical"]["error"]
    assert report["projection"]["count"] is None
    assert "cannot import historian.cli" in report["projection"]["error"]
    assert report["retrieval"]["state"] == "missing"


@requires_numpy
def test_runner_flags_foreign_historian_package(tmp_path: Path) -> None:
    repo = _make_stub_historian_repo(tmp_path)
    foreign = tmp_path / "foreign-historian"
    (foreign / "historian").mkdir(parents=True, exist_ok=True)
    (foreign / "historian" / "__init__.py").write_text("", encoding="utf-8")
    (foreign / "historian" / "cli.py").write_text(
        "def validate():\n    return 999\n\ndef validate_projection():\n    return 999\n",
        encoding="utf-8",
    )
    report = _run_real_runner(repo, pythonpath=foreign)
    assert "different historian package" in report["canonical"]["error"]
    assert "different historian package" in report["projection"]["error"]
    assert report["retrieval"]["state"] == "invalid"
    assert "different historian package" in report["retrieval"]["error"]
    assert report["historian_root"] == str(foreign.resolve())


def test_runner_usage_errors(tmp_path: Path, capsys) -> None:
    assert runner_main(["zth_preflight_historian_runner.py"]) == 2
    assert "usage" in capsys.readouterr().err
    missing = tmp_path / "not-a-repo"
    assert runner_main(["zth_preflight_historian_runner.py", str(missing)]) == 2
    assert "not a directory" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Scope guards
# ---------------------------------------------------------------------------


def test_no_hardcoded_phase_expectations_in_module() -> None:
    source = (REPO_ROOT / "local_harness" / "zth_preflight.py").read_text(
        encoding="utf-8"
    )
    runner_source = RUNNER_SCRIPT.read_text(encoding="utf-8")
    for forbidden in (
        "1eba43f38c574fcac95d1da8a5e2799360613a0f",
        "0285c4de2f44e7a85f4d3d3bef5fe325538bb598",
    ):
        assert forbidden not in source
        assert forbidden not in runner_source
    assert "48" not in source
    assert "48" not in runner_source


# ---------------------------------------------------------------------------
# Negative control: real temporary Git fixture repositories, no mocks
# ---------------------------------------------------------------------------


def _init_real_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for command in (
        ["git", "init", "-q", "."],
        ["git", "config", "user.email", "preflight@example.invalid"],
        ["git", "config", "user.name", "Preflight Fixture"],
    ):
        subprocess.run(command, cwd=path, check=True, capture_output=True)
    (path / "README.md").write_text("fixture baseline\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-qm", "fixture baseline"],
        cwd=path,
        check=True,
        capture_output=True,
    )


@requires_numpy
def test_negative_control_real_git_fixture_fails_closed(tmp_path: Path) -> None:
    """Deliberate negative case against real temporary Git repositories.

    Proves, through the real command path (real git subprocesses, real
    Historian runtime subprocess, no mocks), that a dirty ZTH worktree fails
    the preflight with the exact changed paths surfaced while the Historian
    side still reports its full baseline — and that neither fixture repo is
    mutated by the run.
    """
    zth_fixture = tmp_path / "zth-fixture"
    historian_fixture = tmp_path / "historian-fixture"
    _init_real_git_repo(zth_fixture)
    _init_real_git_repo(historian_fixture)
    _write_stub_historian_package(historian_fixture)
    _write_retrieval_state(historian_fixture)
    corpus_records = (
        historian_fixture / "interfaces" / "khoj" / "corpus" / "records"
    )
    corpus_records.mkdir(parents=True, exist_ok=True)
    (corpus_records / "EVT-a.md").write_text("corpus record\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-A"], cwd=historian_fixture, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-qm", "historian fixture baseline"],
        cwd=historian_fixture,
        check=True,
        capture_output=True,
    )

    with (zth_fixture / "README.md").open("a", encoding="utf-8") as handle:
        handle.write("uncommitted edit\n")
    (zth_fixture / "scratch-note.txt").write_text(
        "stray untracked note\n", encoding="utf-8"
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "local_harness" / "zth_preflight.py"),
            "--zth-repo",
            str(zth_fixture),
            "--historian-repo",
            str(historian_fixture),
            "--historian-python",
            sys.executable,
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout
    assert completed.returncode == 1
    assert "PREFLIGHT: FAIL" in output
    assert "worktree: dirty (2 changed path(s))" in output
    assert " M README.md" in output
    assert "?? scratch-note.txt" in output
    assert f"  canonical: {CANONICAL_COUNT}" in output
    assert "  retrieval: current" in output
    assert "  counts: agree" in output

    historian_status = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=historian_fixture,
        capture_output=True,
        text=True,
        check=False,
    )
    assert historian_status.returncode == 0
    assert historian_status.stdout == ""
