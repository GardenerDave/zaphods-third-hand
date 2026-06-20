#!/usr/bin/env python3
"""Validate Tool Maker and Change Closeout scaffold shape and metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence


TOOL_VERSION = "tool-lifecycle-v1"
CLOSEOUT_VERSION = "change-closeout-v1"
VERSION_TO_KIND = {
    TOOL_VERSION: "tool-lifecycle",
    CLOSEOUT_VERSION: "change-closeout",
}
KIND_TO_VERSION = {kind: version for version, kind in VERSION_TO_KIND.items()}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
INT_RE = re.compile(r"-?[0-9]+")

COMMON_REQUIRED_FIELDS = {
    "scaffold_contract_version",
    "status",
    "requires_human_review",
    "source_material",
    "source_count",
    "max_source_chars",
    "total_source_characters",
    "total_included_characters",
    "any_truncated",
}
TOOL_REQUIRED_FIELDS = COMMON_REQUIRED_FIELDS | {
    "lifecycle_name",
    "intended_operator",
    "risk_level",
    "replayable_steps",
    "validation_checks",
    "known_failure_modes",
    "promotion_recommendation",
}
CLOSEOUT_REQUIRED_FIELDS = COMMON_REQUIRED_FIELDS | {
    "change_name",
    "docs_pass_status",
    "validation_status",
    "promotion_recommendation",
    "safety_boundary_changed",
    "lifecycle_candidate",
}
SOURCE_REQUIRED_FIELDS = {
    "source_index",
    "source_label",
    "source_path",
    "filename",
    "sha256",
    "bytes",
    "characters",
    "lines",
    "included_characters",
    "truncated",
}
TOOL_HEADINGS = (
    "# Tool Lifecycle Draft:",
    "## Purpose",
    "## When to Use",
    "## Inputs Required",
    "## Preconditions",
    "## Human Decisions Required",
    "## Workflow Steps",
    "## Useful Commands",
    "## Validation Checks",
    "## Failure Modes",
    "## Failed-but-Important Attempts",
    "## Things We Are Proud Of",
    "## Things We Are Not Proud Of",
    "## Simplification / Essential Complexity",
    "## Recovery / Rollback",
    "## Artifacts Produced",
    "## Promotion Criteria",
    "## Open Questions",
    "## Source Material Packet",
)
CLOSEOUT_HEADINGS = (
    "# Change Closeout Report:",
    "## Summary",
    "## Files / Areas Changed",
    "## Behavior Changes",
    "## Validation Performed",
    "## Docs Pass",
    "## Safety / Authority Boundary Check",
    "## Things We Are Proud Of",
    "## Things We Are Not Proud Of",
    "## Simplification / Essential Complexity",
    "## Lifecycle Knowledge Captured",
    "## Promotion Readiness",
    "## Follow-Up Tasks",
    "## Open Questions",
    "## Source Evidence Packet",
)


class ScaffoldValidationError(ValueError):
    """Raised when scaffold shape or metadata is inconsistent."""


def parse_scalar(raw: str, *, context: str) -> Any:
    value = raw.strip()
    if value == "":
        raise ScaffoldValidationError(f"{context}: missing value")
    if value in {"true", "false"}:
        return value == "true"
    if INT_RE.fullmatch(value):
        return int(value)
    if value.startswith('"') or value.startswith("["):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ScaffoldValidationError(
                f"{context}: invalid quoted or list value"
            ) from exc
    return value


def parse_header_yaml(block: str) -> dict[str, Any]:
    """Parse the small top-level scalar/list YAML subset emitted by the builders."""

    lines = block.splitlines()
    result: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith((" ", "\t")):
            raise ScaffoldValidationError(
                f"YAML line {index + 1}: unexpected indentation"
            )
        key, separator, raw_value = line.partition(":")
        if not separator or not KEY_RE.fullmatch(key):
            raise ScaffoldValidationError(
                f"YAML line {index + 1}: expected top-level key"
            )
        if key in result:
            raise ScaffoldValidationError(f"YAML field {key!r} is duplicated")

        if raw_value.strip():
            result[key] = parse_scalar(
                raw_value,
                context=f"YAML field {key!r}",
            )
            index += 1
            continue

        values: list[Any] = []
        index += 1
        while index < len(lines) and lines[index].startswith("  - "):
            values.append(
                parse_scalar(
                    lines[index][4:],
                    context=f"YAML field {key!r} item",
                )
            )
            index += 1
        result[key] = values

    return result


def extract_header(text: str) -> tuple[str, dict[str, Any]]:
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ScaffoldValidationError("missing scaffold title on the first line")

    yaml_start = None
    for index in range(1, len(lines)):
        if not lines[index].strip():
            continue
        if lines[index] != "```yaml":
            raise ScaffoldValidationError(
                "the first content after the title must be a YAML fenced block"
            )
        yaml_start = index
        break
    if yaml_start is None:
        raise ScaffoldValidationError("missing YAML fenced block after title")

    try:
        yaml_end = lines.index("```", yaml_start + 1)
    except ValueError as exc:
        raise ScaffoldValidationError("unterminated YAML fenced block") from exc

    return lines[0], parse_header_yaml("\n".join(lines[yaml_start + 1 : yaml_end]))


def extract_source_rows(text: str, packet_heading: str) -> list[dict[str, Any]]:
    marker = f"{packet_heading}\n"
    if marker not in text:
        raise ScaffoldValidationError(f"missing required heading {packet_heading!r}")
    lines = text.split(marker, 1)[1].splitlines()
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        heading_match = re.fullmatch(r"### Source ([0-9]+)", lines[index])
        if not heading_match:
            index += 1
            continue

        heading_index = int(heading_match.group(1))
        index += 1
        while index < len(lines) and not lines[index]:
            index += 1
        if index >= len(lines) or lines[index] != "```json":
            raise ScaffoldValidationError(
                f"source {heading_index} is missing its JSON metadata block"
            )
        index += 1
        json_lines: list[str] = []
        while index < len(lines) and lines[index] != "```":
            json_lines.append(lines[index])
            index += 1
        if index >= len(lines):
            raise ScaffoldValidationError(
                f"source {heading_index} has an unterminated JSON metadata block"
            )

        try:
            payload = json.loads("\n".join(json_lines))
        except json.JSONDecodeError as exc:
            raise ScaffoldValidationError(
                f"source {heading_index} metadata is not valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise ScaffoldValidationError(
                f"source {heading_index} metadata must be a JSON object"
            )
        payload["_heading_index"] = heading_index
        rows.append(payload)

        index += 1
        while index < len(lines) and not lines[index]:
            index += 1
        if index >= len(lines):
            raise ScaffoldValidationError(
                f"source {heading_index} is missing its text evidence block"
            )
        text_fence_match = re.fullmatch(r"(`{3,})text", lines[index])
        if not text_fence_match:
            raise ScaffoldValidationError(
                f"source {heading_index} is missing its text evidence fence"
            )
        closing_fence = text_fence_match.group(1)
        index += 1
        while index < len(lines) and lines[index] != closing_fence:
            index += 1
        if index >= len(lines):
            raise ScaffoldValidationError(
                f"source {heading_index} has an unterminated text evidence block"
            )
        index += 1

    return rows


def require_fields(payload: dict[str, Any], required: set[str], context: str) -> None:
    missing = sorted(required - payload.keys())
    if missing:
        raise ScaffoldValidationError(
            f"{context} missing required fields: {', '.join(missing)}"
        )


def require_string(payload: dict[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ScaffoldValidationError(f"{context} field {key!r} must be a non-empty string")
    return value


def require_integer(payload: dict[str, Any], key: str, context: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ScaffoldValidationError(
            f"{context} field {key!r} must be a non-negative integer"
        )
    return value


def require_enum(
    payload: dict[str, Any],
    key: str,
    allowed: set[str],
    context: str,
) -> None:
    value = payload.get(key)
    if value not in allowed:
        raise ScaffoldValidationError(
            f"{context} field {key!r} must be one of: {', '.join(sorted(allowed))}"
        )


def validate_headings(text: str, headings: Sequence[str]) -> None:
    lines = set(text.splitlines())
    title_prefix = headings[0]
    if not text.splitlines()[0].startswith(title_prefix):
        raise ScaffoldValidationError(f"title must start with {title_prefix!r}")
    if not text.splitlines()[0][len(title_prefix) :].strip():
        raise ScaffoldValidationError("scaffold title must include a name")
    for heading in headings[1:]:
        if heading not in lines:
            raise ScaffoldValidationError(f"missing required heading {heading!r}")


def validate_source_rows(metadata: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    source_material = metadata.get("source_material")
    if not isinstance(source_material, list) or not all(
        isinstance(value, str) and value for value in source_material
    ):
        raise ScaffoldValidationError(
            "YAML field 'source_material' must be a list of non-empty strings"
        )
    if len(source_material) != len(set(source_material)):
        raise ScaffoldValidationError("source_material contains duplicate source labels")

    source_count = require_integer(metadata, "source_count", "YAML")
    max_source_chars = require_integer(metadata, "max_source_chars", "YAML")
    total_source = require_integer(metadata, "total_source_characters", "YAML")
    total_included = require_integer(metadata, "total_included_characters", "YAML")
    if max_source_chars <= 0:
        raise ScaffoldValidationError("YAML field 'max_source_chars' must be greater than zero")
    if not isinstance(metadata.get("any_truncated"), bool):
        raise ScaffoldValidationError("YAML field 'any_truncated' must be boolean")

    if source_count != len(rows):
        raise ScaffoldValidationError(
            f"source_count mismatch: YAML has {source_count}, source packet has {len(rows)}"
        )
    if source_count != len(source_material):
        raise ScaffoldValidationError(
            "source_count does not match source_material item count"
        )

    labels: list[str] = []
    source_character_sum = 0
    included_character_sum = 0
    truncated_values: list[bool] = []
    for expected_index, row in enumerate(rows, start=1):
        context = f"source metadata {expected_index}"
        require_fields(row, SOURCE_REQUIRED_FIELDS, context)
        source_index = require_integer(row, "source_index", context)
        if source_index != expected_index or row["_heading_index"] != expected_index:
            raise ScaffoldValidationError(
                f"{context} source_index must match ordered heading index {expected_index}"
            )
        label = require_string(row, "source_label", context)
        require_string(row, "source_path", context)
        require_string(row, "filename", context)
        digest = require_string(row, "sha256", context)
        if not SHA256_RE.fullmatch(digest):
            raise ScaffoldValidationError(
                f"{context} field 'sha256' must be 64 lowercase hexadecimal characters"
            )
        require_integer(row, "bytes", context)
        characters = require_integer(row, "characters", context)
        require_integer(row, "lines", context)
        included = require_integer(row, "included_characters", context)
        if included > characters:
            raise ScaffoldValidationError(
                f"{context} included_characters cannot exceed characters"
            )
        truncated = row.get("truncated")
        if not isinstance(truncated, bool):
            raise ScaffoldValidationError(f"{context} field 'truncated' must be boolean")

        labels.append(label)
        source_character_sum += characters
        included_character_sum += included
        truncated_values.append(truncated)

    if len(labels) != len(set(labels)):
        raise ScaffoldValidationError("source metadata contains duplicate source labels")
    if source_material != labels:
        raise ScaffoldValidationError(
            "source_material entries must match source_label values in source order"
        )
    if total_source != source_character_sum:
        raise ScaffoldValidationError(
            "total_source_characters does not match source metadata sum"
        )
    if total_included != included_character_sum:
        raise ScaffoldValidationError(
            "total_included_characters does not match source metadata sum"
        )
    if total_included > max_source_chars:
        raise ScaffoldValidationError(
            "total_included_characters cannot exceed max_source_chars"
        )
    if metadata["any_truncated"] != any(truncated_values):
        raise ScaffoldValidationError(
            "any_truncated does not match source metadata truncation values"
        )


def validate_scaffold_text(text: str, expected_kind: str | None = None) -> str:
    _title, metadata = extract_header(text)
    version = metadata.get("scaffold_contract_version")
    if version is None:
        raise ScaffoldValidationError("missing scaffold_contract_version")
    if version not in VERSION_TO_KIND:
        raise ScaffoldValidationError(
            f"unknown scaffold_contract_version: {version!r}"
        )
    kind = VERSION_TO_KIND[version]
    if expected_kind is not None and kind != expected_kind:
        raise ScaffoldValidationError(
            f"scaffold kind mismatch: expected {expected_kind!r}, detected {kind!r}"
        )

    if kind == "tool-lifecycle":
        require_fields(metadata, TOOL_REQUIRED_FIELDS, "Tool Maker YAML")
        validate_headings(text, TOOL_HEADINGS)
        require_string(metadata, "lifecycle_name", "Tool Maker YAML")
        require_string(metadata, "intended_operator", "Tool Maker YAML")
        require_string(metadata, "risk_level", "Tool Maker YAML")
        for key in ("replayable_steps", "validation_checks", "known_failure_modes"):
            if not isinstance(metadata.get(key), list):
                raise ScaffoldValidationError(
                    f"Tool Maker YAML field {key!r} must be a list"
                )
        require_enum(
            metadata,
            "promotion_recommendation",
            {"not_ready", "ready_for_human_review"},
            "Tool Maker YAML",
        )
        packet_heading = "## Source Material Packet"
    else:
        require_fields(metadata, CLOSEOUT_REQUIRED_FIELDS, "Change Closeout YAML")
        validate_headings(text, CLOSEOUT_HEADINGS)
        require_string(metadata, "change_name", "Change Closeout YAML")
        require_enum(
            metadata,
            "docs_pass_status",
            {"updated", "checked_no_change_needed", "incomplete"},
            "Change Closeout YAML",
        )
        require_enum(
            metadata,
            "validation_status",
            {"passed", "partial", "failed", "not_run"},
            "Change Closeout YAML",
        )
        require_enum(
            metadata,
            "promotion_recommendation",
            {"not_ready", "ready_for_human_review", "ready_to_promote"},
            "Change Closeout YAML",
        )
        require_enum(
            metadata,
            "safety_boundary_changed",
            {"yes", "no", "unknown"},
            "Change Closeout YAML",
        )
        require_enum(
            metadata,
            "lifecycle_candidate",
            {"yes", "no", "unknown"},
            "Change Closeout YAML",
        )
        packet_heading = "## Source Evidence Packet"

    if metadata.get("status") != "draft":
        raise ScaffoldValidationError("YAML field 'status' must be 'draft'")
    if metadata.get("requires_human_review") is not True:
        raise ScaffoldValidationError(
            "YAML field 'requires_human_review' must be true"
        )

    rows = extract_source_rows(text, packet_heading)
    validate_source_rows(metadata, rows)
    return kind


def validate_scaffold(path: Path, expected_kind: str | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ScaffoldValidationError(f"scaffold file does not exist: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ScaffoldValidationError(f"scaffold is not valid UTF-8: {path}") from exc
    return validate_scaffold_text(text, expected_kind=expected_kind)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Tool Maker or Change Closeout scaffold shape and metadata. "
            "This does not validate truth, safety, completeness, or promotion readiness."
        ),
    )
    parser.add_argument(
        "--kind",
        choices=sorted(KIND_TO_VERSION),
        help="Optional expected scaffold kind.",
    )
    parser.add_argument("scaffold", help="Markdown scaffold to validate.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.scaffold)
    try:
        kind = validate_scaffold(path, expected_kind=args.kind)
    except ScaffoldValidationError as exc:
        print(f"INVALID {path}: {exc}", file=sys.stderr)
        return 1
    print(f"VALID {path}: {kind} ({KIND_TO_VERSION[kind]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
