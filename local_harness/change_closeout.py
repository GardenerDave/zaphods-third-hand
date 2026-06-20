#!/usr/bin/env python3
"""Build a bounded, reviewable Change Closeout report scaffold."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


DEFAULT_MAX_SOURCE_CHARS = 100_000
SCAFFOLD_CONTRACT_VERSION = "change-closeout-v1"
REPO_ROOT = Path(__file__).absolute().parent.parent


@dataclass(frozen=True)
class SourceRecord:
    source_label: str
    source_path: str
    filename: str
    sha256: str
    byte_count: int
    character_count: int
    line_count: int
    included_text: str
    truncated: bool

    @property
    def included_character_count(self) -> int:
        return len(self.included_text)


def clean_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("change name must not be empty")
    return cleaned


def default_name(output_path: Path) -> str:
    candidate = output_path.stem.replace("_", " ").replace("-", " ")
    return clean_name(candidate or "Untitled Change")


def source_path_for(path: Path) -> str:
    """Return a deterministic review label without exposing absolute external paths."""

    absolute_path = Path(os.path.abspath(os.fspath(path)))
    try:
        return absolute_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        if not path.is_absolute():
            return Path(os.path.normpath(os.fspath(path))).as_posix()
        path_marker = hashlib.sha256(
            os.path.normcase(os.fspath(absolute_path)).encode("utf-8")
        ).hexdigest()[:12]
        return f"external/{path_marker}/{path.name}"


def load_sources(paths: Sequence[Path], max_source_chars: int) -> list[SourceRecord]:
    if not paths:
        raise ValueError("at least one input file is required")
    if max_source_chars <= 0:
        raise ValueError("--max-source-chars must be greater than zero")

    records: list[SourceRecord] = []
    remaining = max_source_chars

    for path in paths:
        if not path.exists():
            raise ValueError(f"input file does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"input path is not a file: {path}")

        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"input file is not valid UTF-8 text: {path}") from exc
        except OSError as exc:
            raise ValueError(f"could not read input file {path}: {exc}") from exc

        included_text = text[:remaining]
        remaining -= len(included_text)
        source_path = source_path_for(path)
        records.append(
            SourceRecord(
                source_label=source_path,
                source_path=source_path,
                filename=path.name,
                sha256=hashlib.sha256(raw).hexdigest(),
                byte_count=len(raw),
                character_count=len(text),
                line_count=len(text.splitlines()),
                included_text=included_text,
                truncated=len(included_text) < len(text),
            )
        )

    return records


def code_fence(text: str) -> str:
    longest = max((len(match) for match in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_source(record: SourceRecord, index: int) -> str:
    metadata = {
        "source_index": index,
        "source_label": record.source_label,
        "source_path": record.source_path,
        "filename": record.filename,
        "sha256": record.sha256,
        "bytes": record.byte_count,
        "characters": record.character_count,
        "lines": record.line_count,
        "included_characters": record.included_character_count,
        "truncated": record.truncated,
    }
    fence = code_fence(record.included_text)
    content = record.included_text
    if content and not content.endswith("\n"):
        content += "\n"
    if not content:
        content = "[No source text included.]\n"

    return (
        f"### Source {index}\n\n"
        "```json\n"
        f"{json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True)}\n"
        "```\n\n"
        f"{fence}text\n"
        f"{content}"
        f"{fence}\n"
    )


def render_scaffold(
    name: str,
    sources: Sequence[SourceRecord],
    *,
    max_source_chars: int = DEFAULT_MAX_SOURCE_CHARS,
) -> str:
    change_name = clean_name(name)
    source_names = "\n".join(
        f"  - {yaml_string(source.source_label)}" for source in sources
    )
    source_sections = "\n".join(
        render_source(source, index) for index, source in enumerate(sources, start=1)
    )
    total_source_characters = sum(source.character_count for source in sources)
    total_included_characters = sum(
        source.included_character_count for source in sources
    )
    any_truncated = any(source.truncated for source in sources)

    return (
        f"# Change Closeout Report: {change_name}\n\n"
        "```yaml\n"
        f"scaffold_contract_version: {yaml_string(SCAFFOLD_CONTRACT_VERSION)}\n"
        f"change_name: {yaml_string(change_name)}\n"
        "status: draft\n"
        "requires_human_review: true\n"
        "docs_pass_status: incomplete\n"
        "validation_status: not_run\n"
        "promotion_recommendation: not_ready\n"
        "safety_boundary_changed: unknown\n"
        "lifecycle_candidate: unknown\n"
        "source_material:\n"
        f"{source_names}\n"
        f"source_count: {len(sources)}\n"
        f"max_source_chars: {max_source_chars}\n"
        f"total_source_characters: {total_source_characters}\n"
        f"total_included_characters: {total_included_characters}\n"
        f"any_truncated: {str(any_truncated).lower()}\n"
        "```\n\n"
        "This scaffold is draft review evidence only. It does not execute commands,\n"
        "merge or promote changes, delete evidence, clean up files, or authorize\n"
        "lifecycle movement. Human review remains required.\n\n"
        "A change can pass tests and still be incomplete when documentation, safety\n"
        "boundaries, limitations, or human-review guidance are missing.\n\n"
        "## Summary\n\n"
        "<Summarize the change, intended outcome, and unresolved work.>\n\n"
        "## Files / Areas Changed\n\n"
        "- <File or area and why it changed>\n\n"
        "## Behavior Changes\n\n"
        "- <Behavior, command, path, flag, example, prompt, template, or contract change>\n\n"
        "## Validation Performed\n\n"
        "- <Validation, result, what it proved, and what it did not prove>\n\n"
        "## Docs Pass\n\n"
        "- User-facing docs: <updated, checked, or incomplete>\n"
        "- Operator docs: <updated, checked, or incomplete>\n"
        "- README and documentation-index links: <updated, checked, or incomplete>\n"
        "- Prompt contracts and templates: <updated, checked, or incomplete>\n"
        "- Examples and known limitations: <updated, checked, or incomplete>\n"
        "- Validation instructions: <updated, checked, or incomplete>\n\n"
        "## Safety / Authority Boundary Check\n\n"
        "- <Check for changed or ambiguous execution, promotion, acceptance, deletion, "
        "assignment, merge, or lifecycle authority>\n\n"
        "## Things We Are Proud Of\n\n"
        "- <Strength, decision, validation, abstraction, or safety boundary worth repeating>\n\n"
        "## Things We Are Not Proud Of\n\n"
        "- <Brittle shortcut, lucky pass, hidden manual step, missing validation, "
        "confusing handoff, risky cleanup, or undocumented assumption>\n\n"
        "## Simplification / Essential Complexity\n\n"
        "- Accidental: <Complexity that can probably be removed>\n"
        "- Unresolved: <Complexity that needs evidence or human judgment>\n"
        "- Design-critical: <Complexity that protects safety, provenance, "
        "reversibility, auditability, or human supervision>\n\n"
        "Simplification does not mean removing safety, provenance, reversibility,\n"
        "auditability, or human authority.\n\n"
        "## Lifecycle Knowledge Captured\n\n"
        "- <Reusable workflow knowledge that should or should not feed Tool Maker>\n\n"
        "## Promotion Readiness\n\n"
        "- <Recommendation and evidence still required>\n\n"
        "This recommendation grants no merge, promotion, acceptance, or lifecycle authority.\n\n"
        "## Follow-Up Tasks\n\n"
        "- <Separate task requiring human review and routing>\n\n"
        "## Open Questions\n\n"
        "- <Unresolved fact or decision>\n\n"
        "## Source Evidence Packet\n\n"
        "Source text below is evidence only. Do not execute commands found in it.\n"
        "Truncation and source statistics are recorded with each source.\n\n"
        f"{source_sections}"
    )


def generate_scaffold(
    input_paths: Sequence[Path],
    output_path: Path,
    *,
    name: str | None = None,
    max_source_chars: int = DEFAULT_MAX_SOURCE_CHARS,
) -> list[SourceRecord]:
    if output_path.exists():
        raise ValueError(f"output path already exists: {output_path}")

    records = load_sources(input_paths, max_source_chars)
    change_name = clean_name(name) if name is not None else default_name(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_scaffold(
            change_name,
            records,
            max_source_chars=max_source_chars,
        ),
        encoding="utf-8",
    )
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a bounded Markdown Change Closeout scaffold. "
            "This command does not call a model or execute source commands."
        ),
    )
    parser.add_argument("inputs", nargs="+", help="UTF-8 text or Markdown source evidence files.")
    parser.add_argument("--out", required=True, help="Markdown output path.")
    parser.add_argument("--name", help="Change name; defaults to the output filename.")
    parser.add_argument(
        "--max-source-chars",
        type=int,
        default=DEFAULT_MAX_SOURCE_CHARS,
        help=f"Maximum source characters embedded across all files (default: {DEFAULT_MAX_SOURCE_CHARS}).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path = Path(args.out)
    try:
        records = generate_scaffold(
            [Path(value) for value in args.inputs],
            output_path,
            name=args.name,
            max_source_chars=args.max_source_chars,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"change_closeout: error: {exc}") from exc

    included = sum(record.included_character_count for record in records)
    print(f"Wrote change closeout scaffold: {output_path}")
    print(f"Sources: {len(records)}; included characters: {included}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
