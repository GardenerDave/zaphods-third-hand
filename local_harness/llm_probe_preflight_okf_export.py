#!/usr/bin/env python3
"""Export completed LLM-probe preflight evidence as an optional OKF-style bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


REQUIRED_FILES = (
    "import_metadata.json",
    "probe_manifest.jsonl",
    "invalid_records.jsonl",
    "preflight_capability_manifest.json",
    "preflight_summary.json",
    "preflight_summary.md",
)
EXPECTED_CONTRACT_VERSION = "zth.llm_probe_preflight.v0.1"
EXPECTED_SCOPE = "preflight_only"


@dataclass(frozen=True)
class PreflightEvidence:
    preflight_dir: Path
    metadata: dict[str, Any]
    capability_manifest: dict[str, Any]
    summary: dict[str, Any]
    observations: list[dict[str, Any]]
    invalid_records: list[dict[str, Any]]
    source_path: Path

    @property
    def run_id(self) -> str:
        return str(self.capability_manifest["source_run_id"])

    @property
    def source_sha256(self) -> str:
        return str(self.capability_manifest["source_sha256"])

    @property
    def preflight_status(self) -> str:
        return str(self.capability_manifest["preflight_status"])

    @property
    def input_format(self) -> str:
        return str(self.capability_manifest["input_format"])

    @property
    def timestamp(self) -> str:
        return str(
            self.summary.get("source_generated_at")
            or self.metadata.get("imported_at")
            or "unknown"
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path} is not valid JSON: line {exc.lineno} column {exc.colno}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{path}:{line_number} is not valid JSON: {exc.msg}"
            ) from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        rows.append(row)
    return rows


def require_contract(payload: dict[str, Any], path: Path) -> None:
    if payload.get("output_contract_version") != EXPECTED_CONTRACT_VERSION:
        raise ValueError(
            f"{path} has unsupported output_contract_version"
        )
    if payload.get("scope") != EXPECTED_SCOPE:
        raise ValueError(f"{path} must have scope {EXPECTED_SCOPE!r}")
    if payload.get("promotion_performed") is not False:
        raise ValueError(f"{path} must record promotion_performed as false")


def load_preflight_evidence(preflight_dir: Path) -> PreflightEvidence:
    if not preflight_dir.is_dir():
        raise ValueError(f"preflight directory does not exist: {preflight_dir}")

    missing = [
        relative
        for relative in REQUIRED_FILES
        if not (preflight_dir / relative).is_file()
    ]
    source_candidates = [
        path
        for path in (
            preflight_dir / "source" / "results.json",
            preflight_dir / "source" / "results.yaml",
        )
        if path.is_file()
    ]
    if not source_candidates:
        missing.append("source/results.json or source/results.yaml")
    if missing:
        raise ValueError(
            "preflight directory is missing required file(s): "
            + ", ".join(missing)
        )
    if len(source_candidates) != 1:
        raise ValueError(
            "preflight directory must contain exactly one preserved source file"
        )

    metadata_path = preflight_dir / "import_metadata.json"
    capability_path = preflight_dir / "preflight_capability_manifest.json"
    summary_path = preflight_dir / "preflight_summary.json"
    metadata = load_json(metadata_path)
    capability = load_json(capability_path)
    summary = load_json(summary_path)
    observations = load_jsonl(preflight_dir / "probe_manifest.jsonl")
    invalid_records = load_jsonl(preflight_dir / "invalid_records.jsonl")

    for payload, path in (
        (metadata, metadata_path),
        (capability, capability_path),
        (summary, summary_path),
    ):
        require_contract(payload, path)

    source_path = source_candidates[0]
    actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    recorded_hashes = {
        str(payload.get("source_sha256", ""))
        for payload in (metadata, capability, summary)
    }
    if recorded_hashes != {actual_sha256}:
        raise ValueError(
            "preserved source SHA-256 does not match all preflight records"
        )

    if capability.get("requires_human_review") is not True:
        raise ValueError(
            "preflight capability manifest must require human review"
        )
    if int(capability.get("valid_record_count", -1)) != len(observations):
        raise ValueError("valid record count does not match probe_manifest.jsonl")
    if int(capability.get("invalid_record_count", -1)) != len(invalid_records):
        raise ValueError(
            "invalid record count does not match invalid_records.jsonl"
        )

    preserved_source_path = metadata.get("preserved_source_path")
    if preserved_source_path != source_path.relative_to(preflight_dir).as_posix():
        raise ValueError("preserved source path does not match import metadata")

    for index, row in enumerate(observations, start=1):
        require_contract(row, preflight_dir / f"probe_manifest.jsonl:{index}")
        for required in ("model_id", "probe_id", "status"):
            if not isinstance(row.get(required), str) or not row[required].strip():
                raise ValueError(
                    f"probe_manifest.jsonl:{index} has invalid {required}"
                )

    return PreflightEvidence(
        preflight_dir=preflight_dir.resolve(),
        metadata=metadata,
        capability_manifest=capability,
        summary=summary,
        observations=observations,
        invalid_records=invalid_records,
        source_path=source_path.resolve(),
    )


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def stable_slug_map(values: Iterable[str], fallback: str) -> dict[str, str]:
    unique_values = sorted(set(values))
    grouped: dict[str, list[str]] = defaultdict(list)
    for value in unique_values:
        grouped[slugify(value, fallback)].append(value)

    result: dict[str, str] = {}
    for base_slug, grouped_values in sorted(grouped.items()):
        if len(grouped_values) == 1:
            result[grouped_values[0]] = base_slug
            continue
        for value in grouped_values:
            suffix = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
            result[value] = f"{base_slug}-{suffix}"
    return result


def row_provider(row: dict[str, Any]) -> str:
    metadata = row.get("metadata")
    if isinstance(metadata, dict):
        provider = metadata.get("provider")
        if isinstance(provider, str) and provider.strip():
            return provider.strip()
    observed_value = row.get("observed_value")
    if isinstance(observed_value, dict):
        provider = observed_value.get("provider")
        if isinstance(provider, str) and provider.strip():
            return provider.strip()
    return "unknown-provider"


def conservative_status(rows: Sequence[dict[str, Any]]) -> str:
    statuses = {str(row.get("status", "")) for row in rows}
    if not statuses:
        return "unknown"
    if statuses & {"fail", "error"}:
        return "fail"
    if statuses & {"warn", "skipped"}:
        return "intermittent"
    return "pass"


def yaml_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def render_frontmatter(
    *,
    concept_type: str,
    title: str,
    description: str,
    resource: str,
    tags: Sequence[str],
    timestamp: str,
    evidence: PreflightEvidence,
) -> str:
    lines = [
        "---",
        f"type: {yaml_string(concept_type)}",
        f"title: {yaml_string(title)}",
        f"description: {yaml_string(description)}",
        f"resource: {yaml_string(resource)}",
        "tags:",
    ]
    lines.extend(f"  - {yaml_string(tag)}" for tag in tags)
    lines.extend(
        [
            f"timestamp: {yaml_string(timestamp)}",
            "zth:",
            "  output_contract_version: "
            f"{yaml_string(EXPECTED_CONTRACT_VERSION)}",
            f"  scope: {yaml_string(EXPECTED_SCOPE)}",
            "  promotion_performed: false",
            "  requires_human_review: true",
            f"  source_sha256: {yaml_string(evidence.source_sha256)}",
            f"  preflight_status: {yaml_string(evidence.preflight_status)}",
            "---",
            "",
        ]
    )
    return "\n".join(lines)


def markdown_document(frontmatter: str, body_lines: Sequence[str]) -> str:
    return frontmatter + "\n".join(body_lines).rstrip() + "\n"


def relative_markdown_link(
    *,
    label: str,
    target: Path,
    source_page: Path,
) -> str:
    relative = os.path.relpath(target, start=source_page.parent)
    return f"[{label}]({Path(relative).as_posix()})"


def prepare_output_dir(out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"out_dir exists and is non-empty: {out_dir}")
    (out_dir / "providers").mkdir(parents=True, exist_ok=True)
    (out_dir / "models").mkdir(parents=True, exist_ok=True)
    (out_dir / "runs").mkdir(parents=True, exist_ok=True)


def write_markdown(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def export_okf_bundle(
    *,
    preflight_dir: Path,
    out_dir: Path,
) -> list[Path]:
    evidence = load_preflight_evidence(preflight_dir)

    models = sorted(
        {
            str(row["model_id"]).strip()
            for row in evidence.observations
        }
    )
    providers = sorted(
        {row_provider(row) for row in evidence.observations}
    )
    model_slugs = stable_slug_map(models, "unknown-model")
    provider_slugs = stable_slug_map(providers, "unknown-provider")
    run_slug = slugify(evidence.run_id, "unknown-run")

    model_rows = {
        model: [
            row for row in evidence.observations
            if row["model_id"] == model
        ]
        for model in models
    }
    provider_models: dict[str, set[str]] = {
        provider: {
            str(row["model_id"])
            for row in evidence.observations
            if row_provider(row) == provider
        }
        for provider in providers
    }

    prepare_output_dir(out_dir)
    out_dir = out_dir.resolve()
    written: list[Path] = []
    base_tags = ("zth", "llm-probe", "preflight", "okf-export")

    index_path = out_dir / "index.md"
    index_body = [
        "# ZTH Model Preflight Bundle",
        "",
        "This optional bundle presents imported LLM-probe preflight evidence as "
        "linked Markdown concepts.",
        "",
        "It is preflight evidence only. The export is not an internal source of "
        "truth and does not promote or audition models.",
        "",
        "## Indexes",
        "",
        f"- {relative_markdown_link(label='Providers', target=out_dir / 'providers' / 'index.md', source_page=index_path)}",
        f"- {relative_markdown_link(label='Models', target=out_dir / 'models' / 'index.md', source_page=index_path)}",
        f"- {relative_markdown_link(label='Runs', target=out_dir / 'runs' / 'index.md', source_page=index_path)}",
    ]
    write_markdown(
        index_path,
        markdown_document(
            render_frontmatter(
                concept_type="ZTH Model Preflight Bundle",
                title=f"Model Preflight Bundle: {evidence.run_id}",
                description="Optional linked export of ZTH preflight evidence.",
                resource=f"zth://llm-probe-preflight/bundles/{run_slug}",
                tags=base_tags,
                timestamp=evidence.timestamp,
                evidence=evidence,
            ),
            index_body,
        ),
    )
    written.append(index_path)

    providers_index_path = out_dir / "providers" / "index.md"
    providers_body = ["# Providers", ""]
    if providers:
        for provider in providers:
            providers_body.append(
                "- "
                + relative_markdown_link(
                    label=provider,
                    target=out_dir / "providers" / f"{provider_slugs[provider]}.md",
                    source_page=providers_index_path,
                )
            )
    else:
        providers_body.append("No providers were observed in valid records.")
    write_markdown(
        providers_index_path,
        markdown_document(
            render_frontmatter(
                concept_type="ZTH Model Provider",
                title="Observed Model Providers",
                description="Index of providers observed in preflight evidence.",
                resource=f"zth://llm-probe-preflight/providers/{run_slug}",
                tags=(*base_tags, "provider-index"),
                timestamp=evidence.timestamp,
                evidence=evidence,
            ),
            providers_body,
        ),
    )
    written.append(providers_index_path)

    run_page = out_dir / "runs" / f"{run_slug}.md"
    for provider in providers:
        provider_slug = provider_slugs[provider]
        provider_path = out_dir / "providers" / f"{provider_slug}.md"
        body = [
            f"# Provider: {provider}",
            "",
            f"- Provider: `{provider}`",
            f"- Input format: `{evidence.input_format}`",
            "",
            "## Observed Models",
            "",
        ]
        for model in sorted(provider_models[provider]):
            body.append(
                "- "
                + relative_markdown_link(
                    label=model,
                    target=out_dir / "models" / f"{model_slugs[model]}.md",
                    source_page=provider_path,
                )
            )
        body.extend(
            [
                "",
                "## Runs",
                "",
                "- "
                + relative_markdown_link(
                    label=evidence.run_id,
                    target=run_page,
                    source_page=provider_path,
                ),
            ]
        )
        write_markdown(
            provider_path,
            markdown_document(
                render_frontmatter(
                    concept_type="ZTH Model Provider",
                    title=f"Model Provider: {provider}",
                    description="Provider observed in imported preflight evidence.",
                    resource=f"zth://llm-probe-preflight/providers/{provider_slug}",
                    tags=(*base_tags, "provider"),
                    timestamp=evidence.timestamp,
                    evidence=evidence,
                ),
                body,
            ),
        )
        written.append(provider_path)

    models_index_path = out_dir / "models" / "index.md"
    models_body = [
        "# Models",
        "",
        "| Model | Preflight status |",
        "|---|---|",
    ]
    for model in models:
        link = relative_markdown_link(
            label=model,
            target=out_dir / "models" / f"{model_slugs[model]}.md",
            source_page=models_index_path,
        )
        models_body.append(
            f"| {link} | `{conservative_status(model_rows[model])}` |"
        )
    if not models:
        models_body.append("| None observed | `unknown` |")
    write_markdown(
        models_index_path,
        markdown_document(
            render_frontmatter(
                concept_type="ZTH Model",
                title="Observed Models",
                description="Index of models observed in preflight evidence.",
                resource=f"zth://llm-probe-preflight/models/{run_slug}",
                tags=(*base_tags, "model-index"),
                timestamp=evidence.timestamp,
                evidence=evidence,
            ),
            models_body,
        ),
    )
    written.append(models_index_path)

    for model in models:
        model_slug = model_slugs[model]
        model_path = out_dir / "models" / f"{model_slug}.md"
        rows = model_rows[model]
        status_counts = Counter(str(row["status"]) for row in rows)
        model_providers = sorted({row_provider(row) for row in rows})
        body = [
            f"# Model: {model}",
            "",
            f"- Preflight status: `{conservative_status(rows)}`",
            "- This model was not promoted and was not auditioned by this export.",
            "",
            "## Providers",
            "",
        ]
        for provider in model_providers:
            body.append(
                "- "
                + relative_markdown_link(
                    label=provider,
                    target=out_dir / "providers" / f"{provider_slugs[provider]}.md",
                    source_page=model_path,
                )
            )
        body.extend(["", "## Observed Probes", ""])
        for probe_id in sorted({str(row["probe_id"]) for row in rows}):
            body.append(f"- `{probe_id}`")
        body.extend(["", "## Status Counts", ""])
        for status, count in sorted(status_counts.items()):
            body.append(f"- `{status}`: {count}")
        body.extend(
            [
                "",
                "## Run",
                "",
                "- "
                + relative_markdown_link(
                    label=evidence.run_id,
                    target=run_page,
                    source_page=model_path,
                ),
            ]
        )
        write_markdown(
            model_path,
            markdown_document(
                render_frontmatter(
                    concept_type="ZTH Model",
                    title=f"Model: {model}",
                    description="Model observed in imported preflight evidence.",
                    resource=f"zth://llm-probe-preflight/models/{model_slug}",
                    tags=(*base_tags, "model"),
                    timestamp=evidence.timestamp,
                    evidence=evidence,
                ),
                body,
            ),
        )
        written.append(model_path)

    runs_index_path = out_dir / "runs" / "index.md"
    runs_body = [
        "# Preflight Runs",
        "",
        "- "
        + relative_markdown_link(
            label=evidence.run_id,
            target=run_page,
            source_page=runs_index_path,
        ),
    ]
    write_markdown(
        runs_index_path,
        markdown_document(
            render_frontmatter(
                concept_type="ZTH Model Preflight Run",
                title="Imported Preflight Runs",
                description="Index of imported model preflight runs.",
                resource=f"zth://llm-probe-preflight/runs/{run_slug}/index",
                tags=(*base_tags, "run-index"),
                timestamp=evidence.timestamp,
                evidence=evidence,
            ),
            runs_body,
        ),
    )
    written.append(runs_index_path)

    evidence_links = [
        ("Import metadata", evidence.preflight_dir / "import_metadata.json"),
        (
            "Preflight capability manifest",
            evidence.preflight_dir / "preflight_capability_manifest.json",
        ),
        ("Preflight summary", evidence.preflight_dir / "preflight_summary.md"),
        ("Probe manifest", evidence.preflight_dir / "probe_manifest.jsonl"),
        ("Invalid records", evidence.preflight_dir / "invalid_records.jsonl"),
        ("Preserved source", evidence.source_path),
    ]
    run_body = [
        f"# Preflight Run: {evidence.run_id}",
        "",
        f"- Source run ID: `{evidence.run_id}`",
        f"- Source SHA-256: `{evidence.source_sha256}`",
        f"- Valid records: {len(evidence.observations)}",
        f"- Invalid records: {len(evidence.invalid_records)}",
        f"- Preflight status: `{evidence.preflight_status}`",
        "",
        "## Source Evidence",
        "",
    ]
    for label, target in evidence_links:
        run_body.append(
            "- "
            + relative_markdown_link(
                label=label,
                target=target,
                source_page=run_page,
            )
        )
    run_body.extend(
        [
            "",
            "## Probes by Model",
            "",
            "| Model | Probe | Status |",
            "|---|---|---|",
        ]
    )
    for row in sorted(
        evidence.observations,
        key=lambda item: (
            str(item["model_id"]),
            str(item["probe_id"]),
            str(item["status"]),
        ),
    ):
        model = str(row["model_id"])
        model_link = relative_markdown_link(
            label=model,
            target=out_dir / "models" / f"{model_slugs[model]}.md",
            source_page=run_page,
        )
        run_body.append(
            f"| {model_link} | `{row['probe_id']}` | `{row['status']}` |"
        )
    if not evidence.observations:
        run_body.append("| None observed | — | — |")
    write_markdown(
        run_page,
        markdown_document(
            render_frontmatter(
                concept_type="ZTH Model Preflight Run",
                title=f"Preflight Run: {evidence.run_id}",
                description="Imported preflight run and its source evidence.",
                resource=f"zth://llm-probe-preflight/runs/{run_slug}",
                tags=(*base_tags, "run"),
                timestamp=evidence.timestamp,
                evidence=evidence,
            ),
            run_body,
        ),
    )
    written.append(run_page)

    log_path = out_dir / "log.md"
    exported_at = utc_now_iso()
    log_body = [
        "# OKF Export Log",
        "",
        "This OKF-style bundle was exported from completed preflight evidence.",
        "",
        f"- Exported at: `{exported_at}`",
        f"- Source directory: `{evidence.preflight_dir}`",
        f"- Output contract version: `{EXPECTED_CONTRACT_VERSION}`",
        "- No promotion or model audition was performed.",
        "- This bundle is optional and is not the internal source of truth.",
    ]
    write_markdown(
        log_path,
        markdown_document(
            render_frontmatter(
                concept_type="ZTH Model Preflight Log",
                title=f"Preflight Export Log: {evidence.run_id}",
                description="Audit log for the optional OKF-style export.",
                resource=f"zth://llm-probe-preflight/logs/{run_slug}",
                tags=(*base_tags, "export-log"),
                timestamp=exported_at,
                evidence=evidence,
            ),
            log_body,
        ),
    )
    written.append(log_path)

    return sorted(written)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preflight-dir",
        required=True,
        help="Completed LLM-probe preflight import directory.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory that will receive the optional Markdown bundle.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        written = export_okf_bundle(
            preflight_dir=Path(args.preflight_dir),
            out_dir=Path(args.out_dir),
        )
    except (FileExistsError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(written)} OKF-style Markdown files.")
    print(f"Bundle index: {Path(args.out_dir) / 'index.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
