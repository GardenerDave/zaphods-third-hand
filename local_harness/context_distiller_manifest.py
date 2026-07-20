#!/usr/bin/env python3
"""Manifest-driven Context Distiller planner and executor.

This module extends the existing Context Distiller workflow without creating a
parallel distiller. It supports:

- schema-validated pass manifests;
- deterministic source selection and planning;
- focused pass execution with explicit dependencies;
- optional synthesis over validated pass artifacts;
- plan-only rendering for review.

The implementation deliberately keeps raw source material out of canonical
context. Generated artifacts are review evidence only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_REGISTRY_PATH = REPO_ROOT / "docs" / "reports" / "model_auditions" / "CONTEXT_DISTILLER_FOCUS_PROFILES_v1.json"
DEFAULT_JOB_ROOT = REPO_ROOT / "outputs" / "context_distiller"
SUPPORTED_SCHEMA = 1
DEFAULT_CHUNKING = {
    "target_chars": 12000,
    "overlap": 1,
    "offset": 1,
    "start_chunk": None,
    "end_chunk": None,
}

EXACT_OUTPUT_CONTRACT = {
    "verdict": "pass | fail | incomplete",
    "review_state": "complete | incomplete",
    "changed_paths": [],
    "verification": {
        "raw_output_structure": "pass | fail | not_applicable",
        "changed_files_against_allowlist": "pass | fail | not_applicable",
        "narrowest_relevant_local_checks": "pass | fail | not_run | not_applicable",
    },
    "evidence": [
        {
            "path": "repository-relative path",
            "observation": "specific observation",
            "existence": "present | absent",
        }
    ],
    "notes": "bounded conclusion",
}


class DistillerManifestError(ValueError):
    """Raised when a manifest or generated artifact is malformed."""


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _safe_repo_relative(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute() or ".." in path.parts:
        raise DistillerManifestError(f"unsafe repository-relative path: {path_text}")
    return path


def load_focus_profiles() -> dict[str, Any]:
    payload = _load_json(PROFILE_REGISTRY_PATH)
    if not isinstance(payload, dict) or payload.get("schema") != 1:
        raise DistillerManifestError(f"invalid focus profile registry: {PROFILE_REGISTRY_PATH}")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise DistillerManifestError("focus profile registry missing profiles object")
    return payload


def profile_registry() -> dict[str, Any]:
    return load_focus_profiles()


def profile_names() -> list[str]:
    registry = profile_registry()
    return sorted(registry["profiles"])


def validate_source_selection(manifest: dict[str, Any], repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        raise DistillerManifestError("manifest.inputs must be an object")

    sources = inputs.get("sources")
    if not isinstance(sources, list) or not sources:
        raise DistillerManifestError("manifest.inputs.sources must be a non-empty list")
    safe_sources: list[str] = []
    seen_sources: set[str] = set()
    source_records: list[dict[str, Any]] = []
    for raw_source in sources:
        if not isinstance(raw_source, str) or not raw_source.strip():
            raise DistillerManifestError("manifest.inputs.sources must contain non-empty strings")
        source_path = _safe_repo_relative(raw_source.strip())
        normalized = os.fspath((repo_root / source_path).resolve())
        if normalized in seen_sources:
            raise DistillerManifestError(f"duplicate source path: {raw_source}")
        seen_sources.add(normalized)
        abs_path = repo_root / source_path
        if not abs_path.is_file():
            raise DistillerManifestError(f"source file does not exist: {raw_source}")
        safe_sources.append(os.fspath(source_path))
        source_records.append(
            {
                "source": os.fspath(source_path),
                "abs_path": os.fspath(abs_path.resolve()),
                "sha256": _sha256_path(abs_path),
                "bytes": abs_path.stat().st_size,
            }
        )

    include_globs = inputs.get("include_globs", [])
    exclude_globs = inputs.get("exclude_globs", [])
    line_ranges = inputs.get("line_ranges", [])
    chunk_indices = inputs.get("chunk_indices", [])

    for name, value in [
        ("include_globs", include_globs),
        ("exclude_globs", exclude_globs),
        ("line_ranges", line_ranges),
        ("chunk_indices", chunk_indices),
    ]:
        if not isinstance(value, list):
            raise DistillerManifestError(f"manifest.inputs.{name} must be a list")

    selected_records = list(source_records)
    if include_globs:
        import fnmatch

        selected_records = [
            record
            for record in selected_records
            if any(fnmatch.fnmatch(record["source"], pattern) for pattern in include_globs)
        ]
    if exclude_globs:
        import fnmatch

        selected_records = [
            record
            for record in selected_records
            if not any(fnmatch.fnmatch(record["source"], pattern) for pattern in exclude_globs)
        ]
    if not selected_records:
        raise DistillerManifestError("source selection resolved to no selected sources")

    return {
        "sources": safe_sources,
        "selected_sources": selected_records,
        "include_globs": list(include_globs),
        "exclude_globs": list(exclude_globs),
        "line_ranges": list(line_ranges),
        "chunk_indices": list(chunk_indices),
    }


def validate_chunking(manifest: dict[str, Any]) -> dict[str, Any]:
    chunking = manifest.get("chunking")
    if not isinstance(chunking, dict):
        raise DistillerManifestError("manifest.chunking must be an object")
    effective = dict(DEFAULT_CHUNKING)
    for key in effective:
        if key in chunking:
            effective[key] = chunking[key]
    if not isinstance(effective["target_chars"], int) or effective["target_chars"] <= 0:
        raise DistillerManifestError("chunking.target_chars must be positive")
    if not isinstance(effective["overlap"], int) or effective["overlap"] < 0:
        raise DistillerManifestError("chunking.overlap must be zero or greater")
    if not isinstance(effective["offset"], int) or effective["offset"] < 0:
        raise DistillerManifestError("chunking.offset must be zero or greater")
    if effective["start_chunk"] is not None and (
        not isinstance(effective["start_chunk"], int) or effective["start_chunk"] < 1
    ):
        raise DistillerManifestError("chunking.start_chunk must be null or a positive integer")
    if effective["end_chunk"] is not None and (
        not isinstance(effective["end_chunk"], int) or effective["end_chunk"] < 1
    ):
        raise DistillerManifestError("chunking.end_chunk must be null or a positive integer")
    if (
        effective["start_chunk"] is not None
        and effective["end_chunk"] is not None
        and effective["start_chunk"] > effective["end_chunk"]
    ):
        raise DistillerManifestError("chunking.start_chunk must be <= chunking.end_chunk")
    return effective


def _validate_output(output: dict[str, Any], seen_filenames: set[str]) -> dict[str, Any]:
    if not isinstance(output, dict):
        raise DistillerManifestError("pass output must be an object")
    artifact_type = output.get("artifact_type")
    filename = output.get("filename")
    if not isinstance(artifact_type, str) or not artifact_type.strip():
        raise DistillerManifestError("pass output.artifact_type must be a non-empty string")
    if not isinstance(filename, str) or not filename.strip():
        raise DistillerManifestError("pass output.filename must be a non-empty string")
    if filename in seen_filenames:
        raise DistillerManifestError(f"duplicate pass output filename: {filename}")
    seen_filenames.add(filename)
    return {"artifact_type": artifact_type, "filename": filename}


def validate_passes(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    passes = manifest.get("passes")
    if not isinstance(passes, list) or not passes:
        raise DistillerManifestError("manifest.passes must be a non-empty list")
    registry = profile_registry()["profiles"]
    seen_ids: set[str] = set()
    seen_filenames: set[str] = set()
    validated: list[dict[str, Any]] = []
    for row in passes:
        if not isinstance(row, dict):
            raise DistillerManifestError("each pass must be an object")
        pass_id = row.get("id")
        profile = row.get("profile")
        questions = row.get("questions", [])
        inputs_from_passes = row.get("inputs_from_passes", [])
        output = row.get("output")
        if not isinstance(pass_id, str) or not pass_id.strip():
            raise DistillerManifestError("pass.id must be a non-empty string")
        if pass_id in seen_ids:
            raise DistillerManifestError(f"duplicate pass id: {pass_id}")
        seen_ids.add(pass_id)
        if pass_id in inputs_from_passes:
            raise DistillerManifestError(f"pass {pass_id} cannot depend on itself")
        if not isinstance(profile, str) or profile not in registry:
            raise DistillerManifestError(f"unknown or missing profile: {profile}")
        if not isinstance(questions, list):
            raise DistillerManifestError("pass.questions must be a list")
        if not isinstance(inputs_from_passes, list):
            raise DistillerManifestError("pass.inputs_from_passes must be a list")
        for dep in inputs_from_passes:
            if not isinstance(dep, str) or not dep.strip():
                raise DistillerManifestError("pass.inputs_from_passes must contain strings")
        validated.append(
            {
                "id": pass_id,
                "profile": profile,
                "questions": list(questions),
                "inputs_from_passes": list(inputs_from_passes),
                "output": _validate_output(output, seen_filenames),
            }
        )
    _validate_pass_dependencies(validated)
    return validated


def _validate_pass_dependencies(passes: list[dict[str, Any]]) -> None:
    by_id = {row["id"]: row for row in passes}
    for row in passes:
        for dep in row["inputs_from_passes"]:
            if dep not in by_id:
                raise DistillerManifestError(f"pass {row['id']} depends on missing pass {dep}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(pass_id: str) -> None:
        if pass_id in visited:
            return
        if pass_id in visiting:
            raise DistillerManifestError("dependency cycle detected")
        visiting.add(pass_id)
        for dep in by_id[pass_id]["inputs_from_passes"]:
            visit(dep)
        visiting.remove(pass_id)
        visited.add(pass_id)

    for pass_id in by_id:
        visit(pass_id)


def validate_synthesis(manifest: dict[str, Any], passes: list[dict[str, Any]]) -> dict[str, Any]:
    synthesis = manifest.get("synthesis", {})
    if not isinstance(synthesis, dict):
        raise DistillerManifestError("manifest.synthesis must be an object")
    enabled = bool(synthesis.get("enabled", False))
    input_passes = synthesis.get("input_passes", [])
    profile = synthesis.get("profile", "synthesis")
    output = synthesis.get("output", {})
    if enabled:
        if not isinstance(input_passes, list) or not input_passes:
            raise DistillerManifestError("synthesis.input_passes must be a non-empty list when enabled")
        known = {row["id"] for row in passes}
        for dep in input_passes:
            if dep not in known:
                raise DistillerManifestError(f"synthesis depends on missing pass {dep}")
    if not isinstance(profile, str) or profile not in profile_registry()["profiles"]:
        raise DistillerManifestError(f"unknown synthesis profile: {profile}")
    output = _validate_output(output, set())
    if output["artifact_type"] != "review_bundle":
        raise DistillerManifestError("synthesis output.artifact_type must be review_bundle")
    return {
        "enabled": enabled,
        "input_passes": list(input_passes),
        "profile": profile,
        "output": output,
    }


def validate_manifest(manifest: Any, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise DistillerManifestError("manifest must be a JSON object")
    if manifest.get("schema") != SUPPORTED_SCHEMA:
        raise DistillerManifestError("unsupported manifest schema")
    source_id = manifest.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise DistillerManifestError("manifest.source_id must be a non-empty string")
    inputs = validate_source_selection(manifest, repo_root=repo_root)
    chunking = validate_chunking(manifest)
    passes = validate_passes(manifest)
    synthesis = validate_synthesis(manifest, passes)
    return {
        "schema": SUPPORTED_SCHEMA,
        "source_id": source_id,
        "inputs": inputs,
        "chunking": chunking,
        "passes": passes,
        "synthesis": synthesis,
    }


def _split_lines(text: str) -> list[str]:
    lines = text.splitlines()
    return lines if lines else [""]


def _apply_line_ranges(lines: list[str], line_ranges: list[Any]) -> list[str]:
    if not line_ranges:
        return lines
    selected: list[str] = []
    for entry in line_ranges:
        if not isinstance(entry, list) or len(entry) != 2:
            raise DistillerManifestError("line_ranges entries must be [start, end]")
        start, end = entry
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
            raise DistillerManifestError("invalid line range")
        if end > len(lines):
            raise DistillerManifestError("line range outside source length")
        selected.extend(lines[start - 1 : end])
    return selected


def _chunk_lines(lines: list[str], target_chars: int, overlap: int, offset: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    start = min(max(offset, 0), len(lines))
    index = 0
    while start < len(lines):
        end = start
        current = len(lines[start]) + 1
        while end + 1 < len(lines):
            if current + len(lines[end + 1]) + 1 > target_chars:
                break
            end += 1
            current += len(lines[end]) + 1
        chunk_lines = lines[start : end + 1]
        chunks.append(
            {
                "chunk_index": index,
                "start_line": start + 1,
                "end_line": end + 1,
                "content": "\n".join(chunk_lines).rstrip() + "\n",
            }
        )
        if end >= len(lines) - 1:
            break
        next_start = end + 1 - max(overlap, 0)
        start = next_start if next_start > start else end + 1
        index += 1
    return chunks


def _select_chunks(chunks: list[dict[str, Any]], start_chunk: int | None, end_chunk: int | None, chunk_indices: list[Any]) -> list[dict[str, Any]]:
    selected = chunks
    if start_chunk is not None:
        selected = [chunk for chunk in selected if chunk["chunk_index"] + 1 >= start_chunk]
    if end_chunk is not None:
        selected = [chunk for chunk in selected if chunk["chunk_index"] + 1 <= end_chunk]
    if chunk_indices:
        wanted = {int(idx) for idx in chunk_indices}
        selected = [chunk for chunk in selected if (chunk["chunk_index"] + 1) in wanted]
    return selected


def _make_source_manifest(source_records: list[dict[str, Any]], selection: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SUPPORTED_SCHEMA,
        "selected_sources": source_records,
        "selection": {
            "include_globs": selection["include_globs"],
            "exclude_globs": selection["exclude_globs"],
            "line_ranges": selection["line_ranges"],
            "chunk_indices": selection["chunk_indices"],
        },
    }


def _render_focus_prompt(profile: str, profile_payload: dict[str, Any], selected_text: str, prior_inputs: list[dict[str, Any]], synthesis: bool = False) -> str:
    sections = [
        "# Context Distiller Focus Prompt",
        "",
        f"Profile: {profile}",
        f"Objective: {profile_payload['objective']}",
        "",
        "## Evidence To Extract",
        profile_payload["evidence_to_extract"],
        "",
        "## Ignore",
        profile_payload["ignore"],
        "",
        "## Required Output",
        json.dumps(profile_payload["required_output"], indent=2, sort_keys=True),
        "",
        "## Uncertainty Handling",
        profile_payload["uncertainty_handling"],
        "",
        "## Contradiction Handling",
        profile_payload["contradiction_handling"],
        "",
        "## Maximum Authority",
        profile_payload["maximum_authority"],
        "",
        "## Prior Pass Inputs",
        json.dumps(prior_inputs, indent=2, sort_keys=True),
        "",
        "## Selected Input",
        selected_text,
    ]
    if synthesis:
        sections.insert(0, "# Context Distiller Synthesis Prompt")
    return "\n".join(sections).rstrip() + "\n"


def _normalize_review_output(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DistillerManifestError("model output must be a JSON object")
    required_top = {"verdict", "review_state", "changed_paths", "verification", "evidence", "notes"}
    if set(payload) != required_top:
        missing = sorted(required_top - set(payload))
        extra = sorted(set(payload) - required_top)
        raise DistillerManifestError(f"model output keys mismatch: missing={missing}, extra={extra}")
    verdict = payload["verdict"]
    review_state = payload["review_state"]
    if verdict not in {"pass", "fail", "incomplete"}:
        raise DistillerManifestError("invalid verdict")
    if review_state not in {"complete", "incomplete"}:
        raise DistillerManifestError("invalid review_state")
    if not isinstance(payload["changed_paths"], list) or not all(isinstance(item, str) for item in payload["changed_paths"]):
        raise DistillerManifestError("changed_paths must be a list of strings")
    verification = payload["verification"]
    if not isinstance(verification, dict):
        raise DistillerManifestError("verification must be an object")
    expected_verification = {
        "raw_output_structure": {"pass", "fail", "not_applicable"},
        "changed_files_against_allowlist": {"pass", "fail", "not_applicable"},
        "narrowest_relevant_local_checks": {"pass", "fail", "not_run", "not_applicable"},
    }
    if set(verification) != set(expected_verification):
        raise DistillerManifestError("verification keys mismatch")
    for key, allowed in expected_verification.items():
        if verification[key] not in allowed:
            raise DistillerManifestError(f"invalid verification value for {key}")
    evidence = payload["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise DistillerManifestError("evidence must be a non-empty list")
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"path", "observation", "existence"}:
            raise DistillerManifestError("evidence items must contain exact keys path, observation, existence")
        if not isinstance(item["path"], str) or not item["path"] or item["path"].startswith("/") or ".." in Path(item["path"]).parts:
            raise DistillerManifestError("evidence path must be a repository-relative path")
        if not isinstance(item["observation"], str) or not item["observation"].strip():
            raise DistillerManifestError("evidence observation must be nonempty")
        if item["existence"] not in {"present", "absent"}:
            raise DistillerManifestError("evidence existence must be present or absent")
    if not isinstance(payload["notes"], str) or not payload["notes"].strip():
        raise DistillerManifestError("notes must be nonempty")
    return payload


def _classify_review_output(payload: dict[str, Any]) -> str:
    verdict = payload["verdict"]
    review_state = payload["review_state"]
    if verdict in {"pass", "fail"} and review_state == "complete":
        return "ready_for_review"
    if verdict == "incomplete" and review_state == "incomplete":
        return "incomplete"
    raise DistillerManifestError("semantic output does not match the required verdict/review_state pairing")


def _call_model(prompt_path: Path, out_path: Path, *, base_url: str, model: str, timeout: int, max_tokens: int) -> dict[str, Any]:
    cmd = [
        "python3",
        os.fspath(REPO_ROOT / "local_harness" / "icm_call.py"),
        "handoff",
        "--api",
        "openai-chat",
        "--base-url",
        base_url,
        "--model",
        model,
        "--timeout",
        str(timeout),
        "--metadata-out",
        os.fspath(out_path),
        "--max-tokens",
        str(max_tokens),
    ]
    with prompt_path.open("r", encoding="utf-8") as stdin:
        proc = subprocess.run(cmd, stdin=stdin, capture_output=True, text=True)
    if proc.returncode != 0:
        raise DistillerManifestError(f"model call failed: {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise DistillerManifestError(f"model output not valid JSON: {exc}") from exc


def _build_pass_dirs(job_dir: Path, pass_id: str, attempt: int) -> Path:
    run_dir = job_dir / "passes" / pass_id / f"attempt_{attempt:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _next_attempt_number(pass_root: Path) -> int:
    attempts = []
    if pass_root.is_dir():
        for child in pass_root.iterdir():
            if child.is_dir() and child.name.startswith("attempt_"):
                try:
                    attempts.append(int(child.name.split("_", 1)[1]))
                except (IndexError, ValueError):
                    continue
    return max(attempts, default=0) + 1


def _select_source_text(selection: dict[str, Any], source_manifest: dict[str, Any], repo_root: Path = REPO_ROOT) -> tuple[str, dict[str, Any]]:
    selected_lines: list[str] = []
    included: list[str] = []
    excluded: list[str] = []
    for record in source_manifest["selected_sources"]:
        rel = record["source"]
        abs_path = Path(record["abs_path"])
        text = abs_path.read_text(encoding="utf-8")
        lines = _split_lines(text)
        lines = _apply_line_ranges(lines, selection["line_ranges"])
        selected_lines.append(f"## Source: {rel}\n")
        selected_lines.extend(lines)
        selected_lines.append("")
        included.append(rel)
    return "\n".join(selected_lines).rstrip() + "\n", {"included_sources": included, "excluded_sources": excluded}


def _profile_payload(profile: str) -> dict[str, Any]:
    return profile_registry()["profiles"][profile]


def render_plan(manifest: dict[str, Any], repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    validated = validate_manifest(manifest, repo_root=repo_root)
    source_manifest = _make_source_manifest(validated["inputs"]["selected_sources"], validated["inputs"])
    plan_passes = []
    for row in validated["passes"]:
        profile_payload = _profile_payload(row["profile"])
        plan_passes.append(
            {
                "id": row["id"],
                "profile": row["profile"],
                "questions": list(row["questions"]),
                "inputs_from_passes": list(row["inputs_from_passes"]),
                "output": row["output"],
                "expected_output_path": f"passes/{row['id']}/attempt_001/{row['output']['filename']}",
                "authority": {
                    "maximum_authority": profile_payload["maximum_authority"],
                    "review_boundary": profile_payload["review_boundary"],
                },
            }
        )
    plan = {
        "schema": SUPPORTED_SCHEMA,
        "source_id": validated["source_id"],
        "source_manifest": source_manifest,
        "chunking": validated["chunking"],
        "passes": plan_passes,
        "synthesis": validated["synthesis"],
        "review_boundary": "review-only; no canonical context modification",
        "selected_source_hashes": [record["sha256"] for record in validated["inputs"]["selected_sources"]],
        "excluded_inputs": validated["inputs"]["exclude_globs"],
    }
    return plan


def _job_id(source_id: str) -> str:
    return f"context_distiller_{source_id}"


def _selected_input_bytes(selected_input: str) -> str:
    return _sha256_bytes(selected_input.encode("utf-8"))


def run_manifest_job(
    manifest: dict[str, Any],
    *,
    out_root: Path = DEFAULT_JOB_ROOT,
    repo_root: Path = REPO_ROOT,
    base_url: str = "http://127.0.0.1:8081/v1",
    model: str = "local-model",
    timeout: int = 900,
    max_tokens: int = 2048,
    model_runner: Callable[[Path, Path], dict[str, Any]] | None = None,
    plan_only: bool = False,
) -> dict[str, Any]:
    validated = validate_manifest(manifest, repo_root=repo_root)
    job_dir = out_root / _job_id(validated["source_id"])
    job_dir.mkdir(parents=True, exist_ok=True)
    plan = render_plan(validated, repo_root=repo_root)
    _write_json(job_dir / "job_manifest.json", validated)
    _write_json(job_dir / "plan.json", plan)
    status = {
        "state": "planned" if plan_only else "running",
        "schema": SUPPORTED_SCHEMA,
        "source_id": validated["source_id"],
        "ready_for_review": False,
        "queue_exhausted": False,
        "passes_completed": 0,
        "passes_planned": len(validated["passes"]),
    }
    _write_json(job_dir / "status.json", status)
    review_dir = job_dir / "review_bundle"
    review_dir.mkdir(parents=True, exist_ok=True)

    source_selection = validated["inputs"]
    source_manifest = _make_source_manifest(source_selection["selected_sources"], source_selection)
    selected_text, selected_meta = _select_source_text(source_selection, source_manifest)
    source_manifest_path = job_dir / "source_manifest.json"
    _write_json(source_manifest_path, source_manifest)
    attempt_counts: dict[str, int] = {}
    pass_outputs: dict[str, dict[str, Any]] = {}
    selected_source_hashes = [item["sha256"] for item in source_selection["selected_sources"]]
    pass_artifact_hashes: dict[str, dict[str, str]] = {}
    ready_passes = 0
    incomplete_passes = 0

    if plan_only:
        return {
            "job_dir": os.fspath(job_dir),
            "plan": plan,
            "status": status,
        }

    runner = model_runner or (lambda prompt_path, metadata_out: _call_model(
        prompt_path,
        metadata_out,
        base_url=base_url,
        model=model,
        timeout=timeout,
        max_tokens=max_tokens,
    ))

    for pass_row in validated["passes"]:
        pass_id = pass_row["id"]
        pass_root = job_dir / "passes" / pass_id
        attempt_counts[pass_id] = _next_attempt_number(pass_root)
        pass_dir = _build_pass_dirs(job_dir, pass_id, attempt_counts[pass_id])
        if attempt_counts[pass_id] > 1:
            prior_dir = pass_root / f"attempt_{attempt_counts[pass_id] - 1:03d}"
            _write_json(
                pass_dir / "recovery_manifest.json",
                {
                    "pass_id": pass_id,
                    "prior_directory": os.fspath(prior_dir),
                    "current_directory": os.fspath(pass_dir),
                    "next_attempt_number": attempt_counts[pass_id],
                    "recovery_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            )
        prior_inputs = [pass_outputs[dep] for dep in pass_row["inputs_from_passes"] if dep in pass_outputs]
        profile_payload = _profile_payload(pass_row["profile"])
        prompt_text = _render_focus_prompt(
            pass_row["profile"],
            profile_payload,
            selected_text,
            prior_inputs,
        )
        (pass_dir / "selected_input.txt").write_text(selected_text, encoding="utf-8")
        (pass_dir / "prompt.md").write_text(prompt_text, encoding="utf-8")
        pass_manifest = {
            "schema": SUPPORTED_SCHEMA,
            "pass": pass_row,
            "source_hashes": selected_source_hashes,
            "selected_input_sha256": _selected_input_bytes(selected_text),
            "effective_chunking": validated["chunking"],
        }
        _write_json(pass_dir / "pass_manifest.json", pass_manifest)
        _write_json(pass_dir / "source_manifest.json", source_manifest)
        raw_output_path = pass_dir / "model_output.raw.json"
        metadata_path = pass_dir / "model_metadata.json"
        raw_output = runner(pass_dir / "prompt.md", metadata_path)
        _write_json(raw_output_path, raw_output)
        structured = _normalize_review_output(raw_output)
        semantic_state = _classify_review_output(structured)
        if semantic_state == "ready_for_review":
            ready_passes += 1
        else:
            incomplete_passes += 1
        _write_json(pass_dir / "model_content.json", structured)
        validation = {
            "raw_output_structure": "pass",
            "changed_files_against_allowlist": "not_applicable",
            "narrowest_relevant_local_checks": "not_run",
            "semantic_state": semantic_state,
        }
        _write_json(pass_dir / "validation.json", validation)
        _write_json(
            pass_dir / "metrics.json",
            {
                "attempt": attempt_counts[pass_id],
                "source_hashes": selected_source_hashes,
                "selected_input_sha256": _selected_input_bytes(selected_text),
                "effective_chunking": validated["chunking"],
            },
        )
        _write_json(
            pass_dir / "provenance.json",
            {
                "source_manifest": os.fspath(source_manifest_path),
                "selected_input": os.fspath(pass_dir / "selected_input.txt"),
                "prompt": os.fspath(pass_dir / "prompt.md"),
                "raw_output": os.fspath(raw_output_path),
                "metadata": os.fspath(metadata_path),
                "model_content": os.fspath(pass_dir / "model_content.json"),
                "validation": os.fspath(pass_dir / "validation.json"),
            },
        )
        pass_outputs[pass_id] = structured
        pass_artifact_hashes[pass_id] = {
            "pass_manifest.json": _sha256_path(pass_dir / "pass_manifest.json"),
            "source_manifest.json": _sha256_path(pass_dir / "source_manifest.json"),
            "selected_input.txt": _sha256_path(pass_dir / "selected_input.txt"),
            "prompt.md": _sha256_path(pass_dir / "prompt.md"),
            "model_output.raw.json": _sha256_path(raw_output_path),
            "model_metadata.json": _sha256_path(metadata_path),
            "model_content.json": _sha256_path(pass_dir / "model_content.json"),
            "validation.json": _sha256_path(pass_dir / "validation.json"),
            "metrics.json": _sha256_path(pass_dir / "metrics.json"),
            "provenance.json": _sha256_path(pass_dir / "provenance.json"),
        }
        if (pass_dir / "recovery_manifest.json").is_file():
            pass_artifact_hashes[pass_id]["recovery_manifest.json"] = _sha256_path(pass_dir / "recovery_manifest.json")

    synthesis_result: dict[str, Any] | None = None
    if validated["synthesis"]["enabled"]:
        synthesis_dir = job_dir / "synthesis"
        synthesis_dir.mkdir(parents=True, exist_ok=True)
        synthesis_inputs = [
            {"pass_id": pid, "output": pass_outputs[pid]}
            for pid in validated["synthesis"]["input_passes"]
        ]
        synthesis_prompt = _render_focus_prompt(
            "synthesis",
            _profile_payload("synthesis"),
            selected_text,
            synthesis_inputs,
            synthesis=True,
        )
        (synthesis_dir / "selected_input.txt").write_text(selected_text, encoding="utf-8")
        (synthesis_dir / "prompt.md").write_text(synthesis_prompt, encoding="utf-8")
        synthesis_raw_path = synthesis_dir / "model_output.raw.json"
        synthesis_meta_path = synthesis_dir / "model_metadata.json"
        synthesis_raw = runner(synthesis_dir / "prompt.md", synthesis_meta_path)
        _write_json(synthesis_raw_path, synthesis_raw)
        synthesis_result = _normalize_review_output(synthesis_raw)
        synthesis_state = _classify_review_output(synthesis_result)
        if synthesis_state == "ready_for_review":
            ready_passes += 1
        else:
            incomplete_passes += 1
        _write_json(synthesis_dir / "model_content.json", synthesis_result)
        _write_json(
            synthesis_dir / "validation.json",
            {
                "raw_output_structure": "pass",
                "changed_files_against_allowlist": "not_applicable",
                "narrowest_relevant_local_checks": "not_run",
                "semantic_state": synthesis_state,
            },
        )
        _write_json(
            synthesis_dir / "provenance.json",
            {
            "consumed_pass_artifacts": {
                pid: pass_artifact_hashes[pid]
                for pid in validated["synthesis"]["input_passes"]
            },
        },
        )
        review_dir.mkdir(parents=True, exist_ok=True)
        _write_json(review_dir / validated["synthesis"]["output"]["filename"], synthesis_result)

    status = {
        "state": "ready_for_review" if ready_passes else "blocked",
        "schema": SUPPORTED_SCHEMA,
        "source_id": validated["source_id"],
        "ready_for_review": bool(ready_passes),
        "queue_exhausted": True,
        "passes_completed": len(pass_outputs),
        "passes_incomplete": incomplete_passes,
        "passes_planned": len(validated["passes"]),
        "review_bundle": os.fspath(review_dir),
    }
    _write_json(job_dir / "status.json", status)
    return {
        "job_dir": os.fspath(job_dir),
        "plan": plan,
        "status": status,
        "synthesis_result": synthesis_result,
    }


def build_legacy_manifest(source_id: str, source_file: str, short_title: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    source_path = _safe_repo_relative(source_file)
    return {
        "schema": SUPPORTED_SCHEMA,
        "source_id": source_id,
        "inputs": {
            "sources": [os.fspath(source_path)],
            "include_globs": [],
            "exclude_globs": [],
            "line_ranges": [],
            "chunk_indices": [],
        },
        "chunking": dict(DEFAULT_CHUNKING),
        "passes": [
            {
                "id": "comprehensive",
                "profile": "comprehensive",
                "questions": [],
                "inputs_from_passes": [],
                "output": {"artifact_type": "review_bundle", "filename": f"{short_title}.md"},
            }
        ],
        "synthesis": {
            "enabled": False,
            "input_passes": [],
            "profile": "synthesis",
            "output": {"artifact_type": "review_bundle", "filename": f"{short_title}.md"},
        },
    }


def load_manifest_path(manifest_path: Path) -> dict[str, Any]:
    return _load_json(manifest_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--out-root", type=Path, default=DEFAULT_JOB_ROOT)
    parser.add_argument("--base-url", default="http://127.0.0.1:8081/v1")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("source_id", nargs="?")
    parser.add_argument("source_file", nargs="?")
    parser.add_argument("short_title", nargs="?")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.manifest:
        manifest = load_manifest_path(args.manifest)
    else:
        if not (args.source_id and args.source_file and args.short_title):
            raise SystemExit("usage: run_context_distiller.sh --manifest MANIFEST [--plan-only]")
        manifest = build_legacy_manifest(args.source_id, args.source_file, args.short_title)
    result = run_manifest_job(
        manifest,
        out_root=args.out_root,
        repo_root=REPO_ROOT,
        base_url=args.base_url,
        model=args.model,
        timeout=args.timeout,
        max_tokens=args.max_tokens,
        plan_only=args.plan_only,
    )
    print(json.dumps(result["plan"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
