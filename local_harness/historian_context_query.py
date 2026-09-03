#!/usr/bin/env python3
"""One-command Project Historian ask and ZTH Historian context binding.

For each question this wrapper:

1. runs one Historian ``ask`` query through the supported bundled Historian
   retrieval runtime (via ``local_harness/historian_ask_runner.py``);
2. captures the exact structured query identity (``request_id`` and request
   directory) the Historian service itself returned — never by scanning or
   sorting Historian work directories;
3. validates that identity against the query artifacts on disk;
4. binds the exact query directory through the existing ZTH Historian
   context binder (``local_harness/historian_context.py``), preserving the
   ``zth.historian_context.v0.1`` artifact and its semantics;
5. reports the resulting context artifact, query id, query directory, cited
   canonical record ids, and retrieval corpus fingerprint.

Each question resolves to exactly one outcome:

- ``bound`` — the answer cites canonical records and the existing strict
  binder binds them into ``zth.historian_context.v0.1`` evidence;
- ``insufficient`` — the answer is contract-valid but cites zero canonical
  records; it is preserved as a separate non-bound artifact and never treated
  as bound evidence or as a failure;
- ``failed`` — any transport, schema, grounding, contract, or provenance
  failure; preserved and blocking.

The Historian answer remains advisory interpretation over evidence. The
cited canonical records remain the evidence. A successful query is not
approval. A successful bind is not approval. This wrapper grants no
execution, file-modification, lifecycle, promotion, training, or review
authority, and it never modifies Project Historian.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.historian_context import (
    CONTEXT_BOUNDARIES,
    HISTORIAN_CONTEXT_SCHEMA,
    HistorianContextError,
    bind_historian_context,
)


ENDPOINT_ENV = "HISTORIAN_REASONER_ENDPOINT"
HISTORIAN_SERVICE_PATH = Path("historian") / "service.py"
HISTORIAN_RECORDS_DIR = Path("records")
BUNDLED_RUNTIME = Path("interfaces/khoj/runtime/py312-cpu/bin/python")
HISTORIAN_WORK_ROOT = Path(".work") / "historian_queries"
RUNNER_SCRIPT = Path(__file__).resolve().parent / "historian_ask_runner.py"
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_MAX_TOKENS = 1536
MAX_STDERR_TAIL = 400

OUTCOME_BOUND = "bound"
OUTCOME_INSUFFICIENT = "insufficient"
OUTCOME_FAILED = "failed"
INSUFFICIENT_CONTEXT_SCHEMA = "zth.historian_insufficient_context.v0.1"
INSUFFICIENT_FILE_PREFIX = "historian_insufficient_"


class HistorianAskBindError(ValueError):
    """Raised when the consolidated ask-and-bind operation fails closed."""


WRAPPER_BOUNDARIES = (
    "The Historian answer is advisory interpretation over evidence; the cited canonical records remain the evidence.",
    "A successful query is not approval; a successful bind is not approval.",
    "This wrapper grants no execution, file-modification, lifecycle, promotion, training, or review authority.",
    "This wrapper does not modify Project Historian or its canonical records.",
)

def _stderr_tail(stderr: str | None) -> str:
    text = (stderr or "").strip()
    if not text:
        return "<no stderr>"
    return text[-MAX_STDERR_TAIL:]


def validate_historian_repo(historian_repo: Path) -> None:
    if not historian_repo.is_dir():
        raise HistorianAskBindError(f"Historian repository does not exist: {historian_repo}")
    if not (historian_repo / HISTORIAN_SERVICE_PATH).is_file():
        raise HistorianAskBindError(
            f"Historian service module not found under: {historian_repo} "
            "(expected historian/service.py)"
        )
    if not (historian_repo / HISTORIAN_RECORDS_DIR).is_dir():
        raise HistorianAskBindError(
            f"Historian canonical records directory not found under: {historian_repo} "
            "(expected records/)"
        )


def resolve_historian_python(historian_repo: Path, override: Path | None) -> Path:
    if override is not None:
        if not override.is_file() or not os.access(override, os.X_OK):
            raise HistorianAskBindError(
                f"--historian-python is not an executable file: {override}"
            )
        return override
    bundled = historian_repo / BUNDLED_RUNTIME
    if bundled.is_file() and os.access(bundled, os.X_OK):
        return bundled
    raise HistorianAskBindError(
        "supported Historian retrieval runtime not found at "
        f"{bundled}; pass --historian-python pointing at a Python "
        "interpreter with the Historian retrieval stack installed"
    )


def resolve_endpoint(explicit: str | None) -> str:
    if explicit is not None and explicit.strip():
        return explicit.strip()
    from_env = os.environ.get(ENDPOINT_ENV, "").strip()
    if from_env:
        return from_env
    raise HistorianAskBindError(
        f"no Historian reasoner endpoint configured: set {ENDPOINT_ENV} or pass --endpoint"
    )


def _runner_environment(historian_repo: Path, endpoint: str) -> dict[str, str]:
    environment = dict(os.environ)
    existing_path = environment.get("PYTHONPATH", "")
    parts = [str(historian_repo)] + [part for part in existing_path.split(os.pathsep) if part]
    environment["PYTHONPATH"] = os.pathsep.join(parts)
    environment[ENDPOINT_ENV] = endpoint
    return environment


def run_historian_ask(
    *,
    historian_repo: Path,
    historian_python: Path,
    question: str,
    endpoint: str,
    max_tokens: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Run one Historian ask query and return its structured result."""
    command = [str(historian_python), str(RUNNER_SCRIPT), question, str(max_tokens)]
    try:
        completed = subprocess.run(
            command,
            cwd=str(historian_repo),
            env=_runner_environment(historian_repo, endpoint),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HistorianAskBindError(
            f"Historian ask timed out after {timeout_seconds}s: {question!r}"
        ) from exc
    except OSError as exc:
        raise HistorianAskBindError(
            f"failed to launch Historian runtime {historian_python}: {exc}"
        ) from exc
    if completed.returncode != 0:
        raise HistorianAskBindError(
            "Historian ask runner failed with exit code "
            f"{completed.returncode}: {_stderr_tail(completed.stderr)}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise HistorianAskBindError(
            "Historian ask runner did not return a JSON result: "
            f"{exc}; stderr tail: {_stderr_tail(completed.stderr)}"
        ) from exc
    if not isinstance(result, dict):
        raise HistorianAskBindError("Historian ask result must be a JSON object")
    return result


def _require_ask_result_fields(result: dict[str, Any]) -> None:
    request_id = result.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise HistorianAskBindError(
            "Historian ask result is missing the request id; refusing to guess the query"
        )
    if not isinstance(result.get("question"), str):
        raise HistorianAskBindError("Historian ask result is missing the question field")


def _resolve_request_dir(result: dict[str, Any], historian_repo: Path) -> Path:
    runtime = result.get("runtime")
    if not isinstance(runtime, dict):
        raise HistorianAskBindError(
            "Historian ask result is missing runtime identity; refusing to guess the query"
        )
    request_dir_value = runtime.get("request_dir")
    if not isinstance(request_dir_value, str) or not request_dir_value.strip():
        raise HistorianAskBindError(
            "Historian ask result is missing the request directory; refusing to scan "
            "Historian work directories"
        )
    request_dir = Path(request_dir_value)
    if not request_dir.is_absolute():
        request_dir = historian_repo / request_dir
    resolved_root = (historian_repo / HISTORIAN_WORK_ROOT).resolve()
    resolved_request = request_dir.resolve()
    if resolved_root not in resolved_request.parents:
        raise HistorianAskBindError(
            "Historian ask result points outside the Historian query work root: "
            f"{request_dir}"
        )
    if not resolved_request.is_dir():
        raise HistorianAskBindError(
            f"Historian query directory does not exist: {request_dir}"
        )
    return resolved_request

def _cross_check_query_identity(
    *,
    request_dir: Path,
    request_id: str,
    question: str,
) -> None:
    query_path = request_dir / "query.json"
    try:
        payload = json.loads(query_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HistorianAskBindError(
            f"Historian query artifact is missing: {query_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise HistorianAskBindError(f"invalid JSON in Historian query artifact: {query_path}") from exc
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise HistorianAskBindError(
            f"Historian query artifact must hold exactly one query entry: {query_path}"
        )
    entry = payload[0]
    if entry.get("id") != request_id:
        raise HistorianAskBindError(
            f"Historian query artifact id does not match the returned request id: "
            f"{entry.get('id')!r} != {request_id!r}"
        )
    recorded_question = entry.get("question")
    if not isinstance(recorded_question, str) or " ".join(recorded_question.split()) != " ".join(
        question.split()
    ):
        raise HistorianAskBindError(
            "Historian query artifact question does not match the asked question: "
            f"{query_path}"
        )


def _summarize_context(context: dict[str, Any], question: str) -> dict[str, Any]:
    provenance = context.get("provenance", {})
    return {
        "question": question,
        "outcome": OUTCOME_BOUND,
        "historian_query_id": context["historian_query_id"],
        "historian_query_dir": provenance.get("query_dir"),
        "historian_context_path": context["historian_context_path"],
        "historian_context_markdown_path": context["historian_context_markdown_path"],
        "historian_context_schema": context["schema_version"],
        "cited_record_ids": [record["record_id"] for record in context["cited_records"]],
        "retrieval_corpus_fingerprint": provenance.get("retrieval_corpus_fingerprint"),
        "retrieval_revision": provenance.get("retrieval_revision"),
        "retrieval_document_count": provenance.get("retrieval_document_count"),
    }


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_query_result(request_dir: Path, request_id: str) -> dict[str, Any] | None:
    """Read the query's own result artifact; None when unreadable."""
    path = request_dir / "reasoner" / f"{request_id}.result.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def insufficient_outcome(result: dict[str, Any]) -> bool:
    """True only for a contract-valid answer that cites zero canonical records.

    Anything else — invalid schema, invalid grounding, an invalid contract, a
    missing or malformed parsed response, a missing answer, or a malformed
    citation list — returns False so the strict binder stays the sole
    validator and the question fails closed instead.
    """
    validation = result.get("validation")
    if not isinstance(validation, dict):
        return False
    for key in ("schema_valid", "grounding_valid"):
        section = validation.get(key)
        if not isinstance(section, dict) or section.get("valid") is not True:
            return False
    if validation.get("contract_valid") is not True:
        return False
    parsed = result.get("parsed_response")
    if not isinstance(parsed, dict):
        return False
    answer = parsed.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return False
    cited = parsed.get("cited_record_ids")
    if not isinstance(cited, list):
        return False
    return not cited


def _preserve_insufficient_context(
    *,
    request_dir: Path,
    request_id: str,
    question: str,
    result: dict[str, Any],
    output_dir: Path,
    overwrite: bool,
) -> dict[str, Any]:
    parsed = result["parsed_response"]
    answer = parsed["answer"]
    retrieval: dict[str, Any] | None = None
    retrieval_path = request_dir / "retrieval.json"
    if retrieval_path.is_file():
        try:
            loaded = json.loads(retrieval_path.read_text(encoding="utf-8"))
            retrieval = loaded if isinstance(loaded, dict) else None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            retrieval = None
    result_path = request_dir / "reasoner" / f"{request_id}.result.json"
    artifact: dict[str, Any] = {
        "schema_version": INSUFFICIENT_CONTEXT_SCHEMA,
        "historian_query_id": request_id,
        "question": question,
        "outcome": OUTCOME_INSUFFICIENT,
        "note": (
            "The Historian returned a contract-valid advisory answer that cites "
            "zero canonical records. This artifact preserves that answer as a "
            "separate non-bound outcome: it is not bound evidence, it cites no "
            "canonical records, and it grants no authority."
        ),
        "advisory_answer": {
            "answer": answer,
            "answer_sha256": _sha256_text(answer),
            "uncertainty_or_limitations": parsed.get("uncertainty_or_limitations"),
            "contradictions_or_missing_evidence": parsed.get(
                "contradictions_or_missing_evidence"
            ),
        },
        "cited_record_ids": [],
        "provenance": {
            "source": "project-historian ask query directory",
            "query_dir": str(request_dir),
            "result_path": str(result_path),
            "result_sha256": _sha256_text(result_path.read_text(encoding="utf-8")),
            "retrieval_corpus_fingerprint": (
                retrieval.get("corpus_fingerprint") if retrieval else None
            ),
            "retrieval_revision": retrieval.get("revision") if retrieval else None,
            "retrieval_document_count": (
                retrieval.get("document_count") if retrieval else None
            ),
        },
        "boundaries": list(WRAPPER_BOUNDARIES),
        "preserved_at": _utc_iso(),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"{INSUFFICIENT_FILE_PREFIX}{request_id}.json"
    if artifact_path.exists() and not overwrite:
        raise HistorianAskBindError(
            f"insufficient context artifact already exists: {artifact_path}"
        )
    artifact_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    artifact["historian_insufficient_path"] = str(artifact_path)
    return artifact


def _summarize_insufficient(artifact: dict[str, Any]) -> dict[str, Any]:
    provenance = artifact["provenance"]
    return {
        "question": artifact["question"],
        "outcome": OUTCOME_INSUFFICIENT,
        "historian_query_id": artifact["historian_query_id"],
        "historian_query_dir": provenance.get("query_dir"),
        "historian_insufficient_path": artifact["historian_insufficient_path"],
        "historian_insufficient_schema": artifact["schema_version"],
        "cited_record_ids": [],
        "answer_sha256": artifact["advisory_answer"]["answer_sha256"],
        "retrieval_corpus_fingerprint": provenance.get("retrieval_corpus_fingerprint"),
        "retrieval_revision": provenance.get("retrieval_revision"),
        "retrieval_document_count": provenance.get("retrieval_document_count"),
        "boundaries": list(WRAPPER_BOUNDARIES),
    }


def ask_and_bind(
    *,
    question: str,
    historian_repo: Path,
    output_dir: Path,
    endpoint: str | None = None,
    historian_python: Path | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Run one Historian ask query and bind its exact result into ZTH context."""
    if not isinstance(question, str) or not question.strip():
        raise HistorianAskBindError("question must be a non-empty string")
    historian_repo = Path(historian_repo)
    validate_historian_repo(historian_repo)
    resolved_python = resolve_historian_python(historian_repo, historian_python)
    resolved_endpoint = resolve_endpoint(endpoint)
    result = run_historian_ask(
        historian_repo=historian_repo,
        historian_python=resolved_python,
        question=question,
        endpoint=resolved_endpoint,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    )
    _require_ask_result_fields(result)
    if result.get("status") != "ok":
        error_code = result.get("error_code", "internal_error")
        error_text = result.get("error", "Historian query failed")
        request_dir = None
        runtime = result.get("runtime")
        if isinstance(runtime, dict) and isinstance(runtime.get("request_dir"), str):
            request_dir = runtime["request_dir"]
        raise HistorianAskBindError(
            f"Historian ask failed ({error_code}): {error_text}; "
            f"request_id={result.get('request_id')!r}, "
            f"preserved query directory={request_dir!r}"
        )
    request_id = result["request_id"]
    request_dir = _resolve_request_dir(result, historian_repo)
    _cross_check_query_identity(
        request_dir=request_dir,
        request_id=request_id,
        question=question,
    )
    query_result = _read_query_result(request_dir, request_id)
    if query_result is not None and insufficient_outcome(query_result):
        artifact = _preserve_insufficient_context(
            request_dir=request_dir,
            request_id=request_id,
            question=question,
            result=query_result,
            output_dir=output_dir,
            overwrite=overwrite,
        )
        return _summarize_insufficient(artifact)
    try:
        context = bind_historian_context(
            query_dir=request_dir,
            records_dir=historian_repo / HISTORIAN_RECORDS_DIR,
            output_dir=output_dir,
            overwrite=overwrite,
        )
    except HistorianContextError as exc:
        raise HistorianAskBindError(f"Historian context binding failed: {exc}") from exc
    summary = _summarize_context(context, question)
    summary["boundaries"] = list(WRAPPER_BOUNDARIES)
    return summary

def ask_and_bind_many(
    *,
    questions: Sequence[str],
    historian_repo: Path,
    output_dir: Path,
    endpoint: str | None = None,
    historian_python: Path | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Run ask-and-bind for each question, stopping at the first failure.

    Bound and insufficient outcomes both continue; only a true transport,
    schema, grounding, contract, or provenance failure stops the run.
    """
    if not questions:
        raise HistorianAskBindError("at least one question is required")
    summaries: list[dict[str, Any]] = []
    insufficient: list[dict[str, Any]] = []
    for index, question in enumerate(questions):
        try:
            summary = ask_and_bind(
                question=question,
                historian_repo=historian_repo,
                output_dir=output_dir,
                endpoint=endpoint,
                historian_python=historian_python,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                overwrite=overwrite,
            )
        except HistorianAskBindError as exc:
            return {
                "status": "failed",
                "outcome": OUTCOME_FAILED,
                "bound": summaries,
                "insufficient": insufficient,
                "failed_question_index": index,
                "failed_question": question,
                "error": str(exc),
                "boundaries": list(WRAPPER_BOUNDARIES),
            }
        if summary.get("outcome") == OUTCOME_INSUFFICIENT:
            insufficient.append(summary)
        else:
            summaries.append(summary)
    return {
        "status": "ok",
        "bound": summaries,
        "bound_count": len(summaries),
        "insufficient": insufficient,
        "insufficient_count": len(insufficient),
        "boundaries": list(WRAPPER_BOUNDARIES),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one or more Project Historian ask queries and bind each exact "
            "result into ZTH Historian context evidence through the existing "
            "binder. The Historian answer remains advisory; a successful query "
            "or bind is not approval."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_bind = subparsers.add_parser(
        "ask-bind",
        help="Ask Project Historian and bind the exact result into ZTH context.",
    )
    ask_bind.add_argument(
        "--question",
        action="append",
        required=True,
        dest="questions",
        help="Question for Project Historian; repeat the flag for multiple questions.",
    )
    ask_bind.add_argument(
        "--historian-repo",
        type=Path,
        required=True,
        help="Project Historian repository root (read-only context source).",
    )
    ask_bind.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for the bound ZTH Historian context artifacts.",
    )
    ask_bind.add_argument(
        "--endpoint",
        help=(
            "Historian reasoner endpoint (HTTP). Falls back to "
            f"{ENDPOINT_ENV}; never hardcoded."
        ),
    )
    ask_bind.add_argument(
        "--historian-python",
        type=Path,
        help=(
            "Python interpreter with the Historian retrieval stack; defaults to "
            "the Historian bundled runtime when present."
        ),
    )
    ask_bind.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Reasoner max tokens (default {DEFAULT_MAX_TOKENS}).",
    )
    ask_bind.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-question timeout in seconds (default {DEFAULT_TIMEOUT_SECONDS}).",
    )
    ask_bind.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing context artifacts for the same query id.",
    )
    ask_bind.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable summary.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "ask-bind":
        raise SystemExit(f"unsupported command: {args.command}")
    try:
        summary = ask_and_bind_many(
            questions=args.questions,
            historian_repo=args.historian_repo,
            output_dir=args.output_dir,
            endpoint=args.endpoint,
            historian_python=args.historian_python,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout,
            overwrite=args.overwrite,
        )
    except HistorianAskBindError as exc:
        if args.json:
            print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(f"historian-context-query: error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["status"] == "ok" else 1
    for bound in summary.get("bound", []):
        print(f"Bound {bound['historian_query_id']} -> {bound['historian_context_path']}")
        print(f"  query directory: {bound['historian_query_dir']}")
        print(f"  cited records: {', '.join(bound['cited_record_ids'])}")
        print(f"  corpus fingerprint: {bound['retrieval_corpus_fingerprint']}")
    for insufficient_entry in summary.get("insufficient", []):
        print(
            f"Insufficient {insufficient_entry['historian_query_id']} -> "
            f"{insufficient_entry['historian_insufficient_path']}"
        )
        print(f"  query directory: {insufficient_entry['historian_query_dir']}")
        print(
            "  cited records: <none>; contract-valid advisory answer preserved "
            "separately, not bound evidence"
        )
    if summary["status"] == "ok":
        print(f"Bound {summary['bound_count']} Historian context artifact(s).")
        if summary.get("insufficient_count"):
            print(
                f"Preserved {summary['insufficient_count']} insufficient "
                "outcome(s) without binding."
            )
    else:
        print(
            f"Failed on question {summary['failed_question_index'] + 1}: "
            f"{summary['error']}",
            file=sys.stderr,
        )
        return 1
    for boundary in WRAPPER_BOUNDARIES:
        print(f"Boundary: {boundary}")
    print("No Historian or ZTH lifecycle authority was granted or exercised.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
