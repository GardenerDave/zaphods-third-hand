#!/usr/bin/env python3
"""Bounded reasoning sweep for the local Qwen3.8-27B endpoint."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


BASE_URL = "http://192.168.137.3:8080/v1/chat/completions"
SYSTEM_PROMPT = "You are a careful coding assistant. Follow the user prompt exactly."


def run_curl(payload: dict) -> dict:
    raw = subprocess.check_output(
        [
            "curl",
            "-sS",
            BASE_URL,
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload),
        ]
    )
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir.parent
    tasks = {
        "B": {
            "prompt": (base / "task_B_prompt.txt").read_text(),
            "rubric": (base / "task_B_rubric.txt").read_text(),
            "max_tokens": 1024,
        },
        "C": {
            "prompt": (base / "task_C_prompt.txt").read_text(),
            "rubric": (base / "task_C_rubric.txt").read_text(),
            "max_tokens": 1536,
        },
    }

    records = []
    for task_id, task in tasks.items():
        for effort in ("low", "medium", "xhigh"):
            for thinking_budget_tokens in (256, 512):
                payload = {
                    "model": "local",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": task["prompt"]},
                    ],
                    "temperature": 0,
                    "max_tokens": task["max_tokens"],
                    "thinking_budget_tokens": thinking_budget_tokens,
                    "chat_template_kwargs": {"reasoning_effort": effort},
                }
                response = run_curl(payload)
                record = {
                    "task_id": task_id,
                    "reasoning_effort": effort,
                    "thinking_budget_tokens": thinking_budget_tokens,
                    "max_tokens": task["max_tokens"],
                    "request": payload,
                    "response": response,
                    "prompt_text": task["prompt"],
                    "rubric_text": task["rubric"],
                }
                stem = f"{task_id}_{effort}_tb{thinking_budget_tokens}_{task['max_tokens']}"
                (out_dir / f"{stem}.json").write_text(
                    json.dumps(record, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                records.append(record)

    (out_dir / "summary.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
