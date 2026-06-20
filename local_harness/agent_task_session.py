#!/usr/bin/env python3
"""Create a scoped, reviewable Agent Task Session packet without executing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSION_ROOT = REPO_ROOT / ".work" / "agent_tasks"
CONTRACT_VERSION = "zth.agent_task_session.v0.1"
TASK_ID_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")
GENERATED_FILES = (
    "task.yaml",
    "codex_prompt.md",
    "allowed_paths.txt",
    "required_checks.txt",
    "status.md",
)


@dataclass(frozen=True)
class TaskSession:
    task_id: str
    output_dir: Path
    generated_files: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    required_checks: tuple[str, ...]


def clean_text(value: str, field: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{field} must not be empty")
    return cleaned


def normalize_allowed_path(value: str) -> str:
    candidate = value.strip().replace("\\", "/")
    if not candidate:
        raise ValueError("allowed paths must not be empty")
    path = PurePosixPath(candidate)
    if path.is_absolute():
        raise ValueError(f"allowed path must be repository-relative: {value!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"allowed path contains an unsafe segment: {value!r}")
    if ".git" in path.parts:
        raise ValueError(f"allowed path must not reference .git: {value!r}")
    normalized = path.as_posix()
    if normalized.startswith("-"):
        raise ValueError(f"allowed path must not start with '-': {value!r}")
    return normalized


def clean_check(value: str) -> str:
    check = " ".join(value.split())
    if not check:
        raise ValueError("required checks must not be empty")
    if "\x00" in check:
        raise ValueError("required checks must not contain NUL bytes")
    return check


def unique_values(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48].rstrip("-") or "task"


def derive_task_id(
    *,
    name: str,
    goal: str,
    branch: str,
    allowed_paths: Sequence[str],
    required_checks: Sequence[str],
) -> str:
    payload = json.dumps(
        {
            "name": name,
            "goal": goal,
            "branch": branch,
            "allowed_paths": list(allowed_paths),
            "required_checks": list(required_checks),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]
    return f"{slugify(name)}-{digest}"


def validate_task_id(value: str) -> str:
    if not TASK_ID_RE.fullmatch(value):
        raise ValueError(
            "task id must contain only lowercase letters, digits, and internal hyphens "
            "and be at most 64 characters"
        )
    return value


def render_task_metadata(
    *,
    task_id: str,
    name: str,
    goal: str,
    branch: str,
    allowed_paths: Sequence[str],
    required_checks: Sequence[str],
) -> str:
    payload = {
        "agent_execution_performed": False,
        "allowed_paths": list(allowed_paths),
        "authority_granted": False,
        "branch": branch,
        "goal": goal,
        "name": name,
        "required_checks": list(required_checks),
        "requires_human_review": True,
        "status": "draft",
        "task_id": task_id,
        "task_session_contract_version": CONTRACT_VERSION,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def bullet_list(values: Sequence[str], *, empty: str) -> str:
    if not values:
        return f"- {empty}\n"
    return "".join(f"- `{value}`\n" for value in values)


def render_prompt(
    *,
    task_id: str,
    name: str,
    goal: str,
    branch: str,
    allowed_paths: Sequence[str],
    required_checks: Sequence[str],
) -> str:
    return (
        f"# Agent Task Session: {name}\n\n"
        f"Task ID: `{task_id}`\n\n"
        "This packet provides procedural constraint and verification for a supervised "
        "agent task. It does not execute the task or grant merge, release, promotion, "
        "cleanup, deletion, or lifecycle authority.\n\n"
        "## Goal\n\n"
        f"{goal}\n\n"
        "## Intended Branch\n\n"
        f"`{branch}`\n\n"
        "The branch value is planning metadata only. Do not switch, create, delete, "
        "merge, pull, push, or reset branches unless a human separately authorizes it.\n\n"
        "## Allowed Paths\n\n"
        f"{bullet_list(allowed_paths, empty='No file edits are authorized.')}\n"
        "Edit only these repository-relative paths. Stop and report if the task needs "
        "any path outside this allowlist.\n\n"
        "## Required Checks\n\n"
        f"{bullet_list(required_checks, empty='No checks were recorded; stop for human review.')}\n"
        "These commands are recorded instructions, not commands executed by this "
        "packet builder. Run them only within the active human-authorized task.\n\n"
        "## Required Boundaries\n\n"
        "- Preserve unrelated user changes and existing evidence.\n"
        "- Do not broaden scope or infer authority from this packet.\n"
        "- Do not mark the task complete automatically.\n"
        "- Do not merge, release, promote, clean up, delete, or move lifecycle state.\n"
        "- Record assumptions, files changed, commands run, results, and unresolved risks.\n"
        "- Human review is required before any acceptance or follow-up action.\n"
        "- Passing checks are evidence, not authority.\n\n"
        "## Expected Handoff\n\n"
        "Return a concise implementation or review report with changed files, validation "
        "evidence, limitations, and a suggested next human action. Do not claim human "
        "approval.\n"
    )


def render_status(task_id: str, name: str) -> str:
    return (
        f"# Agent Task Session Status: {name}\n\n"
        f"- Task ID: `{task_id}`\n"
        "- Status: `draft`\n"
        "- Agent execution performed by builder: `false`\n"
        "- Human review required: `true`\n"
        "- Authority granted by this packet: `false`\n\n"
        "## Human Review Checklist\n\n"
        "- [ ] Confirm the goal and branch metadata.\n"
        "- [ ] Confirm every allowed path is intentional.\n"
        "- [ ] Confirm required checks are sufficient and safe to run.\n"
        "- [ ] Decide whether to hand the packet to an agent.\n"
        "- [ ] Review resulting edits and evidence separately.\n"
        "- [ ] Decide any acceptance, commit, merge, release, promotion, or follow-up.\n\n"
        "This file is review state only. It does not mark the task complete or authorize "
        "lifecycle movement.\n"
    )


def create_task_session(
    *,
    name: str,
    goal: str,
    branch: str,
    allowed_paths: Sequence[str],
    required_checks: Sequence[str],
    task_id: str | None = None,
    session_root: Path = DEFAULT_SESSION_ROOT,
) -> TaskSession:
    clean_name = clean_text(name, "task name")
    clean_goal = clean_text(goal, "goal")
    clean_branch = clean_text(branch, "branch")
    normalized_paths = unique_values(
        [normalize_allowed_path(value) for value in allowed_paths]
    )
    normalized_checks = unique_values(
        [clean_check(value) for value in required_checks]
    )
    if not normalized_paths:
        raise ValueError("at least one allowed path is required")
    if not normalized_checks:
        raise ValueError("at least one required check is required")

    resolved_task_id = validate_task_id(
        task_id
        or derive_task_id(
            name=clean_name,
            goal=clean_goal,
            branch=clean_branch,
            allowed_paths=normalized_paths,
            required_checks=normalized_checks,
        )
    )
    output_dir = session_root / resolved_task_id
    if output_dir.exists():
        raise ValueError(f"task session already exists: {output_dir}")

    contents = {
        "task.yaml": render_task_metadata(
            task_id=resolved_task_id,
            name=clean_name,
            goal=clean_goal,
            branch=clean_branch,
            allowed_paths=normalized_paths,
            required_checks=normalized_checks,
        ),
        "codex_prompt.md": render_prompt(
            task_id=resolved_task_id,
            name=clean_name,
            goal=clean_goal,
            branch=clean_branch,
            allowed_paths=normalized_paths,
            required_checks=normalized_checks,
        ),
        "allowed_paths.txt": "".join(f"{path}\n" for path in normalized_paths),
        "required_checks.txt": "".join(f"{check}\n" for check in normalized_checks),
        "status.md": render_status(resolved_task_id, clean_name),
    }

    output_dir.mkdir(parents=True)
    for filename in GENERATED_FILES:
        (output_dir / filename).write_text(contents[filename], encoding="utf-8")

    return TaskSession(
        task_id=resolved_task_id,
        output_dir=output_dir,
        generated_files=GENERATED_FILES,
        allowed_paths=normalized_paths,
        required_checks=normalized_checks,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a reviewable Agent Task Session packet. This command does not "
            "execute agents, checks, shell commands, or Git operations."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    new_parser = subparsers.add_parser("new", help="Create a new draft task session.")
    new_parser.add_argument("--name", required=True, help="Human-readable task name.")
    new_parser.add_argument("--goal", required=True, help="Specific intended outcome.")
    new_parser.add_argument("--branch", required=True, help="Planned branch metadata.")
    new_parser.add_argument(
        "--task-id",
        help="Optional deterministic task id; lowercase letters, digits, and hyphens.",
    )
    new_parser.add_argument(
        "--allow",
        action="append",
        required=True,
        help="Repository-relative allowed path; repeat as needed.",
    )
    new_parser.add_argument(
        "--check",
        action="append",
        required=True,
        help="Required check to record; repeat as needed. Checks are not executed.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    session_root: Path = DEFAULT_SESSION_ROOT,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        session = create_task_session(
            name=args.name,
            goal=args.goal,
            branch=args.branch,
            allowed_paths=args.allow,
            required_checks=args.check,
            task_id=args.task_id,
            session_root=session_root,
        )
    except ValueError as exc:
        print(f"agent-task-session: error: {exc}", file=sys.stderr)
        return 1

    print(f"Created draft Agent Task Session: {session.output_dir}")
    print(f"Task ID: {session.task_id}")
    print("No agent, check, shell command, or Git operation was executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
