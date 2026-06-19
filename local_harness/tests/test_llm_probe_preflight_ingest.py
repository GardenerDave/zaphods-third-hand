from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_harness.llm_probe_preflight_ingest import (
    OUTPUT_CONTRACT_VERSION,
    ingest_probe_output,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "examples" / "llm_probe_preflight_fixture" / "results.json"
EXPECTED_FILES = {
    "source/results.json",
    "import_metadata.json",
    "probe_manifest.jsonl",
    "invalid_records.jsonl",
    "preflight_summary.json",
    "preflight_summary.md",
}
FORBIDDEN_FIELDS = {
    "audition_commands",
    "board_id",
    "capability_card",
    "metric_rankings",
    "model_registry",
    "rankings",
    "role_fit",
    "suite_scores",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def collect_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for nested in value.values():
            keys.update(collect_keys(nested))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for nested in value:
            keys.update(collect_keys(nested))
        return keys
    return set()


def test_import_writes_expected_plain_files_and_preserves_source(tmp_path: Path) -> None:
    out_dir = tmp_path / "preflight"

    ingest_probe_output(FIXTURE, out_dir)

    written_files = {
        path.relative_to(out_dir).as_posix()
        for path in out_dir.rglob("*")
        if path.is_file()
    }
    assert written_files == EXPECTED_FILES
    assert (out_dir / "source" / "results.json").read_bytes() == FIXTURE.read_bytes()


def test_source_sha256_and_contract_boundary_are_recorded(tmp_path: Path) -> None:
    out_dir = tmp_path / "preflight"
    expected_sha256 = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()

    summary = ingest_probe_output(FIXTURE, out_dir)
    metadata = read_json(out_dir / "import_metadata.json")

    assert metadata["source_sha256"] == expected_sha256
    assert summary["source_sha256"] == expected_sha256
    for payload in (metadata, summary):
        assert payload["output_contract_version"] == OUTPUT_CONTRACT_VERSION
        assert payload["scope"] == "preflight_only"
        assert payload["promotion_performed"] is False


def test_manifest_jsonl_is_valid_and_invalid_records_are_captured(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "preflight"

    ingest_probe_output(FIXTURE, out_dir)
    manifest = read_jsonl(out_dir / "probe_manifest.jsonl")
    invalid = read_jsonl(out_dir / "invalid_records.jsonl")

    assert len(manifest) == 3
    assert [row["source_index"] for row in manifest] == [1, 2, 3]
    assert {row["status"] for row in manifest} == {"pass", "warn", "fail"}
    assert all(row["scope"] == "preflight_only" for row in manifest)
    assert all(row["promotion_performed"] is False for row in manifest)

    assert len(invalid) == 2
    assert invalid[0]["source_index"] == 4
    assert "missing_field(s): probe_id" in invalid[0]["reasons"]
    assert invalid[1]["source_index"] == 5
    assert invalid[1]["reasons"] == ["record_is_not_object"]


def test_summary_contains_only_factual_counts_and_diagnostics(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "preflight"

    summary = ingest_probe_output(FIXTURE, out_dir)

    assert summary["input_record_count"] == 5
    assert summary["valid_record_count"] == 3
    assert summary["invalid_record_count"] == 2
    assert summary["model_count"] == 2
    assert summary["probe_count"] == 2
    assert summary["status_counts"] == {"fail": 1, "pass": 1, "warn": 1}
    assert summary["diagnostics"] == {
        "records_with_diagnostics": 2,
        "diagnostic_message_count": 2,
    }

    markdown = (out_dir / "preflight_summary.md").read_text(encoding="utf-8")
    assert "# LLM-Probe Preflight Import Summary" in markdown
    assert "Promotion performed: `false`" in markdown
    assert "No model was promoted." in markdown


def test_outputs_do_not_emit_audition_card_ranking_or_role_fields(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "preflight"

    ingest_probe_output(FIXTURE, out_dir)
    payloads: list[object] = [
        read_json(out_dir / "import_metadata.json"),
        read_json(out_dir / "preflight_summary.json"),
        *read_jsonl(out_dir / "probe_manifest.jsonl"),
        *read_jsonl(out_dir / "invalid_records.jsonl"),
    ]

    emitted_keys = set().union(*(collect_keys(payload) for payload in payloads))
    assert emitted_keys.isdisjoint(FORBIDDEN_FIELDS)
    assert not any("capability_card" in path.name for path in out_dir.rglob("*"))


def test_unknown_top_level_shape_fails_closed_without_outputs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "unknown.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": "llm_probe.results.v2",
                "run_id": "unknown-shape",
                "generated_at": "2026-06-19T12:00:00Z",
                "observations": [],
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "preflight"

    with pytest.raises(ValueError, match="unsupported schema_version"):
        ingest_probe_output(source, out_dir)

    assert not out_dir.exists()


def test_cli_writes_preflight_output(tmp_path: Path) -> None:
    out_dir = tmp_path / "preflight"

    exit_code = main(
        [
            "--probe-output",
            str(FIXTURE),
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    assert (out_dir / "preflight_summary.json").is_file()
