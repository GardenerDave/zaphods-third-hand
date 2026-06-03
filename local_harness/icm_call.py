#!/usr/bin/env python3
"""Small OpenAI-compatible chat-completions harness for Zaphod's Third Hand.

Configure the endpoint and model before running:

  export ZTH_BASE_URL="http://<LLAMA_CPP_BASE_URL>/v1"
  export ZTH_MODEL="<MODEL_NAME>"
  # Optional, only if your endpoint requires authorization:
  export ZTH_API_KEY="<YOUR_PRIVATE_KEY>"
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "http://<LLAMA_CPP_BASE_URL>/v1"
DEFAULT_MODEL = "<MODEL_NAME>"


def _completion_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    return base_url + "/chat/completions"


def worker_config(worker_name: str) -> dict:
    prefix = "ZTH_" + worker_name.upper()
    base_url = os.environ.get(prefix + "_BASE_URL") or os.environ.get("ZTH_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get(prefix + "_MODEL") or os.environ.get("ZTH_MODEL", DEFAULT_MODEL)
    api_key = os.environ.get(prefix + "_API_KEY") or os.environ.get("ZTH_API_KEY")
    if "<LLAMA_CPP_BASE_URL>" in base_url or model == DEFAULT_MODEL:
        raise SystemExit("Configure ZTH_BASE_URL and ZTH_MODEL before running. See config.example.env.")
    return {
        "url": _completion_url(base_url),
        "model": model,
        "api_key": api_key,
    }


def call_worker(worker_name: str, prompt: str = None, max_tokens: int = 512) -> str:
    worker = worker_config(worker_name)

    if prompt is None:
        prompt = sys.stdin.read()

    payload = {
        "model": worker["model"],
        "messages": [
            {
                "role": "system",
                "content": "You are a concise local AI worker. Follow the user's instructions exactly.",
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

    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if worker.get("api_key"):
        headers["Authorization"] = "Bearer " + worker["api_key"]

    request = urllib.request.Request(
        worker["url"],
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return f"[HTTP error {exc.code}]\n{body}"
    except Exception as exc:
        return f"[request error]\n{exc}"

    try:
        choice = result["choices"][0]
        message = choice.get("message", {})

        content = message.get("content")
        reasoning = message.get("reasoning_content")

        if content:
            return content

        if reasoning:
            return "[reasoning_content only]\n" + reasoning

        return "[empty content]\nRAW RESPONSE:\n" + json.dumps(result, indent=2)

    except Exception as exc:
        return "[harness parse error]\n" + str(exc) + "\nRAW RESPONSE:\n" + json.dumps(result, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Call configured model workers directly.")
    parser.add_argument(
        "worker",
        choices=["deep", "coder", "router", "handoff"],
        help="Worker to call: deep, coder, router, or handoff",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum response tokens",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Prompt text. If omitted, prompt is read from stdin.",
    )

    args = parser.parse_args()

    if args.prompt:
        prompt = " ".join(args.prompt)
    else:
        prompt = None

    output = call_worker(args.worker, prompt, args.max_tokens)
    print(output)


if __name__ == "__main__":
    main()
