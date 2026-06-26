"""Convert completed failure-review Markdown into curriculum-candidate JSONL.

The output is draft evidence for supervised review. It is not final training
data, does not call a model, and does not promote or deploy adapters.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_SYSTEM_PROMPT = "Return only valid JSON. Preserve the requested keys exactly."
INCOMPLETE_VALUES = {"", "todo", "tbd", "n/a"}
CORRECTED_NO = {"no", "n", "false", "none"}
CORRECTED_YES = {"yes", "y", "true"}
KEEP_YES = {"yes", "y", "true", "keep", "include", "next"}
KEEP_NO = {"no", "n", "false", "skip", "exclude"}


@dataclass(frozen=True)
class ReviewRow:
    source_path: Path
    source_label: str
    source_review_type: str
    row_index: str
    target: Any
    adapter_output: Any
    adapter_output_raw: str
    classification: str
    likely_cause: str
    keep_for_next_curriculum: str
    corrected_target_needed: str
    extra_fields: str | None


@dataclass(frozen=True)
class ConversionResult:
    candidates: tuple[dict[str, Any], ...]
    skipped_rows: int
    warnings: tuple[str, ...]


def safe_source_label(path: Path) -> str:
    if path.is_absolute():
        return f"<absolute>/{path.name}"
    return path.as_posix()


def parse_json_text(value: str, *, context: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{context}: invalid JSON: {exc.msg}") from exc


def infer_review_type(text: str) -> str:
    first_heading = next(
        (line.strip().lower() for line in text.splitlines() if line.startswith("#")),
        "",
    )
    if "extra-field" in first_heading or "extra field" in first_heading:
        return "extra_field"
    if "non-exact" in first_heading or "non exact" in first_heading:
        return "non_exact"
    return "review"


def row_sections(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^## Row\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[start:end]))
    return sections


def extract_fenced_block(section: str, label: str, *, required: bool = True) -> tuple[str, str] | None:
    pattern = re.compile(
        rf"^{re.escape(label)}:\s*\n```(?P<lang>[^\n]*)\n(?P<body>.*?)\n```",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(section)
    if not match:
        if required:
            raise ValueError(f"missing fenced {label.lower()} block")
        return None
    return match.group("lang").strip(), match.group("body").strip()


def extract_review_field(section: str, label: str) -> str:
    pattern = re.compile(
        rf"^\s*[-*]\s+{re.escape(label)}:\s*(?P<value>.*?)\s*$",
        flags=re.MULTILINE,
    )
    match = pattern.search(section)
    if not match:
        return ""
    return match.group("value").strip()


def extract_extra_fields(section: str) -> str | None:
    match = re.search(r"^Extra fields:\s*(?P<value>.*?)\s*$", section, flags=re.MULTILINE)
    if not match:
        return None
    return match.group("value").strip().strip("`")


def parse_review_file(path: str | Path) -> list[ReviewRow]:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"{p}: missing input file")

    text = p.read_text(encoding="utf-8")
    source_review_type = infer_review_type(text)
    source_label = safe_source_label(p)
    rows: list[ReviewRow] = []

    sections = row_sections(text)
    if not sections:
        raise ValueError(f"{p}: no '## Row' sections found")

    for row_index, section in sections:
        context = f"{p}: row {row_index}"
        target_block = extract_fenced_block(section, "Target")
        assert target_block is not None
        target = parse_json_text(target_block[1], context=f"{context} target")

        adapter_block = extract_fenced_block(section, "Adapter", required=False)
        adapter_output_raw = adapter_block[1] if adapter_block else ""
        adapter_output: Any = adapter_output_raw
        if adapter_block and adapter_block[0].lower() == "json":
            adapter_output = parse_json_text(adapter_output_raw, context=f"{context} adapter")

        row = ReviewRow(
            source_path=p,
            source_label=source_label,
            source_review_type=source_review_type,
            row_index=row_index,
            target=target,
            adapter_output=adapter_output,
            adapter_output_raw=adapter_output_raw,
            classification=extract_review_field(section, "classification"),
            likely_cause=extract_review_field(section, "likely cause"),
            keep_for_next_curriculum=extract_review_field(section, "keep for next curriculum"),
            corrected_target_needed=extract_review_field(section, "corrected target needed"),
            extra_fields=extract_extra_fields(section),
        )
        rows.append(row)

    return rows


def normalized_failure_mode(classification: str) -> str:
    value = classification.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value or "reviewed_failure"


def should_keep(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in KEEP_YES:
        return True
    if normalized in KEEP_NO:
        return False
    return None


def is_incomplete(value: str) -> bool:
    return value.strip().lower() in INCOMPLETE_VALUES


def validate_completed_review_row(row: ReviewRow) -> bool:
    context = f"{row.source_path}: row {row.row_index}"

    if is_incomplete(row.classification):
        raise ValueError(f"{context}: classification is incomplete")

    if is_incomplete(row.likely_cause):
        raise ValueError(f"{context}: likely cause is incomplete")

    keep = should_keep(row.keep_for_next_curriculum)
    if keep is None:
        raise ValueError(
            f"{context}: keep for next curriculum must be explicit yes or no"
        )

    if keep is False:
        return False

    corrected = row.corrected_target_needed.strip()
    corrected_lower = corrected.lower()
    if corrected_lower in INCOMPLETE_VALUES:
        raise ValueError(
            f"{context}: corrected target needed must be no, yes with corrected JSON, "
            "or valid corrected JSON"
        )

    if corrected_lower in CORRECTED_YES:
        raise ValueError(
            f"{context}: corrected target needed is yes but no corrected JSON was provided"
        )

    if corrected_lower in CORRECTED_NO:
        return True

    parse_json_text(corrected, context=f"{context} corrected target")
    return True


def target_for_candidate(row: ReviewRow) -> tuple[Any, str]:
    corrected = row.corrected_target_needed.strip()
    if corrected.lower() in CORRECTED_NO:
        return row.target, "target_block"
    return (
        parse_json_text(
            corrected,
            context=f"{row.source_path}: row {row.row_index} corrected target",
        ),
        "review_corrected_target",
    )


def candidate_from_row(
    row: ReviewRow,
    *,
    curriculum: str,
    system_prompt: str,
) -> dict[str, Any]:
    assistant_target, target_source = target_for_candidate(row)
    assistant_content = json.dumps(assistant_target, ensure_ascii=False, separators=(",", ":"))

    return {
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    "TODO: replace this draft prompt with the reviewed source prompt "
                    f"before training. Candidate source: {row.source_label} row {row.row_index}. "
                    "Return the assistant JSON target exactly."
                ),
            },
            {
                "role": "assistant",
                "content": assistant_content,
            },
        ],
        "metadata": {
            "candidate_status": "draft",
            "requires_human_review": True,
            "not_final_training_data": True,
            "curriculum": curriculum,
            "failure_mode": normalized_failure_mode(row.classification),
            "classification": row.classification,
            "likely_cause": row.likely_cause,
            "keep_for_next_curriculum": row.keep_for_next_curriculum,
            "corrected_target_source": target_source,
            "adapter_output_raw": row.adapter_output_raw,
            "source_review_file": row.source_label,
            "source_review_type": row.source_review_type,
            "source_row": row.row_index,
            "extra_fields": row.extra_fields,
        },
    }


def convert_review_files(
    paths: list[str | Path],
    *,
    curriculum: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> ConversionResult:
    candidates: list[dict[str, Any]] = []
    warnings: list[str] = []
    skipped_rows = 0

    for path in paths:
        rows = parse_review_file(path)

        for row in rows:
            keep = validate_completed_review_row(row)
            if not keep:
                skipped_rows += 1
                continue
            candidates.append(
                candidate_from_row(
                    row,
                    curriculum=curriculum,
                    system_prompt=system_prompt,
                )
            )

    return ConversionResult(
        candidates=tuple(candidates),
        skipped_rows=skipped_rows,
        warnings=tuple(warnings),
    )


def write_jsonl(path: str | Path, rows: tuple[dict[str, Any], ...]) -> None:
    p = Path(path)
    if p.exists():
        raise ValueError(f"{p}: output already exists")
    p.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    p.write_text(text + ("\n" if text else ""), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert completed failure-review Markdown into draft curriculum-candidate JSONL."
        )
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        type=Path,
        help="Review Markdown file. May be provided multiple times.",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--curriculum", required=True)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = convert_review_files(
            args.input,
            curriculum=args.curriculum,
            system_prompt=args.system_prompt,
        )
        write_jsonl(args.output, result.candidates)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    for path in args.input:
        print(f"read: {path}")
    print(f"wrote: {args.output}")
    print(f"candidate_rows: {len(result.candidates)}")
    print(f"skipped_rows: {result.skipped_rows}")
    if result.warnings:
        for warning in result.warnings:
            print(f"WARNING: {warning}")
    else:
        print("warnings: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
