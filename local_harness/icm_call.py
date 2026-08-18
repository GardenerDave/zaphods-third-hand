#!/usr/bin/env python3
"""Call configured local model workers and return audited metadata."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Sequence

try:  # Works both as ``python local_harness/icm_call.py`` and as a package.
    from .icm_spec import (
        DEFAULT_WORKERS,
        NATIVE_COMPLETION,
        NATIVE_SYSTEM_PROMPT,
        OPENAI_CHAT,
        OPENAI_COMPLETIONS,
        SYSTEM_PROMPT,
        WorkerResponse,
        WorkerSpec,
        completion_url,
        maybe_append_no_think,
        models_url,
        resolve_worker_spec,
    )
except ImportError:  # pragma: no cover - direct script compatibility
    from icm_spec import (
        DEFAULT_WORKERS,
        NATIVE_COMPLETION,
        NATIVE_SYSTEM_PROMPT,
        OPENAI_CHAT,
        OPENAI_COMPLETIONS,
        SYSTEM_PROMPT,
        WorkerResponse,
        WorkerSpec,
        completion_url,
        maybe_append_no_think,
        models_url,
        resolve_worker_spec,
    )


def _request_headers() -> dict[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY") or "dummy"
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def _read_json_response(request: urllib.request.Request, timeout: int) -> Any:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def list_models(spec: WorkerSpec, *, timeout: int = 30) -> Any:
    request = urllib.request.Request(
        models_url(spec),
        headers=_request_headers(),
        method="GET",
    )
    return _read_json_response(request, timeout)


def _looks_like_openai_alias(model: str | None) -> bool:
    return bool(model and model.startswith("openai/"))


def _resolve_model_alias(spec: WorkerSpec, timeout: int) -> tuple[str | None, bool, str | None]:
    if not _looks_like_openai_alias(spec.model) or spec.api == NATIVE_COMPLETION:
        return (spec.model, False, None)

    try:
        payload = list_models(spec, timeout=timeout)
        models = payload.get("data", []) if isinstance(payload, dict) else []
        if models:
            model_id = models[0].get("id")
            if model_id:
                return (model_id, True, None)
        return (spec.model, True, "No model ids returned by /models")
    except Exception as exc:  # keep the configured alias if discovery fails
        return (spec.model, True, str(exc))


def _build_payload(spec: WorkerSpec, prompt: str, model: str | None, max_tokens: int) -> dict[str, Any]:
    prompt = maybe_append_no_think(prompt, spec.append_no_think)

    if spec.api == OPENAI_CHAT:
        return {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "stream": False,
        }

    if spec.api == OPENAI_COMPLETIONS:
        return {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "stream": False,
        }

    if spec.api == NATIVE_COMPLETION:
        return {
            "prompt": f"{NATIVE_SYSTEM_PROMPT}\n\n{prompt}",
            "n_predict": max_tokens,
            "temperature": 0.2,
        }

    raise ValueError(f"Unsupported worker API: {spec.api}")


def _content_from_response(spec: WorkerSpec, result: Any) -> tuple[str, str, str | None]:
    if spec.api == NATIVE_COMPLETION:
        if isinstance(result, dict):
            content = result.get("content") or result.get("response") or ""
            return ("ok" if content else "empty_content", str(content), result.get("stop_reason"))
        return ("ok", str(result), None)

    choice = result["choices"][0]
    finish_reason = choice.get("finish_reason")

    if spec.api == OPENAI_COMPLETIONS:
        content = choice.get("text") or ""
        return ("ok" if content else "empty_content", content, finish_reason)

    message = choice.get("message", {})
    content = message.get("content")
    reasoning = message.get("reasoning_content")

    if content:
        return ("ok", content, finish_reason)
    if reasoning:
        return ("reasoning_only", "[reasoning_content only]\n" + reasoning, finish_reason)
    return ("empty_content", "[empty content]\nRAW RESPONSE:\n" + json.dumps(result, indent=2), finish_reason)


def call_worker(
    spec: WorkerSpec,
    prompt: str | None = None,
    max_tokens: int = 512,
    *,
    timeout: int = 900,
) -> WorkerResponse:
    if prompt is None:
        prompt = sys.stdin.read()

    model, resolution_attempted, resolution_error = _resolve_model_alias(spec, timeout)
    request_url = completion_url(spec)
    payload = _build_payload(spec, prompt, model, max_tokens)
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        request_url,
        data=data,
        headers=_request_headers(),
        method="POST",
    )

    try:
        result = _read_json_response(request, timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return WorkerResponse(
            status="http_error",
            content=f"[HTTP error {exc.code}]\n{body}",
            request_url=request_url,
            model=model,
            configured_model=spec.configured_model,
            finish_reason=None,
            usage=None,
            timings=None,
            raw_response=None,
            error=body,
            model_resolution_attempted=resolution_attempted,
            model_resolution_error=resolution_error,
        )
    except Exception as exc:
        return WorkerResponse(
            status="request_error",
            content=f"[request error]\n{exc}",
            request_url=request_url,
            model=model,
            configured_model=spec.configured_model,
            finish_reason=None,
            usage=None,
            timings=None,
            raw_response=None,
            error=str(exc),
            model_resolution_attempted=resolution_attempted,
            model_resolution_error=resolution_error,
        )

    try:
        status, content, finish_reason = _content_from_response(spec, result)
        response_model = result.get("model", model) if isinstance(result, dict) else model
        usage = result.get("usage") if isinstance(result, dict) else None
        timings = result.get("timings") if isinstance(result, dict) else None
        return WorkerResponse(
            status=status,
            content=content,
            request_url=request_url,
            model=response_model,
            configured_model=spec.configured_model,
            finish_reason=finish_reason,
            usage=usage,
            timings=timings,
            raw_response=result,
            model_resolution_attempted=resolution_attempted,
            model_resolution_error=resolution_error,
        )
    except Exception as exc:
        return WorkerResponse(
            status="parse_error",
            content="[harness parse error]\n" + str(exc) + "\nRAW RESPONSE:\n" + json.dumps(result, indent=2),
            request_url=request_url,
            model=model,
            configured_model=spec.configured_model,
            finish_reason=None,
            usage=None,
            timings=None,
            raw_response=result,
            error=str(exc),
            model_resolution_attempted=resolution_attempted,
            model_resolution_error=resolution_error,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call configured local ICM model workers directly.")
    parser.add_argument("worker", choices=sorted(DEFAULT_WORKERS), help="Worker to call.")
    parser.add_argument("--api", help="Override the worker API style.")
    parser.add_argument("--base-url", help="Override an OpenAI-compatible base URL.")
    parser.add_argument("--url", help="Override the exact completion URL.")
    parser.add_argument("--model", help="Override the model name sent to the worker.")
    parser.add_argument("--max-tokens", type=int, default=512, help="Maximum response tokens.")
    parser.add_argument("--timeout", type=int, default=900, help="HTTP timeout in seconds.")
    parser.add_argument("--final-only", action="store_true", help="Append /no_think for workers that need it.")
    parser.add_argument("--metadata-out", help="Write response metadata JSON to this path.")
    parser.add_argument("--list-models", action="store_true", help="List models for the selected worker.")
    parser.add_argument("prompt", nargs="*", help="Prompt text. If omitted, prompt is read from stdin.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    spec = resolve_worker_spec(
        args.worker,
        base_url=args.base_url,
        url=args.url,
        model=args.model,
        api=args.api,
        final_only=args.final_only,
    )

    if args.list_models:
        try:
            payload = list_models(spec, timeout=args.timeout)
        except Exception as exc:
            print(f"[request error]\n{exc}")
            return 1
        print(json.dumps(payload, indent=2))
        return 0

    prompt = " ".join(args.prompt) if args.prompt else None
    response = call_worker(spec, prompt, args.max_tokens, timeout=args.timeout)
    print(response.content)

    if args.metadata_out:
        with open(args.metadata_out, "w", encoding="utf-8") as metadata_file:
            json.dump(response.metadata(), metadata_file, indent=2)
            metadata_file.write("\n")

    return 0 if response.status in {"ok", "reasoning_only"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
