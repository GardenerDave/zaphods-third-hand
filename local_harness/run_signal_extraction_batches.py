#!/usr/bin/env python3
"""Run signal extraction packets one at a time with run/model attribution."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def tail_text(value: str, max_chars: int = 4000) -> str:
    return value if len(value) <= max_chars else value[-max_chars:]


def is_dir_empty(path: Path) -> bool:
    return (not path.exists()) or (not any(path.iterdir()))


def resolve_model_base_url(arg_value: str | None) -> str | None:
    return arg_value or os.environ.get("ZTH_SIGNAL_EXTRACT_BASE_URL") or None


def create_or_validate_run_metadata(
    *,
    out_dir: Path,
    packets_path: Path,
    run_id: str,
    model_id: str,
    model_base_url: str | None,
    start_index: int,
    end_index: int,
) -> dict[str, Any]:
    metadata_path = out_dir / "run_metadata.json"

    if metadata_path.exists():
        metadata = read_json(metadata_path)
        stored_run_id = metadata.get("run_id")
        stored_model_id = metadata.get("model_id")

        if stored_run_id != run_id:
            raise SystemExit(
                f"ERROR: run_id mismatch for {out_dir}: "
                f"metadata has {stored_run_id!r}, CLI provided {run_id!r}."
            )
        if stored_model_id != model_id:
            raise SystemExit(
                f"ERROR: model_id mismatch for {out_dir}: "
                f"metadata has {stored_model_id!r}, CLI provided {model_id!r}."
            )

        return metadata

    if out_dir.exists() and not is_dir_empty(out_dir):
        raise SystemExit(
            f"ERROR: refusing to write into non-empty out-dir without run_metadata.json: {out_dir}\n"
            "Migrate/backfill this directory first or choose a fresh model-specific out-dir."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "created_at": utc_now(),
        "end_index": end_index,
        "model_base_url": model_base_url,
        "model_id": model_id,
        "out_dir": str(out_dir),
        "packets_path": str(packets_path),
        "run_id": run_id,
        "start_index": start_index,
        "wrapper_script": "local_harness/run_signal_extraction_batches.py",
    }
    write_json(metadata_path, metadata)
    return metadata


def build_packet_command(
    *,
    packets_path: Path,
    out_dir: Path,
    packet_index: int,
    retries: int,
    retry_delay_seconds: int,
    timeout_seconds: int,
    max_tokens: int,
    model_id: str,
    model_base_url: str | None,
    api_key: str | None,
) -> list[str]:
    command = [
        sys.executable,
        "local_harness/run_signal_extraction_packets.py",
        "--packets",
        str(packets_path),
        "--out-dir",
        str(out_dir),
        "--start-index",
        str(packet_index),
        "--end-index",
        str(packet_index),
        "--resume",
        "--validate",
        "--retries",
        str(retries),
        "--retry-delay-seconds",
        str(retry_delay_seconds),
        "--timeout-seconds",
        str(timeout_seconds),
        "--max-tokens",
        str(max_tokens),
        "--model",
        model_id,
    ]
    if model_base_url:
        command.extend(["--base-url", model_base_url])
    if api_key:
        command.extend(["--api-key", api_key])
    return command


def latest_manifest_row_for_index(manifest_path: Path, selected_index: int) -> dict[str, Any] | None:
    matches = [
        row for row in read_jsonl(manifest_path)
        if int(row.get("selected_index", -1)) == selected_index
    ]
    return matches[-1] if matches else None


def packet_has_normalization_failure(packet_record: dict[str, Any]) -> bool:
    return (
        packet_record.get("normalization_status") == "error"
        or int(packet_record.get("normalization_error_count", 0) or 0) > 0
        or bool(packet_record.get("normalization_error"))
    )


def packet_has_run_error(packet_record: dict[str, Any], result: subprocess.CompletedProcess[str]) -> bool:
    return (
        result.returncode != 0
        or int(packet_record.get("error_count", 0) or 0) > 0
        or packet_record.get("status") in {"error", "failed"}
    )


def packet_has_invalid_output(packet_record: dict[str, Any]) -> bool:
    return int(packet_record.get("invalid_count", 0) or 0) > 0


def build_quarantine_record(
    *,
    packet_record: dict[str, Any],
    run_id: str,
    model_id: str,
    model_base_url: str | None,
) -> dict[str, Any]:
    return {
        "model_base_url": model_base_url,
        "model_id": model_id,
        "normalization_error": packet_record.get("normalization_error", ""),
        "packet_id": packet_record.get("packet_id", ""),
        "packet_path": packet_record.get("packet_path", ""),
        "raw_output_path": packet_record.get("raw_output_path", ""),
        "run_id": run_id,
        "selected_index": packet_record.get("selected_index"),
        "timestamp": packet_record.get("timestamp") or utc_now(),
    }


def write_progress_report(
    *,
    out_dir: Path,
    start_index: int,
    end_index: int,
    last_processed_index: int | None,
    processed_packets: int,
    normalization_failures: int,
    normalization_failure_rate: float,
    stopped: bool,
    stop_reason: str,
    run_id: str,
    model_id: str,
    model_base_url: str | None,
) -> None:
    progress_path = out_dir / "batch_reports" / "progress_report.md"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(
        "\n".join(
            [
                "# Signal Extraction Batch Progress",
                "",
                f"- Run ID: {run_id}",
                f"- Model ID: {model_id}",
                f"- Model base URL: {model_base_url or ''}",
                f"- Started at index: {start_index}",
                f"- Target end index: {end_index}",
                f"- Last processed index: {last_processed_index if last_processed_index is not None else ''}",
                f"- Processed packets: {processed_packets}",
                f"- Normalization failures: {normalization_failures}",
                f"- Cumulative normalization failure rate: {normalization_failure_rate:.4f}",
                f"- Stopped: {stopped}",
                f"- Stop reason: {stop_reason}",
                "",
            ]
        )
    )


def write_latest_summary(
    *,
    out_dir: Path,
    start_index: int,
    end_index: int,
    last_processed_index: int | None,
    processed_packets: int,
    normalization_failures: int,
    max_normalization_failure_rate: float,
    stopped: bool,
    stop_reason: str,
    run_id: str,
    model_id: str,
    model_base_url: str | None,
) -> None:
    failure_rate = normalization_failures / processed_packets if processed_packets else 0.0
    summary = {
        "end_index": end_index,
        "last_processed_index": last_processed_index,
        "max_normalization_failure_rate": max_normalization_failure_rate,
        "model_base_url": model_base_url,
        "model_id": model_id,
        "normalization_failure_rate": failure_rate,
        "normalization_failures": normalization_failures,
        "packet_run_manifest_path": str(out_dir / "batch_reports" / "packet_run_manifest.jsonl"),
        "processed_packets": processed_packets,
        "quarantine_path": str(out_dir / "quarantined_normalization_failures.jsonl"),
        "run_id": run_id,
        "start_index": start_index,
        "stop_reason": stop_reason,
        "stopped": stopped,
        "timestamp": utc_now(),
    }
    write_json(out_dir / "batch_reports" / "latest_batch_summary.json", summary)


def run_batches(args: argparse.Namespace) -> int:
    packets_path = Path(args.packets)
    out_dir = Path(args.out_dir)
    model_base_url = resolve_model_base_url(args.model_base_url)

    create_or_validate_run_metadata(
        out_dir=out_dir,
        packets_path=packets_path,
        run_id=args.run_id,
        model_id=args.model_id,
        model_base_url=model_base_url,
        start_index=args.start_index,
        end_index=args.end_index,
    )

    if args.dry_run:
        print(f"Would process packet indexes {args.start_index}..{args.end_index}")
        print(f"Run ID: {args.run_id}")
        print(f"Model ID: {args.model_id}")
        print(f"Out dir: {out_dir}")
        return 0

    (out_dir / "batch_reports").mkdir(parents=True, exist_ok=True)

    processed_packets = 0
    normalization_failures = 0
    last_processed_index: int | None = None
    stopped = False
    stop_reason = ""

    for packet_index in range(args.start_index, args.end_index + 1):
        command = build_packet_command(
            packets_path=packets_path,
            out_dir=out_dir,
            packet_index=packet_index,
            retries=args.retries,
            retry_delay_seconds=args.retry_delay_seconds,
            timeout_seconds=args.timeout_seconds,
            max_tokens=args.max_tokens,
            model_id=args.model_id,
            model_base_url=model_base_url,
            api_key=args.api_key,
        )

        result = subprocess.run(command, capture_output=True, text=True)

        packet_record = latest_manifest_row_for_index(out_dir / "run_manifest.jsonl", packet_index)
        if packet_record is None:
            packet_record = {
                "selected_index": packet_index,
                "packet_id": "",
                "status": "missing_manifest_row",
                "normalization_status": "unknown",
                "normalization_error": "Missing run_manifest.jsonl row for selected_index.",
                "raw_output_path": "",
                "normalized_output_path": "",
                "packet_path": "",
                "timestamp": utc_now(),
            }

        packet_record = dict(packet_record)
        packet_record.update(
            {
                "command": command,
                "model_base_url": model_base_url,
                "model_id": args.model_id,
                "run_id": args.run_id,
                "stderr_tail": tail_text(result.stderr),
                "stdout_tail": tail_text(result.stdout),
                "subprocess_returncode": result.returncode,
            }
        )

        processed_packets += 1
        last_processed_index = packet_index

        normalization_failed = packet_has_normalization_failure(packet_record)
        if normalization_failed:
            normalization_failures += 1
            append_jsonl(
                out_dir / "quarantined_normalization_failures.jsonl",
                build_quarantine_record(
                    packet_record=packet_record,
                    run_id=args.run_id,
                    model_id=args.model_id,
                    model_base_url=model_base_url,
                ),
            )

        append_jsonl(out_dir / "batch_reports" / "packet_run_manifest.jsonl", packet_record)

        failure_rate = normalization_failures / processed_packets if processed_packets else 0.0

        if packet_has_run_error(packet_record, result) and args.stop_on_run_error:
            stopped = True
            stop_reason = f"run error at packet {packet_index}"
        elif packet_has_invalid_output(packet_record) and args.stop_on_invalid:
            stopped = True
            stop_reason = f"invalid output at packet {packet_index}"
        elif failure_rate > args.max_normalization_failure_rate:
            stopped = True
            stop_reason = (
                f"normalization failure rate {failure_rate:.4f} exceeded "
                f"{args.max_normalization_failure_rate:.4f}"
            )

        write_latest_summary(
            out_dir=out_dir,
            start_index=args.start_index,
            end_index=args.end_index,
            last_processed_index=last_processed_index,
            processed_packets=processed_packets,
            normalization_failures=normalization_failures,
            max_normalization_failure_rate=args.max_normalization_failure_rate,
            stopped=stopped,
            stop_reason=stop_reason,
            run_id=args.run_id,
            model_id=args.model_id,
            model_base_url=model_base_url,
        )
        write_progress_report(
            out_dir=out_dir,
            start_index=args.start_index,
            end_index=args.end_index,
            last_processed_index=last_processed_index,
            processed_packets=processed_packets,
            normalization_failures=normalization_failures,
            normalization_failure_rate=failure_rate,
            stopped=stopped,
            stop_reason=stop_reason,
            run_id=args.run_id,
            model_id=args.model_id,
            model_base_url=model_base_url,
        )

        if args.report_every > 0 and processed_packets % args.report_every == 0:
            print(
                f"Processed {processed_packets} packets; "
                f"last={last_processed_index}; "
                f"normalization_failures={normalization_failures}; "
                f"failure_rate={failure_rate:.4f}"
            )

        if stopped:
            print(f"Stopped: {stop_reason}", file=sys.stderr)
            return 2

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run signal extraction packets one at a time.")

    parser.add_argument("--packets", required=True, help="Path to packets.jsonl.")
    parser.add_argument("--out-dir", required=True, help="Model/run-specific output directory.")
    parser.add_argument("--start-index", type=int, required=True)
    parser.add_argument("--end-index", type=int, required=True)

    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-base-url", default=None)
    parser.add_argument("--api-key", default=None)

    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--retry-delay-seconds", type=int, default=0)
    parser.add_argument("--max-normalization-failure-rate", type=float, default=0.20)
    parser.add_argument("--report-every", type=int, default=30)

    parser.set_defaults(stop_on_run_error=True, stop_on_invalid=True)
    parser.add_argument("--stop-on-run-error", dest="stop_on_run_error", action="store_true")
    parser.add_argument("--no-stop-on-run-error", dest="stop_on_run_error", action="store_false")
    parser.add_argument("--stop-on-invalid", dest="stop_on_invalid", action="store_true")
    parser.add_argument("--no-stop-on-invalid", dest="stop_on_invalid", action="store_false")

    parser.add_argument("--dry-run", action="store_true")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.start_index < 1:
        parser.error("--start-index must be 1 or greater.")
    if args.end_index < 1:
        parser.error("--end-index must be 1 or greater.")
    if args.start_index > args.end_index:
        parser.error("--start-index must be less than or equal to --end-index.")
    if args.max_normalization_failure_rate < 0:
        parser.error("--max-normalization-failure-rate must be non-negative.")

    return run_batches(args)


if __name__ == "__main__":
    raise SystemExit(main())
