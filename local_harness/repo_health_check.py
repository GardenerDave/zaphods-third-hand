#!/usr/bin/env python3
"""Run human-invoked repository health checks without changing repository state."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import unquote

import validate_scaffold


REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIP = "SKIP"

MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

PRIVACY_PATTERNS = (
    ("private RFC1918 address", re.compile(r"\b(?:192\.168\.|10\.0\.|172\.16\.)")),
    ("private user/host marker", re.compile(r"\bnavigator@")),
    ("stale auth variable", re.compile(r"\bZTH_API_KEY\b")),
    (
        "concrete local model identifier",
        re.compile(r"\bQwen/Qwen2\.5-Coder-7B-Instruct-GGUF:Q4_K_M\b"),
    ),
)
BOUNDARY_PATTERNS = (
    ("automatic promotion claim", re.compile(r"\bautomatically promotes?\b", re.I)),
    ("automatic promotion claim", re.compile(r"\bauto-promotes?\b", re.I)),
    (
        "truth-validation claim",
        re.compile(r"\bvalidates?\s+(?:semantic\s+)?truth\b", re.I),
    ),
    (
        "safety-validation claim",
        re.compile(r"\bvalidates?\s+(?:semantic\s+)?safety\b", re.I),
    ),
    ("approval-gate claim", re.compile(r"\bapproval gate\b", re.I)),
)
NEGATION_RE = re.compile(
    r"(?:"
    r"\b(?:does|do|did|is|are|was|were|will|can|must|should)\s+not\b|"
    r"\bnever\b|"
    r"\bnot\b|"
    r"\bno\b(?:\s+\w+){0,4}"
    r")[^.!?;:\n]{0,60}$",
    re.I,
)
TEXT_SUFFIXES = {
    ".cfg",
    ".env",
    ".ini",
    ".json",
    ".jsonl",
    ".md",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class CheckResult:
    key: str
    label: str
    status: str
    summary: str
    details: tuple[str, ...] = ()


def relative_display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def tracked_markdown_files(repo_root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--", "*.md"],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise RuntimeError(f"could not run git ls-files: {exc}") from exc
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed: {message or 'unknown error'}")
    return [
        repo_root / raw.decode("utf-8", errors="surrogateescape")
        for raw in result.stdout.split(b"\0")
        if raw
    ]


def fence_marker(line: str) -> tuple[str, int] | None:
    match = FENCE_RE.match(line)
    if not match:
        return None
    marker = match.group(1)
    return marker[0], len(marker)


def markdown_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(None, 1)[0] if target else ""
    if (
        not target
        or target.startswith(("#", "/", "//"))
        or URI_SCHEME_RE.match(target)
    ):
        return None
    path_only = target.split("#", 1)[0].split("?", 1)[0]
    return unquote(path_only) if path_only else None


def check_markdown_links(
    repo_root: Path,
    files: Sequence[Path] | None = None,
) -> CheckResult:
    try:
        markdown_files = list(files) if files is not None else tracked_markdown_files(repo_root)
    except RuntimeError as exc:
        return CheckResult("docs_links", "docs links", STATUS_FAIL, str(exc))

    missing: list[str] = []
    unreadable: list[str] = []
    for source in markdown_files:
        try:
            lines = source.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(f"{relative_display(source, repo_root)}: {exc}")
            continue

        active_fence: tuple[str, int] | None = None
        for line_number, line in enumerate(lines, start=1):
            marker = fence_marker(line)
            if marker:
                if active_fence is None:
                    active_fence = marker
                    continue
                if marker[0] == active_fence[0] and marker[1] >= active_fence[1]:
                    active_fence = None
                    continue
            if active_fence is not None:
                continue

            for match in MARKDOWN_LINK_RE.finditer(line):
                target = markdown_target(match.group(1))
                if target is None:
                    continue
                candidate = source.parent / target
                if not candidate.exists():
                    missing.append(
                        f"{relative_display(source, repo_root)}:{line_number}: "
                        f"missing target {match.group(1)!r}"
                    )

    details = tuple(unreadable + missing)
    if details:
        return CheckResult(
            "docs_links",
            "docs links",
            STATUS_FAIL,
            f"checked {len(markdown_files)} Markdown files; found {len(details)} problem(s)",
            details,
        )
    return CheckResult(
        "docs_links",
        "docs links",
        STATUS_PASS,
        f"checked {len(markdown_files)} tracked Markdown files; no missing file targets",
    )


def is_public_text_file(path: Path) -> bool:
    return path.name == "config.example.env" or path.suffix.lower() in TEXT_SUFFIXES


def public_surface_files(repo_root: Path) -> list[Path]:
    candidates: set[Path] = set()
    for name in ("README.md", "QUICKSTART.md", "FIRST_SUCCESS.md", "config.example.env"):
        path = repo_root / name
        if path.is_file():
            candidates.add(path)

    for directory_name in ("docs", "examples"):
        directory = repo_root / directory_name
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or not is_public_text_file(path):
                continue
            relative = path.relative_to(repo_root)
            if relative.parts[:2] == ("docs", "reports"):
                continue
            if any(part in {".pytest_cache", "__pycache__"} for part in relative.parts):
                continue
            candidates.add(path)
    return sorted(candidates)


def scan_patterns(
    repo_root: Path,
    files: Sequence[Path],
    patterns: Sequence[tuple[str, re.Pattern[str]]],
) -> tuple[list[str], list[str]]:
    findings: list[str] = []
    unreadable: list[str] = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(f"{relative_display(path, repo_root)}: {exc}")
            continue
        for line_number, line in enumerate(lines, start=1):
            for description, pattern in patterns:
                if pattern.search(line):
                    findings.append(
                        f"{relative_display(path, repo_root)}:{line_number}: {description}"
                    )
    return findings, unreadable


def check_privacy(
    repo_root: Path,
    files: Sequence[Path] | None = None,
) -> CheckResult:
    public_files = list(files) if files is not None else public_surface_files(repo_root)
    findings, unreadable = scan_patterns(repo_root, public_files, PRIVACY_PATTERNS)
    details = tuple(unreadable + findings)
    if details:
        return CheckResult(
            "privacy",
            "privacy",
            STATUS_FAIL,
            f"checked {len(public_files)} public-surface files; found {len(details)} problem(s)",
            details,
        )
    return CheckResult(
        "privacy",
        "privacy",
        STATUS_PASS,
        (
            f"checked {len(public_files)} public-surface files; no configured leaks found "
            "(docs/reports excluded)"
        ),
    )


def claim_is_negated(line: str, start: int) -> bool:
    prefix = line[:start]
    if re.search(r"\bnot\s+only\b[^.!?;:\n]{0,60}$", prefix, re.I):
        return False
    return NEGATION_RE.search(prefix) is not None


def check_boundary_language(
    repo_root: Path,
    files: Sequence[Path] | None = None,
) -> CheckResult:
    try:
        markdown_files = list(files) if files is not None else tracked_markdown_files(repo_root)
    except RuntimeError as exc:
        return CheckResult(
            "boundary_language",
            "boundary language",
            STATUS_FAIL,
            str(exc),
        )

    findings: list[str] = []
    unreadable: list[str] = []
    for path in markdown_files:
        if relative_display(path, repo_root).startswith("docs/reports/"):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(f"{relative_display(path, repo_root)}: {exc}")
            continue
        for line_index, line in enumerate(lines):
            line_number = line_index + 1
            prior_lines = lines[max(0, line_index - 2) : line_index]
            prior_context = " ".join(prior_lines)
            context = f"{prior_context} {line}" if prior_context else line
            context_offset = len(prior_context) + 1 if prior_context else 0
            for description, pattern in BOUNDARY_PATTERNS:
                for match in pattern.finditer(line):
                    if not claim_is_negated(context, context_offset + match.start()):
                        findings.append(
                            f"{relative_display(path, repo_root)}:{line_number}: "
                            f"{description}: {match.group(0)!r}"
                        )

    details = tuple(unreadable + findings)
    if details:
        return CheckResult(
            "boundary_language",
            "boundary language",
            STATUS_FAIL,
            f"found {len(details)} positive or ambiguous authority claim(s)",
            details,
        )
    return CheckResult(
        "boundary_language",
        "boundary language",
        STATUS_PASS,
        "no configured positive authority-expanding claims found",
    )


def discover_tracked_scaffolds(repo_root: Path) -> list[Path]:
    discovered: list[Path] = []
    for path in tracked_markdown_files(repo_root):
        relative = path.relative_to(repo_root)
        if relative.parts[:2] in {("docs", "templates"), ("docs", "prompts")}:
            continue
        if relative.parts and relative.parts[0] == "prompts":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        first_line = text.splitlines()[0] if text else ""
        if (
            "scaffold_contract_version:" in text
            and first_line.startswith(("# Tool Lifecycle Draft:", "# Change Closeout Report:"))
        ):
            discovered.append(path)
    return discovered


def check_scaffolds(
    repo_root: Path,
    scaffold_paths: Sequence[Path] | None = None,
) -> CheckResult:
    explicit = list(scaffold_paths or ())
    if explicit:
        paths = [path if path.is_absolute() else repo_root / path for path in explicit]
    else:
        try:
            paths = discover_tracked_scaffolds(repo_root)
        except RuntimeError as exc:
            return CheckResult("scaffolds", "scaffolds", STATUS_FAIL, str(exc))

    if not paths:
        return CheckResult(
            "scaffolds",
            "scaffolds",
            STATUS_SKIP,
            "no explicit or tracked completed scaffolds found; .work was not scanned",
        )

    invalid: list[str] = []
    valid: list[str] = []
    for path in paths:
        try:
            kind = validate_scaffold.validate_scaffold(path)
        except (OSError, validate_scaffold.ScaffoldValidationError) as exc:
            invalid.append(f"{relative_display(path, repo_root)}: {exc}")
        else:
            valid.append(f"{relative_display(path, repo_root)}: {kind}")
    if invalid:
        return CheckResult(
            "scaffolds",
            "scaffolds",
            STATUS_FAIL,
            f"validated {len(paths)} scaffold(s); {len(invalid)} invalid",
            tuple(invalid),
        )
    return CheckResult(
        "scaffolds",
        "scaffolds",
        STATUS_PASS,
        f"validated {len(valid)} scaffold(s)",
        tuple(valid),
    )


def run_subprocess_check(
    *,
    key: str,
    label: str,
    command: Sequence[str],
    repo_root: Path,
    stream_output: bool = False,
) -> CheckResult:
    try:
        if stream_output:
            result = subprocess.run(command, cwd=repo_root, check=False)
            output = ""
        else:
            result = subprocess.run(
                command,
                cwd=repo_root,
                check=False,
                text=True,
                capture_output=True,
            )
            output = "\n".join(
                part.strip() for part in (result.stdout, result.stderr) if part.strip()
            )
    except OSError as exc:
        return CheckResult(key, label, STATUS_FAIL, f"could not run command: {exc}")
    if result.returncode:
        details = tuple(output.splitlines()) if output else ()
        return CheckResult(
            key,
            label,
            STATUS_FAIL,
            f"command exited {result.returncode}",
            details,
        )
    return CheckResult(key, label, STATUS_PASS, "command passed")


def run_diff_check(repo_root: Path) -> CheckResult:
    return run_subprocess_check(
        key="diff_check",
        label="diff check",
        command=("git", "diff", "--check"),
        repo_root=repo_root,
    )


def run_pytest_check(repo_root: Path) -> CheckResult:
    return run_subprocess_check(
        key="pytest",
        label="pytest",
        command=(sys.executable, "-m", "pytest", "local_harness/tests"),
        repo_root=repo_root,
        stream_output=True,
    )


def print_result(result: CheckResult) -> None:
    print(f"[{result.status}] {result.label}: {result.summary}")
    for detail in result.details:
        print(f"  {detail}")


def skipped_result(key: str, label: str) -> CheckResult:
    return CheckResult(key, label, STATUS_SKIP, "not requested")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report repository health without fixing files or granting merge, "
            "promotion, acceptance, or lifecycle authority."
        ),
    )
    parser.add_argument(
        "--docs",
        action="store_true",
        help="Check tracked Markdown file links and boundary language.",
    )
    parser.add_argument(
        "--privacy",
        action="store_true",
        help="Scan public setup/docs/examples surfaces, excluding docs/reports.",
    )
    parser.add_argument(
        "--scaffolds",
        action="store_true",
        help="Validate explicit or discoverable tracked completed scaffolds.",
    )
    parser.add_argument(
        "--scaffold",
        action="append",
        default=[],
        type=Path,
        metavar="PATH",
        help="Explicit Tool Maker or Change Closeout scaffold; repeat as needed.",
    )
    parser.add_argument(
        "--diff-check",
        action="store_true",
        help="Run git diff --check.",
    )
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="Run python -m pytest local_harness/tests.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run docs, privacy, scaffolds, diff hygiene, and the full harness tests.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    repo_root: Path | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    root = (repo_root or REPO_ROOT).resolve()
    any_selection = any(
        (
            args.docs,
            args.privacy,
            args.scaffolds,
            bool(args.scaffold),
            args.diff_check,
            args.pytest,
            args.all,
        )
    )
    run_docs = args.all or args.docs or not any_selection
    run_privacy = args.all or args.privacy or not any_selection
    run_scaffold_validation = args.all or args.scaffolds or bool(args.scaffold)
    run_diff = args.all or args.diff_check
    run_tests = args.all or args.pytest

    checks: list[tuple[str, str, bool, Callable[[], CheckResult]]] = [
        (
            "docs_links",
            "docs links",
            run_docs,
            lambda: check_markdown_links(root),
        ),
        (
            "privacy",
            "privacy",
            run_privacy,
            lambda: check_privacy(root),
        ),
        (
            "boundary_language",
            "boundary language",
            run_docs,
            lambda: check_boundary_language(root),
        ),
        (
            "scaffolds",
            "scaffolds",
            run_scaffold_validation,
            lambda: check_scaffolds(root, args.scaffold),
        ),
        (
            "diff_check",
            "diff check",
            run_diff,
            lambda: run_diff_check(root),
        ),
        (
            "pytest",
            "pytest",
            run_tests,
            lambda: run_pytest_check(root),
        ),
    ]

    results: list[CheckResult] = []
    for key, label, enabled, check in checks:
        result = check() if enabled else skipped_result(key, label)
        results.append(result)
        if enabled:
            print_result(result)

    print("\nRepo health summary:")
    for result in results:
        print(f"* {result.label}: {result.status}")

    return 1 if any(result.status == STATUS_FAIL for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
