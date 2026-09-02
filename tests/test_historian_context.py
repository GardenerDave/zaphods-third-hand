from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from local_harness.historian_context import (
    HISTORIAN_CONTEXT_SCHEMA,
    HistorianContextError,
    bind_historian_context,
    render_historian_context_markdown,
    resolve_record_path,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "historian_context.py"

QUERY_ID = "op-11111111-2222-3333-4444-555555555555"
CITED_RECORDS = {
    "CLM-example-gap": "claim",
    "REV-example-separation": "revision",
}


def _write_record(records_dir: Path, record_id: str, kind: str) -> Path:
    kind_dir = records_dir / f"{kind}s"
    kind_dir.mkdir(parents=True, exist_ok=True)
    path = kind_dir / f"{record_id}.md"
    path.write_text(
        "---\n"
        f"id: {record_id}\n"
        f"kind: {kind}\n"
        "---\n"
        "\n"
        f"Body text for {record_id}.\n",
        encoding="utf-8",
    )
    return path


def _make_records_dir(tmp_path: Path) -> Path:
    records_dir = tmp_path / "records"
    records_dir.mkdir(exist_ok=True)
    for record_id, kind in CITED_RECORDS.items():
        _write_record(records_dir, record_id, kind)
    return records_dir


def _make_query_dir(
    tmp_path: Path,
    *,
    parsed_response: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    retrieval: dict[str, Any] | None = None,
    include_transaction: bool = True,
) -> Path:
    query_dir = tmp_path / "queries" / QUERY_ID
    reasoner_dir = query_dir / "reasoner"
    reasoner_dir.mkdir(parents=True, exist_ok=True)
    query_dir.joinpath("query.json").write_text(
        json.dumps([{"id": QUERY_ID, "question": "What remains unresolved?"}]) + "\n",
        encoding="utf-8",
    )
    result = {
        "query_id": QUERY_ID,
        "question": "What remains unresolved?",
        "parsed_response": parsed_response
        or {
            "answer": "The downstream completion join remains unresolved.",
            "cited_record_ids": sorted(CITED_RECORDS),
            "evidence_used": sorted(CITED_RECORDS),
            "uncertainty_or_limitations": "The answer is advisory only.",
            "contradictions_or_missing_evidence": ["No broader capability claim is supported."],
        },
        "validation": validation
        or {
            "schema_valid": {"valid": True, "errors": []},
            "grounding_valid": {"valid": True, "errors": []},
            "contract_valid": True,
        },
    }
    result_path = reasoner_dir / f"{QUERY_ID}.result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if retrieval is None:
        retrieval = {
            "document_count": 2,
            "corpus_fingerprint": "f" * 64,
            "revision": "a" * 40,
        }
    if retrieval is not False:
        query_dir.joinpath("retrieval.json").write_text(
            json.dumps(retrieval, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if include_transaction:
        reasoner_dir.joinpath(f"{QUERY_ID}.transaction.json").write_text(
            json.dumps({"query_id": QUERY_ID, "state": "COMPLETE"}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return query_dir


def _bind(tmp_path: Path, *, query_dir: Path | None = None, records_dir: Path | None = None, out_dir: Path | None = None, overwrite: bool = False) -> dict[str, Any]:
    return bind_historian_context(
        query_dir=query_dir or _make_query_dir(tmp_path),
        records_dir=records_dir or _make_records_dir(tmp_path),
        output_dir=out_dir or (tmp_path / "context_out"),
        overwrite=overwrite,
    )


def test_bind_writes_validated_context_artifacts(tmp_path: Path) -> None:
    records_dir = _make_records_dir(tmp_path)
    result = _bind(tmp_path, records_dir=records_dir)

    context_path = Path(result["historian_context_path"])
    markdown_path = Path(result["historian_context_markdown_path"])
    assert context_path.is_file() and markdown_path.is_file()

    context = json.loads(context_path.read_text(encoding="utf-8"))
    assert context["schema_version"] == HISTORIAN_CONTEXT_SCHEMA
    assert context["historian_query_id"] == QUERY_ID
    assert context["corpus"]["record_count"] == len(CITED_RECORDS)
    assert context["corpus"]["cited_record_count"] == len(CITED_RECORDS)
    assert context["provenance"]["retrieval_corpus_fingerprint"] == "f" * 64
    assert context["provenance"]["query_state"] == "COMPLETE"
    assert context["boundaries"]
    assert "advisory interpretation" in " ".join(context["boundaries"])

    cited_ids = {record["record_id"] for record in context["cited_records"]}
    assert cited_ids == set(CITED_RECORDS)
    for record in context["cited_records"]:
        record_path = Path(record["path"])
        assert record_path.is_file()
        assert record["sha256"] == hashlib.sha256(record_path.read_bytes()).hexdigest()
        assert record["kind"] == CITED_RECORDS[record["record_id"]]

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "advisory, not authority" in markdown
    assert QUERY_ID in markdown
    for record_id in CITED_RECORDS:
        assert record_id in markdown
    assert "advisory interpretation over evidence" in markdown


def test_bind_fails_closed_on_unknown_cited_record(tmp_path: Path) -> None:
    parsed = {
        "answer": "Answer text.",
        "cited_record_ids": ["CLM-missing-record"],
    }
    query_dir = _make_query_dir(tmp_path, parsed_response=parsed)
    with pytest.raises(HistorianContextError, match="does not resolve in corpus"):
        _bind(tmp_path, query_dir=query_dir)


def test_bind_fails_closed_on_empty_citations(tmp_path: Path) -> None:
    parsed = {"answer": "Answer text.", "cited_record_ids": []}
    query_dir = _make_query_dir(tmp_path, parsed_response=parsed)
    with pytest.raises(HistorianContextError, match="cited_record_ids"):
        _bind(tmp_path, query_dir=query_dir)


def test_bind_fails_closed_on_invalid_contract(tmp_path: Path) -> None:
    validation = {
        "schema_valid": {"valid": True, "errors": []},
        "grounding_valid": {"valid": True, "errors": []},
        "contract_valid": False,
    }
    query_dir = _make_query_dir(tmp_path, validation=validation)
    with pytest.raises(HistorianContextError, match="contract_valid"):
        _bind(tmp_path, query_dir=query_dir)


def test_bind_fails_closed_on_invalid_grounding(tmp_path: Path) -> None:
    validation = {
        "schema_valid": {"valid": True, "errors": []},
        "grounding_valid": {"valid": False, "errors": ["citation not grounded"]},
        "contract_valid": True,
    }
    query_dir = _make_query_dir(tmp_path, validation=validation)
    with pytest.raises(HistorianContextError, match="grounding_valid"):
        _bind(tmp_path, query_dir=query_dir)


def test_bind_fails_closed_on_record_frontmatter_mismatch(tmp_path: Path) -> None:
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    mismatched = records_dir / "claim" / "CLM-example-gap.md"
    mismatched.parent.mkdir(parents=True)
    mismatched.write_text(
        "---\nid: CLM-different-id\nkind: claim\n---\n\nBody.\n",
        encoding="utf-8",
    )
    query_dir = _make_query_dir(tmp_path)
    with pytest.raises(HistorianContextError, match="frontmatter id"):
        _bind(tmp_path, query_dir=query_dir, records_dir=records_dir)


def test_bind_fails_closed_on_ambiguous_record_id(tmp_path: Path) -> None:
    records_dir = _make_records_dir(tmp_path)
    _write_record(records_dir / "duplicates" / "nested", "CLM-example-gap", "claim")
    query_dir = _make_query_dir(tmp_path)
    with pytest.raises(HistorianContextError, match="ambiguous"):
        _bind(tmp_path, query_dir=query_dir, records_dir=records_dir)


def test_bind_fails_closed_without_overwrite(tmp_path: Path) -> None:
    out_dir = tmp_path / "context_out"
    first = _bind(tmp_path, out_dir=out_dir)
    assert Path(first["historian_context_path"]).is_file()
    with pytest.raises(HistorianContextError, match="already exists"):
        _bind(tmp_path, out_dir=out_dir)
    rebound = _bind(tmp_path, out_dir=out_dir, overwrite=True)
    assert Path(rebound["historian_context_path"]).is_file()


def test_bind_fails_closed_on_missing_result(tmp_path: Path) -> None:
    query_dir = _make_query_dir(tmp_path)
    (query_dir / "reasoner" / f"{QUERY_ID}.result.json").unlink()
    with pytest.raises(HistorianContextError, match="missing historian query result"):
        _bind(tmp_path, query_dir=query_dir)


def test_bind_fails_closed_on_query_id_mismatch(tmp_path: Path) -> None:
    query_dir = _make_query_dir(tmp_path)
    result_path = query_dir / "reasoner" / f"{QUERY_ID}.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["query_id"] = "op-00000000-0000-0000-0000-000000000000"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(HistorianContextError, match="query_id does not match"):
        _bind(tmp_path, query_dir=query_dir)


def test_bind_without_retrieval_and_transaction_still_binds(tmp_path: Path) -> None:
    query_dir = _make_query_dir(tmp_path, retrieval=False, include_transaction=False)
    result = _bind(tmp_path, query_dir=query_dir)
    context = json.loads(Path(result["historian_context_path"]).read_text(encoding="utf-8"))
    assert context["provenance"]["retrieval_corpus_fingerprint"] is None
    assert context["provenance"]["query_state"] is None


def test_resolve_record_path_requires_unique_match(tmp_path: Path) -> None:
    records_dir = _make_records_dir(tmp_path)
    assert resolve_record_path(records_dir, "CLM-example-gap").is_file()
    with pytest.raises(HistorianContextError, match="does not resolve"):
        resolve_record_path(records_dir, "CLM-nope")
    with pytest.raises(HistorianContextError, match="records directory does not exist"):
        resolve_record_path(tmp_path / "missing", "CLM-example-gap")


def test_rendered_markdown_lists_every_cited_record_and_boundary(tmp_path: Path) -> None:
    result = _bind(tmp_path)
    context = json.loads(Path(result["historian_context_path"]).read_text(encoding="utf-8"))
    markdown = render_historian_context_markdown(context)
    for boundary in context["boundaries"]:
        assert boundary in markdown
    for record in context["cited_records"]:
        assert record["record_id"] in markdown
        assert record["sha256"] in markdown
    assert "requires explicit human review" in markdown


def test_cli_bind_happy_path(tmp_path: Path) -> None:
    query_dir = _make_query_dir(tmp_path)
    records_dir = _make_records_dir(tmp_path)
    out_dir = tmp_path / "cli_out"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bind",
            "--query-dir",
            str(query_dir),
            "--records-dir",
            str(records_dir),
            "--out-dir",
            str(out_dir),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["historian_query_id"] == QUERY_ID
    assert summary["cited_record_ids"] == sorted(CITED_RECORDS)
    assert Path(summary["historian_context_path"]).is_file()


def test_cli_bind_fails_closed_on_unknown_record(tmp_path: Path) -> None:
    parsed = {"answer": "Answer.", "cited_record_ids": ["CLM-missing"]}
    query_dir = _make_query_dir(tmp_path, parsed_response=parsed)
    records_dir = _make_records_dir(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "bind",
            "--query-dir",
            str(query_dir),
            "--records-dir",
            str(records_dir),
            "--out-dir",
            str(tmp_path / "cli_out"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "does not resolve in corpus" in completed.stderr
