#!/usr/bin/env python3
"""Import one versioned LLM-probe result file as preflight-only evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


INPUT_SCHEMA_VERSION = "llm_probe.results.v1"
YAML_INPUT_SCHEMA_VERSION = "llm_probe.verified_yaml.v1"
JSON_INPUT_FORMAT = "zth_normalized_json"
YAML_INPUT_FORMAT = "llm_probe_verified_yaml"
OUTPUT_CONTRACT_VERSION = "zth.llm_probe_preflight.v0.1"
SCOPE = "preflight_only"
PROMOTION_PERFORMED = False
ALLOWED_STATUSES = {"pass", "warn", "fail", "error", "skipped"}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "run_id",
    "generated_at",
    "observations",
}
OBSERVATION_FIELDS = {
    "model_id",
    "probe_id",
    "status",
    "observed_value",
    "latency_ms",
    "diagnostics",
    "metadata",
}
REQUIRED_OBSERVATION_FIELDS = {
    "model_id",
    "probe_id",
    "status",
    "observed_value",
}


@dataclass(frozen=True)
class LoadedProbeInput:
    document: dict[str, Any]
    input_format: str
    input_schema_version: str
    preserved_source_name: str
    observation_records: list[tuple[int, Any]]
    adapter_invalid_rows: list[dict[str, Any]]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def contract_fields() -> dict[str, Any]:
    return {
        "output_contract_version": OUTPUT_CONTRACT_VERSION,
        "scope": SCOPE,
        "promotion_performed": PROMOTION_PERFORMED,
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def nonempty_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def load_probe_document(source_bytes: bytes, source_path: Path) -> dict[str, Any]:
    """Load the existing strict ZTH-normalized JSON input contract."""
    try:
        document = json.loads(source_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source_path} is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{source_path} is not valid JSON: line {exc.lineno} column {exc.colno}"
        ) from exc

    if not isinstance(document, dict):
        raise ValueError(f"{source_path} must contain a top-level JSON object")

    unknown_fields = sorted(set(document) - TOP_LEVEL_FIELDS)
    if unknown_fields:
        raise ValueError(
            "unknown top-level field(s): " + ", ".join(unknown_fields)
        )

    missing_fields = sorted(TOP_LEVEL_FIELDS - set(document))
    if missing_fields:
        raise ValueError(
            "missing top-level field(s): " + ", ".join(missing_fields)
        )

    if document["schema_version"] != INPUT_SCHEMA_VERSION:
        raise ValueError(
            "unsupported schema_version: "
            f"{document['schema_version']!r}; expected {INPUT_SCHEMA_VERSION!r}"
        )
    if not isinstance(document["run_id"], str) or not document["run_id"].strip():
        raise ValueError("run_id must be a non-empty string")
    if (
        not isinstance(document["generated_at"], str)
        or not document["generated_at"].strip()
    ):
        raise ValueError("generated_at must be a non-empty string")
    if not isinstance(document["observations"], list):
        raise ValueError("observations must be a JSON array")

    return document


def load_json_probe_input(source_bytes: bytes, source_path: Path) -> LoadedProbeInput:
    document = load_probe_document(source_bytes, source_path)
    return LoadedProbeInput(
        document=document,
        input_format=JSON_INPUT_FORMAT,
        input_schema_version=document["schema_version"],
        preserved_source_name="results.json",
        observation_records=list(enumerate(document["observations"], start=1)),
        adapter_invalid_rows=[],
    )


def yaml_run_id(provider: str, last_run: str) -> str:
    return f"{provider or 'unknown-provider'}-{last_run or 'unknown-run'}"


def yaml_latency(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return value
    return None


def load_yaml_probe_input(source_bytes: bytes, source_path: Path) -> LoadedProbeInput:
    try:
        import yaml
    except ImportError as exc:
        raise ValueError(
            "LLM-probe YAML input requires PyYAML; install or declare PyYAML "
            "before using --input-format llm-probe-yaml"
        ) from exc

    try:
        source_text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source_path} is not valid UTF-8") from exc

    try:
        loaded = yaml.safe_load(source_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"{source_path} is not valid YAML: {exc}") from exc

    payload = json_safe(loaded)
    if not isinstance(payload, dict):
        raise ValueError(f"{source_path} must contain a top-level YAML mapping")
    if "models" not in payload:
        raise ValueError(f"{source_path} is missing required top-level field 'models'")
    if not isinstance(payload["models"], list):
        raise ValueError(f"{source_path} top-level field 'models' must be a list")

    provider = nonempty_text(payload.get("provider"))
    last_run = nonempty_text(payload.get("last_run"))
    observations: list[tuple[int, Any]] = []
    adapter_invalid_rows: list[dict[str, Any]] = []
    source_index = 0

    for model_index, model in enumerate(payload["models"], start=1):
        if not isinstance(model, dict):
            source_index += 1
            adapter_invalid_rows.append(
                invalid_record(
                    {
                        "model_index": model_index,
                        "model": model,
                    },
                    source_index,
                    ["model_is_not_object"],
                )
            )
            continue

        model_id = nonempty_text(model.get("id"))
        tests = model.get("tests")
        if not isinstance(tests, dict) or not tests:
            source_index += 1
            reasons = ["tests_missing_or_not_object"]
            if not model_id:
                reasons.insert(0, "model_id_missing_or_empty")
            adapter_invalid_rows.append(
                invalid_record(
                    {
                        "model_index": model_index,
                        "model": model,
                    },
                    source_index,
                    reasons,
                )
            )
            continue

        for test_name, test_result in tests.items():
            source_index += 1
            raw_test = {
                "model_index": model_index,
                "model_id": model.get("id"),
                "test_name": test_name,
                "test_result": test_result,
            }
            reasons: list[str] = []
            if not model_id:
                reasons.append("model_id_missing_or_empty")
            if not isinstance(test_name, str) or not test_name.strip():
                reasons.append("test_name_must_be_non_empty_string")
            if not isinstance(test_result, dict):
                reasons.append("test_result_is_not_object")
            elif "passed" not in test_result:
                reasons.append("missing_field(s): passed")
            elif not isinstance(test_result["passed"], bool):
                reasons.append("passed_must_be_boolean")

            if reasons:
                adapter_invalid_rows.append(
                    invalid_record(raw_test, source_index, reasons)
                )
                continue

            passed = test_result["passed"]
            observations.append(
                (
                    source_index,
                    {
                        "model_id": model_id,
                        "probe_id": test_name.strip(),
                        "status": "pass" if passed else "fail",
                        "observed_value": {
                            "passed": passed,
                            "pass_rate": test_result.get("pass_rate"),
                            "provider": provider,
                            "tool_call": model.get("tool_call"),
                            "think_blocks": model.get("think_blocks"),
                            "avg_response_ms": model.get("avg_response_ms"),
                            "last_tested": model.get("last_tested"),
                        },
                        "latency_ms": yaml_latency(model.get("avg_response_ms")),
                        "diagnostics": [],
                        "metadata": {
                            "source_format": YAML_INPUT_FORMAT,
                            "provider": provider,
                            "last_run": last_run,
                        },
                    },
                )
            )

    document = {
        "schema_version": YAML_INPUT_SCHEMA_VERSION,
        "run_id": yaml_run_id(provider, last_run),
        "generated_at": last_run,
        "observations": [record for _, record in observations],
    }
    return LoadedProbeInput(
        document=document,
        input_format=YAML_INPUT_FORMAT,
        input_schema_version=YAML_INPUT_SCHEMA_VERSION,
        preserved_source_name="results.yaml",
        observation_records=observations,
        adapter_invalid_rows=adapter_invalid_rows,
    )


def resolve_input_format(probe_output: Path, requested_format: str) -> str:
    if requested_format != "auto":
        return requested_format
    suffix = probe_output.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "llm-probe-yaml"
    raise ValueError(
        "cannot infer input format from extension "
        f"{probe_output.suffix!r}; use --input-format json or llm-probe-yaml"
    )


def load_probe_input(
    source_bytes: bytes,
    source_path: Path,
    requested_format: str,
) -> LoadedProbeInput:
    resolved_format = resolve_input_format(source_path, requested_format)
    if resolved_format == "json":
        return load_json_probe_input(source_bytes, source_path)
    if resolved_format == "llm-probe-yaml":
        return load_yaml_probe_input(source_bytes, source_path)
    raise ValueError(f"unsupported input format: {resolved_format}")


def observation_errors(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["record_is_not_object"]

    reasons: list[str] = []
    unknown_fields = sorted(set(record) - OBSERVATION_FIELDS)
    if unknown_fields:
        reasons.append("unknown_field(s): " + ", ".join(unknown_fields))

    missing_fields = sorted(REQUIRED_OBSERVATION_FIELDS - set(record))
    if missing_fields:
        reasons.append("missing_field(s): " + ", ".join(missing_fields))

    for field in ("model_id", "probe_id"):
        if field in record and (
            not isinstance(record[field], str) or not record[field].strip()
        ):
            reasons.append(f"{field}_must_be_non_empty_string")

    if "status" in record:
        status = record["status"]
        if not isinstance(status, str) or status.strip().lower() not in ALLOWED_STATUSES:
            reasons.append(
                "status_must_be_one_of: " + ", ".join(sorted(ALLOWED_STATUSES))
            )

    if "latency_ms" in record and record["latency_ms"] is not None:
        latency = record["latency_ms"]
        if (
            isinstance(latency, bool)
            or not isinstance(latency, (int, float))
            or latency < 0
        ):
            reasons.append("latency_ms_must_be_non_negative_number_or_null")

    if "diagnostics" in record:
        diagnostics = record["diagnostics"]
        if not isinstance(diagnostics, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in diagnostics
        ):
            reasons.append("diagnostics_must_be_array_of_non_empty_strings")

    if "metadata" in record and not isinstance(record["metadata"], dict):
        reasons.append("metadata_must_be_object")

    return reasons


def normalize_observation(record: dict[str, Any], source_index: int) -> dict[str, Any]:
    return {
        **contract_fields(),
        "observation_id": f"probe-observation-{source_index:04d}",
        "source_index": source_index,
        "model_id": record["model_id"].strip(),
        "probe_id": record["probe_id"].strip(),
        "status": record["status"].strip().lower(),
        "observed_value": record["observed_value"],
        "latency_ms": record.get("latency_ms"),
        "diagnostics": [item.strip() for item in record.get("diagnostics", [])],
        "metadata": record.get("metadata", {}),
    }


def invalid_record(
    record: Any,
    source_index: int,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        **contract_fields(),
        "source_index": source_index,
        "reasons": reasons,
        "raw_record": record,
    }


def prepare_output_dir(out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"out_dir exists and is non-empty: {out_dir}")
    (out_dir / "source").mkdir(parents=True, exist_ok=True)


def build_summary(
    *,
    document: dict[str, Any],
    input_format: str,
    input_schema_version: str,
    source_sha256: str,
    source_byte_count: int,
    valid_rows: list[dict[str, Any]],
    invalid_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts = Counter(row["status"] for row in valid_rows)
    diagnostic_message_count = sum(
        len(row["diagnostics"]) for row in valid_rows
    )

    return {
        **contract_fields(),
        "input_format": input_format,
        "input_schema_version": input_schema_version,
        "run_id": document["run_id"].strip(),
        "source_generated_at": document["generated_at"].strip(),
        "source_sha256": source_sha256,
        "source_byte_count": source_byte_count,
        "input_record_count": len(valid_rows) + len(invalid_rows),
        "valid_record_count": len(valid_rows),
        "invalid_record_count": len(invalid_rows),
        "model_count": len({row["model_id"] for row in valid_rows}),
        "probe_count": len({row["probe_id"] for row in valid_rows}),
        "status_counts": dict(sorted(status_counts.items())),
        "diagnostics": {
            "records_with_diagnostics": sum(
                bool(row["diagnostics"]) for row in valid_rows
            ),
            "diagnostic_message_count": diagnostic_message_count,
        },
    }


def determine_preflight_status(valid_rows: list[dict[str, Any]]) -> str:
    statuses = {row["status"] for row in valid_rows}
    if not statuses:
        return "unknown"
    if statuses & {"fail", "error"}:
        return "fail"
    if statuses & {"warn", "skipped"}:
        return "intermittent"
    return "pass"


def build_preflight_capability_manifest(
    *,
    document: dict[str, Any],
    input_format: str,
    input_schema_version: str,
    source_sha256: str,
    valid_rows: list[dict[str, Any]],
    invalid_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts = Counter(row["status"] for row in valid_rows)
    return {
        **contract_fields(),
        "requires_human_review": True,
        "source_sha256": source_sha256,
        "source_run_id": document["run_id"].strip(),
        "input_format": input_format,
        "input_schema_version": input_schema_version,
        "model_ids_observed": sorted(
            {row["model_id"] for row in valid_rows}
        ),
        "probe_ids_observed": sorted(
            {row["probe_id"] for row in valid_rows}
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "valid_record_count": len(valid_rows),
        "invalid_record_count": len(invalid_rows),
        "preflight_status": determine_preflight_status(valid_rows),
    }


def render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"output_contract_version: {summary['output_contract_version']}",
        "",
        "# LLM-Probe Preflight Import Summary",
        "",
        f"- Scope: `{summary['scope']}`",
        f"- Promotion performed: `{str(summary['promotion_performed']).lower()}`",
        f"- Run ID: `{summary['run_id']}`",
        f"- Input format: `{summary['input_format']}`",
        f"- Input schema: `{summary['input_schema_version']}`",
        f"- Source SHA-256: `{summary['source_sha256']}`",
        f"- Source bytes: {summary['source_byte_count']}",
        "",
        "## Record Counts",
        "",
        f"- Input records: {summary['input_record_count']}",
        f"- Valid records: {summary['valid_record_count']}",
        f"- Invalid records: {summary['invalid_record_count']}",
        f"- Distinct models: {summary['model_count']}",
        f"- Distinct probes: {summary['probe_count']}",
        "",
        "## Status Counts",
        "",
    ]

    status_counts = summary["status_counts"]
    if status_counts:
        for status, count in sorted(status_counts.items()):
            lines.append(f"- `{status}`: {count}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Diagnostics",
            "",
            "- Records with diagnostics: "
            f"{summary['diagnostics']['records_with_diagnostics']}",
            "- Diagnostic messages: "
            f"{summary['diagnostics']['diagnostic_message_count']}",
            "",
            "## Boundary",
            "",
            "- This output is preflight import evidence only.",
            "- No model was promoted.",
            "- No model audition, ranking, or role assignment was performed.",
            "",
        ]
    )
    return "\n".join(lines)


def ingest_probe_output(
    probe_output: Path,
    out_dir: Path,
    *,
    input_format: str = "auto",
) -> dict[str, Any]:
    if not probe_output.is_file():
        raise ValueError(f"probe output is not a file: {probe_output}")

    source_bytes = probe_output.read_bytes()
    loaded_input = load_probe_input(source_bytes, probe_output, input_format)
    document = loaded_input.document
    prepare_output_dir(out_dir)

    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    preserved_source = out_dir / "source" / loaded_input.preserved_source_name
    preserved_source.write_bytes(source_bytes)

    valid_rows: list[dict[str, Any]] = []
    invalid_rows = list(loaded_input.adapter_invalid_rows)
    for source_index, record in loaded_input.observation_records:
        reasons = observation_errors(record)
        if reasons:
            invalid_rows.append(invalid_record(record, source_index, reasons))
        else:
            valid_rows.append(normalize_observation(record, source_index))

    metadata = {
        **contract_fields(),
        "imported_at": utc_now_iso(),
        "importer": "local_harness/llm_probe_preflight_ingest.py",
        "input_format": loaded_input.input_format,
        "input_schema_version": loaded_input.input_schema_version,
        "run_id": document["run_id"].strip(),
        "source_input_path": str(probe_output.resolve()),
        "preserved_source_path": (
            f"source/{loaded_input.preserved_source_name}"
        ),
        "source_sha256": source_sha256,
        "source_byte_count": len(source_bytes),
    }
    summary = build_summary(
        document=document,
        input_format=loaded_input.input_format,
        input_schema_version=loaded_input.input_schema_version,
        source_sha256=source_sha256,
        source_byte_count=len(source_bytes),
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
    )
    capability_manifest = build_preflight_capability_manifest(
        document=document,
        input_format=loaded_input.input_format,
        input_schema_version=loaded_input.input_schema_version,
        source_sha256=source_sha256,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
    )

    write_json(out_dir / "import_metadata.json", metadata)
    write_jsonl(out_dir / "probe_manifest.jsonl", valid_rows)
    write_jsonl(out_dir / "invalid_records.jsonl", invalid_rows)
    write_json(out_dir / "preflight_summary.json", summary)
    write_json(
        out_dir / "preflight_capability_manifest.json",
        capability_manifest,
    )
    (out_dir / "preflight_summary.md").write_text(
        render_summary_markdown(summary),
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import versioned LLM-probe output as preflight-only evidence.",
    )
    parser.add_argument(
        "--probe-output",
        required=True,
        help="Path to a normalized JSON or LLM-probe verified YAML file.",
    )
    parser.add_argument(
        "--input-format",
        choices=("auto", "json", "llm-probe-yaml"),
        default="auto",
        help="Input format. Auto infers JSON or YAML from the file extension.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory that will receive normalized plain-file evidence.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = ingest_probe_output(
            Path(args.probe_output),
            Path(args.out_dir),
            input_format=args.input_format,
        )
    except (FileExistsError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Valid observations: {summary['valid_record_count']}")
    print(f"Invalid observations: {summary['invalid_record_count']}")
    print(f"Preflight summary: {Path(args.out_dir) / 'preflight_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
