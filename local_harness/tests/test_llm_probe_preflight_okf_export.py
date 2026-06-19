from __future__ import annotations

import re
from pathlib import Path

import pytest

from local_harness.llm_probe_preflight_ingest import ingest_probe_output
from local_harness.llm_probe_preflight_okf_export import (
    export_okf_bundle,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
YAML_FIXTURE = (
    REPO_ROOT
    / "examples"
    / "llm_probe_preflight_fixture"
    / "verified-provider.yaml"
)
EXPECTED_MARKDOWN_FILES = {
    "index.md",
    "log.md",
    "providers/index.md",
    "providers/synthetic-provider.md",
    "models/index.md",
    "models/synthetic-all-pass-model.md",
    "models/synthetic-mixed-model.md",
    "runs/index.md",
    "runs/synthetic-provider-2026-03-31.md",
}
REQUIRED_FRONTMATTER_FIELDS = {
    "type",
    "title",
    "description",
    "resource",
    "tags",
    "timestamp",
    "zth",
}
FORBIDDEN_FRONTMATTER_FIELDS = {
    "audition",
    "audition_status",
    "capability_card",
    "metric_rankings",
    "promoted_model_id",
    "promotion_status",
    "rank",
    "ranking",
    "rankings",
    "role_fit",
    "suite_scores",
}
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def build_yaml_preflight(tmp_path: Path) -> Path:
    pytest.importorskip("yaml")
    preflight_dir = tmp_path / "preflight"
    ingest_probe_output(
        YAML_FIXTURE,
        preflight_dir,
        input_format="llm-probe-yaml",
    )
    return preflight_dir


def parse_markdown(path: Path) -> tuple[dict, str]:
    yaml = pytest.importorskip("yaml")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    parts = text.split("---", 2)
    assert len(parts) == 3
    frontmatter = yaml.safe_load(parts[1])
    assert isinstance(frontmatter, dict)
    return frontmatter, parts[2]


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


def test_export_writes_expected_markdown_tree(tmp_path: Path) -> None:
    preflight_dir = build_yaml_preflight(tmp_path)
    out_dir = tmp_path / "okf" / "model-preflight"

    written = export_okf_bundle(
        preflight_dir=preflight_dir,
        out_dir=out_dir,
    )

    relative_written = {
        path.relative_to(out_dir).as_posix()
        for path in written
    }
    actual_files = {
        path.relative_to(out_dir).as_posix()
        for path in out_dir.rglob("*.md")
    }
    assert relative_written == EXPECTED_MARKDOWN_FILES
    assert actual_files == EXPECTED_MARKDOWN_FILES


def test_every_markdown_file_has_required_frontmatter_and_zth_boundary(
    tmp_path: Path,
) -> None:
    preflight_dir = build_yaml_preflight(tmp_path)
    out_dir = tmp_path / "okf" / "model-preflight"
    export_okf_bundle(preflight_dir=preflight_dir, out_dir=out_dir)

    for path in out_dir.rglob("*.md"):
        frontmatter, _ = parse_markdown(path)
        assert REQUIRED_FRONTMATTER_FIELDS.issubset(frontmatter)
        assert isinstance(frontmatter["type"], str)
        assert frontmatter["title"]
        assert frontmatter["description"]
        assert frontmatter["resource"].startswith("zth://")
        assert isinstance(frontmatter["tags"], list)
        assert frontmatter["timestamp"]
        assert frontmatter["zth"]["scope"] == "preflight_only"
        assert frontmatter["zth"]["promotion_performed"] is False
        assert frontmatter["zth"]["requires_human_review"] is True


def test_bundle_content_links_concepts_and_preserves_model_boundary(
    tmp_path: Path,
) -> None:
    preflight_dir = build_yaml_preflight(tmp_path)
    out_dir = tmp_path / "okf" / "model-preflight"
    export_okf_bundle(preflight_dir=preflight_dir, out_dir=out_dir)

    index = (out_dir / "index.md").read_text(encoding="utf-8")
    assert "[Providers](providers/index.md)" in index
    assert "[Models](models/index.md)" in index
    assert "[Runs](runs/index.md)" in index
    assert "preflight evidence only" in index

    model_page = (
        out_dir / "models" / "synthetic-mixed-model.md"
    ).read_text(encoding="utf-8")
    assert "not promoted and was not auditioned" in model_page
    assert "`system_prompt`" in model_page
    assert "`fail`: 1" in model_page

    provider_page = (
        out_dir / "providers" / "synthetic-provider.md"
    ).read_text(encoding="utf-8")
    assert "Input format: `llm_probe_verified_yaml`" in provider_page
    assert "../models/synthetic-all-pass-model.md" in provider_page
    assert "../runs/synthetic-provider-2026-03-31.md" in provider_page

    run_page = (
        out_dir / "runs" / "synthetic-provider-2026-03-31.md"
    ).read_text(encoding="utf-8")
    assert "Valid records: 7" in run_page
    assert "Invalid records: 0" in run_page
    assert "Preflight status: `fail`" in run_page
    assert "Source SHA-256:" in run_page
    assert "source/results.yaml" in run_page
    assert "| Model | Probe | Status |" in run_page


def test_all_markdown_links_are_relative(tmp_path: Path) -> None:
    preflight_dir = build_yaml_preflight(tmp_path)
    out_dir = tmp_path / "okf" / "model-preflight"
    export_okf_bundle(preflight_dir=preflight_dir, out_dir=out_dir)

    links: list[str] = []
    for path in out_dir.rglob("*.md"):
        _, body = parse_markdown(path)
        links.extend(MARKDOWN_LINK_RE.findall(body))

    assert links
    assert all("://" not in link for link in links)
    assert all(not Path(link).is_absolute() for link in links)


def test_frontmatter_does_not_emit_selection_or_audition_fields(
    tmp_path: Path,
) -> None:
    preflight_dir = build_yaml_preflight(tmp_path)
    out_dir = tmp_path / "okf" / "model-preflight"
    export_okf_bundle(preflight_dir=preflight_dir, out_dir=out_dir)

    emitted_keys: set[str] = set()
    for path in out_dir.rglob("*.md"):
        frontmatter, _ = parse_markdown(path)
        emitted_keys.update(collect_keys(frontmatter))

    assert emitted_keys.isdisjoint(FORBIDDEN_FRONTMATTER_FIELDS)
    assert not any("capability_card" in path.name for path in out_dir.rglob("*"))


def test_export_fails_closed_when_required_preflight_file_is_missing(
    tmp_path: Path,
) -> None:
    preflight_dir = build_yaml_preflight(tmp_path)
    (preflight_dir / "preflight_summary.json").unlink()
    out_dir = tmp_path / "okf" / "model-preflight"

    with pytest.raises(ValueError, match="missing required file"):
        export_okf_bundle(preflight_dir=preflight_dir, out_dir=out_dir)

    assert not out_dir.exists()


def test_cli_exports_bundle(tmp_path: Path) -> None:
    preflight_dir = build_yaml_preflight(tmp_path)
    out_dir = tmp_path / "okf" / "model-preflight"

    exit_code = main(
        [
            "--preflight-dir",
            str(preflight_dir),
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    assert (out_dir / "index.md").is_file()
    assert (out_dir / "log.md").is_file()
