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
YAML_FIXTURE = (
    REPO_ROOT
    / "examples"
    / "llm_probe_preflight_fixture"
    / "verified-provider.yaml"
)
EXPECTED_FILES = {
    "source/results.json",
    "import_metadata.json",
    "probe_manifest.jsonl",
    "invalid_records.jsonl",
    "preflight_capability_manifest.json",
    "preflight_summary.json",
    "preflight_summary.md",
}
YAML_EXPECTED_FILES = {
    *EXPECTED_FILES - {"source/results.json"},
    "source/results.yaml",
}
FORBIDDEN_FIELDS = {
    "audition",
    "audition_commands",
    "audition_status",
    "board_id",
    "capability_card",
    "metric_rankings",
    "model_registry",
    "promoted_model_id",
    "promotion_status",
    "rank",
    "ranking",
    "rankings",
    "role_fit",
    "suite_scores",
}
CAPABILITY_MANIFEST_FIELDS = {
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


def write_probe_fixture(
    path: Path,
    observations: list[object],
    *,
    run_id: str = "synthetic-status-test",
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "llm_probe.results.v1",
                "run_id": run_id,
                "generated_at": "2026-06-19T12:00:00Z",
                "observations": observations,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def observation(status: str, index: int) -> dict:
    return {
        "model_id": f"synthetic-model-{index}",
        "probe_id": f"synthetic-probe-{index}",
        "status": status,
        "observed_value": status == "pass",
    }


def write_yaml_fixture(path: Path, payload: object) -> None:
    yaml = pytest.importorskip("yaml")
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


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
    assert read_json(out_dir / "import_metadata.json")["input_format"] == (
        "zth_normalized_json"
    )


def test_source_sha256_and_contract_boundary_are_recorded(tmp_path: Path) -> None:
    out_dir = tmp_path / "preflight"
    expected_sha256 = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()

    summary = ingest_probe_output(FIXTURE, out_dir)
    metadata = read_json(out_dir / "import_metadata.json")
    capability_manifest = read_json(
        out_dir / "preflight_capability_manifest.json"
    )

    assert metadata["source_sha256"] == expected_sha256
    assert summary["source_sha256"] == expected_sha256
    assert capability_manifest["source_sha256"] == expected_sha256
    for payload in (metadata, summary, capability_manifest):
        assert payload["output_contract_version"] == OUTPUT_CONTRACT_VERSION
        assert payload["scope"] == "preflight_only"
        assert payload["promotion_performed"] is False
    assert capability_manifest["requires_human_review"] is True


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
        read_json(out_dir / "preflight_capability_manifest.json"),
        *read_jsonl(out_dir / "probe_manifest.jsonl"),
        *read_jsonl(out_dir / "invalid_records.jsonl"),
    ]

    emitted_keys = set().union(*(collect_keys(payload) for payload in payloads))
    assert emitted_keys.isdisjoint(FORBIDDEN_FIELDS)
    assert not any("capability_card" in path.name for path in out_dir.rglob("*"))


def test_fixture_capability_manifest_records_fail_status_and_observed_ids(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "preflight"

    ingest_probe_output(FIXTURE, out_dir)
    manifest = read_json(out_dir / "preflight_capability_manifest.json")

    assert set(manifest) == CAPABILITY_MANIFEST_FIELDS
    assert manifest["source_run_id"] == "synthetic-preflight-001"
    assert manifest["input_format"] == "zth_normalized_json"
    assert manifest["input_schema_version"] == "llm_probe.results.v1"
    assert manifest["model_ids_observed"] == [
        "synthetic-model-a",
        "synthetic-model-b",
    ]
    assert manifest["probe_ids_observed"] == [
        "endpoint_response",
        "json_shape",
    ]
    assert manifest["status_counts"] == {"fail": 1, "pass": 1, "warn": 1}
    assert manifest["valid_record_count"] == 3
    assert manifest["invalid_record_count"] == 2
    assert manifest["preflight_status"] == "fail"


@pytest.mark.parametrize(
    ("statuses", "expected_status"),
    [
        (["pass", "pass"], "pass"),
        (["warn", "skipped"], "intermittent"),
    ],
)
def test_capability_manifest_conservative_non_failure_statuses(
    tmp_path: Path,
    statuses: list[str],
    expected_status: str,
) -> None:
    source = tmp_path / "results.json"
    write_probe_fixture(
        source,
        [observation(status, index) for index, status in enumerate(statuses, 1)],
    )
    out_dir = tmp_path / "preflight"

    ingest_probe_output(source, out_dir)
    manifest = read_json(out_dir / "preflight_capability_manifest.json")

    assert manifest["preflight_status"] == expected_status
    assert manifest["valid_record_count"] == len(statuses)


def test_capability_manifest_uses_unknown_when_there_are_no_valid_records(
    tmp_path: Path,
) -> None:
    source = tmp_path / "results.json"
    write_probe_fixture(source, [{"model_id": "missing-required-fields"}])
    out_dir = tmp_path / "preflight"

    ingest_probe_output(source, out_dir)
    manifest = read_json(out_dir / "preflight_capability_manifest.json")

    assert manifest["preflight_status"] == "unknown"
    assert manifest["valid_record_count"] == 0
    assert manifest["invalid_record_count"] == 1
    assert manifest["model_ids_observed"] == []
    assert manifest["probe_ids_observed"] == []
    assert manifest["status_counts"] == {}


def test_yaml_fixture_writes_expected_files_and_preserves_source(
    tmp_path: Path,
) -> None:
    pytest.importorskip("yaml")
    out_dir = tmp_path / "preflight"

    ingest_probe_output(YAML_FIXTURE, out_dir)

    written_files = {
        path.relative_to(out_dir).as_posix()
        for path in out_dir.rglob("*")
        if path.is_file()
    }
    assert written_files == YAML_EXPECTED_FILES
    assert (out_dir / "source" / "results.yaml").read_bytes() == (
        YAML_FIXTURE.read_bytes()
    )
    assert not (out_dir / "source" / "results.json").exists()


def test_yaml_fixture_records_source_identity_and_normalized_observations(
    tmp_path: Path,
) -> None:
    pytest.importorskip("yaml")
    out_dir = tmp_path / "preflight"
    expected_sha256 = hashlib.sha256(YAML_FIXTURE.read_bytes()).hexdigest()

    ingest_probe_output(YAML_FIXTURE, out_dir)
    metadata = read_json(out_dir / "import_metadata.json")
    summary = read_json(out_dir / "preflight_summary.json")
    capability_manifest = read_json(
        out_dir / "preflight_capability_manifest.json"
    )
    rows = read_jsonl(out_dir / "probe_manifest.jsonl")

    for payload in (metadata, summary, capability_manifest):
        assert payload["input_format"] == "llm_probe_verified_yaml"
        assert payload["input_schema_version"] == "llm_probe.verified_yaml.v1"
        assert payload["source_sha256"] == expected_sha256
        assert payload["scope"] == "preflight_only"
        assert payload["promotion_performed"] is False

    assert metadata["preserved_source_path"] == "source/results.yaml"
    assert capability_manifest["source_run_id"] == (
        "synthetic-provider-2026-03-31"
    )
    assert capability_manifest["preflight_status"] == "fail"
    assert capability_manifest["requires_human_review"] is True
    assert len(rows) == 7
    assert {row["model_id"] for row in rows} == {
        "synthetic-all-pass-model",
        "synthetic-mixed-model",
    }
    failed = next(row for row in rows if row["probe_id"] == "system_prompt")
    assert failed["status"] == "fail"
    assert failed["observed_value"]["passed"] is False
    assert failed["observed_value"]["provider"] == "synthetic-provider"
    assert failed["metadata"] == {
        "source_format": "llm_probe_verified_yaml",
        "provider": "synthetic-provider",
        "last_run": "2026-03-31",
    }


def test_all_pass_yaml_yields_pass_preflight_status(tmp_path: Path) -> None:
    source = tmp_path / "verified.yaml"
    write_yaml_fixture(
        source,
        {
            "provider": "synthetic-pass-provider",
            "last_run": "2026-04-01",
            "models": [
                {
                    "id": "synthetic-pass-model",
                    "tool_call": "pass",
                    "think_blocks": "none",
                    "avg_response_ms": 100,
                    "tests": {
                        "tool_call_basic": {
                            "passed": True,
                            "pass_rate": "3/3",
                        },
                        "tool_call_large": {
                            "passed": True,
                            "pass_rate": "3/3",
                        },
                    },
                    "last_tested": "2026-04-01",
                }
            ],
        },
    )
    out_dir = tmp_path / "preflight"

    ingest_probe_output(source, out_dir)
    manifest = read_json(out_dir / "preflight_capability_manifest.json")

    assert manifest["preflight_status"] == "pass"
    assert manifest["status_counts"] == {"pass": 2}


@pytest.mark.parametrize(
    ("source_text", "expected_error"),
    [
        ("provider: broken\nmodels: [unterminated\n", "not valid YAML"),
        ("provider: missing-models\nlast_run: '2026-04-01'\n", "missing required"),
    ],
)
def test_invalid_yaml_shapes_fail_closed_without_outputs(
    tmp_path: Path,
    source_text: str,
    expected_error: str,
) -> None:
    pytest.importorskip("yaml")
    source = tmp_path / "verified.yaml"
    source.write_text(source_text, encoding="utf-8")
    out_dir = tmp_path / "preflight"

    with pytest.raises(ValueError, match=expected_error):
        ingest_probe_output(source, out_dir)

    assert not out_dir.exists()


def test_malformed_yaml_model_and_test_entries_are_invalid_records(
    tmp_path: Path,
) -> None:
    source = tmp_path / "verified.yaml"
    write_yaml_fixture(
        source,
        {
            "provider": "synthetic-invalid-provider",
            "last_run": "2026-04-01",
            "models": [
                {
                    "id": "synthetic-model",
                    "tests": {
                        "not_an_object": "broken",
                        "missing_passed": {"pass_rate": "0/3"},
                    },
                },
                {
                    "tests": {
                        "missing_model_id": {
                            "passed": True,
                            "pass_rate": "3/3",
                        }
                    }
                },
                "not-a-model-object",
            ],
        },
    )
    out_dir = tmp_path / "preflight"

    ingest_probe_output(source, out_dir)
    invalid_rows = read_jsonl(out_dir / "invalid_records.jsonl")
    manifest = read_json(out_dir / "preflight_capability_manifest.json")

    assert len(invalid_rows) == 4
    reasons = {
        reason
        for row in invalid_rows
        for reason in row["reasons"]
    }
    assert "test_result_is_not_object" in reasons
    assert "missing_field(s): passed" in reasons
    assert "model_id_missing_or_empty" in reasons
    assert "model_is_not_object" in reasons
    assert manifest["valid_record_count"] == 0
    assert manifest["invalid_record_count"] == 4
    assert manifest["preflight_status"] == "unknown"


def test_yaml_outputs_do_not_emit_audition_or_selection_fields(
    tmp_path: Path,
) -> None:
    pytest.importorskip("yaml")
    out_dir = tmp_path / "preflight"

    ingest_probe_output(YAML_FIXTURE, out_dir)
    payloads: list[object] = [
        read_json(out_dir / "import_metadata.json"),
        read_json(out_dir / "preflight_summary.json"),
        read_json(out_dir / "preflight_capability_manifest.json"),
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


def test_cli_accepts_explicit_yaml_input_format(tmp_path: Path) -> None:
    pytest.importorskip("yaml")
    out_dir = tmp_path / "preflight"

    exit_code = main(
        [
            "--probe-output",
            str(YAML_FIXTURE),
            "--input-format",
            "llm-probe-yaml",
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    assert (out_dir / "source" / "results.yaml").is_file()
