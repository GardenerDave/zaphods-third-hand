#!/usr/bin/env python3
"""Structured runner for one Project Historian ask query.

This script is executed by the Historian retrieval runtime (not by ZTH's own
interpreter) with the Project Historian repository as both working directory
and import root. It performs exactly one Historian ``ask`` query and prints
the full structured result — including the query's ``request_id`` and the
exact request directory the service just created — as a single JSON object on
stdout, so callers can bind the query they just created without scanning
Historian work directories.

It writes only the query artifacts the Historian service itself writes. It
grants no authority and performs no ZTH operations.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: historian_ask_runner.py QUESTION MAX_TOKENS", file=sys.stderr)
        return 2
    question = argv[1]
    if not question.strip():
        print("question must be a non-empty string", file=sys.stderr)
        return 2
    try:
        max_tokens = int(argv[2])
    except ValueError:
        print("max_tokens must be an integer", file=sys.stderr)
        return 2
    from historian.ask import ask

    work_root = Path.cwd() / ".work" / "historian_queries"
    endpoint = os.environ.get("HISTORIAN_REASONER_ENDPOINT") or None
    result = ask(question, endpoint=endpoint, work_root=work_root, max_tokens=max_tokens)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
