#!/usr/bin/env python3
"""Compare two ZTH preflight capability manifests as review-only evidence."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


INPUT_CONTRACT_VERSION = "zth.llm_probe_preflight.v0.1"
INPUT_SCOPE = "preflight_only"
OUTPUT_CONTRACT_VERSION = "zth.llm_probe_preflight_comparison.v0.1"
OUTPUT_SCOPE = "preflight_comparison_only"
PREFLIGHT_STATUSES = {"pass", "intermittent", "fail", "unknown"}
OBSERVATION_STATUSES = {"pass", "warn", "fail", "error", "skipped"}
REQUIRED_MANIFEST_FIELDS = {
    "output_contract_version",
    "scope",
    "promotion_performed",
    "requires_human_review",
    "source_sha256",
    "source_run_id",
    "input_format",
    "input_schema_version",
    "model_ids_observed",
    "probe_ids_observed",
    "status_counts",
    "valid_record_count",
    "invalid_record_count",
    "preflight_status",
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
LIMITATIONS = [
    (
        "Comparison is manifest-only and cannot identify per-model/per-probe "
        "status transitions."
    )
]


@dataclass(frozen=True)
class LoadedManifest:
    path: Path
    source_bytes: bytes
    manifest_sha256: str
    payload: dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def require_nonempty_string(payload: dict[str, Any], field: str, path: Path) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} field {field!r} must be a non-empty string")
    return value.strip()


def require_nonnegative_integer(
    payload: dict[str, Any],
    field: str,
    path: Path,
) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{path} field {field!r} must be a non-negative integer"
        )
    return value


def validate_id_list(payload: dict[str, Any], field: str, path: Path) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ValueError(f"{path} field {field!r} must be a list")

    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{path} field {field!r} item {index} must be a non-empty string"
            )
        normalized.append(item.strip())

    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{path} field {field!r} must contain unique values")
    return normalized


def expected_preflight_status(
    status_counts: dict[str, int],
    valid_record_count: int,
) -> str:
    if valid_record_count == 0:
        return "unknown"
    if status_counts.get("fail", 0) or status_counts.get("error", 0):
        return "fail"
    if status_counts.get("warn", 0) or status_counts.get("skipped", 0):
        return "intermittent"
    return "pass"


def validate_manifest(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    unknown_fields = sorted(set(payload) - REQUIRED_MANIFEST_FIELDS)
    if unknown_fields:
        raise ValueError(
            f"{path} has unsupported field(s): " + ", ".join(unknown_fields)
        )

    missing_fields = sorted(REQUIRED_MANIFEST_FIELDS - set(payload))
    if missing_fields:
        raise ValueError(
            f"{path} is missing required field(s): " + ", ".join(missing_fields)
        )

    if payload["output_contract_version"] != INPUT_CONTRACT_VERSION:
        raise ValueError(
            f"{path} has unsupported output_contract_version; "
            f"expected {INPUT_CONTRACT_VERSION!r}"
        )
    if payload["scope"] != INPUT_SCOPE:
        raise ValueError(f"{path} must have scope {INPUT_SCOPE!r}")
    if payload["promotion_performed"] is not False:
        raise ValueError(f"{path} must record promotion_performed as false")
    if payload["requires_human_review"] is not True:
        raise ValueError(f"{path} must record requires_human_review as true")

    source_sha256 = require_nonempty_string(payload, "source_sha256", path)
    if not SHA256_RE.fullmatch(source_sha256):
        raise ValueError(f"{path} field 'source_sha256' must be a SHA-256 hex digest")

    for field in ("source_run_id", "input_format", "input_schema_version"):
        require_nonempty_string(payload, field, path)

    model_ids = validate_id_list(payload, "model_ids_observed", path)
    probe_ids = validate_id_list(payload, "probe_ids_observed", path)
    valid_record_count = require_nonnegative_integer(
        payload,
        "valid_record_count",
        path,
    )
    invalid_record_count = require_nonnegative_integer(
        payload,
        "invalid_record_count",
        path,
    )

    raw_status_counts = payload["status_counts"]
    if not isinstance(raw_status_counts, dict):
        raise ValueError(f"{path} field 'status_counts' must be an object")
    unknown_statuses = sorted(set(raw_status_counts) - OBSERVATION_STATUSES)
    if unknown_statuses:
        raise ValueError(
            f"{path} status_counts has unknown status(es): "
            + ", ".join(unknown_statuses)
        )

    status_counts: dict[str, int] = {}
    for status, count in raw_status_counts.items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(
                f"{path} status count for {status!r} must be a non-negative integer"
            )
        status_counts[status] = count

    if sum(status_counts.values()) != valid_record_count:
        raise ValueError(
            f"{path} status counts must sum to valid_record_count"
        )

    preflight_status = payload["preflight_status"]
    if preflight_status not in PREFLIGHT_STATUSES:
        raise ValueError(
            f"{path} preflight_status must be one of: "
            + ", ".join(sorted(PREFLIGHT_STATUSES))
        )
    expected_status = expected_preflight_status(
        status_counts,
        valid_record_count,
    )
    if preflight_status != expected_status:
        raise ValueError(
            f"{path} preflight_status {preflight_status!r} is incompatible "
            f"with status_counts; expected {expected_status!r}"
        )

    return {
        **payload,
        "source_sha256": source_sha256.lower(),
        "source_run_id": payload["source_run_id"].strip(),
        "input_format": payload["input_format"].strip(),
        "input_schema_version": payload["input_schema_version"].strip(),
        "model_ids_observed": sorted(model_ids),
        "probe_ids_observed": sorted(probe_ids),
        "status_counts": dict(sorted(status_counts.items())),
        "valid_record_count": valid_record_count,
        "invalid_record_count": invalid_record_count,
    }


def load_manifest(path: Path) -> LoadedManifest:
    if not path.is_file():
        raise ValueError(f"preflight capability manifest is not a file: {path}")

    source_bytes = path.read_bytes()
    try:
        payload = json.loads(source_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path} is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path} is not valid JSON: line {exc.lineno} column {exc.colno}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level JSON object")

    return LoadedManifest(
        path=path,
        source_bytes=source_bytes,
        manifest_sha256=hashlib.sha256(source_bytes).hexdigest(),
        payload=validate_manifest(payload, path),
    )


def classify_transition(previous: str, latest: str) -> tuple[str, str]:
    if previous == latest:
        return "unchanged", f"{previous}_unchanged"
    if previous == "unknown":
        return "resolved_unknown", f"unknown_to_{latest}"
    if latest == "unknown":
        return "regression", f"{previous}_to_unknown"
    if (previous, latest) in {
        ("pass", "intermittent"),
        ("pass", "fail"),
        ("intermittent", "fail"),
    }:
        return "regression", f"{previous}_to_{latest}"
    if (previous, latest) in {
        ("fail", "intermittent"),
        ("fail", "pass"),
        ("intermittent", "pass"),
    }:
        return "improvement", f"{previous}_to_{latest}"
    raise ValueError(
        f"unsupported preflight status transition: {previous!r} to {latest!r}"
    )


def set_changes(previous: list[str], latest: list[str]) -> dict[str, list[str]]:
    previous_set = set(previous)
    latest_set = set(latest)
    return {
        "added": sorted(latest_set - previous_set),
        "removed": sorted(previous_set - latest_set),
        "unchanged": sorted(previous_set & latest_set),
    }


def count_change(previous: int, latest: int) -> dict[str, int]:
    return {
        "previous": previous,
        "latest": latest,
        "delta": latest - previous,
    }


def transition_review_reason(
    previous: str,
    latest: str,
    classification: str,
) -> str:
    if classification == "regression":
        return (
            f"Overall preflight status regressed from {previous} to {latest}."
        )
    if classification == "improvement":
        return (
            f"Overall preflight status improved from {previous} to {latest}."
        )
    if classification == "resolved_unknown":
        return (
            f"Overall preflight status changed from unknown to {latest}, "
            "resolving unknown evidence; this indicates improved evidence "
            "completeness, not necessarily improved model capability."
        )
    return f"Overall preflight status is unchanged at {latest}."


def input_summary(
    loaded: LoadedManifest,
    preserved_path: str,
) -> dict[str, Any]:
    payload = loaded.payload
    return {
        "preserved_path": preserved_path,
        "manifest_sha256": loaded.manifest_sha256,
        "source_sha256": payload["source_sha256"],
        "source_run_id": payload["source_run_id"],
        "input_format": payload["input_format"],
        "input_schema_version": payload["input_schema_version"],
        "preflight_status": payload["preflight_status"],
    }


def build_comparison(
    previous: LoadedManifest,
    latest: LoadedManifest,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    previous_payload = previous.payload
    latest_payload = latest.payload
    previous_status = previous_payload["preflight_status"]
    latest_status = latest_payload["preflight_status"]
    classification, reason = classify_transition(previous_status, latest_status)

    statuses = sorted(OBSERVATION_STATUSES)
    status_count_changes = {
        status: count_change(
            previous_payload["status_counts"].get(status, 0),
            latest_payload["status_counts"].get(status, 0),
        )
        for status in statuses
    }
    model_id_changes = set_changes(
        previous_payload["model_ids_observed"],
        latest_payload["model_ids_observed"],
    )
    probe_id_changes = set_changes(
        previous_payload["probe_ids_observed"],
        latest_payload["probe_ids_observed"],
    )
    record_count_changes = {
        "valid": count_change(
            previous_payload["valid_record_count"],
            latest_payload["valid_record_count"],
        ),
        "invalid": count_change(
            previous_payload["invalid_record_count"],
            latest_payload["invalid_record_count"],
        ),
    }
    input_differences = {
        "source_run_id_changed": (
            previous_payload["source_run_id"] != latest_payload["source_run_id"]
        ),
        "source_sha256_changed": (
            previous_payload["source_sha256"] != latest_payload["source_sha256"]
        ),
        "input_format_changed": (
            previous_payload["input_format"] != latest_payload["input_format"]
        ),
        "input_schema_version_changed": (
            previous_payload["input_schema_version"]
            != latest_payload["input_schema_version"]
        ),
        "same_run_id_different_source_sha256": (
            previous_payload["source_run_id"] == latest_payload["source_run_id"]
            and previous_payload["source_sha256"]
            != latest_payload["source_sha256"]
        ),
    }

    review_reasons = [
        transition_review_reason(
            previous_status,
            latest_status,
            classification,
        )
    ]
    if any(change["delta"] for change in status_count_changes.values()):
        review_reasons.append("Aggregate observation status counts changed.")
    if model_id_changes["added"] or model_id_changes["removed"]:
        review_reasons.append("The set of observed model IDs changed.")
    if probe_id_changes["added"] or probe_id_changes["removed"]:
        review_reasons.append("The set of observed probe IDs changed.")
    if any(change["delta"] for change in record_count_changes.values()):
        review_reasons.append("Valid or invalid record counts changed.")
    if input_differences["same_run_id_different_source_sha256"]:
        review_reasons.append(
            "The same source run ID is associated with different source SHA-256 "
            "values."
        )
    if input_differences["input_format_changed"]:
        review_reasons.append("The recorded input format changed.")
    if input_differences["input_schema_version_changed"]:
        review_reasons.append("The recorded input schema version changed.")

    return {
        "output_contract_version": OUTPUT_CONTRACT_VERSION,
        "scope": OUTPUT_SCOPE,
        "promotion_performed": False,
        "requires_human_review": True,
        "generated_at": generated_at or utc_now_iso(),
        "inputs": {
            "previous": input_summary(
                previous,
                "source/previous_preflight_capability_manifest.json",
            ),
            "latest": input_summary(
                latest,
                "source/latest_preflight_capability_manifest.json",
            ),
        },
        "input_differences": input_differences,
        "status_transition": {
            "previous": previous_status,
            "latest": latest_status,
            "changed": previous_status != latest_status,
            "classification": classification,
            "reason": reason,
        },
        "status_count_changes": status_count_changes,
        "model_id_changes": model_id_changes,
        "probe_id_changes": probe_id_changes,
        "record_count_changes": record_count_changes,
        "review_reasons": review_reasons,
        "limitations": list(LIMITATIONS),
    }


def markdown_code(value: str) -> str:
    visible = value.replace("\r", r"\r").replace("\n", r"\n")
    escaped = html.escape(visible, quote=False)
    escaped = escaped.replace("|", "&#124;").replace("`", "&#96;")
    return f"<code>{escaped}</code>"


def markdown_id_list(values: list[str]) -> str:
    if not values:
        return "None."
    return ", ".join(markdown_code(value) for value in values)


def render_markdown(comparison: dict[str, Any]) -> str:
    previous = comparison["inputs"]["previous"]
    latest = comparison["inputs"]["latest"]
    transition = comparison["status_transition"]
    lines = [
        f"output_contract_version: {OUTPUT_CONTRACT_VERSION}",
        "",
        "# LLM-Probe Preflight Regression Comparison",
        "",
        "This report compares two canonical ZTH preflight capability manifests. "
        "It is human-review evidence only.",
        "",
        "## Inputs",
        "",
        "| Position | Source run ID | Source SHA-256 | Manifest SHA-256 | Format | Schema |",
        "|---|---|---|---|---|---|",
        (
            f"| Previous | {markdown_code(previous['source_run_id'])} | "
            f"{markdown_code(previous['source_sha256'])} | "
            f"{markdown_code(previous['manifest_sha256'])} | "
            f"{markdown_code(previous['input_format'])} | "
            f"{markdown_code(previous['input_schema_version'])} |"
        ),
        (
            f"| Latest | {markdown_code(latest['source_run_id'])} | "
            f"{markdown_code(latest['source_sha256'])} | "
            f"{markdown_code(latest['manifest_sha256'])} | "
            f"{markdown_code(latest['input_format'])} | "
            f"{markdown_code(latest['input_schema_version'])} |"
        ),
        "",
        "## Overall Status Transition",
        "",
        f"- Previous: `{transition['previous']}`",
        f"- Latest: `{transition['latest']}`",
        f"- Changed: `{str(transition['changed']).lower()}`",
        f"- Classification: `{transition['classification']}`",
        f"- Reason: `{transition['reason']}`",
        "",
        "## Aggregate Status Count Changes",
        "",
        "| Observation status | Previous | Latest | Delta |",
        "|---|---:|---:|---:|",
    ]
    for status, change in comparison["status_count_changes"].items():
        lines.append(
            f"| `{status}` | {change['previous']} | {change['latest']} | "
            f"{change['delta']:+d} |"
        )

    for heading, field in (
        ("Model ID Changes", "model_id_changes"),
        ("Probe ID Changes", "probe_id_changes"),
    ):
        changes = comparison[field]
        lines.extend(
            [
                "",
                f"## {heading}",
                "",
                f"- Added: {markdown_id_list(changes['added'])}",
                f"- Removed: {markdown_id_list(changes['removed'])}",
                f"- Unchanged: {markdown_id_list(changes['unchanged'])}",
            ]
        )

    lines.extend(
        [
            "",
            "## Record Count Changes",
            "",
            "| Record class | Previous | Latest | Delta |",
            "|---|---:|---:|---:|",
        ]
    )
    for record_class, change in comparison["record_count_changes"].items():
        lines.append(
            f"| {record_class.title()} | {change['previous']} | "
            f"{change['latest']} | {change['delta']:+d} |"
        )

    lines.extend(["", "## Review Reasons", ""])
    lines.extend(
        f"- {reason}" for reason in comparison["review_reasons"]
    )
    lines.extend(["", "## Limitations", ""])
    lines.extend(
        f"- {limitation}" for limitation in comparison["limitations"]
    )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- This comparison performs no ranking.",
            "- This comparison performs no model audition.",
            "- This comparison performs no model promotion.",
            "- This comparison grants no lifecycle authorization.",
            "- This comparison makes no production-readiness claim.",
            "",
        ]
    )
    return "\n".join(lines)


def prepare_output_dir(out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"out_dir exists and is non-empty: {out_dir}")
    (out_dir / "source").mkdir(parents=True, exist_ok=True)


def compare_preflight_manifests(
    *,
    previous_manifest: Path,
    latest_manifest: Path,
    out_dir: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    previous = load_manifest(previous_manifest)
    latest = load_manifest(latest_manifest)
    comparison = build_comparison(
        previous,
        latest,
        generated_at=generated_at,
    )

    prepare_output_dir(out_dir)
    (out_dir / "source" / "previous_preflight_capability_manifest.json").write_bytes(
        previous.source_bytes
    )
    (out_dir / "source" / "latest_preflight_capability_manifest.json").write_bytes(
        latest.source_bytes
    )
    write_json(out_dir / "preflight_comparison.json", comparison)
    (out_dir / "preflight_comparison.md").write_text(
        render_markdown(comparison),
        encoding="utf-8",
    )
    return comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--previous-manifest",
        required=True,
        help="Earlier canonical preflight_capability_manifest.json.",
    )
    parser.add_argument(
        "--latest-manifest",
        required=True,
        help="Later canonical preflight_capability_manifest.json.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Empty or absent directory for plain-file comparison evidence.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        compare_preflight_manifests(
            previous_manifest=Path(args.previous_manifest),
            latest_manifest=Path(args.latest_manifest),
            out_dir=Path(args.out_dir),
        )
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Comparison JSON: {Path(args.out_dir) / 'preflight_comparison.json'}")
    print(f"Comparison Markdown: {Path(args.out_dir) / 'preflight_comparison.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
