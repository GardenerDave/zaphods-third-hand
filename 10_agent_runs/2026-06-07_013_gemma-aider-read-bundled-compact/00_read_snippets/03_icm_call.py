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

