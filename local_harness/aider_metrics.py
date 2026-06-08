#!/usr/bin/env python3
"""Metrics helpers for Aider runs."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def build_metrics(
    run_folder: Path,
    command: Sequence[str],
    args: Any,
    result: subprocess.CompletedProcess[str],
    elapsed_seconds: float,
) -> dict[str, object]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_folder": str(run_folder),
        "profile": args.profile,
        "command": list(command),
        "model": args.model,
        "openai_api_base": args.openai_api_base,
        "map_tokens": args.map_tokens,
        "protocol_overhead_tokens": args.protocol_overhead_tokens,
        "context_window": args.context_window,
        "completion_reserve": args.completion_reserve,
        "compact_request": args.compact_request,
        "fit_read_context": args.fit_read_context,
        "bundle_read_inputs": args.bundle_read_inputs,
        "inline_read_digest": args.inline_read_digest,
        "minimal_prompt": args.minimal_prompt,
        "skip_example_chat": args.skip_example_chat,
        "capture_debug_artifacts": args.capture_debug_artifacts,
        "direct_edit_short_circuit": args.direct_edit_short_circuit,
        "edit_format": args.edit_format,
        "prewarm": args.prewarm,
        "manager_retries": args.manager_retries,
        "selected_files": list(args.files),
        "read_only_files": list(args.read),
        "exit_code": result.returncode,
        "elapsed_seconds": elapsed_seconds,
        "error": result.stderr or None,
    }
