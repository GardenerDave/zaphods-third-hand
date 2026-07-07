#!/usr/bin/env python3
"""Operator CLI runner for deterministic supervised chain smoke artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.render_supervised_chain_smoke_report import render_supervised_chain_smoke_report
from local_harness.supervised_chain_smoke import run_supervised_chain_smoke, validate_supervised_chain_smoke_record


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_messy_input(*, messy_input: str | None, messy_input_file: Path | None) -> str:
    if bool(messy_input) == bool(messy_input_file):
        raise ValueError("provide exactly one of --messy-input or --messy-input-file")
    if messy_input is not None:
        value = messy_input.strip()
        if not value:
            raise ValueError("--messy-input must be non-empty")
        return value
    assert messy_input_file is not None
    if not messy_input_file.is_file():
        raise ValueError(f"--messy-input-file does not exist: {messy_input_file}")
    value = messy_input_file.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("--messy-input-file must contain non-empty text")
    return value


def run_smoke_cli(
    *,
    messy_input: str,
    out_dir: Path,
    timestamp: str | None = None,
    run_id: str | None = None,
    overwrite: bool = False,
) -> dict[str, Path | str | dict]:
    ts = timestamp or _utc_timestamp()
    if not ts.strip():
        raise ValueError("timestamp must be non-empty when provided")
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir = out_dir / ts
    if run_dir.exists() and not overwrite:
        raise FileExistsError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=overwrite)

    smoke_id = run_id if run_id else f"supervised_chain_smoke_{ts.lower()}"
    smoke_record = run_supervised_chain_smoke(
        messy_input=messy_input,
        smoke_id=smoke_id,
        completed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    validated = validate_supervised_chain_smoke_record(smoke_record)
    report = render_supervised_chain_smoke_report(validated)

    messy_input_path = run_dir / "messy_input.txt"
    smoke_json_path = run_dir / "supervised_chain_smoke.json"
    report_path = run_dir / "supervised_chain_smoke_report.txt"
    model_prompt_path = run_dir / "model_prompt_packet.md"
    handoff_path = run_dir / "handoff_packet.json"

    messy_input_path.write_text(messy_input + "\n", encoding="utf-8")
    smoke_json_path.write_text(json.dumps(validated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")

    model_prompt_packet = validated.get("artifacts", {}).get("model_prompt_packet")
    if isinstance(model_prompt_packet, str) and model_prompt_packet.strip():
        model_prompt_path.write_text(model_prompt_packet.rstrip() + "\n", encoding="utf-8")

    handoff_packet = validated.get("artifacts", {}).get("handoff_packet")
    if isinstance(handoff_packet, dict):
        handoff_path.write_text(json.dumps(handoff_packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "run_dir": run_dir,
        "smoke_status": validated["smoke_status"],
        "report_path": report_path,
        "record": validated,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--messy-input")
    parser.add_argument("--messy-input-file", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--timestamp")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        messy_input = _read_messy_input(
            messy_input=args.messy_input,
            messy_input_file=args.messy_input_file,
        )
        result = run_smoke_cli(
            messy_input=messy_input,
            out_dir=args.out_dir,
            timestamp=args.timestamp,
            run_id=args.run_id,
            overwrite=bool(args.overwrite),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"run_dir: {result['run_dir']}")
    print(f"smoke_status: {result['smoke_status']}")
    print(f"report_path: {result['report_path']}")

    if result["smoke_status"] != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
