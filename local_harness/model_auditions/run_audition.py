#!/usr/bin/env python3
"""Run prompt suites against OpenAI-compatible local model endpoints."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    from common import (
        DEFAULT_MODEL_CONFIG,
        DEFAULT_PROMPT_CONFIG,
        ensure_dir,
        filter_by_keys,
        load_models,
        load_prompts,
        utc_run_id,
    )
else:
    from .common import (
        DEFAULT_MODEL_CONFIG,
        DEFAULT_PROMPT_CONFIG,
        ensure_dir,
        filter_by_keys,
        load_models,
        load_prompts,
        utc_run_id,
    )


def post_chat_completion(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            parsed.setdefault("client_elapsed_seconds", round(time.time() - started, 3))
            return parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "error": "http_error",
            "status": exc.code,
            "body": body,
            "client_elapsed_seconds": round(time.time() - started, 3),
        }
    except Exception as exc:  # noqa: BLE001 - preserve harness robustness.
        return {
            "error": type(exc).__name__,
            "message": str(exc),
            "client_elapsed_seconds": round(time.time() - started, 3),
        }


def build_payload(
    prompt,
    *,
    api_model: str = "local",
    max_tokens_override: int | None = None,
) -> dict[str, Any]:
    return {
        "model": api_model,
        "messages": [
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": prompt.user},
        ],
        "temperature": prompt.temperature,
        "max_tokens": max_tokens_override or prompt.max_tokens,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=DEFAULT_MODEL_CONFIG)
    parser.add_argument("--prompts", default=DEFAULT_PROMPT_CONFIG)
    parser.add_argument("--only-models", default=None, help="Comma-separated model keys.")
    parser.add_argument("--only-prompts", default=None, help="Comma-separated prompt keys.")
    parser.add_argument("--out", default=None, help="Output run directory.")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=None, help="Override prompt max_tokens.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configs and print resolved endpoints without network calls.",
    )
    args = parser.parse_args(argv)

    models = filter_by_keys(load_models(args.models), args.only_models)
    prompts = filter_by_keys(load_prompts(args.prompts), args.only_prompts)
    if args.dry_run:
        inspection = {
            "models_config": str(Path(args.models).expanduser()),
            "prompts_config": str(Path(args.prompts).expanduser()),
            "models": [
                {
                    "key": model.key,
                    "label": model.label,
                    "endpoint": model.endpoint_base_url,
                    "chat_completions_url": model.url,
                    "api_model": model.api_model,
                    "managed_locally": model.managed_locally,
                    "model_path": (
                        str(Path(model.path).expanduser())
                        if model.path
                        else None
                    ),
                    "tmux_session": (
                        model.tmux_session if model.managed_locally else None
                    ),
                }
                for model in models
            ],
            "prompts": [
                {
                    "key": prompt.key,
                    "kind": prompt.kind,
                    "max_tokens": args.max_tokens or prompt.max_tokens,
                }
                for prompt in prompts
            ],
            "network_calls_performed": False,
        }
        print(json.dumps(inspection, indent=2, sort_keys=True))
        return 0

    out_dir = ensure_dir(args.out or Path(".work/model_auditions") / utc_run_id())

    metadata = {
        "run_id": out_dir.name,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "models_config": args.models,
        "prompts_config": args.prompts,
        "models": [m.__dict__ for m in models],
        "prompts": [p.__dict__ for p in prompts],
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    response_path = out_dir / "responses.jsonl"
    with response_path.open("w", encoding="utf-8") as handle:
        for model in models:
            for prompt in prompts:
                print(f"RUN {model.key} :: {prompt.key}")
                payload = build_payload(
                    prompt,
                    api_model=model.api_model,
                    max_tokens_override=args.max_tokens,
                )
                response = post_chat_completion(model.url, payload, timeout=args.timeout)
                record = {
                    "run_id": out_dir.name,
                    "model_key": model.key,
                    "model_label": model.label,
                    "port": model.port,
                    "endpoint": model.endpoint_base_url,
                    "chat_completions_url": model.url,
                    "prompt_key": prompt.key,
                    "prompt_label": prompt.label,
                    "prompt_kind": prompt.kind,
                    "expected": prompt.expected or {},
                    "request": payload,
                    "response": response,
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
    print(f"WROTE: {response_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
