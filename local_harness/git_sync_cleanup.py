#!/usr/bin/env python3
"""Report post-merge Git sync and cleanup evidence without changing Git state."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
READ_ONLY_GIT_COMMANDS = {
    "for-each-ref",
    "merge-base",
    "rev-parse",
    "status",
    "symbolic-ref",
}


class AdvisorError(RuntimeError):
    """Raised when repository inspection cannot complete."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def run_process(command: Sequence[str], cwd: Path) -> CommandResult:
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError as exc:
        raise AdvisorError(f"could not run {command[0]!r}: {exc}") from exc
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


class GitReader:
    """Run only the small read-only Git command set used by this advisor."""

    def __init__(
        self,
        repo_root: Path,
        process_runner: Callable[[Sequence[str], Path], CommandResult] = run_process,
    ) -> None:
        self.repo_root = repo_root
        self.process_runner = process_runner

    def run(self, *arguments: str, allowed_codes: set[int] | None = None) -> CommandResult:
        if not arguments or arguments[0] not in READ_ONLY_GIT_COMMANDS:
            raise AdvisorError(f"refusing non-read-only Git command: {arguments!r}")
        result = self.process_runner(("git", *arguments), self.repo_root)
        accepted = allowed_codes or {0}
        if result.returncode not in accepted:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
            raise AdvisorError(f"git {' '.join(arguments)} failed: {detail}")
        return result

    def ref_commit(self, ref: str) -> str | None:
        result = self.run(
            "rev-parse",
            "--verify",
            "--quiet",
            ref,
            allowed_codes={0, 1},
        )
        return result.stdout.strip() if result.returncode == 0 else None

    def is_ancestor(self, older: str, newer: str) -> bool:
        result = self.run(
            "merge-base",
            "--is-ancestor",
            older,
            newer,
            allowed_codes={0, 1},
        )
        return result.returncode == 0

    def list_refs(self, namespace: str) -> dict[str, str]:
        result = self.run(
            "for-each-ref",
            "--format=%(refname:short)\t%(objectname)\t%(symref)",
            namespace,
        )
        refs: dict[str, str] = {}
        for line in result.stdout.splitlines():
            fields = line.split("\t", 2)
            if len(fields) != 3:
                continue
            name, commit, symbolic_target = fields
            if name and commit and not symbolic_target:
                refs[name] = commit
        return refs


def classify_working_tree(porcelain: str) -> dict[str, object]:
    staged = 0
    unstaged = 0
    untracked = 0
    entries = [line for line in porcelain.splitlines() if line]
    for line in entries:
        if line.startswith("??"):
            untracked += 1
            continue
        if len(line) >= 1 and line[0] not in {" ", "?"}:
            staged += 1
        if len(line) >= 2 and line[1] not in {" ", "?"}:
            unstaged += 1
    return {
        "state": "clean" if not entries else "dirty",
        "clean": not entries,
        "staged_changes": staged,
        "unstaged_changes": unstaged,
        "untracked_files": untracked,
        "entry_count": len(entries),
    }


def classify_relation(
    left_commit: str | None,
    right_commit: str | None,
    is_ancestor: Callable[[str, str], bool],
    *,
    missing_left: str,
    missing_right: str,
) -> str:
    if left_commit is None:
        return missing_left
    if right_commit is None:
        return missing_right
    if left_commit == right_commit:
        return "aligned"
    if is_ancestor(left_commit, right_commit):
        return "behind"
    if is_ancestor(right_commit, left_commit):
        return "ahead"
    return "diverged"


def collect_repository_state(reader: GitReader) -> dict[str, object]:
    inside = reader.run(
        "rev-parse",
        "--is-inside-work-tree",
        allowed_codes={0, 128},
    )
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise AdvisorError(f"not a Git working tree: {reader.repo_root}")

    branch_result = reader.run(
        "symbolic-ref",
        "--quiet",
        "--short",
        "HEAD",
        allowed_codes={0, 1},
    )
    current_branch = (
        branch_result.stdout.strip() if branch_result.returncode == 0 else None
    )
    head_commit = reader.ref_commit("HEAD")
    status = classify_working_tree(
        reader.run("status", "--porcelain=v1", "--untracked-files=all").stdout
    )

    local_refs = reader.list_refs("refs/heads")
    remote_refs = {
        name: commit
        for name, commit in reader.list_refs("refs/remotes").items()
        if not name.endswith("/HEAD")
    }
    local_main = local_refs.get("main")
    origin_main = remote_refs.get("origin/main")
    main_relation = classify_relation(
        local_main,
        origin_main,
        reader.is_ancestor,
        missing_left="missing_local_main",
        missing_right="missing_origin_main",
    )

    if current_branch == "main":
        current_relation = "current_branch_is_main"
    elif head_commit is None or origin_main is None:
        current_relation = "relation_unavailable"
    else:
        current_relation = classify_relation(
            head_commit,
            origin_main,
            reader.is_ancestor,
            missing_left="relation_unavailable",
            missing_right="relation_unavailable",
        )

    non_main_local = sorted(name for name in local_refs if name != "main")
    merged_main: list[str] = []
    merged_origin: list[str] = []
    not_merged_origin: list[str] = []
    for name in non_main_local:
        commit = local_refs[name]
        if local_main is not None and reader.is_ancestor(commit, local_main):
            merged_main.append(name)
        if origin_main is not None:
            if reader.is_ancestor(commit, origin_main):
                merged_origin.append(name)
            else:
                not_merged_origin.append(name)

    local_names = set(local_refs)
    remote_findings: list[dict[str, object]] = []
    for name in sorted(remote_refs):
        if name == "origin/main":
            continue
        reasons: list[str] = []
        local_name = name.removeprefix("origin/")
        if name.startswith("origin/revert-"):
            reasons.append("revert_pattern")
        if local_name not in local_names:
            reasons.append("no_matching_local_branch")
        if origin_main is not None and reader.is_ancestor(remote_refs[name], origin_main):
            reasons.append("merged_into_origin_main")
        if reasons:
            remote_findings.append({"branch": name, "reasons": reasons})

    return {
        "current_branch": current_branch,
        "head_commit": head_commit,
        "working_tree": status,
        "main_status": {
            "status": main_relation,
            "local_main_commit": local_main,
            "origin_main_commit": origin_main,
        },
        "current_branch_status": {
            "status": current_relation,
            "commit": head_commit,
            "origin_main_commit": origin_main,
        },
        "local_branches": {
            "all": sorted(local_refs),
            "merged_into_main": merged_main,
            "merged_into_origin_main": merged_origin,
            "not_merged_into_origin_main": not_merged_origin,
        },
        "local_branch_commits": dict(sorted(local_refs.items())),
        "remote_branch_commits": dict(sorted(remote_refs.items())),
        "remote_findings": remote_findings,
    }


def command_text(*parts: str) -> str:
    return shlex.join(parts)


def branch_merged(state: dict[str, object], branch: str, target: str) -> bool:
    branches = state["local_branches"]
    assert isinstance(branches, dict)
    values = branches.get(target, [])
    return isinstance(values, list) and branch in values


def focused_branch_report(
    state: dict[str, object],
    branch: str,
) -> dict[str, object]:
    local_commits = state["local_branch_commits"]
    remote_commits = state["remote_branch_commits"]
    assert isinstance(local_commits, dict)
    assert isinstance(remote_commits, dict)
    remote_name = f"origin/{branch}"
    return {
        "branch": branch,
        "local_exists": branch in local_commits,
        "remote_exists": remote_name in remote_commits,
        "ancestor_merged_into_main": branch_merged(
            state,
            branch,
            "merged_into_main",
        ),
        "ancestor_merged_into_origin_main": branch_merged(
            state,
            branch,
            "merged_into_origin_main",
        ),
    }


def build_recommendations(
    state: dict[str, object],
    *,
    include_fetch_advice: bool = False,
    after_merge_branch: str | None = None,
) -> list[str]:
    recommendations: list[str] = []
    working_tree = state["working_tree"]
    main_status = state["main_status"]
    current_status = state["current_branch_status"]
    current_branch = state["current_branch"]
    assert isinstance(working_tree, dict)
    assert isinstance(main_status, dict)
    assert isinstance(current_status, dict)

    clean = working_tree.get("clean") is True
    if not clean:
        recommendations.append(
            "STOP: the working tree is dirty; review "
            + command_text("git", "status", "--short")
            + " before sync or cleanup."
        )

    if include_fetch_advice:
        recommendations.append(
            "Refresh local remote-tracking evidence when authorized: "
            + command_text("git", "fetch", "--prune")
        )

    relation = main_status.get("status")
    if relation == "behind":
        if clean:
            recommendations.extend(
                [
                    "Switch to main: " + command_text("git", "switch", "main"),
                    "Fast-forward main: " + command_text("git", "pull", "--ff-only"),
                ]
            )
        else:
            recommendations.append(
                "After preserving or resolving local changes, reassess before "
                "fast-forwarding main."
            )
    elif relation == "ahead":
        recommendations.extend(
            [
                "Inspect local-only main commits: "
                + command_text("git", "log", "--oneline", "origin/main..main"),
                "Create a review branch or PR before any reset or push; this advisor "
                "does not recommend git reset --hard.",
            ]
        )
    elif relation == "diverged":
        recommendations.extend(
            [
                "Inspect main divergence: "
                + command_text("git", "log", "--oneline", "--left-right", "main...origin/main"),
                "Choose a reconciliation plan manually; do not reset, merge, pull, or "
                "push from this report alone.",
            ]
        )

    if (
        clean
        and isinstance(current_branch, str)
        and current_branch != "main"
        and branch_merged(state, current_branch, "merged_into_main")
    ):
        recommendations.extend(
            [
                "Current branch is ancestor-merged into local main; after review: "
                + command_text("git", "switch", "main"),
                "Delete the merged local branch with Git's safe check: "
                + command_text("git", "branch", "-d", current_branch),
            ]
        )

    if after_merge_branch:
        focused = focused_branch_report(state, after_merge_branch)
        if focused["local_exists"]:
            if focused["ancestor_merged_into_main"]:
                if clean:
                    recommendations.append(
                        "Focused branch is ancestor-merged into local main; after "
                        "review, use: "
                        + command_text("git", "branch", "-d", after_merge_branch)
                    )
            else:
                recommendations.extend(
                    [
                        "Inspect focused branch commits, including possible squash-merge "
                        "residue: "
                        + command_text(
                            "git",
                            "log",
                            "--oneline",
                            f"origin/main..{after_merge_branch}",
                        ),
                        "Compare the focused branch before cleanup: "
                        + command_text(
                            "git",
                            "diff",
                            "--stat",
                            f"origin/main...{after_merge_branch}",
                        ),
                        "Only after a human confirms the PR was merged may they choose: "
                        + command_text("git", "branch", "-D", after_merge_branch),
                    ]
                )
        else:
            recommendations.append(
                f"Focused local branch {after_merge_branch!r} is absent; no local "
                "deletion is needed."
            )

        if focused["remote_exists"]:
            remote_name = f"origin/{after_merge_branch}"
            recommendations.extend(
                [
                    "Inspect the focused remote branch: "
                    + command_text("git", "log", "--oneline", "--decorate", remote_name, "-3"),
                    "Compare the focused remote branch: "
                    + command_text("git", "diff", "--stat", f"origin/main...{remote_name}"),
                    "Only after human confirmation may the remote branch be deleted: "
                    + command_text("git", "push", "origin", "--delete", after_merge_branch),
                ]
            )

    remote_findings = state["remote_findings"]
    assert isinstance(remote_findings, list)
    for finding in remote_findings:
        assert isinstance(finding, dict)
        branch = finding["branch"]
        reasons = finding["reasons"]
        if not isinstance(branch, str) or not isinstance(reasons, list):
            continue
        if "revert_pattern" not in reasons:
            continue
        short_name = branch.removeprefix("origin/")
        recommendations.extend(
            [
                "Inspect suspicious revert branch first: "
                + command_text("git", "log", "--oneline", "--decorate", branch, "-3"),
                "Compare suspicious revert branch first: "
                + command_text("git", "diff", "--stat", f"origin/main...{branch}"),
                "If a human confirms it was accidental, they may choose: "
                + command_text("git", "push", "origin", "--delete", short_name),
            ]
        )

    if not recommendations:
        recommendations.append(
            "No cleanup action is indicated by current local refs. Run with "
            "--include-fetch-advice to print the optional refresh command."
        )
    return recommendations


def run_health_check(repo_root: Path) -> dict[str, object]:
    command = (sys.executable, "local_harness/repo_health_check.py")
    result = run_process(command, repo_root)
    return {
        "status": "pass" if result.returncode == 0 else "fail",
        "exit_code": result.returncode,
        "command": command_text(*command),
        "output": (result.stdout + result.stderr).strip(),
    }


def render_human(report: dict[str, object]) -> str:
    lines = [
        "Git Sync / Cleanup Advisor",
        "",
        "Advisory only. No fetch, pull, prune, switch, merge, reset, push, or "
        "branch deletion was performed.",
        "Remote information comes from local remote-tracking refs and may be stale.",
        "",
        f"Current branch: {report['current_branch'] or '(detached HEAD)'}",
    ]
    working_tree = report["working_tree"]
    main_status = report["main_status"]
    current_status = report["current_branch_status"]
    local_branches = report["local_branches"]
    assert isinstance(working_tree, dict)
    assert isinstance(main_status, dict)
    assert isinstance(current_status, dict)
    assert isinstance(local_branches, dict)
    lines.extend(
        [
            (
                "Working tree: "
                f"{working_tree['state']} "
                f"(staged={working_tree['staged_changes']}, "
                f"unstaged={working_tree['unstaged_changes']}, "
                f"untracked={working_tree['untracked_files']})"
            ),
            (
                "Main relationship: "
                f"{main_status['status']} "
                f"(main={main_status['local_main_commit'] or 'missing'}, "
                f"origin/main={main_status['origin_main_commit'] or 'missing'})"
            ),
            f"Current branch relationship: {current_status['status']}",
            "",
            "Local branches:",
            "  merged into main: "
            + ", ".join(local_branches["merged_into_main"] or ["(none)"]),
            "  merged into origin/main: "
            + ", ".join(local_branches["merged_into_origin_main"] or ["(none)"]),
            "  not merged into origin/main: "
            + ", ".join(local_branches["not_merged_into_origin_main"] or ["(none)"]),
            "",
            "Remote findings:",
        ]
    )
    remote_findings = report["remote_findings"]
    assert isinstance(remote_findings, list)
    if remote_findings:
        for finding in remote_findings:
            assert isinstance(finding, dict)
            lines.append(
                f"  {finding['branch']}: {', '.join(finding['reasons'])}"
            )
    else:
        lines.append("  (none)")

    focused = report.get("after_merge_branch")
    if isinstance(focused, dict):
        lines.extend(
            [
                "",
                f"Focused after-merge branch: {focused['branch']}",
                f"  local exists: {str(focused['local_exists']).lower()}",
                f"  remote exists: {str(focused['remote_exists']).lower()}",
                (
                    "  ancestor-merged into main: "
                    f"{str(focused['ancestor_merged_into_main']).lower()}"
                ),
                (
                    "  ancestor-merged into origin/main: "
                    f"{str(focused['ancestor_merged_into_origin_main']).lower()}"
                ),
            ]
        )

    lines.extend(["", "Recommendations:"])
    for recommendation in report["recommendations"]:
        lines.append(f"  - {recommendation}")

    health = report.get("health_status")
    if isinstance(health, dict):
        lines.extend(
            [
                "",
                f"Repo health: {health['status']} (exit {health['exit_code']})",
            ]
        )
        output = health.get("output")
        if output:
            lines.extend(f"  {line}" for line in str(output).splitlines())

    lines.extend(
        [
            "",
            "Passing checks are evidence for human review, not cleanup, merge, "
            "release, or promotion authority.",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect post-merge Git state and print cleanup advice without changing "
            "branches, refs, remotes, or files."
        )
    )
    parser.add_argument(
        "--include-fetch-advice",
        action="store_true",
        help="Print git fetch --prune as an optional human-run recommendation.",
    )
    parser.add_argument(
        "--after-merge-branch",
        metavar="BRANCH_NAME",
        help="Add focused inspection advice for a just-merged branch.",
    )
    parser.add_argument(
        "--run-health",
        action="store_true",
        help="Run the read-only default repository health command.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable report.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    repo_root: Path | None = None,
    reader: GitReader | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    root = (repo_root or REPO_ROOT).resolve()
    git_reader = reader or GitReader(root)
    try:
        report = collect_repository_state(git_reader)
        if args.after_merge_branch:
            report["after_merge_branch"] = focused_branch_report(
                report,
                args.after_merge_branch,
            )
        report["recommendations"] = build_recommendations(
            report,
            include_fetch_advice=args.include_fetch_advice,
            after_merge_branch=args.after_merge_branch,
        )
        if args.run_health:
            report["health_status"] = run_health_check(root)
    except AdvisorError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(f"git-sync-cleanup: error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_human(report))
    health = report.get("health_status")
    return 1 if isinstance(health, dict) and health.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
