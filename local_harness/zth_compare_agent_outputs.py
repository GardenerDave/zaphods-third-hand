#!/usr/bin/env python3
"""Compare completed ZTH agent output Markdown files."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


REQUIRED_SECTIONS = (
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
)
OPTIONAL_SECTIONS = ("Optional handoff notes",)
KNOWN_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
INLINE_LABEL_RE = re.compile(r"^\s*-?\s*([A-Za-z][A-Za-z /-]+):\s*(.*)$")


@dataclass(frozen=True)
class AgentOutput:
    path: Path
    sections: dict[str, list[str]]

    @property
    def display_name(self) -> str:
        return self.path.name


def normalize_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


SECTION_BY_NORMALIZED = {normalize_name(name): name for name in KNOWN_SECTIONS}


def clean_line(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^[-*]\s+", "", value)
    value = re.sub(r"^\d+[.)]\s+", "", value)
    return value.strip()


def nonempty_lines(lines: Iterable[str]) -> list[str]:
    return [line for line in (clean_line(value) for value in lines) if line]


def parse_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for raw_line in text.splitlines():
        heading_match = HEADING_RE.match(raw_line)
        if heading_match:
            normalized = normalize_name(heading_match.group(2))
            current = SECTION_BY_NORMALIZED.get(normalized)
            if current:
                sections.setdefault(current, [])
            continue

        inline_match = INLINE_LABEL_RE.match(raw_line)
        if inline_match:
            normalized = normalize_name(inline_match.group(1))
            section = SECTION_BY_NORMALIZED.get(normalized)
            if section:
                current = section
                sections.setdefault(section, [])
                if inline_match.group(2).strip():
                    sections[section].append(inline_match.group(2).strip())
                continue

        if current:
            sections[current].append(raw_line)

    return {section: nonempty_lines(lines) for section, lines in sections.items()}


def load_agent_output(path: Path) -> AgentOutput:
    return AgentOutput(path=path, sections=parse_sections(path.read_text(encoding="utf-8")))


def section_items(outputs: Sequence[AgentOutput], section: str) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for output in outputs:
        for item in output.sections.get(section, []):
            if item not in seen:
                seen.add(item)
                items.append(item)
    return items


def format_bullets(items: Sequence[str]) -> str:
    if not items:
        return "- None reported.\n"
    return "".join(f"- {item}\n" for item in items)


def first_value(output: AgentOutput, section: str) -> str:
    values = output.sections.get(section, [])
    return values[0] if values else ""


def decision_agreements(outputs: Sequence[AgentOutput]) -> list[str]:
    agreements: list[str] = []
    decisions = [first_value(output, "Decision") for output in outputs if first_value(output, "Decision")]
    next_steps = [
        first_value(output, "Suggested next step")
        for output in outputs
        if first_value(output, "Suggested next step")
    ]
    inspected_sets = [
        set(output.sections.get("Files inspected", []))
        for output in outputs
        if output.sections.get("Files inspected")
    ]

    if decisions and len(set(decisions)) == 1 and len(decisions) == len(outputs):
        agreements.append(f"All agents reported decision: {decisions[0]}")
    if next_steps and len(set(next_steps)) == 1 and len(next_steps) == len(outputs):
        agreements.append(f"All agents suggested next step: {next_steps[0]}")
    if inspected_sets:
        shared = sorted(set.intersection(*inspected_sets)) if len(inspected_sets) > 1 else sorted(inspected_sets[0])
        if shared:
            agreements.append("Shared inspected files: " + ", ".join(shared))
    return agreements


def decision_divergences(outputs: Sequence[AgentOutput]) -> list[str]:
    divergences: list[str] = []
    for section in ("Decision", "Suggested next step"):
        values = [(output.display_name, first_value(output, section)) for output in outputs]
        unique_values = {value for _, value in values if value}
        if len(unique_values) > 1:
            joined = "; ".join(f"{name}: {value or 'missing'}" for name, value in values)
            divergences.append(f"{section} differs: {joined}")

    risk_counter: Counter[str] = Counter()
    for output in outputs:
        risk_counter.update(output.sections.get("Risks", []))
    unique_risks = sorted(risk for risk, count in risk_counter.items() if count == 1)
    if unique_risks:
        divergences.append("Risks mentioned by only one agent: " + "; ".join(unique_risks))
    return divergences


def missing_sections(output: AgentOutput) -> list[str]:
    return [
        section
        for section in REQUIRED_SECTIONS
        if section not in output.sections or not output.sections[section]
    ]


def render_comparison(outputs: Sequence[AgentOutput]) -> str:
    return (
        "# ZTH Agent Output Comparison\n\n"
        "## Inputs\n\n"
        f"{format_bullets([str(output.path) for output in outputs])}\n"
        "## Files Inspected Across Agents\n\n"
        f"{format_bullets(section_items(outputs, 'Files inspected'))}\n"
        "## Files Changed Across Agents\n\n"
        f"{format_bullets(section_items(outputs, 'Files changed'))}\n"
        "## Commands Run Across Agents\n\n"
        f"{format_bullets(section_items(outputs, 'Commands run'))}\n"
        "## Agreements\n\n"
        f"{format_bullets(decision_agreements(outputs))}\n"
        "## Divergences\n\n"
        f"{format_bullets(decision_divergences(outputs))}\n"
        "## Risks Mentioned\n\n"
        f"{format_bullets(section_items(outputs, 'Risks'))}\n"
        "## Confidence Values\n\n"
        f"{format_bullets([f'{output.display_name}: {first_value(output, 'Confidence') or 'missing'}' for output in outputs])}\n"
        "## Missing Required Sections\n\n"
        f"{format_bullets([f'{output.display_name}: {', '.join(missing)}' for output in outputs if (missing := missing_sections(output))])}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare multiple completed ZTH agent output Markdown files.",
    )
    parser.add_argument("agent_outputs", nargs="+", help="Completed agent output Markdown files.")
    parser.add_argument("--output", help="Optional output path. Omit to print to stdout.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = [load_agent_output(Path(path)) for path in args.agent_outputs]
    report = render_comparison(outputs)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
