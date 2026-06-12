#!/usr/bin/env python3
"""Compare completed ZTH agent output Markdown files."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


EXPECTED_CONTRACT_VERSION = "zth.agent_output.v0.2"
COMPARISON_CONTRACT_VERSION = "zth.agent_comparison.v0.2"
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
CONTRACT_VERSION_RE = re.compile(r"^\s*output_contract_version\s*:\s*(.+?)\s*$")


@dataclass(frozen=True)
class AgentOutput:
    path: Path
    sections: dict[str, list[str]]
    contract_version: str | None = None

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


def parse_contract_version(text: str) -> str | None:
    for raw_line in text.splitlines():
        match = CONTRACT_VERSION_RE.match(raw_line)
        if match:
            return match.group(1).strip().strip('"').strip("'")
    return None


def load_agent_output(path: Path) -> AgentOutput:
    text = path.read_text(encoding="utf-8")
    return AgentOutput(
        path=path,
        sections=parse_sections(text),
        contract_version=parse_contract_version(text),
    )


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


def contract_warnings(outputs: Sequence[AgentOutput]) -> list[str]:
    warnings: list[str] = []
    versions = {output.contract_version for output in outputs if output.contract_version}
    for output in outputs:
        if not output.contract_version:
            warnings.append(f"{output.display_name}: missing output_contract_version")
        elif output.contract_version != EXPECTED_CONTRACT_VERSION:
            warnings.append(
                f"{output.display_name}: expected {EXPECTED_CONTRACT_VERSION}, got {output.contract_version}"
            )
    if len(versions) > 1:
        warnings.append("Mismatched output contract versions across agent outputs: " + ", ".join(sorted(versions)))
    return warnings


def agreement_map(outputs: Sequence[AgentOutput]) -> list[str]:
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
    risk_counter: Counter[str] = Counter()
    for output in outputs:
        risk_counter.update(output.sections.get("Risks", []))

    if decisions and len(set(decisions)) == 1 and len(decisions) == len(outputs):
        agreements.append(
            "\n".join(
                (
                    "- Finding/topic: Decision convergence",
                    f"  - Agents that independently found it: {', '.join(output.display_name for output in outputs)}",
                    "  - Role lenses involved: See source agent packets or filenames.",
                    "  - Final synthesized severity/priority: N/A",
                    "  - Confidence: high",
                    f"  - Why the convergence matters: all agents reported `{decisions[0]}`.",
                )
            )
        )
    if next_steps and len(set(next_steps)) == 1 and len(next_steps) == len(outputs):
        agreements.append(
            "\n".join(
                (
                    "- Finding/topic: Suggested next step convergence",
                    f"  - Agents that independently found it: {', '.join(output.display_name for output in outputs)}",
                    "  - Role lenses involved: See source agent packets or filenames.",
                    "  - Final synthesized severity/priority: N/A",
                    "  - Confidence: high",
                    f"  - Why the convergence matters: all agents suggested `{next_steps[0]}`.",
                )
            )
        )
    if inspected_sets:
        shared = sorted(set.intersection(*inspected_sets)) if len(inspected_sets) > 1 else sorted(inspected_sets[0])
        if shared:
            agreements.append(
                "\n".join(
                    (
                        "- Finding/topic: Shared evidence coverage",
                        f"  - Agents that independently found it: {', '.join(output.display_name for output in outputs)}",
                        "  - Role lenses involved: See source agent packets or filenames.",
                        "  - Final synthesized severity/priority: N/A",
                        "  - Confidence: medium",
                        "  - Why the convergence matters: agents inspected shared files: " + ", ".join(shared),
                    )
                )
            )
    for risk, count in sorted(risk_counter.items()):
        if count > 1:
            agreements.append(
                "\n".join(
                    (
                        f"- Finding/topic: Shared risk `{risk}`",
                        f"  - Agents that independently found it: {count} agents",
                        "  - Role lenses involved: See source agent packets or filenames.",
                        "  - Final synthesized severity/priority: Needs human review",
                        "  - Confidence: medium",
                        "  - Why the convergence matters: repeated risk mentions are stronger review signals.",
                    )
                )
            )
    return agreements


def disagreements(outputs: Sequence[AgentOutput]) -> list[str]:
    items: list[str] = []
    for section in ("Decision", "Suggested next step"):
        values = [(output.display_name, first_value(output, section)) for output in outputs]
        unique_values = {value for _, value in values if value}
        if len(unique_values) > 1:
            assessments = "; ".join(f"{name}: {value or 'missing'}" for name, value in values)
            items.append(
                "\n".join(
                    (
                        f"- Conflict topic: {section}",
                        "  - Agents involved: " + ", ".join(name for name, _ in values),
                        f"  - Each agent's assessment: {assessments}",
                        "  - Evidence basis: contract section values from completed agent outputs.",
                        "  - Synthesis resolution: human synthesis required.",
                        "  - Rationale: independent outputs conflict on a required synthesis field.",
                        "  - Confidence: medium",
                    )
                )
            )

    risk_counter: Counter[str] = Counter()
    for output in outputs:
        risk_counter.update(output.sections.get("Risks", []))
    unique_risks = sorted(risk for risk, count in risk_counter.items() if count == 1)
    if unique_risks:
        items.append(
            "\n".join(
                (
                    "- Conflict topic: Risk coverage differs",
                    "  - Agents involved: agents with non-overlapping risk mentions",
                    "  - Each agent's assessment: " + "; ".join(unique_risks),
                    "  - Evidence basis: `Risks` sections from completed agent outputs.",
                    "  - Synthesis resolution: review whether unique risks are valid blind spots or noise.",
                    "  - Rationale: non-overlapping risks can reveal role-specific signal.",
                    "  - Confidence: medium",
                )
            )
        )
    return items


def missing_sections(output: AgentOutput) -> list[str]:
    return [
        section
        for section in REQUIRED_SECTIONS
        if section not in output.sections or not output.sections[section]
    ]


def render_comparison(outputs: Sequence[AgentOutput]) -> str:
    contract_versions = [
        f"{output.display_name}: {output.contract_version or 'missing'}"
        for output in outputs
    ]
    return (
        f"output_contract_version: {COMPARISON_CONTRACT_VERSION}\n\n"
        "# ZTH Agent Output Comparison\n\n"
        "## Inputs\n\n"
        f"{format_bullets([str(output.path) for output in outputs])}\n"
        "## Contract Versions\n\n"
        f"{format_bullets(contract_versions)}\n"
        "## Contract Warnings\n\n"
        f"{format_bullets(contract_warnings(outputs))}\n"
        "## Files Inspected Across Agents\n\n"
        f"{format_bullets(section_items(outputs, 'Files inspected'))}\n"
        "## Files Changed Across Agents\n\n"
        f"{format_bullets(section_items(outputs, 'Files changed'))}\n"
        "## Commands Run Across Agents\n\n"
        f"{format_bullets(section_items(outputs, 'Commands run'))}\n"
        "## Cross-Agent Agreement Map\n\n"
        f"{format_bullets(agreement_map(outputs))}\n"
        "## Disagreements\n\n"
        f"{format_bullets(disagreements(outputs))}\n"
        # Keep these legacy section names for compatibility with v0.1 adapter readers.
        "## Agreements\n\n"
        f"{format_bullets(agreement_map(outputs))}\n"
        "## Divergences\n\n"
        f"{format_bullets(disagreements(outputs))}\n"
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
