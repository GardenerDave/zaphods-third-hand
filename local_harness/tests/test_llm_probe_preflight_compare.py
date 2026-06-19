from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_harness.llm_probe_preflight_compare import (
    OUTPUT_CONTRACT_VERSION,
    compare_preflight_manifests,
    main,
)


FIXED_TIMESTAMP = "2026-06-19T12:00:00Z"
EXPECTED_FILES = {
    "source/previous_preflight_capability_manifest.json",
    "source/latest_preflight_capability_manifest.json",
    "preflight_comparison.json",
    "preflight_comparison.md",
}
FORBIDDEN_FIELDS = {
    "audition",
    "audition_status",
    "capability_card",
    "metric_rankings",
    "model_registry",
    "promoted_model_id",
    "promotion_status",
    "rank",
    "ranking",
    "rankings",
    "role_fit",
    "role_assignment",
    "suite_scores",
}


def default_counts(status: str) -> dict[str, int]:
    return {
        "pass": {"pass": 2},
        "intermittent": {"pass": 1, "warn": 1},
        "fail": {"fail": 1, "pass": 1},
        "unknown": {},
    }[status]


def make_manifest(
    status: str,
    *,
    run_id: str = "synthetic-run",
    source_sha256: str = "a" * 64,
    status_counts: dict[str, int] | None = None,
    valid_record_count: int | None = None,
    invalid_record_count: int = 0,
    model_ids: list[str] | None = None,
    probe_ids: list[str] | None = None,
    input_format: str = "zth_normalized_json",
    input_schema_version: str = "llm_probe.results.v1",
) -> dict:
    counts = default_counts(status) if status_counts is None else status_counts
    valid_count = (
        sum(counts.values())
        if valid_record_count is None
        else valid_record_count
    )
    return {
        "output_contract_version": "zth.llm_probe_preflight.v0.1",
        "scope": "preflight_only",
        "promotion_performed": False,
        "requires_human_review": True,
        "source_sha256": source_sha256,
        "source_run_id": run_id,
        "input_format": input_format,
        "input_schema_version": input_schema_version,
        "model_ids_observed": (
            ["synthetic-model"] if model_ids is None else model_ids
        ),
        "probe_ids_observed": (
            ["synthetic-probe"] if probe_ids is None else probe_ids
        ),
        "status_counts": counts,
        "valid_record_count": valid_count,
        "invalid_record_count": invalid_record_count,
        "preflight_status": status,
    }


def write_manifest(path: Path, payload: object, *, compact: bool = False) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(payload, separators=(",", ":"))
        if compact
        else json.dumps(payload, indent=2)
    ) + "\n"
    source_bytes = text.encode("utf-8")
    path.write_bytes(source_bytes)
    return source_bytes


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_comparison(
    tmp_path: Path,
    previous: dict,
    latest: dict,
    *,
    out_name: str = "comparison",
) -> tuple[dict, Path, Path, Path]:
    previous_path = tmp_path / f"{out_name}-previous.json"
    latest_path = tmp_path / f"{out_name}-latest.json"
    write_manifest(previous_path, previous)
    write_manifest(latest_path, latest)
    out_dir = tmp_path / out_name
    comparison = compare_preflight_manifests(
        previous_manifest=previous_path,
        latest_manifest=latest_path,
        out_dir=out_dir,
        generated_at=FIXED_TIMESTAMP,
    )
    return comparison, previous_path, latest_path, out_dir


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


@pytest.mark.parametrize(
    ("previous_status", "latest_status", "classification", "reason"),
    [
        ("pass", "fail", "regression", "pass_to_fail"),
        ("pass", "intermittent", "regression", "pass_to_intermittent"),
        ("intermittent", "fail", "regression", "intermittent_to_fail"),
        ("fail", "pass", "improvement", "fail_to_pass"),
        ("fail", "intermittent", "improvement", "fail_to_intermittent"),
        ("intermittent", "pass", "improvement", "intermittent_to_pass"),
        ("unknown", "pass", "resolved_unknown", "unknown_to_pass"),
        ("unknown", "fail", "resolved_unknown", "unknown_to_fail"),
        ("pass", "pass", "unchanged", "pass_unchanged"),
        ("fail", "unknown", "regression", "fail_to_unknown"),
    ],
)
def test_status_transition_classification(
    tmp_path: Path,
    previous_status: str,
    latest_status: str,
    classification: str,
    reason: str,
) -> None:
    comparison, _, _, _ = run_comparison(
        tmp_path,
        make_manifest(previous_status),
        make_manifest(latest_status, source_sha256="b" * 64),
    )

    assert comparison["status_transition"] == {
        "previous": previous_status,
        "latest": latest_status,
        "changed": previous_status != latest_status,
        "classification": classification,
        "reason": reason,
    }
    assert comparison["requires_human_review"] is True
    if classification == "resolved_unknown":
        assert "evidence completeness" in comparison["review_reasons"][0]
        assert "not necessarily improved model capability" in (
            comparison["review_reasons"][0]
        )


def test_writes_expected_plain_files_and_contract(tmp_path: Path) -> None:
    comparison, _, _, out_dir = run_comparison(
        tmp_path,
        make_manifest("pass"),
        make_manifest("fail", source_sha256="b" * 64),
    )

    written = {
        path.relative_to(out_dir).as_posix()
        for path in out_dir.rglob("*")
        if path.is_file()
    }
    assert written == EXPECTED_FILES
    assert comparison["output_contract_version"] == OUTPUT_CONTRACT_VERSION
    assert comparison["scope"] == "preflight_comparison_only"
    assert comparison["promotion_performed"] is False
    assert comparison["requires_human_review"] is True
    assert comparison["generated_at"] == FIXED_TIMESTAMP

    markdown = (out_dir / "preflight_comparison.md").read_text(encoding="utf-8")
    assert "# LLM-Probe Preflight Regression Comparison" in markdown
    assert "no ranking" in markdown
    assert "no model audition" in markdown
    assert "no model promotion" in markdown
    assert "no lifecycle authorization" in markdown
    assert "no production-readiness claim" in markdown
    assert "cannot identify per-model/per-probe status transitions" in markdown


def test_unchanged_status_can_have_aggregate_count_changes(tmp_path: Path) -> None:
    comparison, _, _, _ = run_comparison(
        tmp_path,
        make_manifest("pass", status_counts={"pass": 2}),
        make_manifest(
            "pass",
            source_sha256="b" * 64,
            status_counts={"pass": 3},
        ),
    )

    assert comparison["status_transition"]["classification"] == "unchanged"
    assert comparison["status_count_changes"]["pass"] == {
        "previous": 2,
        "latest": 3,
        "delta": 1,
    }
    assert "Aggregate observation status counts changed." in (
        comparison["review_reasons"]
    )


def test_reports_added_removed_and_unchanged_model_and_probe_ids(
    tmp_path: Path,
) -> None:
    comparison, _, _, _ = run_comparison(
        tmp_path,
        make_manifest(
            "pass",
            model_ids=["model-a", "model-shared"],
            probe_ids=["probe-a", "probe-shared"],
        ),
        make_manifest(
            "pass",
            source_sha256="b" * 64,
            model_ids=["model-b", "model-shared"],
            probe_ids=["probe-b", "probe-shared"],
        ),
    )

    assert comparison["model_id_changes"] == {
        "added": ["model-b"],
        "removed": ["model-a"],
        "unchanged": ["model-shared"],
    }
    assert comparison["probe_id_changes"] == {
        "added": ["probe-b"],
        "removed": ["probe-a"],
        "unchanged": ["probe-shared"],
    }


@pytest.mark.parametrize(
    ("unsafe_character", "markdown_escape"),
    [
        ("|", "&#124;"),
        ("`", "&#96;"),
        ("\n", r"\n"),
        ("\r", r"\r"),
    ],
)
def test_manifest_strings_are_markdown_safe_without_changing_json_values(
    tmp_path: Path,
    unsafe_character: str,
    markdown_escape: str,
) -> None:
    run_id = f"run{unsafe_character}id"
    input_format = f"format{unsafe_character}name"
    input_schema_version = f"schema{unsafe_character}version"
    model_id = f"model{unsafe_character}id"
    probe_id = f"probe{unsafe_character}id"
    manifest = make_manifest(
        "pass",
        run_id=run_id,
        model_ids=[model_id],
        probe_ids=[probe_id],
        input_format=input_format,
        input_schema_version=input_schema_version,
    )

    comparison, _, _, out_dir = run_comparison(
        tmp_path,
        manifest,
        manifest,
    )
    written = read_json(out_dir / "preflight_comparison.json")

    for payload in (comparison, written):
        assert payload["inputs"]["previous"]["source_run_id"] == run_id
        assert payload["inputs"]["previous"]["input_format"] == input_format
        assert payload["inputs"]["previous"]["input_schema_version"] == (
            input_schema_version
        )
        assert payload["model_id_changes"]["unchanged"] == [model_id]
        assert payload["probe_id_changes"]["unchanged"] == [probe_id]

    markdown = (out_dir / "preflight_comparison.md").read_text(encoding="utf-8")
    for prefix, suffix in (
        ("run", "id"),
        ("format", "name"),
        ("schema", "version"),
        ("model", "id"),
        ("probe", "id"),
    ):
        assert f"<code>{prefix}{markdown_escape}{suffix}</code>" in markdown
        assert f"{prefix}{unsafe_character}{suffix}" not in markdown

    previous_row = next(
        line for line in markdown.splitlines() if line.startswith("| Previous |")
    )
    assert previous_row.count("|") == 7


def test_same_run_id_and_source_hash_are_recorded_as_unchanged(
    tmp_path: Path,
) -> None:
    comparison, _, _, _ = run_comparison(
        tmp_path,
        make_manifest("pass", run_id="same-run", source_sha256="a" * 64),
        make_manifest("pass", run_id="same-run", source_sha256="a" * 64),
    )

    differences = comparison["input_differences"]
    assert differences["source_run_id_changed"] is False
    assert differences["source_sha256_changed"] is False
    assert differences["same_run_id_different_source_sha256"] is False


def test_same_run_id_with_different_source_hash_requires_review(
    tmp_path: Path,
) -> None:
    comparison, _, _, _ = run_comparison(
        tmp_path,
        make_manifest("pass", run_id="same-run", source_sha256="a" * 64),
        make_manifest("pass", run_id="same-run", source_sha256="b" * 64),
    )

    assert comparison["input_differences"][
        "same_run_id_different_source_sha256"
    ] is True
    assert any(
        "same source run ID" in reason
        for reason in comparison["review_reasons"]
    )


def test_source_manifests_are_preserved_byte_for_byte_and_hashed(
    tmp_path: Path,
) -> None:
    previous_path = tmp_path / "previous.json"
    latest_path = tmp_path / "latest.json"
    previous_bytes = write_manifest(
        previous_path,
        make_manifest("pass"),
        compact=True,
    )
    latest_bytes = write_manifest(
        latest_path,
        make_manifest("fail", source_sha256="b" * 64),
    )
    out_dir = tmp_path / "comparison"

    comparison = compare_preflight_manifests(
        previous_manifest=previous_path,
        latest_manifest=latest_path,
        out_dir=out_dir,
        generated_at=FIXED_TIMESTAMP,
    )

    preserved_previous = (
        out_dir / "source" / "previous_preflight_capability_manifest.json"
    )
    preserved_latest = (
        out_dir / "source" / "latest_preflight_capability_manifest.json"
    )
    assert preserved_previous.read_bytes() == previous_bytes
    assert preserved_latest.read_bytes() == latest_bytes
    assert comparison["inputs"]["previous"]["manifest_sha256"] == (
        hashlib.sha256(previous_bytes).hexdigest()
    )
    assert comparison["inputs"]["latest"]["manifest_sha256"] == (
        hashlib.sha256(latest_bytes).hexdigest()
    )
    assert "previous.json" not in json.dumps(comparison)
    assert str(tmp_path) not in json.dumps(comparison)


def test_output_is_deterministic_for_fixed_inputs_and_timestamp(
    tmp_path: Path,
) -> None:
    previous = make_manifest(
        "intermittent",
        model_ids=["model-z", "model-a"],
        probe_ids=["probe-z", "probe-a"],
    )
    latest = make_manifest(
        "pass",
        source_sha256="b" * 64,
        model_ids=["model-a", "model-b"],
        probe_ids=["probe-a", "probe-b"],
    )
    first, _, _, first_out = run_comparison(
        tmp_path,
        previous,
        latest,
        out_name="first",
    )
    second, _, _, second_out = run_comparison(
        tmp_path,
        previous,
        latest,
        out_name="second",
    )

    assert first == second
    assert (
        first_out / "preflight_comparison.json"
    ).read_bytes() == (
        second_out / "preflight_comparison.json"
    ).read_bytes()
    assert (
        first_out / "preflight_comparison.md"
    ).read_bytes() == (
        second_out / "preflight_comparison.md"
    ).read_bytes()
    assert first["model_id_changes"]["unchanged"] == ["model-a"]
    assert list(first["status_count_changes"]) == [
        "error",
        "fail",
        "pass",
        "skipped",
        "warn",
    ]


def test_output_does_not_emit_selection_or_audition_fields(
    tmp_path: Path,
) -> None:
    comparison, _, _, _ = run_comparison(
        tmp_path,
        make_manifest("pass"),
        make_manifest("fail", source_sha256="b" * 64),
    )

    emitted_keys = collect_keys(comparison)
    assert emitted_keys.isdisjoint(FORBIDDEN_FIELDS)
    assert set(key for key in emitted_keys if "promotion" in key) == {
        "promotion_performed"
    }


@pytest.mark.parametrize(
    ("mutation", "error_match"),
    [
        (
            lambda manifest: manifest.update(
                output_contract_version="zth.llm_probe_preflight.v9"
            ),
            "unsupported output_contract_version",
        ),
        (
            lambda manifest: manifest.update(scope="wrong_scope"),
            "must have scope",
        ),
        (
            lambda manifest: manifest.update(promotion_performed=True),
            "promotion_performed as false",
        ),
        (
            lambda manifest: manifest.update(requires_human_review=False),
            "requires_human_review as true",
        ),
        (
            lambda manifest: manifest.update(preflight_status="unexpected"),
            "preflight_status must be one of",
        ),
        (
            lambda manifest: manifest.update(status_counts={"pass": -1}),
            "non-negative integer",
        ),
        (
            lambda manifest: manifest.update(status_counts={"pass": True}),
            "non-negative integer",
        ),
        (
            lambda manifest: manifest.update(valid_record_count=99),
            "must sum to valid_record_count",
        ),
        (
            lambda manifest: manifest.update(
                model_ids_observed=["duplicate", "duplicate"]
            ),
            "must contain unique values",
        ),
        (
            lambda manifest: manifest.update(
                probe_ids_observed=["duplicate", "duplicate"]
            ),
            "must contain unique values",
        ),
    ],
)
def test_invalid_manifest_shapes_fail_closed(
    tmp_path: Path,
    mutation,
    error_match: str,
) -> None:
    previous = make_manifest("pass")
    mutation(previous)
    previous_path = tmp_path / "previous.json"
    latest_path = tmp_path / "latest.json"
    write_manifest(previous_path, previous)
    write_manifest(latest_path, make_manifest("pass"))
    out_dir = tmp_path / "comparison"

    with pytest.raises(ValueError, match=error_match):
        compare_preflight_manifests(
            previous_manifest=previous_path,
            latest_manifest=latest_path,
            out_dir=out_dir,
        )

    assert not out_dir.exists()


def test_invalid_json_fails_closed(tmp_path: Path) -> None:
    previous_path = tmp_path / "previous.json"
    latest_path = tmp_path / "latest.json"
    previous_path.write_text("{not json\n", encoding="utf-8")
    write_manifest(latest_path, make_manifest("pass"))
    out_dir = tmp_path / "comparison"

    with pytest.raises(ValueError, match="not valid JSON"):
        compare_preflight_manifests(
            previous_manifest=previous_path,
            latest_manifest=latest_path,
            out_dir=out_dir,
        )

    assert not out_dir.exists()


def test_missing_manifest_fails_closed(tmp_path: Path) -> None:
    latest_path = tmp_path / "latest.json"
    write_manifest(latest_path, make_manifest("pass"))
    out_dir = tmp_path / "comparison"

    with pytest.raises(ValueError, match="is not a file"):
        compare_preflight_manifests(
            previous_manifest=tmp_path / "missing.json",
            latest_manifest=latest_path,
            out_dir=out_dir,
        )

    assert not out_dir.exists()


def test_existing_nonempty_output_directory_fails_closed(tmp_path: Path) -> None:
    previous_path = tmp_path / "previous.json"
    latest_path = tmp_path / "latest.json"
    write_manifest(previous_path, make_manifest("pass"))
    write_manifest(latest_path, make_manifest("pass"))
    out_dir = tmp_path / "comparison"
    out_dir.mkdir()
    marker = out_dir / "keep.txt"
    marker.write_text("existing evidence\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="non-empty"):
        compare_preflight_manifests(
            previous_manifest=previous_path,
            latest_manifest=latest_path,
            out_dir=out_dir,
        )

    assert marker.read_text(encoding="utf-8") == "existing evidence\n"
    assert not (out_dir / "preflight_comparison.json").exists()


def test_cli_writes_comparison_bundle(tmp_path: Path) -> None:
    previous_path = tmp_path / "previous.json"
    latest_path = tmp_path / "latest.json"
    write_manifest(previous_path, make_manifest("pass"))
    write_manifest(
        latest_path,
        make_manifest("fail", source_sha256="b" * 64),
    )
    out_dir = tmp_path / "comparison"

    exit_code = main(
        [
            "--previous-manifest",
            str(previous_path),
            "--latest-manifest",
            str(latest_path),
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    assert (out_dir / "preflight_comparison.json").is_file()
    assert (out_dir / "preflight_comparison.md").is_file()
