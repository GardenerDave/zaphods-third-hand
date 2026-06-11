#!/usr/bin/env python3
"""Execute a single-worker local-agent run into the audited folder shape."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from validate_agent_run import validate_run_folder  # type: ignore  # noqa: E402
from icm_call import DEFAULT_WORKERS, call_worker, resolve_worker_spec  # noqa: E402


REQUIRED_INPUT_FILES = ("TASK.md", "INPUT.md", "MODEL_REQUEST.md")
REVIEW_STUB = """# Manager Review

## Status
- pending

## Notes
- Review not completed yet.
"""

ACCEPTED_STUB = """# Accepted Artifact

Manager review is still pending. Do not reuse this file as downstream context yet.
"""


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(ensure_trailing_newline(content), encoding="utf-8")


def scaffold_required_files(run_folder: Path, prompt_text: str | None) -> None:
    write_if_missing(
        run_folder / "TASK.md",
        "# Local Agent Task\n\nPopulate this audit record before promoting the run.\n",
    )
    write_if_missing(
        run_folder / "INPUT.md",
        "# Input Bundle\n\nList the files, excerpts, or repo paths given to the worker.\n",
    )
    if prompt_text is not None:
        write_if_missing(run_folder / "MODEL_REQUEST.md", prompt_text)
    else:
        write_if_missing(
            run_folder / "MODEL_REQUEST.md",
            "# Model Request\n\nWrite the compact worker prompt here.\n",
        )


def missing_inputs(run_folder: Path) -> list[str]:
    return [name for name in REQUIRED_INPUT_FILES if not (run_folder / name).is_file()]


def build_metrics(
    run_folder: Path,
    worker: str,
    prompt_text: str,
    response,
) -> dict[str, object]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_folder": str(run_folder),
        "worker": worker,
        "status": response.status,
        "request_url": response.request_url,
        "model": response.model,
        "finish_reason": response.finish_reason,
        "usage": response.usage,
        "timings": response.timings,
        "input_est_tokens": estimate_tokens(prompt_text),
        "output_est_tokens": estimate_tokens(response.content),
        "token_estimate_method": "characters_divided_by_4",
        "error": response.error,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a single local worker against MODEL_REQUEST.md and write audited artifacts.",
    )
    parser.add_argument("run_folder", help="Target run folder under outputs/agent_runs or another path.")
    parser.add_argument(
        "worker",
        choices=sorted(DEFAULT_WORKERS),
        help="Worker key to use for the request.",
    )
    parser.add_argument("--api", help="Override the worker API style.")
    parser.add_argument("--base-url", help="Override the worker base URL, such as http://localhost:8083/v1")
    parser.add_argument("--url", help="Override the exact completion URL.")
    parser.add_argument("--model", help="Override the model name sent to the worker.")
    parser.add_argument("--prompt-file", help="Seed MODEL_REQUEST.md from this file when scaffolding.")
    parser.add_argument("--max-tokens", type=int, default=512, help="Maximum response tokens.")
    parser.add_argument("--timeout", type=int, default=900, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--final-only",
        action="store_true",
        help="Append /no_think when the prompt does not already include it.",
    )
    parser.add_argument(
        "--init-stubs",
        action="store_true",
        help="Create missing TASK.md, INPUT.md, MODEL_REQUEST.md, REVIEW.md, and ACCEPTED.md files.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Prompt text used only when scaffolding a missing MODEL_REQUEST.md.",
    )
    return parser


def parse_args(parser: argparse.ArgumentParser, argv: Sequence[str] | None) -> argparse.Namespace:
    if hasattr(parser, "parse_intermixed_args"):
        return parser.parse_intermixed_args(argv)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parse_args(parser, argv)

    run_folder = Path(args.run_folder)
    run_folder.mkdir(parents=True, exist_ok=True)

    prompt_text: str | None = None
    if args.prompt_file:
        prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")
    elif args.prompt:
        prompt_text = " ".join(args.prompt)

    if args.init_stubs:
        scaffold_required_files(run_folder, prompt_text)

    missing = missing_inputs(run_folder)
    if missing:
        print(f"Run folder is missing required input files: {', '.join(missing)}")
        return 1

    request_path = run_folder / "MODEL_REQUEST.md"
    request_text = request_path.read_text(encoding="utf-8")
    spec = resolve_worker_spec(
        args.worker,
        base_url=args.base_url,
        url=args.url,
        model=args.model,
        api=args.api,
        final_only=args.final_only,
    )
    response = call_worker(
        spec,
        request_text,
        args.max_tokens,
        timeout=args.timeout,
    )

    (run_folder / "OUTPUT.md").write_text(ensure_trailing_newline(response.content), encoding="utf-8")
    (run_folder / "METRICS.json").write_text(
        json.dumps(build_metrics(run_folder, args.worker, request_text, response), indent=2) + "\n",
        encoding="utf-8",
    )
    if args.init_stubs:
        write_if_missing(run_folder / "REVIEW.md", REVIEW_STUB)
        write_if_missing(run_folder / "ACCEPTED.md", ACCEPTED_STUB)

    validation = validate_run_folder(run_folder)
    if validation.valid:
        print(f"Validated run folder: {run_folder}")
    else:
        print(f"Invalid run folder: {run_folder}")
        if validation.path_error:
            print(f"Error: {validation.path_error}")
        if validation.missing_files:
            print("Missing required files:")
            for filename in validation.missing_files:
                print(f"- {filename}")

    return 0 if response.status == "ok" and validation.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
