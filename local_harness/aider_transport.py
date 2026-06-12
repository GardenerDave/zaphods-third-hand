#!/usr/bin/env python3
"""Command and environment helpers for Aider runs."""

from __future__ import annotations

import os
import urllib.parse
from pathlib import Path
from typing import Any, Sequence


DEFAULT_PREWARM_PROMPT = "Reply with exactly: ok"


def build_aider_command(args: Any, prompt_path: Path, read_paths: Sequence[str]) -> list[str]:
    command = [
        args.aider_python,
        "-m",
        "aider",
        "--model",
        args.model,
        "--no-show-model-warnings",
        "--map-tokens",
        str(args.map_tokens),
        "--no-auto-commits",
        "--no-dirty-commits",
        "--no-gitignore",
        "--yes-always",
        "--message-file",
        str(prompt_path),
        "--input-history-file",
        str(args.run_folder / "AIDER_INPUT_HISTORY.md"),
        "--chat-history-file",
        str(args.run_folder / "AIDER_CHAT_HISTORY.md"),
    ]
    if args.openai_api_base:
        command.extend(["--openai-api-base", args.openai_api_base])
    if args.edit_format:
        command.extend(["--edit-format", args.edit_format])
    if args.timeout is not None:
        command.extend(["--timeout", str(args.timeout)])
    if args.stream is False:
        command.append("--no-stream")
    for read_path in read_paths:
        command.extend(["--read", read_path])
    command.extend(args.files)
    return command


def build_aider_env(args: Any) -> dict[str, str]:
    env = os.environ.copy()
    if args.openai_api_base and not env.get("OPENAI_API_KEY"):
        env["OPENAI_API_KEY"] = "dummy"
    if args.minimal_prompt:
        env["AIDER_MINIMAL_PROMPT"] = "1"
    if args.skip_example_chat:
        env["AIDER_SKIP_EXAMPLE_CHAT"] = "1"
    if args.capture_debug_artifacts:
        env["AIDER_DUMP_REQUEST_JSON"] = str(args.run_folder / "AIDER_REQUEST.json")
        env["AIDER_DUMP_EVENTS_FILE"] = str(args.run_folder / "AIDER_EVENTS.jsonl")
    return env


def build_chat_completions_url(base_url: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", "chat/completions")
