# Bundled read-only context

## Source 1: local_harness/run_aider_worker.py

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

[truncated after 22 lines]

## Source 2: local_harness/run_single_worker.py

#!/usr/bin/env python3
"""Execute a single-worker local-agent run into the audited folder shape."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "XX_backend"))

from validate_agent_run import validate_run_folder  # type: ignore  # noqa: E402
from icm_call import DEFAULT_WORKERS, call_worker, resolve_worker_spec  # noqa: E402


REQUIRED_INPUT_FILES = ("TASK.md", "INPUT.md", "MODEL_REQUEST.md")

[truncated after 20 lines]

## Source 3: local_harness/icm_call.py

#!/usr/bin/env python3
"""Call local ICM model workers with configurable endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_WORKERS: dict[str, dict[str, Any]] = {
    "deep": {
        "api": "native-completion",
        "url": "http://<LAN_HOST>:8080/completion",
        "model": "Llama-3.3-70B-Instruct-Q4_K_M.gguf",
        "append_no_think": True,
    },
    "coder": {
        "api": "openai-chat",

[truncated after 25 lines]

## Source 4: local_harness/README.md

# Local Harness

This folder contains the manager-side helper scripts for supervised local-worker runs.

## Scripts

- `icm_call.py`: configurable one-shot worker caller for native `/completion` and OpenAI-compatible `/v1` endpoints.
- `run_single_worker.py`: executes one audited single-worker run folder and writes `OUTPUT.md` plus `METRICS.json`.
- `run_aider_worker.py`: executes one audited Aider task from `MODEL_REQUEST.md`, adds Gemma-local preflight safeguards, and records the command output plus metrics.

## Configuration


[truncated after 12 lines]

## Source 5: XX_backend/validate_agent_run.py

#!/usr/bin/env python3
"""Validate the file shape of a single-worker local-agent run folder."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


REQUIRED_FILES: tuple[str, ...] = (
    "TASK.md",
    "INPUT.md",
    "MODEL_REQUEST.md",
    "OUTPUT.md",
    "REVIEW.md",
    "METRICS.json",
    "ACCEPTED.md",
)


@dataclass(frozen=True)
class ValidationResult:
    """Presence-only validation result for a local-agent run folder."""

    run_folder: Path
    missing_files: tuple[str, ...]
    path_error: str | None = None

    @property
    def valid(self) -> bool:

[truncated after 32 lines]

## Source 6: 10_agent_runs/README.md

# Local Agent Runs

Author: [REDACTED]

This folder stores file-mediated local-agent runs for ICM and InternalCodename support work.

Use it when Codex/Nav or [REDACTED_AUTHOR] delegates a bounded task to a local model such as Gemma or Qwen. Local agents should write draft reports, summaries, fixture ideas, and analysis here. Canonical ICM files and app source files should change only after manager review.

Worker agents may process personal planner/runtime data when explicitly delegated. Keep raw personal details out of the manager Codex context by default; hand back sanitized findings, metrics, file paths, and conclusions unless [REDACTED_AUTHOR] explicitly asks for raw detail.
