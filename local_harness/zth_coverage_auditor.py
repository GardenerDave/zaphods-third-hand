#!/usr/bin/env python3
"""Heuristic pre-synthesis coverage audit for ZTH role packets or agent outputs."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


COVERAGE_CONTRACT_VERSION = "zth.coverage_audit.v0.2"
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "security": ("security", "auth", "authentication", "authorization", "vulnerability", "exploit"),
    "data integrity": ("data integrity", "database", "migration", "schema", "consistency", "corruption"),
    "privacy/compliance": ("privacy", "compliance", "pii", "personal data", "regulatory", "retention"),
    "functional/UX": ("functional", "ux", "user experience", "workflow", "behavior", "usability"),
    "performance/resilience": ("performance", "resilience", "timeout", "latency", "scale", "retry"),
    "operations/deployment": ("operations", "deployment", "deploy", "rollback", "monitoring", "runtime"),
    "documentation/onboarding": ("documentation", "docs", "readme", "onboarding", "quickstart", "guide"),
    "testing/regression": ("testing", "test", "pytest", "regression", "fixture", "coverage"),
    "safety/supervision": ("safety", "supervision", "human", "unattended", "batched", "approval"),
}


@dataclass(frozen=True)
class CoverageResult:
    covered: dict[str, list[str]]
    blind_spots: list[str]
    notes: list[str]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def category_matches(text: str, keywords: Sequence[str]) -> bool:
    normalized = normalize_text(text)
    return any(keyword in normalized for keyword in keywords)


def audit_paths(paths: Sequence[Path]) -> CoverageResult:
    covered: dict[str, list[str]] = {category: [] for category in CATEGORY_KEYWORDS}
    notes = [
        "This is a heuristic keyword audit, not semantic proof of coverage.",
        "Use it before synthesis to expose obvious unassigned lenses or missing review topics.",
    ]

    if not paths:
        notes.append("No input files were supplied.")

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for category, keywords in CATEGORY_KEYWORDS.items():
            if category_matches(text, keywords):
                covered[category].append(str(path))

    blind_spots = [category for category, matches in covered.items() if not matches]
    return CoverageResult(covered=covered, blind_spots=blind_spots, notes=notes)


def format_covered(covered: dict[str, list[str]]) -> str:
    lines: list[str] = []
    for category in CATEGORY_KEYWORDS:
        matches = covered[category]
        if matches:
            lines.append(f"- {category}: " + ", ".join(matches))
    return "\n".join(lines) + "\n" if lines else "- None detected.\n"


def format_blind_spots(blind_spots: Sequence[str]) -> str:
    if not blind_spots:
        return "- None detected by this heuristic.\n"
    return "".join(f"- {category}\n" for category in blind_spots)


def confidence_for(result: CoverageResult) -> str:
    if not any(result.covered.values()):
        return "low"
    if result.blind_spots:
        return "medium"
    return "medium"


def render_report(paths: Sequence[Path], result: CoverageResult) -> str:
    inputs = "\n".join(f"- {path}" for path in paths) if paths else "- None supplied."
    notes = "\n".join(f"- {note}" for note in result.notes)
    return (
        f"output_contract_version: {COVERAGE_CONTRACT_VERSION}\n\n"
        "# ZTH Pre-Synthesis Coverage Audit\n\n"
        "## Inputs\n\n"
        f"{inputs}\n\n"
        "## Covered Areas\n\n"
        f"{format_covered(result.covered)}\n"
        "## Potential Blind Spots\n\n"
        f"{format_blind_spots(result.blind_spots)}\n"
        "## Notes / Assumptions\n\n"
        f"{notes}\n\n"
        "## Confidence\n\n"
        f"{confidence_for(result)}\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a heuristic pre-synthesis coverage audit over role packets or agent outputs.",
    )
    parser.add_argument("inputs", nargs="*", help="Role packet or completed agent output Markdown files.")
    parser.add_argument("--output", help="Optional output path. Omit to print to stdout.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = [Path(path) for path in args.inputs]
    report = render_report(paths, audit_paths(paths))

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
