#!/usr/bin/env python3
"""Generate a lightweight ZTH role packet for one independent external agent."""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path
from typing import Iterable, Sequence


MODES = ("quick", "standard", "rig")
INTRO_TEXT = (
    "This packet is for one independent external agent. ZTH prepares context and evidence; it does "
    "not orchestrate panels or run permanent agents."
)
INDEPENDENCE_RULE = (
    "Use only the repo/context evidence in this packet. Do not include, rely on, or react to another "
    "agent's conclusions before synthesis/comparison. Shared source-of-truth files are allowed; "
    "cross-agent conclusions are not."
)
OUTPUT_CONTRACT_SECTIONS = (
    "Decision",
    "Summary",
    "Files inspected",
    "Files changed",
    "Commands run",
    "Evidence",
    "Assumptions",
    "Risks",
    "Confidence",
    "Suggested next step",
    "Optional handoff notes",
)


def flatten(values: Sequence[Sequence[str]] | None) -> list[str]:
    if not values:
        return []
    return [item for group in values for item in group]


def clean_value(value: str) -> str:
    return " ".join(value.strip().split())


def clean_values(values: Iterable[str]) -> list[str]:
    return [cleaned for value in values if (cleaned := clean_value(value))]


def bullet_list(values: Sequence[str]) -> str:
    if not values:
        return "- None provided.\n"
    return "".join(f"- {value}\n" for value in values)


def paragraph(value: str) -> str:
    return textwrap.fill(clean_value(value), width=100) + "\n"


def render_packet(
    *,
    task: str,
    role: str,
    mode: str,
    scope: str,
    files: Sequence[str] = (),
    constraints: Sequence[str] = (),
    acceptance: Sequence[str] = (),
    commands: Sequence[str] = (),
    risks: Sequence[str] = (),
    do_not_touch: Sequence[str] = (),
) -> str:
    """Return deterministic Markdown for one independent agent role packet."""

    if mode not in MODES:
        raise ValueError(f"mode must be one of: {', '.join(MODES)}")

    files = clean_values(files)
    constraints = clean_values(constraints)
    acceptance = clean_values(acceptance)
    commands = clean_values(commands)
    risks = clean_values(risks)
    do_not_touch = clean_values(do_not_touch)

    return (
        "# ZTH Agent Role Packet\n\n"
        f"{paragraph(INTRO_TEXT)}\n"
        "## Task\n\n"
        f"{paragraph(task)}\n"
        "## Role\n\n"
        f"{paragraph(role)}\n"
        "## Mode\n\n"
        f"{mode}\n\n"
        "## Repo Scope\n\n"
        f"{paragraph(scope)}\n"
        "## Relevant Files\n\n"
        f"{bullet_list(files)}\n"
        "## Constraints\n\n"
        f"{bullet_list(constraints)}\n"
        "## Acceptance Criteria\n\n"
        f"{bullet_list(acceptance)}\n"
        "## Known Risks\n\n"
        f"{bullet_list(risks)}\n"
        "## Commands To Run\n\n"
        f"{bullet_list(commands)}\n"
        "## Do-Not-Touch Areas\n\n"
        f"{bullet_list(do_not_touch)}\n"
        "## Independence Rule\n\n"
        f"{paragraph(INDEPENDENCE_RULE)}\n"
        "## Required Output Contract\n\n"
        "Return your final response using `docs/prompts/AGENT_OUTPUT_CONTRACT.md`.\n"
        "Include these sections exactly:\n\n"
        f"{bullet_list(OUTPUT_CONTRACT_SECTIONS)}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic Markdown role packet for one independent external agent.",
    )
    parser.add_argument("--task", required=True, help="Task the agent should perform.")
    parser.add_argument("--role", required=True, help="Role name for the independent agent.")
    parser.add_argument("--mode", choices=MODES, required=True, help="Run mode: quick, standard, or rig.")
    parser.add_argument("--scope", required=True, help="Repo scope or path scope for the packet.")
    parser.add_argument("--files", action="append", nargs="+", default=[], help="Relevant files.")
    parser.add_argument("--constraints", action="append", nargs="+", default=[], help="Constraints.")
    parser.add_argument(
        "--acceptance",
        action="append",
        nargs="+",
        default=[],
        help="Acceptance criteria.",
    )
    parser.add_argument("--commands", action="append", nargs="+", default=[], help="Commands to run.")
    parser.add_argument("--risks", action="append", nargs="+", default=[], help="Known risks.")
    parser.add_argument(
        "--do-not-touch",
        action="append",
        nargs="+",
        default=[],
        help="Areas the agent must not touch.",
    )
    parser.add_argument("--output", help="Optional output path. Omit to print to stdout.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packet = render_packet(
        task=args.task,
        role=args.role,
        mode=args.mode,
        scope=args.scope,
        files=flatten(args.files),
        constraints=flatten(args.constraints),
        acceptance=flatten(args.acceptance),
        commands=flatten(args.commands),
        risks=flatten(args.risks),
        do_not_touch=flatten(args.do_not_touch),
    )

    if args.output:
        Path(args.output).write_text(packet, encoding="utf-8")
    else:
        print(packet, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
