# Bundled read-only context

## Source 1: local_harness/run_aider_worker.py

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

## Source 2: local_harness/run_single_worker.py

# Read-only snippet
# Source: local_harness/run_single_worker.py

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
REVIEW_STUB = """# Manager Review

## Status
- pending

## Notes
- Review not completed yet.
"""

ACCEPTED_STUB = """# Accepted Artifact

Manager review is still pending. Do not reuse this file as downstream context yet.
"""


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(ensure_trailing_newline(content), encoding="utf-8")


def scaffold_required_files(run_folder: Path, prompt_text: str | None) -> None:
    write_if_missing(
        run_folder / "TASK.md",
        "# Local Agent Task\n\nPopulate this audit record before promoting the run.\n",
    )
    write_if_missing(
        run_folder / "INPUT.md",
        "# Input Bundle\n\nList the files, excerpts, or repo paths given to the worker.\n",
    )
    if prompt_text is not None:
        write_if_missing(run_folder / "MODEL_REQUEST.md", prompt_text)
    else:
        write_if_missing(
            run_folder / "MODEL_REQUEST.md",
            "# Model Request\n\nWrite the compact worker prompt here.\n",
        )


def missing_inputs(run_folder: Path) -> list[str]:
    return [name for name in REQUIRED_INPUT_FILES if not (run_folder / name).is_file()]


def build_metrics(

## Source 3: local_harness/icm_call.py

# Read-only snippet
# Source: local_harness/icm_call.py

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
        "base_url": "http://<LAN_HOST>:8081/v1",
        "model": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M",
    },
    "router": {
        "api": "openai-chat",
        "base_url": "http://<LAN_HOST>:8082/v1",
        "model": "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M",
    },
    "handoff": {
        "api": "openai-chat",
        "base_url": "http://<LAN_HOST>:8083/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M",
    },
}

OPENAI_CHAT = "openai-chat"
OPENAI_COMPLETIONS = "openai-completions"
NATIVE_COMPLETION = "native-completion"
OPENAI_SUFFIXES = {
    OPENAI_CHAT: "chat/completions",
    OPENAI_COMPLETIONS: "completions",
}
SYSTEM_PROMPT = "You are a concise local AI worker. Follow the user's instructions exactly."
NATIVE_SYSTEM_PROMPT = (
    "You are a deterministic assistant. Respond only to the user's instruction. "
    "Do not continue unrelated text. Do not invent context."
)


@dataclass(frozen=True)
class WorkerSpec:
    name: str
    api: str
    model: str | None = None
    base_url: str | None = None
    url: str | None = None
    append_no_think: bool = False


@dataclass(frozen=True)
class WorkerResponse:
    status: str
    content: str
    request_url: str
    model: str | None
    finish_reason: str | None
    usage: Mapping[str, Any] | None
    timings: Mapping[str, Any] | None
    raw_response: Any
    error: str | None = None

## Source 4: local_harness/README.md

# Read-only snippet
# Source: local_harness/README.md

# Local Harness

This folder contains the manager-side helper scripts for supervised local-worker runs.

## Scripts

- `icm_call.py`: configurable one-shot worker caller for native `/completion` and OpenAI-compatible `/v1` endpoints.
- `run_single_worker.py`: executes one audited single-worker run folder and writes `OUTPUT.md` plus `METRICS.json`.
- `run_aider_worker.py`: executes one audited Aider task from `MODEL_REQUEST.md`, adds Gemma-local preflight safeguards, and records the command output plus metrics.

## Configuration

The defaults preserve the sanitized placeholder hosts from the handoff bundle. Override them per call with CLI flags or environment variables:

```text
ICM_HANDOFF_BASE_URL
ICM_HANDOFF_URL
ICM_HANDOFF_MODEL
ICM_HANDOFF_API
```

The same suffix pattern works for `DEEP`, `CODER`, and `ROUTER`.

## Examples

List models on a live OpenAI-compatible worker:

```text
python3 local_harness/icm_call.py handoff \
  --base-url http://localhost:8083/v1 \
  --list-models
```

Call a live worker and force final-answer output:

```text
python3 local_harness/icm_call.py handoff \
  --base-url http://localhost:8083/v1 \
  --model gemma-4-12B-it-qat-UD-Q4_K_XL.gguf \
  --final-only \
  "Reply with exactly: ok"
```

Run a supervised single-worker smoke test folder:

```text
python3 local_harness/run_single_worker.py \
  10_agent_runs/2026-06-07_001_smoke-test \
  handoff \
  --base-url http://localhost:8083/v1 \
  --model gemma-4-12B-it-qat-UD-Q4_K_XL.gguf \
  --final-only \
  --init-stubs \
  "Reply with exactly: ok"
```

When the worker call succeeds, review `OUTPUT.md`, edit `REVIEW.md`, promote any approved content into `ACCEPTED.md`, and rerun `python3 XX_backend/validate_agent_run.py <run-folder>` before downstream use.

Run a supervised Aider task from the same run-folder shape:

```text
python3 local_harness/run_aider_worker.py \
  10_agent_runs/2026-06-07_004_aider-worker-wrapper \
  --init-stubs \
  --read local_harness/run_single_worker.py \
  --read-head-lines 120 \

## Source 5: XX_backend/validate_agent_run.py

# Read-only snippet
# Source: XX_backend/validate_agent_run.py

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
        return self.path_error is None and not self.missing_files


def validate_run_folder(
    run_folder: str | Path,
    required_files: Iterable[str] = REQUIRED_FILES,
) -> ValidationResult:
    """Check that required artifact filenames exist without reading file contents."""

    folder = Path(run_folder)
    if not folder.exists():
        return ValidationResult(folder, tuple(required_files), "path does not exist")
    if not folder.is_dir():
        return ValidationResult(folder, tuple(required_files), "path is not a directory")

    missing = tuple(name for name in required_files if not (folder / name).is_file())
    return ValidationResult(folder, missing)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the required artifact files for a local-agent run folder.",
    )
    parser.add_argument("run_folder", help="Path to the local-agent run folder.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = validate_run_folder(args.run_folder)

    if result.valid:
        print(f"Valid local-agent run folder: {result.run_folder}")
        return 0

    print(f"Invalid local-agent run folder: {result.run_folder}")
    if result.path_error:

[truncated after 70 lines]

## Source 6: 10_agent_runs/README.md

# Read-only snippet
# Source: 10_agent_runs/README.md

# Local Agent Runs

Author: [REDACTED]

This folder stores file-mediated local-agent runs for ICM and InternalCodename support work.

Use it when Codex/Nav or [REDACTED_AUTHOR] delegates a bounded task to a local model such as Gemma or Qwen. Local agents should write draft reports, summaries, fixture ideas, and analysis here. Canonical ICM files and app source files should change only after manager review.

Worker agents may process personal planner/runtime data when explicitly delegated. Keep raw personal details out of the manager Codex context by default; hand back sanitized findings, metrics, file paths, and conclusions unless [REDACTED_AUTHOR] explicitly asks for raw detail.

Qwen worker tasks should use `/no_think` or an equivalent final-answer-only request convention when final assistant content is required.

Gemma markdown-output tasks should explicitly request raw markdown and forbid enclosing code fences around the whole response.

Typical run folder:

```text
YYYY-MM-DD_short-task/
  RUN.md
  00_inputs/
  01_fast_gemma/
  02_deep_qwen/
  03_manager_review/
  FINAL_REPORT.md
```

For new single-worker supervised pilot runs, prefer:

```text
YYYY-MM-DD_###_short-task/
  TASK.md
  INPUT.md
  MODEL_REQUEST.md
  OUTPUT.md
  REVIEW.md
  METRICS.json
  ACCEPTED.md
```

`TASK.md` is the full audit record. `MODEL_REQUEST.md` is the compact prompt actually sent to the worker when the full task would waste context or trigger timeouts. `OUTPUT.md` is raw draft output. `REVIEW.md` records manager evaluation. `ACCEPTED.md` is the only promoted artifact that should feed another worker or a Codex prompt.

For this single-worker shape, run the backend validator before handoff, downstream promotion, or commit:

```text
python3 ../XX_backend/validate_agent_run.py YYYY-MM-DD_###_short-task/
```

The validator checks required file presence only. Manager review is still required before any content is promoted.


[truncated after 49 lines]
