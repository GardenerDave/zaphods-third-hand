#!/usr/bin/env python3
"""Qualification sweep for a local Qwen3.8-27B OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Task:
    task_id: str
    prompt_path: Path
    rubric_path: Path


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
            parsed.setdefault("client_elapsed_seconds", round(time.time() - started, 3))
            return parsed
    except urllib.error.HTTPError as exc:
        return {
            "error": "http_error",
            "status": exc.code,
            "body": exc.read().decode("utf-8", errors="replace"),
            "client_elapsed_seconds": round(time.time() - started, 3),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "error": type(exc).__name__,
            "message": str(exc),
            "client_elapsed_seconds": round(time.time() - started, 3),
        }


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_payload(system: str, user: str, *, reasoning_effort: str, max_tokens: int) -> dict[str, Any]:
    return {
        "model": "local",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"reasoning_effort": reasoning_effort},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://192.168.137.3:8080/v1")
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = [
        Task("A", Path("docs/reports/evidence/qwen38_27b_20260907/task_A_prompt.txt"), Path("docs/reports/evidence/qwen38_27b_20260907/task_A_rubric.txt")),
        Task("B", Path("docs/reports/evidence/qwen38_27b_20260907/task_B_prompt.txt"), Path("docs/reports/evidence/qwen38_27b_20260907/task_B_rubric.txt")),
        Task("C", Path("docs/reports/evidence/qwen38_27b_20260907/task_C_prompt.txt"), Path("docs/reports/evidence/qwen38_27b_20260907/task_C_rubric.txt")),
    ]
    matrix = [(task.task_id, effort, 768) for task in tasks for effort in ("low", "medium", "xhigh")]
    results = []
    for task_id, effort, max_tokens in matrix:
        task = next(t for t in tasks if t.task_id == task_id)
        system = "You are a careful coding assistant. Follow the user prompt exactly."
        user = load_text(task.prompt_path)
        payload = build_payload(system, user, reasoning_effort=effort, max_tokens=max_tokens)
        response = post_json(f"{args.base_url}/chat/completions", payload, timeout=args.timeout)
        record = {
            "task_id": task_id,
            "reasoning_effort": effort,
            "max_tokens": max_tokens,
            "request": payload,
            "response": response,
            "prompt_text": user,
            "rubric_text": load_text(task.rubric_path),
        }
        (out_dir / f"{task_id}_{effort}_{max_tokens}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        results.append(record)
    (out_dir / "summary.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
