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
    run_folder: Path,
    worker: str,
    prompt_text: str,
    response,
) -> dict[str, object]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_folder": str(run_folder),
        "worker": worker,
        "status": response.status,
        "request_url": response.request_url,
        "model": response.model,
        "finish_reason": response.finish_reason,
        "usage": response.usage,
        "timings": response.timings,
        "input_est_tokens": estimate_tokens(prompt_text),
        "output_est_tokens": estimate_tokens(response.content),
        "token_estimate_method": "characters_divided_by_4",
        "error": response.error,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a single local worker against MODEL_REQUEST.md and write audited artifacts.",
    )
    parser.add_argument("run_folder", help="Target run folder under 10_agent_runs or another path.")
    parser.add_argument(
        "worker",
        choices=sorted(DEFAULT_WORKERS),
        help="Worker key to use for the request.",
    )
    parser.add_argument("--api", help="Override the worker API style.")
    parser.add_argument("--base-url", help="Override the worker base URL, such as http://localhost:8083/v1")

[truncated after 105 lines]
