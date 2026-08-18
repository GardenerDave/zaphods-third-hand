#!/usr/bin/env python3
"""Shared worker specs and URL helpers for local ICM callers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping


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
    configured_model: str | None = None


@dataclass(frozen=True)
class WorkerResponse:
    status: str
    content: str
    request_url: str
    model: str | None
    configured_model: str | None
    finish_reason: str | None
    usage: Mapping[str, Any] | None
    timings: Mapping[str, Any] | None
    raw_response: Any
    error: str | None = None
    model_resolution_attempted: bool = False
    model_resolution_error: str | None = None
    request_provenance: Mapping[str, Any] | None = None

    def metadata(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "request_url": self.request_url,
            "model": self.model,
            "configured_model": self.configured_model,
            "resolved_model": self.model,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "timings": self.timings,
            "error": self.error,
            "model_resolution_attempted": self.model_resolution_attempted,
            "model_resolution_error": self.model_resolution_error,
            "request_provenance": self.request_provenance,
            "transport_classification": classify_worker_response(self.status, self.error),
        }


def classify_worker_response(status: str, error: str | None = None) -> str:
    """Classify transport/model outcomes before any capability validation."""
    if status == "ok":
        return "model_response"
    if status == "empty_content":
        return "empty_model_response"
    if status == "reasoning_only":
        return "model_response"
    if status in {"timeout", "request_timeout"}:
        return "transport_timeout"
    if status == "request_error":
        text = (error or "").lower()
        return "transport_timeout" if "timed out" in text or "timeout" in text else "transport_request_error"
    if status == "http_error":
        return "transport_http_error"
    return "other_infrastructure_error"


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def build_url(base_url: str, suffix: str) -> str:
    return f"{normalize_base_url(base_url)}/{suffix.lstrip('/')}"


def env_name(worker_name: str, suffix: str) -> str:
    return f"ICM_{worker_name.upper()}_{suffix}"


def env_override(worker_name: str, suffix: str) -> str | None:
    return os.environ.get(env_name(worker_name, suffix))


def resolve_worker_spec(
    worker_name: str,
    *,
    base_url: str | None = None,
    url: str | None = None,
    model: str | None = None,
    api: str | None = None,
    final_only: bool = False,
) -> WorkerSpec:
    if worker_name not in DEFAULT_WORKERS:
        raise KeyError(f"Unknown worker: {worker_name}")

    defaults = DEFAULT_WORKERS[worker_name]
    resolved_api = api or env_override(worker_name, "API") or defaults["api"]
    resolved_base_url = base_url or env_override(worker_name, "BASE_URL") or defaults.get("base_url")
    resolved_url = url or env_override(worker_name, "URL")
    if resolved_url is None and resolved_base_url is None:
        resolved_url = defaults.get("url")
    resolved_model = model or env_override(worker_name, "MODEL") or defaults.get("model")
    append_no_think = final_only or bool(defaults.get("append_no_think"))

    if resolved_base_url:
        resolved_base_url = normalize_base_url(resolved_base_url)

    return WorkerSpec(
        name=worker_name,
        api=resolved_api,
        model=resolved_model,
        base_url=resolved_base_url,
        url=resolved_url,
        append_no_think=append_no_think,
        configured_model=resolved_model,
    )


def maybe_append_no_think(prompt: str, enabled: bool) -> str:
    if enabled and "/no_think" not in prompt:
        return prompt.rstrip() + "\n/no_think"
    return prompt


def completion_url(spec: WorkerSpec) -> str:
    if spec.api == NATIVE_COMPLETION:
        if spec.url:
            return spec.url
        raise ValueError(f"{spec.name} is missing a completion URL")

    if spec.url:
        return spec.url
    if spec.base_url:
        return build_url(spec.base_url, OPENAI_SUFFIXES[spec.api])
    raise ValueError(f"{spec.name} is missing a base URL")


def models_url(spec: WorkerSpec) -> str:
    if spec.api == NATIVE_COMPLETION:
        raise ValueError(f"{spec.name} does not expose an OpenAI-compatible /models endpoint")
    if spec.base_url:
        return build_url(spec.base_url, "models")
    if spec.url and spec.url.endswith("/chat/completions"):
        return spec.url[: -len("/chat/completions")] + "/models"
    if spec.url and spec.url.endswith("/completions"):
        return spec.url[: -len("/completions")] + "/models"
    raise ValueError(f"{spec.name} is missing a base URL for model discovery")
