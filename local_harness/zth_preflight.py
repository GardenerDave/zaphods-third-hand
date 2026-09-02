#!/usr/bin/env python3
"""ZTH + Project Historian baseline preflight: one read-only, fail-closed command.

This tool reports the operational baseline for both repositories and exits
non-zero on material drift. It replaces the repeated per-repo status ceremony
(git status, git rev-parse, Historian canonical/projection validation, and a
separate retrieval-state currency check) with a single command.

Boundaries:

- this tool is an observer only; it grants no execution, file-modification,
  commit, merge, lifecycle, review, promotion, or training authority;
- a PASS means only that the requested baseline invariants were observed;
  it is not permission to act;
- neither repository is modified, cleaned, stashed, reset, rebuilt, or
  repaired by this command; retrieval state is never silently rebuilt;
- a dirty worktree is a failed clean-baseline precondition, not a defect
  this tool fixes.

Expected phase HEADs and record counts are never hardcoded here. Optional
expectations are explicit CLI arguments supplied by the operator.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_NAME = "local_harness/zth_preflight.py"
PREFLIGHT_SCHEMA = "zth.historian_baseline_preflight.v1"
RUNNER_SCRIPT = Path(__file__).resolve().parent / "zth_preflight_historian_runner.py"
BUNDLED_RUNTIME = Path("interfaces/khoj/runtime/py312-cpu/bin/python")

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
RETRIEVAL_CURRENT = "current"
SUPPORTED_RETRIEVAL_STATES = ("current", "stale", "missing", "invalid")
DEFAULT_TIMEOUT_SECONDS = 120
MAX_STDERR_TAIL = 400
HEAD_RE = re.compile(r"^[0-9a-f]{40}$")

PREFLIGHT_BOUNDARIES = (
    "This preflight is an observer only; it grants no execution, file-modification, commit, merge, lifecycle, review, promotion, or training authority.",
    "A PASS means only that the requested baseline invariants were observed; it is not permission to act.",
    "Neither repository is modified, cleaned, stashed, reset, rebuilt, or repaired by this command.",
    "A dirty worktree is a failed clean-baseline precondition, not a defect to be fixed by this tool.",
)


@dataclass(frozen=True)
class GitStatus:
    repo: Path
    exists: bool
    git_repo: bool
    head: str | None
    head_error: str | None
    clean: bool | None
    changed: tuple[tuple[str, str], ...]
    status_error: str | None
    git_error: str | None


@dataclass(frozen=True)
class HistorianBaseline:
    runtime: str | None = None
    runtime_error: str | None = None
    runner_error: str | None = None
    canonical_count: int | None = None
    canonical_error: str | None = None
    projected_count: int | None = None
    projection_error: str | None = None
    counts_agree: bool | None = None
    retrieval_state: str | None = None
    retrieval_error: str | None = None


@dataclass(frozen=True)
class PreflightResult:
    status: str
    zth: GitStatus
    historian: GitStatus
    historian_baseline: HistorianBaseline
    checks: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="surrogateescape")


def _stderr_tail(stderr: bytes | str | None) -> str:
    text = (stderr if isinstance(stderr, str) else _decode(stderr or b"")).strip()
    if not text:
        return "<no stderr>"
    return text[-MAX_STDERR_TAIL:]


def _run_git(repo: Path, args: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )


def _parse_porcelain(raw: bytes) -> tuple[tuple[str, str], ...] | None:
    """Parse ``git status --porcelain=v1 -z --no-renames`` output.

    With ``--no-renames`` every record is exactly ``XY PATH`` terminated by
    one NUL byte, so parsing stays deterministic without quoting rules. Any
    structurally unexpected record is refused (fail-closed) by returning
    ``None``.
    """
    entries: list[tuple[str, str]] = []
    for record in raw.split(b"\x00"):
        if not record:
            continue
        if len(record) < 4 or record[2:3] != b" ":
            return None
        status_code = record[:2].decode("ascii", errors="replace")
        path = record[3:].decode("utf-8", errors="surrogateescape")
        if not path:
            return None
        entries.append((status_code, path))
    return tuple(entries)


def observe_git(repo: Path, label: str) -> GitStatus:
    """Observe one repository's baseline Git state without changing it."""
    if not repo.exists():
        return GitStatus(
            repo=repo,
            exists=False,
            git_repo=False,
            head=None,
            head_error=None,
            clean=None,
            changed=(),
            status_error=None,
            git_error=f"{label} repository path does not exist: {repo}",
        )
    if not repo.is_dir():
        return GitStatus(
            repo=repo,
            exists=False,
            git_repo=False,
            head=None,
            head_error=None,
            clean=None,
            changed=(),
            status_error=None,
            git_error=f"{label} repository path is not a directory: {repo}",
        )
    try:
        git_dir = _run_git(repo, ("rev-parse", "--git-dir"))
    except OSError as exc:
        return GitStatus(repo, True, False, None, None, None, (), None,
                         f"{label} git subprocess could not be launched: {exc}")
    if git_dir.returncode != 0:
        detail = _decode(git_dir.stderr).strip() or "git rev-parse --git-dir failed"
        return GitStatus(repo, True, False, None, None, None, (), None,
                         f"{label} is not a usable Git repository: {detail}")

    head: str | None = None
    head_error: str | None = None
    try:
        head_result = _run_git(repo, ("rev-parse", "HEAD"))
    except OSError as exc:
        head_error = f"{label} git subprocess could not be launched: {exc}"
    else:
        if head_result.returncode != 0:
            detail = _decode(head_result.stderr).strip() or "git rev-parse HEAD failed"
            head_error = f"{label} has no commits on HEAD: {detail}"
        else:
            head = _decode(head_result.stdout).strip()
            if not HEAD_RE.fullmatch(head):
                head = None
                head_error = f"{label} returned an unexpected HEAD value: {head!r}"

    clean: bool | None = None
    changed: tuple[tuple[str, str], ...] = ()
    status_error: str | None = None
    try:
        status_result = _run_git(
            repo, ("status", "--porcelain=v1", "-z", "--no-renames")
        )
    except OSError as exc:
        status_error = f"{label} git subprocess could not be launched: {exc}"
    else:
        if status_result.returncode != 0:
            detail = _decode(status_result.stderr).strip() or "git status failed"
            status_error = f"{label} git status failed: {detail}"
        else:
            parsed = _parse_porcelain(status_result.stdout)
            if parsed is None:
                status_error = (
                    f"{label} git status returned output this tool cannot parse "
                    "safely; refusing to guess"
                )
            else:
                changed = parsed
                clean = not changed
    return GitStatus(repo, True, True, head, head_error, clean, changed,
                     status_error, None)


def resolve_historian_python(
    historian_repo: Path, override: Path | None
) -> tuple[Path | None, str | None]:
    if override is not None:
        if not override.is_file() or not os.access(override, os.X_OK):
            return None, (
                "unsupported Historian runtime: --historian-python is not an "
                f"executable file: {override}"
            )
        return override, None
    bundled = historian_repo / BUNDLED_RUNTIME
    if bundled.is_file() and os.access(bundled, os.X_OK):
        return bundled, None
    return None, (
        "unsupported Historian runtime: no bundled Historian retrieval runtime "
        f"at {bundled}; pass --historian-python pointing at a Python interpreter "
        "with the Historian retrieval stack installed"
    )


def _runner_environment(historian_repo: Path) -> dict[str, str]:
    environment = dict(os.environ)
    existing_path = environment.get("PYTHONPATH", "")
    parts = [str(historian_repo)] + [
        part for part in existing_path.split(os.pathsep) if part
    ]
    environment["PYTHONPATH"] = os.pathsep.join(parts)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def run_historian_runner(
    historian_repo: Path, historian_python: Path, timeout_seconds: int
) -> tuple[dict[str, Any] | None, str | None]:
    if not RUNNER_SCRIPT.is_file():
        return None, f"preflight runner script not found: {RUNNER_SCRIPT}"
    command = [str(historian_python), str(RUNNER_SCRIPT), str(historian_repo)]
    try:
        completed = subprocess.run(
            command,
            cwd=str(historian_repo),
            env=_runner_environment(historian_repo),
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, (
            f"Historian baseline runner timed out after {timeout_seconds}s "
            f"using {historian_python}"
        )
    except OSError as exc:
        return None, f"failed to launch Historian runtime {historian_python}: {exc}"
    if completed.returncode != 0:
        return None, (
            "Historian baseline runner exited "
            f"{completed.returncode}: {_stderr_tail(completed.stderr)}"
        )
    try:
        report = json.loads(_decode(completed.stdout))
    except json.JSONDecodeError as exc:
        return None, (
            "Historian baseline runner did not return JSON: "
            f"{exc}; stderr tail: {_stderr_tail(completed.stderr)}"
        )
    if not isinstance(report, dict):
        return None, "Historian baseline runner did not return a JSON object"
    return report, None


def _runner_count(
    report: dict[str, Any], key: str
) -> tuple[int | None, str | None]:
    section = report.get(key)
    if not isinstance(section, dict):
        return None, f"runner {key} section is missing or malformed"
    error = section.get("error")
    if error is not None:
        if not isinstance(error, str) or not error:
            return None, f"runner {key} error is malformed (expected a string or null)"
        return None, error
    count = section.get("count")
    if not isinstance(count, int) or isinstance(count, bool):
        return None, f"runner {key} count is missing or malformed"
    return count, None


def _runner_retrieval(report: dict[str, Any]) -> tuple[str, str | None]:
    section = report.get("retrieval")
    if not isinstance(section, dict):
        return "invalid", "runner retrieval section is missing or malformed"
    state = section.get("state")
    if state not in SUPPORTED_RETRIEVAL_STATES:
        return "invalid", f"runner reported an unsupported retrieval state: {state!r}"
    error = section.get("error")
    if error is None or (isinstance(error, str) and not error):
        return state, None
    if not isinstance(error, str):
        return "invalid", "runner retrieval error is malformed (expected a string or null)"
    return state, error


def _record(
    checks: list[dict[str, Any]], name: str, ok: bool, **detail: Any
) -> None:
    entry: dict[str, Any] = {"name": name, "status": STATUS_PASS if ok else STATUS_FAIL}
    entry.update(detail)
    checks.append(entry)


def _observe_repo_checks(
    *,
    status: GitStatus,
    label: str,
    expected_head: str | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    prefix = label.lower()
    if not status.exists:
        errors.append(status.git_error or f"{label} repository is missing")
        _record(checks, f"{prefix}_repo_exists", False, error=status.git_error)
        return
    _record(checks, f"{prefix}_repo_exists", True)
    if not status.git_repo:
        errors.append(status.git_error or f"{label} is not a usable Git repository")
        _record(checks, f"{prefix}_git_repo", False, error=status.git_error)
        return
    _record(checks, f"{prefix}_git_repo", True)

    if status.head is None:
        message = status.head_error or f"{label} HEAD could not be observed"
        errors.append(message)
        _record(checks, f"{prefix}_head", False, error=message)
    elif expected_head is not None and status.head != expected_head:
        message = f"{label} HEAD is {status.head}, expected {expected_head}"
        errors.append(message)
        _record(
            checks,
            f"{prefix}_head",
            False,
            head=status.head,
            expected=expected_head,
        )
    else:
        _record(
            checks, f"{prefix}_head", True, head=status.head, expected=expected_head
        )

    if status.clean is None:
        message = status.status_error or f"{label} worktree status could not be observed"
        errors.append(message)
        _record(checks, f"{prefix}_clean", False, error=message)
    elif not status.clean:
        listing = ", ".join(f"{code} {path}" for code, path in status.changed)
        message = (
            f"{label} worktree is dirty ({len(status.changed)} changed path(s)): {listing}"
        )
        errors.append(message)
        _record(
            checks,
            f"{prefix}_clean",
            False,
            changed_paths=[
                {"status": code, "path": path} for code, path in status.changed
            ],
        )
    else:
        _record(checks, f"{prefix}_clean", True, changed_paths=[])


def _observe_historian_baseline(
    *,
    historian_repo: Path,
    historian_python: Path | None,
    timeout_seconds: int,
    expect_record_count: int | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> HistorianBaseline:
    runtime, runtime_error = resolve_historian_python(historian_repo, historian_python)
    if runtime is None:
        errors.append(runtime_error or "unsupported Historian runtime")
        _record(
            checks, "historian_runtime", False, error=runtime_error
        )
        return HistorianBaseline(runtime_error=runtime_error)
    _record(checks, "historian_runtime", True, runtime=str(runtime))

    report, runner_error = run_historian_runner(
        historian_repo, runtime, timeout_seconds
    )
    if report is None:
        errors.append(runner_error or "Historian baseline runner failed")
        for name in (
            "historian_canonical",
            "historian_projection",
            "historian_counts_agree",
            "historian_retrieval",
        ):
            _record(checks, name, False, error=runner_error)
        if expect_record_count is not None:
            _record(
                checks, "historian_record_count", False, error=runner_error
            )
        return HistorianBaseline(
            runtime=str(runtime), runner_error=runner_error
        )

    canonical_count, canonical_error = _runner_count(report, "canonical")
    projected_count, projection_error = _runner_count(report, "projection")
    retrieval_state, retrieval_error = _runner_retrieval(report)

    if canonical_error is not None:
        errors.append(f"Historian canonical validation failed: {canonical_error}")
        _record(checks, "historian_canonical", False, error=canonical_error)
    else:
        _record(checks, "historian_canonical", True, count=canonical_count)

    if projection_error is not None:
        errors.append(f"Historian projection validation failed: {projection_error}")
        _record(checks, "historian_projection", False, error=projection_error)
    else:
        _record(checks, "historian_projection", True, count=projected_count)

    counts_agree: bool | None = None
    if canonical_count is not None and projected_count is not None:
        counts_agree = canonical_count == projected_count
    if counts_agree is True:
        _record(
            checks,
            "historian_counts_agree",
            True,
            canonical=canonical_count,
            projected=projected_count,
        )
    else:
        if counts_agree is False:
            message = (
                "Historian canonical/projected counts disagree: "
                f"canonical={canonical_count}, projected={projected_count}"
            )
        else:
            message = (
                "Historian canonical/projected count agreement could not be "
                "verified: canonical or projection validation failed"
            )
        errors.append(message)
        _record(
            checks,
            "historian_counts_agree",
            False,
            canonical=canonical_count,
            projected=projected_count,
            error=message,
        )

    if expect_record_count is not None:
        if canonical_count == expect_record_count:
            _record(
                checks,
                "historian_record_count",
                True,
                actual=canonical_count,
                expected=expect_record_count,
            )
        else:
            message = (
                "Historian canonical record count is "
                f"{canonical_count!r}, expected {expect_record_count}"
            )
            errors.append(message)
            _record(
                checks,
                "historian_record_count",
                False,
                actual=canonical_count,
                expected=expect_record_count,
                error=message,
            )

    if retrieval_state != RETRIEVAL_CURRENT:
        message = f"Historian retrieval state is {retrieval_state}"
        if retrieval_error:
            message = f"{message}: {retrieval_error}"
        errors.append(message)
        _record(
            checks,
            "historian_retrieval",
            False,
            retrieval_state=retrieval_state,
            error=retrieval_error,
        )
    else:
        _record(
            checks, "historian_retrieval", True, retrieval_state=RETRIEVAL_CURRENT
        )

    return HistorianBaseline(
        runtime=str(runtime),
        canonical_count=canonical_count,
        canonical_error=canonical_error,
        projected_count=projected_count,
        projection_error=projection_error,
        counts_agree=counts_agree,
        retrieval_state=retrieval_state,
        retrieval_error=retrieval_error,
    )


def run_preflight(
    *,
    zth_repo: Path,
    historian_repo: Path,
    historian_python: Path | None = None,
    expect_zth_head: str | None = None,
    expect_historian_head: str | None = None,
    expect_record_count: int | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> PreflightResult:
    """Observe both repos' baseline state; return a structured result."""
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    zth = observe_git(zth_repo, "ZTH")
    _observe_repo_checks(
        status=zth,
        label="ZTH",
        expected_head=expect_zth_head,
        checks=checks,
        errors=errors,
    )

    historian = observe_git(historian_repo, "Historian")
    _observe_repo_checks(
        status=historian,
        label="Historian",
        expected_head=expect_historian_head,
        checks=checks,
        errors=errors,
    )

    baseline = HistorianBaseline()
    if historian.exists and historian.git_repo:
        baseline = _observe_historian_baseline(
            historian_repo=historian_repo,
            historian_python=historian_python,
            timeout_seconds=timeout_seconds,
            expect_record_count=expect_record_count,
            checks=checks,
            errors=errors,
        )

    status = STATUS_PASS if not errors else STATUS_FAIL
    return PreflightResult(
        status=status,
        zth=zth,
        historian=historian,
        historian_baseline=baseline,
        checks=tuple(checks),
        errors=tuple(errors),
    )


def _indent_error(error: str) -> str:
    lines = [line for line in error.splitlines() if line.strip()]
    return "\n".join(f"    {line}" for line in lines) if lines else "    <no detail>"


def _format_repo_section(label: str, status: GitStatus) -> list[str]:
    lines = [label]
    if not status.exists:
        lines.append(f"  repository: {status.git_error}")
        return lines
    if not status.git_repo:
        lines.append(f"  git: {status.git_error}")
        return lines
    lines.append(f"  head: {status.head if status.head is not None else 'unknown'}")
    if status.head_error:
        lines.append(_indent_error(status.head_error))
    if status.clean is None:
        lines.append(f"  worktree: unknown ({status.status_error})")
    elif status.clean:
        lines.append("  worktree: clean")
    else:
        lines.append(f"  worktree: dirty ({len(status.changed)} changed path(s))")
        for code, path in status.changed:
            lines.append(f"    {code} {path}")
    if status.status_error and status.clean is not None:
        lines.append(_indent_error(status.status_error))
    return lines


def format_human(result: PreflightResult) -> str:
    lines: list[str] = []
    lines.extend(_format_repo_section("ZTH", result.zth))
    lines.append("")
    lines.extend(_format_repo_section("Historian", result.historian))
    baseline = result.historian_baseline
    if result.historian.exists and result.historian.git_repo:
        if baseline.runtime_error:
            lines.append(f"  runtime: unsupported ({baseline.runtime_error})")
        elif baseline.runtime:
            lines.append(f"  runtime: {baseline.runtime}")
        if baseline.runner_error:
            lines.append(f"  baseline runner: failed")
            lines.append(_indent_error(baseline.runner_error))
        if baseline.canonical_count is not None:
            lines.append(f"  canonical: {baseline.canonical_count}")
        elif baseline.canonical_error:
            lines.append("  canonical: FAILED")
            lines.append(_indent_error(baseline.canonical_error))
        elif baseline.runner_error or baseline.runtime_error:
            lines.append("  canonical: not evaluated")
        if baseline.projected_count is not None:
            lines.append(f"  projected: {baseline.projected_count}")
        elif baseline.projection_error:
            lines.append("  projected: FAILED")
            lines.append(_indent_error(baseline.projection_error))
        elif baseline.runner_error or baseline.runtime_error:
            lines.append("  projected: not evaluated")
        if baseline.counts_agree is True:
            lines.append("  counts: agree")
        elif baseline.counts_agree is False:
            lines.append(
                "  counts: MISMATCH "
                f"(canonical={baseline.canonical_count}, "
                f"projected={baseline.projected_count})"
            )
        elif baseline.runner_error or baseline.runtime_error:
            lines.append("  counts: not evaluated")
        if baseline.retrieval_state is not None:
            lines.append(f"  retrieval: {baseline.retrieval_state}")
            if baseline.retrieval_error:
                lines.append(_indent_error(baseline.retrieval_error))
        elif baseline.runner_error or baseline.runtime_error:
            lines.append("  retrieval: not evaluated")
    lines.append("")
    if result.errors:
        lines.append(f"Failures ({len(result.errors)}):")
        for error in result.errors:
            flattened = " | ".join(
                line.strip() for line in error.splitlines() if line.strip()
            )
            lines.append(f"  - {flattened}")
        lines.append("")
    lines.append(f"PREFLIGHT: {result.status.upper()}")
    for boundary in PREFLIGHT_BOUNDARIES:
        lines.append(f"Boundary: {boundary}")
    return "\n".join(lines)


def _repo_json(status: GitStatus) -> dict[str, Any]:
    return {
        "repo": str(status.repo),
        "exists": status.exists,
        "git_repo": status.git_repo,
        "head": status.head,
        "clean": status.clean,
        "changed_paths": [
            {"status": code, "path": path} for code, path in status.changed
        ],
        "git_error": status.git_error,
        "head_error": status.head_error,
        "status_error": status.status_error,
    }


def result_json(result: PreflightResult) -> dict[str, Any]:
    baseline = result.historian_baseline
    historian = _repo_json(result.historian)
    historian.update(
        {
            "runtime": baseline.runtime,
            "runtime_error": baseline.runtime_error,
            "runner_error": baseline.runner_error,
            "canonical_count": baseline.canonical_count,
            "canonical_error": baseline.canonical_error,
            "projected_count": baseline.projected_count,
            "projection_error": baseline.projection_error,
            "counts_agree": baseline.counts_agree,
            "retrieval_state": baseline.retrieval_state,
            "retrieval_error": baseline.retrieval_error,
        }
    )
    return {
        "schema_version": PREFLIGHT_SCHEMA,
        "status": result.status,
        "zth": _repo_json(result.zth),
        "historian": historian,
        "checks": [dict(check) for check in result.checks],
        "errors": list(result.errors),
        "boundaries": list(PREFLIGHT_BOUNDARIES),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report the ZTH and Project Historian operational baseline and exit "
            "non-zero on drift. Read-only observer: this command changes nothing "
            "and grants no authority."
        )
    )
    parser.add_argument(
        "--zth-repo",
        type=Path,
        default=REPO_ROOT,
        help="ZTH repository root (defaults to the repository containing this module).",
    )
    parser.add_argument(
        "--historian-repo",
        type=Path,
        required=True,
        help="Project Historian repository root (read-only baseline source).",
    )
    parser.add_argument(
        "--historian-python",
        type=Path,
        help=(
            "Python interpreter with the Historian retrieval stack; defaults to "
            "the Historian bundled runtime when present."
        ),
    )
    parser.add_argument(
        "--expect-zth-head",
        help="Optional expected ZTH HEAD (full 40-hex commit id); omitted means report only.",
    )
    parser.add_argument(
        "--expect-historian-head",
        help="Optional expected Historian HEAD (full 40-hex commit id); omitted means report only.",
    )
    parser.add_argument(
        "--expect-record-count",
        type=int,
        help="Optional expected Historian canonical record count; omitted means report only.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Historian baseline runner timeout in seconds (default {DEFAULT_TIMEOUT_SECONDS}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON report instead of human-readable text.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_preflight(
        zth_repo=args.zth_repo,
        historian_repo=args.historian_repo,
        historian_python=args.historian_python,
        expect_zth_head=args.expect_zth_head,
        expect_historian_head=args.expect_historian_head,
        expect_record_count=args.expect_record_count,
        timeout_seconds=args.timeout,
    )
    if args.json:
        print(json.dumps(result_json(result), indent=2, sort_keys=True))
    else:
        print(format_human(result))
    return 0 if result.status == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
