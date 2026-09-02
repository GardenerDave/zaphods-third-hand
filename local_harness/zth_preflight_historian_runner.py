#!/usr/bin/env python3
"""Structured baseline-validation runner for Project Historian.

This script is executed by the supported Historian retrieval runtime (not by
ZTH's own interpreter) with the Project Historian repository passed as its
single argument. It performs the Historian-side baseline observations for
``local_harness/zth_preflight.py``:

- canonical record validation count (``historian.cli.validate``);
- projected record validation count (``historian.cli.validate_projection``);
- retrieval-state currency, classified as ``current``, ``stale``, ``missing``,
  or ``invalid`` using Historian's own ``historian.retrieval.validate_state``
  corpus-fingerprint check plus a minimal embeddings artifact consistency
  check.

It prints exactly one JSON object on stdout and exits 0 whenever that report
was produced. Individual validation failures are reported as structured
fields inside the JSON, not as exit codes, so the caller can render every
failure at once. It is strictly read-only: it writes nothing, rebuilds
nothing, and repairs nothing. It grants no authority.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


RUNNER_SCHEMA = "zth.historian_baseline_preflight_runner.v1"
RETRIEVAL_CURRENT = "current"
RETRIEVAL_STALE = "stale"
RETRIEVAL_MISSING = "missing"
RETRIEVAL_INVALID = "invalid"
SUPPORTED_RETRIEVAL_STATES = (
    RETRIEVAL_CURRENT,
    RETRIEVAL_STALE,
    RETRIEVAL_MISSING,
    RETRIEVAL_INVALID,
)
CORPUS_SUBPATH = Path("interfaces") / "khoj" / "corpus"
STATE_SUBPATH = Path("interfaces") / "retrieval" / "state"
MANIFEST_NAME = "manifest.json"
EMBEDDINGS_NAME = "embeddings.npy"
REQUIRED_MANIFEST_KEYS = (
    "corpus_sha256",
    "corpus_files",
    "dimensionality",
    "document_count",
    "encoder_revision",
    "record_ids",
)


def _check_canonical(repo: Path) -> dict[str, Any]:
    try:
        from historian.cli import validate as canonical_validate
    except Exception as exc:
        return {"count": None, "error": f"cannot import historian.cli: {exc}"}
    try:
        return {"count": canonical_validate(), "error": None}
    except AssertionError as exc:
        return {"count": None, "error": f"canonical validation failed: {exc}"}
    except Exception as exc:
        return {"count": None, "error": f"canonical validation failed: {type(exc).__name__}: {exc}"}


def _check_projection(repo: Path) -> dict[str, Any]:
    try:
        from historian.cli import validate_projection as projection_validate
    except Exception as exc:
        return {"count": None, "error": f"cannot import historian.cli: {exc}"}
    try:
        return {"count": projection_validate(), "error": None}
    except AssertionError as exc:
        return {"count": None, "error": f"projection validation failed: {exc}"}
    except Exception as exc:
        return {"count": None, "error": f"projection validation failed: {type(exc).__name__}: {exc}"}


def _load_manifest(repo: Path) -> dict[str, Any]:
    manifest_path = repo / STATE_SUBPATH / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise _RetrievalProblem(
            RETRIEVAL_INVALID, f"cannot read retrieval state manifest: {exc}"
        )
    except json.JSONDecodeError as exc:
        raise _RetrievalProblem(
            RETRIEVAL_INVALID, f"retrieval state manifest is not valid JSON: {exc}"
        )
    if not isinstance(manifest, dict):
        raise _RetrievalProblem(
            RETRIEVAL_INVALID, "retrieval state manifest must be a JSON object"
        )
    missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
    if missing:
        raise _RetrievalProblem(
            RETRIEVAL_INVALID,
            f"retrieval state manifest is missing required keys: {missing}",
        )
    return manifest


def _check_embeddings(repo: Path, manifest: dict[str, Any]) -> None:
    embeddings_path = repo / STATE_SUBPATH / EMBEDDINGS_NAME
    try:
        import numpy as np
    except Exception as exc:
        raise _RetrievalProblem(
            RETRIEVAL_INVALID,
            f"cannot verify retrieval embeddings (numpy unavailable in this runtime): {exc}",
        )
    try:
        vectors = np.load(embeddings_path, allow_pickle=False)
    except Exception as exc:
        raise _RetrievalProblem(
            RETRIEVAL_INVALID, f"cannot load retrieval embeddings: {type(exc).__name__}: {exc}"
        )
    expected_shape = (manifest["document_count"], manifest["dimensionality"])
    if tuple(vectors.shape) != tuple(expected_shape):
        raise _RetrievalProblem(
            RETRIEVAL_INVALID,
            f"retrieval embeddings shape {tuple(vectors.shape)} does not match the "
            f"manifest document_count/dimensionality {expected_shape}",
        )


class _RetrievalProblem(Exception):
    def __init__(self, state: str, error: str) -> None:
        super().__init__(error)
        self.state = state
        self.error = error


def _check_retrieval(repo: Path) -> dict[str, Any]:
    manifest_path = repo / STATE_SUBPATH / MANIFEST_NAME
    embeddings_path = repo / STATE_SUBPATH / EMBEDDINGS_NAME
    if not manifest_path.is_file():
        return {
            "state": RETRIEVAL_MISSING,
            "error": f"retrieval state manifest not found: {manifest_path.relative_to(repo)}",
        }
    if not embeddings_path.is_file():
        return {
            "state": RETRIEVAL_MISSING,
            "error": f"retrieval state embeddings not found: {embeddings_path.relative_to(repo)}",
        }
    try:
        manifest = _load_manifest(repo)
    except _RetrievalProblem as problem:
        return {"state": problem.state, "error": problem.error}
    try:
        from historian.retrieval import (
            RetrievalStateMismatch,
            load_documents,
            validate_state,
        )
    except Exception as exc:
        return {
            "state": RETRIEVAL_INVALID,
            "error": f"cannot import historian.retrieval: {exc}",
        }
    try:
        _check_embeddings(repo, manifest)
    except _RetrievalProblem as problem:
        return {"state": problem.state, "error": problem.error}
    try:
        docs = load_documents(repo / CORPUS_SUBPATH)
    except Exception as exc:
        return {
            "state": RETRIEVAL_INVALID,
            "error": f"cannot load retrieval corpus documents: {type(exc).__name__}: {exc}",
        }
    try:
        validate_state(manifest, docs)
    except RetrievalStateMismatch as exc:
        return {"state": RETRIEVAL_STALE, "error": str(exc)}
    except Exception as exc:
        return {
            "state": RETRIEVAL_INVALID,
            "error": f"retrieval state validation failed: {type(exc).__name__}: {exc}",
        }
    return {"state": RETRIEVAL_CURRENT, "error": None}


def _historian_root() -> Path | None:
    try:
        import historian
    except Exception:
        return None
    return Path(historian.__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: zth_preflight_historian_runner.py HISTORIAN_REPO", file=sys.stderr)
        return 2
    repo = Path(argv[1]).resolve()
    if not repo.is_dir():
        print(f"historian repository is not a directory: {repo}", file=sys.stderr)
        return 2

    package_root = _historian_root()
    root_mismatch = package_root is not None and package_root != repo
    mismatch_error = (
        "this runtime resolved a different historian package "
        f"({package_root}) than the requested repository ({repo})"
        if root_mismatch
        else None
    )

    if root_mismatch:
        canonical = {"count": None, "error": mismatch_error}
        projection = {"count": None, "error": mismatch_error}
        retrieval = {"state": RETRIEVAL_INVALID, "error": mismatch_error}
    else:
        canonical = _check_canonical(repo)
        projection = _check_projection(repo)
        retrieval = _check_retrieval(repo)

    report: dict[str, Any] = {
        "schema_version": RUNNER_SCHEMA,
        "historian_root": str(package_root) if package_root is not None else None,
        "runtime_python": sys.executable,
        "canonical": canonical,
        "projection": projection,
        "retrieval": retrieval,
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
