#!/usr/bin/env python3
"""Bind Project Historian query results into validated ZTH evidence artifacts.

This is a read-only integration adapter. It takes a durable Project Historian
`ask` query directory, verifies the recorded answer contract, resolves every
cited record id against a canonical records corpus, and emits plain-file
Historian context evidence for supervised ZTH work.

The Historian answer is advisory interpretation over evidence. The cited
canonical records remain the evidence. Binding context grants no execution,
file modification, promotion, or lifecycle authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HISTORIAN_CONTEXT_SCHEMA = "zth.historian_context.v0.1"
CONTEXT_BOUNDARIES = (
    "The Historian answer is advisory interpretation over evidence; the cited canonical records remain the evidence.",
    "This context grants no execution, file modification, promotion, training, or lifecycle authority.",
    "Cited records are read-only references preserved by Project Historian.",
)
_FRONTMATTER_ID_RE = re.compile(r"^id:\s*([A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
_FRONTMATTER_KIND_RE = re.compile(r"^kind:\s*([a-z]+)\s*$", re.MULTILINE)


class HistorianContextError(ValueError):
    """Raised when Historian context binding fails or fails closed."""


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _read_json(path: Path, *, kind: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HistorianContextError(f"missing {kind}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HistorianContextError(f"invalid JSON in {kind}: {path}") from exc


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HistorianContextError(f"{field} must be a non-empty string")
    return value


def _require_str_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise HistorianContextError(f"{field} must be a non-empty list")
    for item in value:
        _require_str(item, field=field)
    return value


def resolve_record_path(records_dir: Path, record_id: str) -> Path:
    if not records_dir.is_dir():
        raise HistorianContextError(f"records directory does not exist: {records_dir}")
    matches = sorted(records_dir.glob(f"**/{record_id}.md"))
    if not matches:
        raise HistorianContextError(f"cited record does not resolve in corpus: {record_id}")
    if len(matches) > 1:
        raise HistorianContextError(f"cited record id is ambiguous in corpus: {record_id}")
    return matches[0]


def _read_record_metadata(record_path: Path) -> tuple[str, str | None]:
    text = record_path.read_text(encoding="utf-8")
    frontmatter = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            frontmatter = text[:end]
    id_match = _FRONTMATTER_ID_RE.search(frontmatter)
    if id_match is None:
        raise HistorianContextError(f"record is missing frontmatter id: {record_path}")
    kind_match = _FRONTMATTER_KIND_RE.search(frontmatter)
    return id_match.group(1), kind_match.group(1) if kind_match is not None else None


def _load_query(query_dir: Path) -> dict[str, Any]:
    payload = _read_json(query_dir / "query.json", kind="historian query")
    if not isinstance(payload, list) or len(payload) != 1:
        raise HistorianContextError("query.json must contain exactly one query entry")
    entry = payload[0]
    if not isinstance(entry, dict):
        raise HistorianContextError("query.json entry must be an object")
    return {
        "query_id": _require_str(entry.get("id"), field="query.json id"),
        "question": _require_str(entry.get("question"), field="query.json question"),
    }


def _load_result(query_dir: Path, query_id: str) -> dict[str, Any]:
    result = _read_json(query_dir / "reasoner" / f"{query_id}.result.json", kind="historian query result")
    if not isinstance(result, dict):
        raise HistorianContextError("historian query result must be an object")
    if result.get("query_id") != query_id:
        raise HistorianContextError("result query_id does not match query.json id")
    _require_str(result.get("question"), field="result question")
    validation = result.get("validation")
    if not isinstance(validation, dict):
        raise HistorianContextError("historian query result must include validation")
    for key in ("schema_valid", "grounding_valid"):
        section = validation.get(key)
        if not isinstance(section, dict) or section.get("valid") is not True:
            raise HistorianContextError(f"historian query result {key} must be valid")
    if validation.get("contract_valid") is not True:
        raise HistorianContextError("historian query result contract_valid must be true")
    parsed = result.get("parsed_response")
    if not isinstance(parsed, dict):
        raise HistorianContextError("historian query result must include parsed_response")
    _require_str(parsed.get("answer"), field="parsed_response answer")
    cited = _require_str_list(parsed.get("cited_record_ids"), field="parsed_response cited_record_ids")
    if len(cited) != len(set(cited)):
        raise HistorianContextError("parsed_response cited_record_ids must be unique")
    return result


def _load_retrieval(query_dir: Path) -> dict[str, Any] | None:
    path = query_dir / "retrieval.json"
    if not path.is_file():
        return None
    payload = _read_json(path, kind="historian retrieval")
    if not isinstance(payload, dict):
        raise HistorianContextError("historian retrieval must be an object")
    return payload


def _load_transaction_state(query_dir: Path, query_id: str) -> dict[str, Any] | None:
    path = query_dir / "reasoner" / f"{query_id}.transaction.json"
    if not path.is_file():
        return None
    payload = _read_json(path, kind="historian query transaction")
    if not isinstance(payload, dict):
        raise HistorianContextError("historian query transaction must be an object")
    return payload


def bind_historian_context(
    *,
    query_dir: Path,
    records_dir: Path,
    output_dir: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    query = _load_query(query_dir)
    query_id = query["query_id"]
    result = _load_result(query_dir, query_id)
    parsed = result["parsed_response"]
    retrieval = _load_retrieval(query_dir)
    transaction = _load_transaction_state(query_dir, query_id)

    cited_records: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for record_id in parsed["cited_record_ids"]:
        record_path = resolve_record_path(records_dir, record_id)
        if record_path in seen_paths:
            raise HistorianContextError(f"cited record resolves twice: {record_id}")
        seen_paths.add(record_path)
        frontmatter_id, kind = _read_record_metadata(record_path)
        if frontmatter_id != record_id:
            raise HistorianContextError(
                f"cited record id does not match record frontmatter id: {record_id} != {frontmatter_id}"
            )
        cited_records.append(
            {
                "record_id": record_id,
                "kind": kind,
                "path": str(record_path),
                "sha256": _sha256_text(record_path.read_text(encoding="utf-8")),
            }
        )

    answer_text = parsed["answer"]
    context = {
        "schema_version": HISTORIAN_CONTEXT_SCHEMA,
        "historian_query_id": query_id,
        "question": query["question"],
        "advisory_answer": {
            "answer": answer_text,
            "answer_sha256": _sha256_text(answer_text),
            "uncertainty_or_limitations": parsed.get("uncertainty_or_limitations"),
            "contradictions_or_missing_evidence": parsed.get("contradictions_or_missing_evidence"),
        },
        "cited_records": cited_records,
        "corpus": {
            "records_dir": str(records_dir),
            "record_count": sum(1 for _ in records_dir.glob("**/*.md")),
            "cited_record_count": len(cited_records),
        },
        "provenance": {
            "source": "project-historian ask query directory",
            "query_dir": str(query_dir),
            "result_path": str(query_dir / "reasoner" / f"{query_id}.result.json"),
            "result_sha256": _sha256_text((query_dir / "reasoner" / f"{query_id}.result.json").read_text(encoding="utf-8")),
            "retrieval_corpus_fingerprint": retrieval.get("corpus_fingerprint") if retrieval else None,
            "retrieval_revision": retrieval.get("revision") if retrieval else None,
            "retrieval_document_count": retrieval.get("document_count") if retrieval else None,
            "query_state": transaction.get("state") if transaction else None,
        },
        "boundaries": list(CONTEXT_BOUNDARIES),
        "bound_at": _utc_iso(),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    context_path = output_dir / f"historian_context_{query_id}.json"
    markdown_path = output_dir / f"historian_context_{query_id}.md"
    if context_path.exists() and not overwrite:
        raise HistorianContextError(f"context artifact already exists: {context_path}")
    if markdown_path.exists() and not overwrite:
        raise HistorianContextError(f"context artifact already exists: {markdown_path}")
    context_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_historian_context_markdown(context), encoding="utf-8")

    context["historian_context_path"] = str(context_path)
    context["historian_context_markdown_path"] = str(markdown_path)
    return context


def render_historian_context_markdown(context: dict[str, Any]) -> str:
    advisory = context["advisory_answer"]
    cited_lines = [
        f"- `{record['record_id']}` ({record.get('kind') or 'unknown'}) — `{record['path']}` (sha256 `{record['sha256']}`)"
        for record in context["cited_records"]
    ]
    contradiction_lines = [
        f"- {item}" for item in (advisory.get("contradictions_or_missing_evidence") or [])
    ] or ["- <none recorded>"]
    provenance = context["provenance"]
    lines = [
        "# ZTH Historian Context (Advisory Interpretation)",
        "",
        *(
            f"> {boundary}"
            for boundary in context["boundaries"]
        ),
        "",
        "## Question",
        "",
        context["question"],
        "",
        "## Historian Answer (advisory, not authority)",
        "",
        advisory["answer"].rstrip(),
        "",
        "## Uncertainty or Limitations",
        "",
        str(advisory.get("uncertainty_or_limitations") or "<none recorded>"),
        "",
        "## Contradictions or Missing Evidence",
        "",
        *contradiction_lines,
        "",
        "## Cited Canonical Records (the evidence)",
        "",
        *cited_lines,
        "",
        "## Provenance",
        "",
        f"- historian_query_id: `{context['historian_query_id']}`",
        f"- query_dir: `{provenance['query_dir']}`",
        f"- result_sha256: `{provenance['result_sha256']}`",
        f"- retrieval_corpus_fingerprint: `{provenance.get('retrieval_corpus_fingerprint')}`",
        f"- retrieval_revision: `{provenance.get('retrieval_revision')}`",
        f"- retrieval_document_count: {provenance.get('retrieval_document_count')}",
        f"- query_state: {provenance.get('query_state')}",
        f"- answer_sha256: `{advisory['answer_sha256']}`",
        f"- corpus_records_dir: `{context['corpus']['records_dir']}`",
        f"- corpus_record_count: {context['corpus']['record_count']}",
        f"- bound_at: {context['bound_at']}",
        "",
        "## Review Boundary",
        "",
        "- This artifact is bound evidence for supervised review, not a decision record.",
        "- Accepting any part of this context requires explicit human review.",
        "- It does not select workers, promote outputs, or move lifecycle state.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    bind = subparsers.add_parser("bind", help="Bind one Historian query result into ZTH evidence artifacts.")
    bind.add_argument("--query-dir", type=Path, required=True, help="Historian ask query directory.")
    bind.add_argument("--records-dir", type=Path, required=True, help="Canonical Historian records directory (read-only).")
    bind.add_argument("--out-dir", type=Path, required=True, help="Output directory for context artifacts.")
    bind.add_argument("--overwrite", action="store_true", help="Replace existing context artifacts.")
    bind.add_argument("--json", action="store_true", help="Print a machine-readable binding summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        context = bind_historian_context(
            query_dir=args.query_dir,
            records_dir=args.records_dir,
            output_dir=args.out_dir,
            overwrite=bool(args.overwrite),
        )
    except HistorianContextError as exc:
        print(f"historian-context: error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": context["schema_version"],
                    "historian_query_id": context["historian_query_id"],
                    "cited_record_ids": [record["record_id"] for record in context["cited_records"]],
                    "historian_context_path": context["historian_context_path"],
                    "historian_context_markdown_path": context["historian_context_markdown_path"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"Bound Historian context: {context['historian_context_path']}")
        print("No model, endpoint, shell command, or Git operation was invoked by this binding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
