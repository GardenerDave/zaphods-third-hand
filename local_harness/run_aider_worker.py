#!/usr/bin/env python3
"""Execute a supervised Aider run into the audited run-folder shape."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from aider_prep import (
    build_aider_read_inputs,
    build_effective_prompt,
    build_inline_read_digest,
    build_preflight,
    build_preflight_output,
    missing_inputs,
    prepare_read_inputs,
    resolve_project_path,
    scaffold_required_files,
    should_inline_read_digest,
    write_if_missing,
)
from aider_runtime import (
    build_aider_command,
    build_aider_env,
    build_chat_completions_url,
    build_metrics,
    build_output_text,
    parse_aider_event_log,
    render_attempt_outputs,
    should_retry_after_connection_failure,
    summarize_aider_output,
    archive_attempt_artifacts,
    DEFAULT_PREWARM_PROMPT,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AIDER_PYTHON = str(PROJECT_ROOT / "_aider-chat" / "bin" / "python")
DEFAULT_SUBPROCESS_TIMEOUT_SLACK_SECONDS = 20
REQUIRED_INPUT_FILES = ("TASK.md", "INPUT.md", "MODEL_REQUEST.md")
DIRECT_EDIT_MAX_PROMPT_CHARS = 1200
DIRECT_EDIT_EXCERPT_PATCH_MAX_PROMPT_CHARS = 4096
DIRECT_EDIT_MULTI_FILE_MAX_PROMPT_CHARS = 2400
DIRECT_EDIT_MAX_FILE_BYTES = 24576
DIRECT_EDIT_MAX_SELECTED_FILES = 4
DIRECT_EDIT_HEADING_RE = re.compile(r"(?is)^\s*#\s*Model Request\s*")
DIRECT_EDIT_FINAL_RE = re.compile(r"(?is)\s*[-*]\s*Edit only the listed file(?:s)?\.?\s*$")
DIRECT_EDIT_REPLACE_RE = re.compile(
    r"(?is)^\s*[-*]\s*In\s+`([^`]+)`\s*,\s*(?:update|change|replace)\s+`([^`]+)`\s+(?:to|with)\s+`([^`]+)`\s*\.\s*"
)
DIRECT_EDIT_INSERT_RE = re.compile(
    r"(?is)^\s*[-*]\s*In\s+`([^`]+)`\s*,\s*insert\s+`([^`]+)`\s+(before|after)\s+`([^`]+)`\s*\.\s*"
)
DIRECT_EDIT_BLOCK_RE = re.compile(
    r"(?is)^\s*[-*]\s*In\s+`([^`]+)`\s*,\s*replace\s+the\s+block\s+from\s+`([^`]+)`\s+through\s+`([^`]+)`\s+with\s+`([^`]+)`\s*\.\s*"
)
DIRECT_EDIT_EXCERPT_PATCH_RE = re.compile(
    r"(?is)^\s*[-*]\s*In\s+`([^`]+)`\s*,\s*apply\s+excerpt\s+patches\s*\.\s*```(?:[a-zA-Z0-9_-]+)?\n(.*?)\n```\s*"
)
DIRECT_EDIT_EXCERPT_HUNK_RE = re.compile(
    r"(?s)^\s*<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE\s*"
)
REVIEW_STUB = """# Manager Review

- Status: pending
- Notes:
"""
ACCEPTED_STUB = """# Accepted Output

- Status: pending
"""
PROFILE_DEFAULTS: dict[str, dict[str, Any]] = {
    "gemma-local": {
        "aider_python": DEFAULT_AIDER_PYTHON,
        "model": "openai/gemma4",
        "openai_api_base": "http://localhost:8083/v1",
        "map_tokens": 0,
        "timeout": 90,
        "stream": False,
        "compact_request": True,
        "compact_request_max_chars": 1200,
        "read_head_lines": 10,
        "fit_read_context": True,
        "bundle_read_inputs": True,
        "inline_read_digest": True,
        "inline_read_digest_token_threshold": 256,
        "inline_read_digest_chars_per_file": 240,
        "context_window": 8192,
        "completion_reserve": 1536,
        "protocol_overhead_tokens": 1400,
        "minimal_prompt": True,
        "skip_example_chat": True,
        "capture_debug_artifacts": True,
        "prewarm": True,
        "manager_retries": 1,
        "direct_edit_short_circuit": True,
        "edit_format": None,
    }
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_folder")
    parser.add_argument("files", nargs="*")
    parser.add_argument("--profile", default="gemma-local")
    parser.add_argument("--read", action="append", default=[])
    parser.add_argument("--aider-python")
    parser.add_argument("--model")
    parser.add_argument("--openai-api-base")
    parser.add_argument("--map-tokens", type=int)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--edit-format")
    parser.add_argument("--context-window", type=int)
    parser.add_argument("--completion-reserve", type=int)
    parser.add_argument("--protocol-overhead-tokens", type=int)
    parser.add_argument("--compact-request-max-chars", type=int)
    parser.add_argument("--read-head-lines", type=int)
    parser.add_argument("--inline-read-digest-token-threshold", type=int)
    parser.add_argument("--inline-read-digest-chars-per-file", type=int)
    parser.add_argument("--manager-retries", type=int)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--allow-over-budget", action="store_true")
    parser.add_argument("--init-stubs", action="store_true")
    parser.add_argument("--compact-request", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--fit-read-context", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--bundle-read-inputs", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--inline-read-digest", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--minimal-prompt", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--skip-example-chat", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--capture-debug-artifacts", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--direct-edit-short-circuit", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--prewarm", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--stream", action=argparse.BooleanOptionalAction, default=None)
    return parser


def parse_args(parser: argparse.ArgumentParser, argv: list[str] | None = None) -> argparse.Namespace:
    if hasattr(parser, "parse_intermixed_args"):
        return parser.parse_intermixed_args(argv)
    return parser.parse_args(argv)


def apply_profile_defaults(args: argparse.Namespace) -> argparse.Namespace:
    defaults = PROFILE_DEFAULTS.get(args.profile, {})
    for key, value in defaults.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)

    if not args.aider_python:
        args.aider_python = DEFAULT_AIDER_PYTHON
    if not args.read:
        args.read = []
    return args


def run_endpoint_prewarm(args: argparse.Namespace, env: dict[str, str]) -> dict[str, Any] | None:
    if not args.prewarm or not args.openai_api_base:
        return None

    url = build_chat_completions_url(args.openai_api_base)
    timeout_seconds = min(max(args.timeout or 30, 1), 30)
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": DEFAULT_PREWARM_PROMPT}],
        "temperature": 0,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    api_key = env.get("OPENAI_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    artifact: dict[str, Any] = {
        "attempted": True,
        "url": url,
        "model": args.model,
        "timeout_seconds": timeout_seconds,
    }
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            artifact["http_status"] = getattr(response, "status", None)
    except Exception as err:
        artifact["elapsed_seconds"] = time.monotonic() - start
        artifact["success"] = False
        artifact["error_type"] = type(err).__name__
        artifact["error"] = str(err)
        return artifact

    artifact["elapsed_seconds"] = time.monotonic() - start
    artifact["success"] = True
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        parsed = None
    artifact["response_preview"] = (
        parsed.get("choices", [{}])[0].get("message", {}).get("content", "")[:200]
        if isinstance(parsed, dict)
        else body[:200]
    )
    return artifact


def scaffold_manager_files(run_folder: Path) -> None:
    write_if_missing(run_folder / "REVIEW.md", REVIEW_STUB)
    write_if_missing(run_folder / "ACCEPTED.md", ACCEPTED_STUB)


def build_error_output(title: str, details: list[str]) -> str:
    lines = [title, ""]
    lines.extend(details)
    return "\n".join(lines).rstrip() + "\n"


def coerce_subprocess_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_aider_subprocess(command: list[str], args: argparse.Namespace, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    timeout_seconds = None
    if args.timeout is not None:
        timeout_seconds = max(args.timeout + DEFAULT_SUBPROCESS_TIMEOUT_SLACK_SECONDS, 1)

    try:
        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as err:
        stdout_text = coerce_subprocess_text(err.stdout)
        stderr_text = coerce_subprocess_text(err.stderr)
        manager_note = f"Manager timeout expired after {timeout_seconds} seconds."
        stderr_text = f"{stderr_text.rstrip()}\n{manager_note}\n" if stderr_text else manager_note + "\n"
        return subprocess.CompletedProcess(
            args=command,
            returncode=124,
            stdout=stdout_text,
            stderr=stderr_text,
        )


def summarize_direct_edit_request(request: dict[str, Any]) -> dict[str, Any]:
    operations = list(request["operations"])
    target_files = list(dict.fromkeys(operation["file"] for operation in operations))
    contains_excerpt_patch = any(operation["operation"] == "excerpt_patch" for operation in operations)
    contains_non_excerpt_operation = any(operation["operation"] != "excerpt_patch" for operation in operations)
    if len(operations) == 1:
        operation_name = operations[0]["operation"]
    elif contains_excerpt_patch and contains_non_excerpt_operation:
        operation_name = "mixed_batch"
    elif len(target_files) > 1:
        operation_name = "multi_file_batch"
    else:
        operation_name = "batch"
    return {
        "operation": operation_name,
        "operation_count": len(operations),
        "operation_types": [operation["operation"] for operation in operations],
        "target_files": target_files,
        "target_file_count": len(target_files),
        "contains_excerpt_patch": contains_excerpt_patch,
    }


def direct_edit_prompt_limit(request: dict[str, Any]) -> int:
    summary = summarize_direct_edit_request(request)
    if summary["contains_excerpt_patch"]:
        return DIRECT_EDIT_EXCERPT_PATCH_MAX_PROMPT_CHARS
    if summary["target_file_count"] > 1:
        return DIRECT_EDIT_MULTI_FILE_MAX_PROMPT_CHARS
    return DIRECT_EDIT_MAX_PROMPT_CHARS


def resolve_selected_direct_edit_file(prompt_file: str, selected_files: list[str]) -> str | None:
    prompt_path = Path(prompt_file)
    for selected in selected_files:
        if Path(selected) == prompt_path:
            return selected
    return None


def direct_edit_request_matches_selected_files(request: dict[str, Any], selected_files: list[str]) -> bool:
    summary = summarize_direct_edit_request(request)
    if summary["target_file_count"] != len(selected_files):
        return False
    selected_paths = {Path(selected) for selected in selected_files}
    target_paths = {Path(target) for target in summary["target_files"]}
    return target_paths == selected_paths


def parse_excerpt_patch_hunks(patch_body: str) -> list[dict[str, str]] | None:
    patch_remaining = patch_body
    patches: list[dict[str, str]] = []
    while patch_remaining.strip():
        hunk_match = DIRECT_EDIT_EXCERPT_HUNK_RE.match(patch_remaining)
        if hunk_match is None:
            return None
        old_text, new_text = hunk_match.groups()
        patches.append(
            {
                "search": old_text,
                "replace": new_text,
            }
        )
        patch_remaining = patch_remaining[hunk_match.end() :]
    if not patches:
        return None
    return patches


def decode_direct_edit_literal(text: str) -> str:
    return (
        text.replace("\\r", "\r")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\\\", "\\")
    )


def parse_direct_edit_request(prompt_text: str, selected_files: list[str]) -> dict[str, Any] | None:
    if not selected_files:
        return None

    normalized = DIRECT_EDIT_HEADING_RE.sub("", prompt_text.strip(), count=1).lstrip()
    final_match = DIRECT_EDIT_FINAL_RE.search(normalized)
    if final_match is None:
        return None

    remaining = normalized[: final_match.start()]
    operations: list[dict[str, Any]] = []
    while remaining.strip():
        excerpt_patch_match = DIRECT_EDIT_EXCERPT_PATCH_RE.match(remaining)
        if excerpt_patch_match:
            prompt_file, patch_body = excerpt_patch_match.groups()
            matched_file = resolve_selected_direct_edit_file(prompt_file, selected_files)
            if matched_file is None:
                return None
            patches = parse_excerpt_patch_hunks(patch_body)
            if patches is None:
                return None
            operations.append(
                {
                    "file": matched_file,
                    "operation": "excerpt_patch",
                    "patches": patches,
                }
            )
            remaining = remaining[excerpt_patch_match.end() :]
            continue

        replace_match = DIRECT_EDIT_REPLACE_RE.match(remaining)
        if replace_match:
            prompt_file, old_text, new_text = replace_match.groups()
            matched_file = resolve_selected_direct_edit_file(prompt_file, selected_files)
            if matched_file is None:
                return None
            operations.append(
                {
                    "file": matched_file,
                    "operation": "replace",
                    "old": decode_direct_edit_literal(old_text),
                    "new": decode_direct_edit_literal(new_text),
                }
            )
            remaining = remaining[replace_match.end() :]
            continue

        insert_match = DIRECT_EDIT_INSERT_RE.match(remaining)
        if insert_match:
            prompt_file, new_text, position, anchor_text = insert_match.groups()
            matched_file = resolve_selected_direct_edit_file(prompt_file, selected_files)
            if matched_file is None:
                return None
            operations.append(
                {
                    "file": matched_file,
                    "operation": f"insert_{position.lower()}",
                    "anchor": decode_direct_edit_literal(anchor_text),
                    "new": decode_direct_edit_literal(new_text),
                }
            )
            remaining = remaining[insert_match.end() :]
            continue

        block_match = DIRECT_EDIT_BLOCK_RE.match(remaining)
        if block_match:
            prompt_file, start_anchor, end_anchor, new_text = block_match.groups()
            matched_file = resolve_selected_direct_edit_file(prompt_file, selected_files)
            if matched_file is None:
                return None
            operations.append(
                {
                    "file": matched_file,
                    "operation": "replace_block",
                    "start_anchor": decode_direct_edit_literal(start_anchor),
                    "end_anchor": decode_direct_edit_literal(end_anchor),
                    "new": decode_direct_edit_literal(new_text),
                }
            )
            remaining = remaining[block_match.end() :]
            continue

        return None

    if not operations:
        return None

    return {"operations": operations}


def evaluate_direct_edit_request(request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str] | None]:
    operations = list(request["operations"])
    summary = summarize_direct_edit_request(request)
    candidate: dict[str, Any] = {
        "eligible": False,
        "reason": None,
        **summary,
        "target_file": summary["target_files"][0] if summary["target_file_count"] == 1 else None,
        "operations": [],
        "file_details": [],
    }

    current_text_by_file: dict[str, str] = {}
    for target_file in summary["target_files"]:
        target_path = resolve_project_path(target_file)
        file_detail = {
            "file": target_file,
            "resolved_target_path": str(target_path),
            "file_exists": target_path.is_file(),
        }
        if not target_path.is_file():
            candidate["reason"] = "target_missing"
            candidate["failing_file"] = target_file
            candidate["file_details"].append(file_detail)
            if summary["target_file_count"] == 1:
                candidate["resolved_target_path"] = str(target_path)
                candidate["file_exists"] = False
            return (candidate, None)

        file_detail["file_bytes"] = target_path.stat().st_size
        file_detail["within_file_size_limit"] = file_detail["file_bytes"] <= DIRECT_EDIT_MAX_FILE_BYTES
        candidate["file_details"].append(file_detail)
        if not file_detail["within_file_size_limit"]:
            candidate["reason"] = "file_too_large"
            candidate["failing_file"] = target_file
            if summary["target_file_count"] == 1:
                candidate["resolved_target_path"] = str(target_path)
                candidate["file_exists"] = True
                candidate["file_bytes"] = file_detail["file_bytes"]
                candidate["within_file_size_limit"] = False
            return (candidate, None)

        current_text_by_file[target_file] = target_path.read_text(encoding="utf-8", errors="replace")

    if summary["target_file_count"] == 1 and candidate["file_details"]:
        only_file = candidate["file_details"][0]
        candidate["resolved_target_path"] = only_file["resolved_target_path"]
        candidate["file_exists"] = only_file["file_exists"]
        candidate["file_bytes"] = only_file["file_bytes"]
        candidate["within_file_size_limit"] = only_file["within_file_size_limit"]

    for index, operation in enumerate(operations, start=1):
        current_text = current_text_by_file[operation["file"]]
        summary: dict[str, Any] = {
            "index": index,
            "operation": operation["operation"],
            "file": operation["file"],
        }
        if operation["operation"] == "replace":
            match_count = current_text.count(operation["old"])
            summary["match_count"] = match_count
            if match_count != 1:
                candidate["reason"] = "no_unique_match"
                candidate["failing_operation_index"] = index
                candidate["failing_file"] = operation["file"]
                candidate["operations"].append(summary)
                return (candidate, None)
            current_text = current_text.replace(operation["old"], operation["new"], 1)
        elif operation["operation"] in {"insert_after", "insert_before"}:
            match_count = current_text.count(operation["anchor"])
            summary["match_count"] = match_count
            if match_count != 1:
                candidate["reason"] = "no_unique_match"
                candidate["failing_operation_index"] = index
                candidate["failing_file"] = operation["file"]
                candidate["operations"].append(summary)
                return (candidate, None)
            if operation["operation"] == "insert_after":
                current_text = current_text.replace(operation["anchor"], operation["anchor"] + operation["new"], 1)
            else:
                current_text = current_text.replace(operation["anchor"], operation["new"] + operation["anchor"], 1)
        elif operation["operation"] == "replace_block":
            start_count = current_text.count(operation["start_anchor"])
            end_count = current_text.count(operation["end_anchor"])
            summary["start_anchor_match_count"] = start_count
            summary["end_anchor_match_count"] = end_count
            if start_count != 1:
                candidate["reason"] = "no_unique_start_anchor"
                candidate["failing_operation_index"] = index
                candidate["failing_file"] = operation["file"]
                candidate["operations"].append(summary)
                return (candidate, None)
            if end_count != 1:
                candidate["reason"] = "no_unique_end_anchor"
                candidate["failing_operation_index"] = index
                candidate["failing_file"] = operation["file"]
                candidate["operations"].append(summary)
                return (candidate, None)
            start_idx = current_text.find(operation["start_anchor"])
            end_idx = current_text.find(operation["end_anchor"])
            summary["anchor_order_valid"] = start_idx <= end_idx
            if end_idx < start_idx:
                candidate["reason"] = "invalid_block_order"
                candidate["failing_operation_index"] = index
                candidate["failing_file"] = operation["file"]
                candidate["operations"].append(summary)
                return (candidate, None)
            block_end = end_idx + len(operation["end_anchor"])
            summary["block_span_chars"] = block_end - start_idx
            current_text = current_text[:start_idx] + operation["new"] + current_text[block_end:]
        elif operation["operation"] == "excerpt_patch":
            summary["patch_count"] = len(operation["patches"])
            patch_summaries: list[dict[str, Any]] = []
            for patch_index, patch in enumerate(operation["patches"], start=1):
                match_count = current_text.count(patch["search"])
                patch_summary = {
                    "patch_index": patch_index,
                    "match_count": match_count,
                }
                patch_summaries.append(patch_summary)
                if match_count != 1:
                    candidate["reason"] = "no_unique_patch_match"
                    candidate["failing_operation_index"] = index
                    candidate["failing_file"] = operation["file"]
                    summary["patch_summaries"] = patch_summaries
                    candidate["operations"].append(summary)
                    return (candidate, None)
                current_text = current_text.replace(patch["search"], patch["replace"], 1)
            summary["patch_summaries"] = patch_summaries
        else:
            candidate["reason"] = "unsupported_operation"
            candidate["failing_operation_index"] = index
            candidate["failing_file"] = operation["file"]
            candidate["operations"].append(summary)
            return (candidate, None)

        current_text_by_file[operation["file"]] = current_text
        candidate["operations"].append(summary)

    candidate["eligible"] = True
    candidate["reason"] = "eligible"
    return (candidate, current_text_by_file)


def classify_direct_edit_candidate(prompt_text: str, selected_files: list[str]) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "eligible": False,
        "reason": None,
        "operation": None,
        "selected_file_count": len(selected_files),
        "selected_file_limit": DIRECT_EDIT_MAX_SELECTED_FILES,
        "prompt_char_count": len(prompt_text),
        "prompt_char_limit": DIRECT_EDIT_MAX_PROMPT_CHARS,
        "file_size_limit_bytes": DIRECT_EDIT_MAX_FILE_BYTES,
        "prompt_matches_pattern": False,
        "target_file": selected_files[0] if len(selected_files) == 1 else None,
        "file_exists": None,
        "file_bytes": None,
        "within_file_size_limit": None,
        "unique_match_count": None,
    }
    if not selected_files:
        candidate["reason"] = "requires_selected_files"
        return candidate
    if len(selected_files) > DIRECT_EDIT_MAX_SELECTED_FILES:
        candidate["reason"] = "too_many_selected_files"
        return candidate

    request = parse_direct_edit_request(prompt_text, selected_files)
    if request is None:
        if len(prompt_text) > DIRECT_EDIT_EXCERPT_PATCH_MAX_PROMPT_CHARS:
            candidate["reason"] = "prompt_too_long"
            candidate["prompt_char_limit"] = DIRECT_EDIT_EXCERPT_PATCH_MAX_PROMPT_CHARS
            return candidate
        candidate["reason"] = "prompt_pattern_mismatch"
        return candidate

    candidate.update(summarize_direct_edit_request(request))
    candidate["prompt_matches_pattern"] = True
    candidate["prompt_char_limit"] = direct_edit_prompt_limit(request)
    if len(prompt_text) > candidate["prompt_char_limit"]:
        candidate["reason"] = "prompt_too_long"
        return candidate
    if not direct_edit_request_matches_selected_files(request, selected_files):
        candidate["reason"] = "selected_file_mismatch"
        return candidate

    evaluated_candidate, _ = evaluate_direct_edit_request(request)
    candidate.update(evaluated_candidate)
    return candidate


def try_direct_edit_fallback(run_folder: Path, prompt_text: str, selected_files: list[str]) -> dict[str, Any] | None:
    if not selected_files or len(selected_files) > DIRECT_EDIT_MAX_SELECTED_FILES:
        return None

    request = parse_direct_edit_request(prompt_text, selected_files)
    if request is None:
        return None
    if len(prompt_text) > direct_edit_prompt_limit(request):
        return None
    if not direct_edit_request_matches_selected_files(request, selected_files):
        return None

    candidate, updated_text_by_file = evaluate_direct_edit_request(request)
    if candidate["reason"] == "target_missing":
        return None
    if candidate["reason"] == "file_too_large":
        return None
    if candidate["reason"] in {
        "no_unique_match",
        "no_unique_patch_match",
        "no_unique_start_anchor",
        "no_unique_end_anchor",
        "invalid_block_order",
        "unsupported_operation",
    }:
        (run_folder / "AIDER_DIRECT_EDIT.json").write_text(
            json.dumps(
                {
                    "triggered": False,
                    "status": candidate["reason"],
                    "operation": candidate["operation"],
                    "operation_count": candidate["operation_count"],
                    "operation_types": candidate["operation_types"],
                    "file": candidate["target_file"],
                    "target_files": candidate["target_files"],
                    "operations": candidate["operations"],
                    "failing_operation_index": candidate.get("failing_operation_index"),
                    "failing_file": candidate.get("failing_file"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "triggered": False,
            "eligible": True,
            "status": candidate["reason"],
            "operation": candidate["operation"],
            "operation_count": candidate["operation_count"],
            "operation_types": candidate["operation_types"],
            "file": candidate["target_file"],
            "target_files": candidate["target_files"],
            "operations": candidate["operations"],
            "failing_operation_index": candidate.get("failing_operation_index"),
            "failing_file": candidate.get("failing_file"),
        }
    if not candidate["eligible"] or updated_text_by_file is None:
        return None

    target_files = candidate["target_files"]
    if candidate["operation_count"] == 1:
        operation = request["operations"][0]
        if operation["operation"] == "replace":
            output_text = (
                "[direct-edit fallback]\n"
                f"Applied deterministic replacement in {operation['file']}\n"
                f"- old: `{operation['old']}`\n"
                f"- new: `{operation['new']}`\n"
            )
        elif operation["operation"] == "insert_after":
            output_text = (
                "[direct-edit fallback]\n"
                f"Applied deterministic insert-after edit in {operation['file']}\n"
                f"- anchor: `{operation['anchor']}`\n"
                f"- inserted: `{operation['new']}`\n"
            )
        elif operation["operation"] == "insert_before":
            output_text = (
                "[direct-edit fallback]\n"
                f"Applied deterministic insert-before edit in {operation['file']}\n"
                f"- anchor: `{operation['anchor']}`\n"
                f"- inserted: `{operation['new']}`\n"
            )
        elif operation["operation"] == "replace_block":
            output_text = (
                "[direct-edit fallback]\n"
                f"Applied deterministic block replacement in {operation['file']}\n"
                f"- start: `{operation['start_anchor']}`\n"
                f"- end: `{operation['end_anchor']}`\n"
                f"- replacement: `{operation['new']}`\n"
            )
        elif operation["operation"] == "excerpt_patch":
            output_text = (
                "[direct-edit fallback]\n"
                f"Applied deterministic excerpt patch in {operation['file']}\n"
                + "\n".join(
                    f"- patch {index}: search/replace"
                    for index, _patch in enumerate(operation["patches"], start=1)
                )
                + "\n"
            )
        else:
            return None
    elif candidate["operation"] in {"multi_file_batch", "mixed_batch"}:
        batch_label = "mixed batch" if candidate["operation"] == "mixed_batch" else "multi-file batch"
        output_text = (
            "[direct-edit fallback]\n"
            f"Applied deterministic {batch_label} edit across {candidate['target_file_count']} files\n"
            + "\n".join(
                f"- operation {summary['index']}: {summary['operation']} in {summary['file']}"
                for summary in candidate["operations"]
            )
            + "\n"
        )
    else:
        output_text = (
            "[direct-edit fallback]\n"
            f"Applied deterministic batch edit in {target_files[0]}\n"
            + "\n".join(
                f"- operation {summary['index']}: {summary['operation']}"
                for summary in candidate["operations"]
            )
            + "\n"
        )

    for target_file, updated_text in updated_text_by_file.items():
        resolve_project_path(target_file).write_text(updated_text, encoding="utf-8")

    (run_folder / "AIDER_DIRECT_EDIT.json").write_text(
        json.dumps(
            {
                "triggered": True,
                "status": "applied",
                "operation": candidate["operation"],
                "operation_count": candidate["operation_count"],
                "operation_types": candidate["operation_types"],
                "file": candidate["target_file"],
                "target_files": target_files,
                "operations": request["operations"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "triggered": True,
        "eligible": True,
        "status": "applied",
        "operation": candidate["operation"],
        "operation_count": candidate["operation_count"],
        "operation_types": candidate["operation_types"],
        "file": candidate["target_file"],
        "target_files": target_files,
        "operations": request["operations"],
        "output_text": output_text,
    }


def write_run_artifacts(
    run_folder: Path,
    output_text: str,
    metrics: dict[str, Any],
) -> None:
    (run_folder / "OUTPUT.md").write_text(output_text, encoding="utf-8")
    (run_folder / "METRICS.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")


def build_direct_edit_metrics(
    run_folder: Path,
    args: argparse.Namespace,
    preflight: dict[str, Any],
    read_metadata: list[dict[str, Any]],
    aider_read_inputs: list[str],
    read_bundle: dict[str, Any] | None,
    read_digest: dict[str, Any] | None,
    direct_edit_result: dict[str, Any],
    *,
    shortcut_triggered: bool,
    fallback_triggered: bool,
) -> dict[str, Any]:
    result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    metrics = build_metrics(run_folder, [], args, result, 0.0)
    metrics["preflight"] = preflight
    metrics["preflight_blocked"] = False
    metrics["prepared_read_inputs"] = read_metadata
    metrics["aider_read_inputs"] = aider_read_inputs
    metrics["read_bundle"] = read_bundle
    metrics["read_digest"] = read_digest
    metrics["prewarm"] = None
    metrics["prewarm_attempts"] = []
    metrics["aider_attempts"] = []
    metrics["manager_retry_triggered"] = False
    metrics["final_attempt_number"] = 0
    metrics["aider_summary"] = {
        **summarize_aider_output("", args.files),
        "timeout_event_detected": False,
        "manager_timeout_detected": False,
        "direct_edit_fallback_triggered": fallback_triggered,
        "direct_edit_short_circuit_triggered": shortcut_triggered,
        "fatal_error_detected": False,
    }
    metrics["aider_debug"] = {
        "request_dump_path": None,
        "events_path": None,
        "event_summary": None,
        "direct_edit_path": str(run_folder / "AIDER_DIRECT_EDIT.json") if (run_folder / "AIDER_DIRECT_EDIT.json").is_file() else None,
    }
    metrics["direct_edit"] = direct_edit_result
    return metrics


def main(argv: list[str] | None = None) -> int:
    args = parse_args(build_parser(), argv)
    apply_profile_defaults(args)
    run_folder = Path(args.run_folder)
    run_folder.mkdir(parents=True, exist_ok=True)
    args.run_folder = run_folder

    if args.init_stubs:
        scaffold_required_files(run_folder)
        scaffold_manager_files(run_folder)

    missing_required = missing_inputs(run_folder, REQUIRED_INPUT_FILES)
    missing_file_selection = not args.files
    missing_selected = [path for path in args.files if not resolve_project_path(path).is_file()]
    missing_reads = [path for path in args.read if not resolve_project_path(path).is_file()]
    if missing_required or missing_file_selection or missing_selected or missing_reads:
        details: list[str] = []
        if missing_required:
            details.append("Missing required input files:")
            details.extend(f"- {name}" for name in missing_required)
        if missing_file_selection:
            details.append("No editable files were selected.")
        if missing_selected:
            details.append("Missing editable files:")
            details.extend(f"- {path}" for path in missing_selected)
        if missing_reads:
            details.append("Missing read-only files:")
            details.extend(f"- {path}" for path in missing_reads)

        output_text = build_error_output("# Aider Run Error", details)
        failed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="missing inputs")
        metrics = build_metrics(run_folder, [], args, failed, 0.0)
        metrics["preflight_blocked"] = False
        metrics["preflight"] = None
        metrics["prepared_read_inputs"] = []
        metrics["aider_read_inputs"] = []
        metrics["read_bundle"] = None
        metrics["read_digest"] = None
        metrics["prewarm"] = None
        metrics["prewarm_attempts"] = []
        metrics["aider_attempts"] = []
        metrics["manager_retry_triggered"] = False
        metrics["final_attempt_number"] = 0
        metrics["aider_summary"] = summarize_aider_output("", args.files)
        metrics["aider_debug"] = {
            "request_dump_path": None,
            "events_path": None,
            "event_summary": None,
        }
        write_run_artifacts(run_folder, output_text, metrics)
        return 1

    prompt_path = run_folder / "MODEL_REQUEST.md"
    args.original_prompt_text = prompt_path.read_text(encoding="utf-8")
    effective_prompt, args.prompt_mode = build_effective_prompt(args, args.original_prompt_text)

    prepared_reads, read_metadata = prepare_read_inputs(args, run_folder, effective_prompt)
    aider_read_inputs, read_bundle = build_aider_read_inputs(args, run_folder, prepared_reads, read_metadata)
    read_digest = None
    if should_inline_read_digest(args, read_metadata):
        digest_text, read_digest = build_inline_read_digest(args, run_folder, prepared_reads, read_metadata)
        effective_prompt = effective_prompt.rstrip() + "\n\n" + digest_text
        aider_read_inputs = []

    preflight = build_preflight(args, effective_prompt, prepared_reads, read_metadata)
    preflight["direct_edit_candidate"] = classify_direct_edit_candidate(args.original_prompt_text, args.files)
    preflight["direct_edit_budget_bypass_available"] = bool(
        args.direct_edit_short_circuit and preflight["direct_edit_candidate"].get("eligible")
    )
    (run_folder / "AIDER_MESSAGE.md").write_text(effective_prompt, encoding="utf-8")
    (run_folder / "AIDER_PREFLIGHT.json").write_text(json.dumps(preflight, indent=2) + "\n", encoding="utf-8")

    blocked = (
        preflight["within_budget"] is False
        and not args.allow_over_budget
        and not preflight["direct_edit_budget_bypass_available"]
    )
    if blocked or args.preflight_only:
        status_code = 1 if blocked else 0
        output_text = build_preflight_output(preflight, blocked, args.preflight_only)
        result = subprocess.CompletedProcess(args=[], returncode=status_code, stdout="", stderr="")
        metrics = build_metrics(run_folder, [], args, result, 0.0)
        metrics["preflight"] = preflight
        metrics["preflight_blocked"] = blocked
        metrics["prepared_read_inputs"] = read_metadata
        metrics["aider_read_inputs"] = aider_read_inputs
        metrics["read_bundle"] = read_bundle
        metrics["read_digest"] = read_digest
        metrics["prewarm"] = None
        metrics["prewarm_attempts"] = []
        metrics["aider_attempts"] = []
        metrics["manager_retry_triggered"] = False
        metrics["final_attempt_number"] = 0
        metrics["aider_summary"] = summarize_aider_output("", args.files)
        metrics["aider_debug"] = {
            "request_dump_path": None,
            "events_path": None,
            "event_summary": None,
        }
        write_run_artifacts(run_folder, output_text, metrics)
        return status_code

    direct_edit_result = None
    if args.direct_edit_short_circuit:
        direct_edit_result = try_direct_edit_fallback(run_folder, args.original_prompt_text, args.files)
    if direct_edit_result and direct_edit_result.get("triggered"):
        output_text = "# Direct Edit Shortcut\n\n" + direct_edit_result["output_text"]
        metrics = build_direct_edit_metrics(
            run_folder,
            args,
            preflight,
            read_metadata,
            aider_read_inputs,
            read_bundle,
            read_digest,
            direct_edit_result,
            shortcut_triggered=True,
            fallback_triggered=False,
        )
        write_run_artifacts(run_folder, output_text, metrics)
        return 0

    command = build_aider_command(args, run_folder / "AIDER_MESSAGE.md", aider_read_inputs)
    env = build_aider_env(args)
    prewarm_attempts: list[dict[str, Any]] = []
    render_attempts: list[dict[str, Any]] = []
    archived_attempts: list[dict[str, Any]] = []
    final_result: subprocess.CompletedProcess[str] | None = None
    final_summary = summarize_aider_output("", args.files)
    final_prewarm = None
    final_event_summary = None
    overall_start = time.monotonic()

    for attempt_number in range(1, max(args.manager_retries, 0) + 2):
        final_prewarm = run_endpoint_prewarm(args, env)
        if final_prewarm is not None:
            prewarm_attempts.append(final_prewarm)
            (run_folder / "AIDER_PREWARM.json").write_text(
                json.dumps(final_prewarm, indent=2) + "\n",
                encoding="utf-8",
            )

        final_result = run_aider_subprocess(command, args, env)
        output_text = build_output_text(final_result)
        final_summary = summarize_aider_output(output_text, args.files)
        final_event_summary = parse_aider_event_log(run_folder / "AIDER_EVENTS.jsonl")
        archived = archive_attempt_artifacts(
            run_folder,
            attempt_number,
            output_text,
            final_prewarm,
            parse_aider_event_log,
        )
        archived_attempts.append(archived)
        render_attempts.append(
            {
                "attempt_number": attempt_number,
                "output_text": output_text,
                "prewarm": final_prewarm,
            }
        )

        if attempt_number > max(args.manager_retries, 0):
            break
        if not should_retry_after_connection_failure(final_result, final_summary, final_event_summary):
            break

    if final_result is None:
        final_result = subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="no attempt executed")

    output_text = render_attempt_outputs(render_attempts)
    elapsed_seconds = time.monotonic() - overall_start
    last_error = final_event_summary.get("last_error") if final_event_summary else None
    timeout_event_detected = bool(
        final_event_summary
        and (
            (isinstance(last_error, dict) and last_error.get("error_type") == "Timeout")
            or "timed out" in str(last_error).lower()
        )
    )
    manager_timeout_detected = final_result.returncode == 124
    fallback_result = None
    if (manager_timeout_detected or timeout_event_detected) and final_summary["applied_edit_count"] == 0:
        fallback_result = try_direct_edit_fallback(run_folder, args.original_prompt_text, args.files)
        if fallback_result and fallback_result.get("triggered"):
            output_text = output_text.rstrip() + "\n\n# Direct Edit Fallback\n\n" + fallback_result["output_text"]
            final_summary = summarize_aider_output(output_text, args.files)

    fallback_applied = bool(fallback_result and fallback_result.get("triggered"))
    if fallback_applied:
        fatal_error_detected = False
        exit_code = 0
    else:
        fatal_error_detected = (
            final_summary["fatal_error_detected"]
            or timeout_event_detected
            or manager_timeout_detected
        )
        exit_code = 0 if final_result.returncode == 0 and not fatal_error_detected else 1

    metrics = build_metrics(run_folder, command, args, final_result, elapsed_seconds)
    metrics["preflight"] = preflight
    metrics["preflight_blocked"] = False
    metrics["prepared_read_inputs"] = read_metadata
    metrics["aider_read_inputs"] = aider_read_inputs
    metrics["read_bundle"] = read_bundle
    metrics["read_digest"] = read_digest
    metrics["prewarm"] = final_prewarm
    metrics["prewarm_attempts"] = prewarm_attempts
    metrics["aider_attempts"] = archived_attempts
    metrics["manager_retry_triggered"] = len(render_attempts) > 1
    metrics["final_attempt_number"] = len(render_attempts)
    metrics["aider_summary"] = {
        **final_summary,
        "timeout_event_detected": timeout_event_detected,
        "manager_timeout_detected": manager_timeout_detected,
        "direct_edit_fallback_triggered": fallback_applied,
        "direct_edit_short_circuit_triggered": False,
        "fatal_error_detected": fatal_error_detected,
    }
    metrics["aider_debug"] = {
        "request_dump_path": str(run_folder / "AIDER_REQUEST.json") if (run_folder / "AIDER_REQUEST.json").is_file() else None,
        "events_path": str(run_folder / "AIDER_EVENTS.jsonl") if (run_folder / "AIDER_EVENTS.jsonl").is_file() else None,
        "event_summary": final_event_summary,
        "direct_edit_path": str(run_folder / "AIDER_DIRECT_EDIT.json") if (run_folder / "AIDER_DIRECT_EDIT.json").is_file() else None,
    }
    metrics["direct_edit"] = fallback_result

    write_run_artifacts(run_folder, output_text, metrics)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
