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
        "bundle_read_inputs": False,
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
        "bundle_read_inputs": True,
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



[truncated after 74 lines]
