#!/usr/bin/env python3
"""Response parsers for local ICM callers."""

from __future__ import annotations

import json
from typing import Any, Mapping

from icm_spec import WorkerResponse


def response_metadata_kwargs(
    configured_model: str | None,
    resolved_model: str | None,
    model_resolution_attempted: bool,
    model_resolution_error: str | None,
) -> dict[str, Any]:
    return {
        "model": resolved_model,
        "configured_model": configured_model,
        "model_resolution_attempted": model_resolution_attempted,
        "model_resolution_error": model_resolution_error,
    }


def parse_native_response(
    result: Mapping[str, Any],
    request_url: str,
    configured_model: str | None,
    resolved_model: str | None,
    model_resolution_attempted: bool,
    model_resolution_error: str | None,
) -> WorkerResponse:
    content = result.get("content")
    metadata = response_metadata_kwargs(
        configured_model,
        resolved_model or result.get("model"),
        model_resolution_attempted,
        model_resolution_error,
    )
    if isinstance(content, str) and content:
        return WorkerResponse(
            status="ok",
            content=content,
            request_url=request_url,
            finish_reason=result.get("stop_reason"),
            usage=result.get("usage"),
            timings=result.get("timings"),
            raw_response=result,
            **metadata,
        )
    return WorkerResponse(
        status="empty",
        content="[empty content]\nRAW RESPONSE:\n" + json.dumps(result, indent=2),
        request_url=request_url,
        finish_reason=result.get("stop_reason"),
        usage=result.get("usage"),
        timings=result.get("timings"),
        raw_response=result,
        **metadata,
    )


def parse_openai_completion_response(
    result: Mapping[str, Any],
    request_url: str,
    configured_model: str | None,
    resolved_model: str | None,
    model_resolution_attempted: bool,
    model_resolution_error: str | None,
) -> WorkerResponse:
    metadata = response_metadata_kwargs(
        configured_model,
        resolved_model or result.get("model"),
        model_resolution_attempted,
        model_resolution_error,
    )
    try:
        choice = result["choices"][0]
    except (KeyError, IndexError, TypeError) as exc:
        return WorkerResponse(
            status="parse_error",
            content="[harness parse error]\n" + str(exc) + "\nRAW RESPONSE:\n" + json.dumps(result, indent=2),
            request_url=request_url,
            finish_reason=None,
            usage=result.get("usage"),
            timings=result.get("timings"),
            raw_response=result,
            error=str(exc),
            **metadata,
        )

    finish_reason = choice.get("finish_reason")
    text = choice.get("text")
    if isinstance(text, str) and text:
        return WorkerResponse(
            status="ok",
            content=text,
            request_url=request_url,
            finish_reason=finish_reason,
            usage=result.get("usage"),
            timings=result.get("timings"),
            raw_response=result,
            **metadata,
        )

    return WorkerResponse(
        status="empty",
        content="[empty content]\nRAW RESPONSE:\n" + json.dumps(result, indent=2),
        request_url=request_url,
        finish_reason=finish_reason,
        usage=result.get("usage"),
        timings=result.get("timings"),
        raw_response=result,
        **metadata,
    )


def parse_openai_chat_response(
    result: Mapping[str, Any],
    request_url: str,
    configured_model: str | None,
    resolved_model: str | None,
    model_resolution_attempted: bool,
    model_resolution_error: str | None,
) -> WorkerResponse:
    metadata = response_metadata_kwargs(
        configured_model,
        resolved_model or result.get("model"),
        model_resolution_attempted,
        model_resolution_error,
    )
    try:
        choice = result["choices"][0]
        message = choice.get("message", {})
    except (KeyError, IndexError, TypeError) as exc:
        return WorkerResponse(
            status="parse_error",
            content="[harness parse error]\n" + str(exc) + "\nRAW RESPONSE:\n" + json.dumps(result, indent=2),
            request_url=request_url,
            finish_reason=None,
            usage=result.get("usage"),
            timings=result.get("timings"),
            raw_response=result,
            error=str(exc),
            **metadata,
        )

    content = message.get("content")
    reasoning = message.get("reasoning_content")
    finish_reason = choice.get("finish_reason")

    if isinstance(content, str) and content:
        return WorkerResponse(
            status="ok",
            content=content,
            request_url=request_url,
            finish_reason=finish_reason,
            usage=result.get("usage"),
            timings=result.get("timings"),
            raw_response=result,
            **metadata,
        )

    if isinstance(reasoning, str) and reasoning:
        return WorkerResponse(
            status="reasoning_only",
            content="[reasoning_content only]\n" + reasoning,
            request_url=request_url,
            finish_reason=finish_reason,
            usage=result.get("usage"),
            timings=result.get("timings"),
            raw_response=result,
            **metadata,
        )

    return WorkerResponse(
        status="empty",
        content="[empty content]\nRAW RESPONSE:\n" + json.dumps(result, indent=2),
        request_url=request_url,
        finish_reason=finish_reason,
        usage=result.get("usage"),
        timings=result.get("timings"),
        raw_response=result,
        **metadata,
    )
