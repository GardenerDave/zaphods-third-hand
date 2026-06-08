#!/usr/bin/env python3
"""Thin compatibility layer over smaller Aider runtime helper modules."""

from __future__ import annotations

from aider_metrics import build_metrics
from aider_reporting import (
    ATTEMPTS_DIRNAME,
    archive_attempt_artifacts,
    build_output_text,
    parse_aider_event_log,
    parse_token_count,
    render_attempt_outputs,
    reset_debug_artifacts,
    should_retry_after_connection_failure,
    summarize_aider_output,
)
from aider_transport import (
    DEFAULT_PREWARM_PROMPT,
    build_aider_command,
    build_aider_env,
    build_chat_completions_url,
)


__all__ = [
    "ATTEMPTS_DIRNAME",
    "DEFAULT_PREWARM_PROMPT",
    "archive_attempt_artifacts",
    "build_aider_command",
    "build_aider_env",
    "build_chat_completions_url",
    "build_metrics",
    "build_output_text",
    "parse_aider_event_log",
    "parse_token_count",
    "render_attempt_outputs",
    "reset_debug_artifacts",
    "should_retry_after_connection_failure",
    "summarize_aider_output",
]
