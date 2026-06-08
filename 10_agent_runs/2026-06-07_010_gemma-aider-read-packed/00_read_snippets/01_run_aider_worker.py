# Read-only snippet
# Source: local_harness/run_aider_worker.py

#!/usr/bin/env python3
"""Execute a supervised Aider run into the audited single-worker folder shape."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "XX_backend"))

from validate_agent_run import validate_run_folder  # type: ignore  # noqa: E402


REQUIRED_INPUT_FILES = ("TASK.md", "INPUT.md", "MODEL_REQUEST.md")
DEFAULT_AIDER_PYTHON = PROJECT_ROOT / "_aider-chat" / "bin" / "python"
PROFILE_DEFAULTS: dict[str, dict[str, Any]] = {
    "custom": {
        "model": "openai/gemma4",
        "openai_api_base": None,
        "map_tokens": 2048,
        "timeout": None,
        "stream": True,
        "compact_request": False,
        "compact_request_max_chars": 1600,
        "context_window": None,
        "completion_reserve": None,
        "read_head_lines": None,
        "fit_read_context": False,
        "protocol_overhead_tokens": 0,
    },
    "gemma-local": {
        "model": "openai/gemma4",
        "openai_api_base": "http://localhost:8083/v1",
        "map_tokens": 0,
        "timeout": 90,
        "stream": False,
        "compact_request": True,
        "compact_request_max_chars": 1200,
        "context_window": 8192,
        "completion_reserve": 1536,
        "read_head_lines": 160,
        "fit_read_context": True,
        "protocol_overhead_tokens": 1400,
    },
}
REVIEW_STUB = """# Manager Review

## Status
- pending

## Notes
- Review not completed yet.
"""

ACCEPTED_STUB = """# Accepted Artifact

Manager review is still pending. Do not reuse this file as downstream context yet.
"""


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(ensure_trailing_newline(content), encoding="utf-8")


def scaffold_required_files(run_folder: Path) -> None:
    write_if_missing(
        run_folder / "TASK.md",
        "# Local Agent Task\n\nPopulate this audit record before promoting the run.\n",
    )
    write_if_missing(
        run_folder / "INPUT.md",
        "# Input Bundle\n\nList the files, excerpts, or repo paths given to the worker.\n",
    )
    write_if_missing(
        run_folder / "MODEL_REQUEST.md",
        "# Model Request\n\nWrite the compact Aider prompt here.\n",
    )


def missing_inputs(run_folder: Path) -> list[str]:
    return [name for name in REQUIRED_INPUT_FILES if not (run_folder / name).is_file()]


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def resolve_project_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def apply_profile_defaults(args: argparse.Namespace) -> None:
    defaults = PROFILE_DEFAULTS[args.profile]
    for key, value in defaults.items():
        if getattr(args, key) is None:
            setattr(args, key, value)


def compact_request_text(prompt_text: str, editable_files: Sequence[str], max_chars: int) -> str:
    lines = [" ".join(line.strip().split()) for line in prompt_text.splitlines() if line.strip()]
