#!/usr/bin/env python3
"""Plan supervised packet-run batches for a ChatGPT export distiller run."""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any, Sequence


DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_TOKENS = 1200
DEFAULT_RETRIES = 0
DEFAULT_RETRY_DELAY_SECONDS = 0
PLACEHOLDER_BASE_URL = "http://192.168.1.13:8081/v1"
PLACEHOLDER_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object")
        rows.append(row)
    return rows


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def discover_chunk_plans(chunk_root: Path) -> list[Path]:
    return sorted(chunk_root.glob("*/chunk_plan.json"))


def summarize_chunk_plans(chunk_root: Path) -> tuple[int, dict[str, int]]:
    chunk_count = 0
    pass_counts: dict[str, int] = {}
    for plan_path in discover_chunk_plans(chunk_root):
        plan = read_json(plan_path)
        passes = plan.get("passes", [])
        if not isinstance(passes, list):
            continue
        for pass_row in passes:
            if not isinstance(pass_row, dict):
                continue
            pass_name = str(pass_row.get("name", "unknown") or "unknown")
            chunks = pass_row.get("chunks", [])
            if not isinstance(chunks, list):
                continue
            count = len([chunk for chunk in chunks if isinstance(chunk, dict)])
            chunk_count += count
            pass_counts[pass_name] = pass_counts.get(pass_name, 0) + count
    return chunk_count, dict(sorted(pass_counts.items()))


def packet_counts_by_conversation(packet_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in packet_rows:
        conversation_id = str(row.get("conversation_id", "") or "unknown")
        counts[conversation_id] = counts.get(conversation_id, 0) + 1
    return dict(sorted(counts.items()))


def largest_conversations(packet_counts: dict[str, int], limit: int = 10) -> list[dict[str, Any]]:
    ordered = sorted(packet_counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"conversation_id": conversation_id, "packet_count": count} for conversation_id, count in ordered[:limit]]


def build_batch_rows(packet_count: int, batch_size: int) -> list[dict[str, Any]]:
    if batch_size <= 0:
        raise ValueError("--batch-size must be greater than zero.")
    rows: list[dict[str, Any]] = []
    start_index = 1
    while start_index <= packet_count:
        end_index = min(start_index + batch_size - 1, packet_count)
        rows.append(
            {
                "batch_id": f"batch-{len(rows) + 1:04d}",
                "start_index": start_index,
                "end_index": end_index,
                "packet_count": end_index - start_index + 1,
                "status": "planned",
            }
        )
        start_index = end_index + 1
    return rows


def shell_quote(value: Any) -> str:
    return shlex.quote(str(value))


def shell_double_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`") + '"'


def commented_export(name: str, value: str) -> str:
    return f"# export {name}={shell_double_quote(value)}"


def build_command_lines(
    *,
    packets_path: Path,
    model_out_dir: Path,
    batch: dict[str, Any],
    retries: int,
    retry_delay_seconds: float,
    timeout_seconds: int,
    max_tokens: int,
) -> list[str]:
    return [
        "# python3 local_harness/run_signal_extraction_packets.py \\",
        f"#   --packets {shell_quote(packets_path)} \\",
        f"#   --out-dir {shell_quote(model_out_dir)} \\",
        f"#   --start-index {batch['start_index']} \\",
        f"#   --end-index {batch['end_index']} \\",
        "#   --resume \\",
        "#   --validate \\",
        f"#   --retries {retries} \\",
        f"#   --retry-delay-seconds {retry_delay_seconds:g} \\",
        f"#   --timeout-seconds {timeout_seconds} \\",
        f"#   --max-tokens {max_tokens}",
    ]


def build_batch_commands(
    *,
    packets_path: Path,
    model_out_dir: Path,
    batches: list[dict[str, Any]],
    base_url: str,
    model: str,
    retries: int,
    retry_delay_seconds: float,
    timeout_seconds: int,
    max_tokens: int,
) -> str:
    lines = [
        "# ChatGPT Export Distiller Batch Commands",
        "#",
        "# Review this file and run one commented command manually at a time.",
        "# It is intentionally comments only; executing this file should do nothing.",
        "#",
        commented_export("ZTH_SIGNAL_EXTRACT_BASE_URL", base_url or PLACEHOLDER_BASE_URL),
        commented_export("ZTH_SIGNAL_EXTRACT_MODEL", model or PLACEHOLDER_MODEL),
        "# export ZTH_SIGNAL_EXTRACT_API_KEY=not-needed-for-local",
        "#",
        f"# Packets: {packets_path}",
        f"# Model output directory: {model_out_dir}",
        "#",
    ]
    for batch in batches:
        lines.append(f"# {batch['batch_id']}: packets {batch['start_index']}-{batch['end_index']}")
        lines.extend(
            build_command_lines(
                packets_path=packets_path,
                model_out_dir=model_out_dir,
                batch=batch,
                retries=retries,
                retry_delay_seconds=retry_delay_seconds,
                timeout_seconds=timeout_seconds,
                max_tokens=max_tokens,
            )
        )
        lines.append("#")
    return "\n".join(lines).rstrip() + "\n"


def build_readme(
    *,
    summary: dict[str, Any],
    model_out_dir: Path,
) -> str:
    lines = [
        "# ChatGPT Export Run Plan",
        "",
        "This directory contains a supervised run plan for packet extraction. It does not execute model calls.",
        "",
        "## Planned Scale",
        "",
        f"- Conversations: {summary['conversation_count']}",
        f"- Chunks: {summary['chunk_count']}",
        f"- Packets: {summary['packet_count']}",
        f"- Batch size: {summary['batch_size']}",
        f"- Batches: {summary['batch_count']}",
        "",
        "## Run One Batch Manually",
        "",
        "Open `batch_commands.sh`, review the environment comments, and copy one batch command into a shell.",
        "Each command uses `--start-index`, `--end-index`, `--resume`, and `--validate`.",
        "",
        "## Resume",
        "",
        f"Batch commands write model outputs to `{model_out_dir}`. Re-run the same batch command with `--resume`",
        "to skip packet rows that already have successful raw output files.",
        "",
        "## Inspect After Each Batch",
        "",
        "Check the runner files before starting the next batch:",
        "",
        f"- `{model_out_dir / 'run_summary.json'}`",
        f"- `{model_out_dir / 'run_manifest.jsonl'}`",
        f"- `{model_out_dir / 'normalization_summary.json'}`",
        f"- `{model_out_dir / 'validated' / 'validation_summary.json'}`",
        "",
        "## Later Review Steps",
        "",
        "Run `signal_dedupe.py` and `signal_review_bundle.py` only after the chosen batches are complete and",
        "the validated raw signals have been inspected. Dedupe and review bundle generation remain explicit steps.",
        "",
        "## Safety",
        "",
        "This planner does not call models, dedupe signals, promote lifecycle state, or update canonical memory.",
        "All generated files and downstream outputs are review material only.",
        "",
    ]
    return "\n".join(lines)


def write_run_plan(
    *,
    ingest_manifest: Path,
    chunk_root: Path,
    packets_path: Path,
    out_dir: Path,
    batch_size: int,
    base_url: str = "",
    model: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    retries: int = DEFAULT_RETRIES,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("--batch-size must be greater than zero.")
    if timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be greater than zero.")
    if max_tokens <= 0:
        raise ValueError("--max-tokens must be greater than zero.")
    if retries < 0:
        raise ValueError("--retries must be zero or greater.")
    if retry_delay_seconds < 0:
        raise ValueError("--retry-delay-seconds must be zero or greater.")

    ingest_rows = read_jsonl(ingest_manifest)
    packet_rows = read_jsonl(packets_path)
    chunk_count, chunk_pass_counts = summarize_chunk_plans(chunk_root)
    conversation_packet_counts = packet_counts_by_conversation(packet_rows)
    batches = build_batch_rows(len(packet_rows), batch_size)

    out_dir.mkdir(parents=True, exist_ok=True)
    model_out_dir = out_dir.parent / "model_raw_signals"
    summary_path = out_dir / "run_plan_summary.json"
    batch_manifest_path = out_dir / "batch_manifest.jsonl"
    batch_commands_path = out_dir / "batch_commands.sh"
    readme_path = out_dir / "README.md"

    summary = {
        "conversation_count": len(ingest_rows),
        "chunk_count": chunk_count,
        "packet_count": len(packet_rows),
        "batch_size": batch_size,
        "batch_count": len(batches),
        "chunk_pass_counts": chunk_pass_counts,
        "conversation_packet_counts": conversation_packet_counts,
        "largest_conversations_by_packets": largest_conversations(conversation_packet_counts),
        "outputs": {
            "run_plan_summary": str(summary_path),
            "batch_manifest": str(batch_manifest_path),
            "batch_commands": str(batch_commands_path),
            "readme": str(readme_path),
            "model_output_dir": str(model_out_dir),
        },
    }

    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_jsonl(batch_manifest_path, batches)
    batch_commands_path.write_text(
        build_batch_commands(
            packets_path=packets_path,
            model_out_dir=model_out_dir,
            batches=batches,
            base_url=base_url,
            model=model,
            retries=retries,
            retry_delay_seconds=retry_delay_seconds,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        ),
        encoding="utf-8",
    )
    readme_path.write_text(build_readme(summary=summary, model_out_dir=model_out_dir), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan supervised ChatGPT export packet-run batches.")
    parser.add_argument("--ingest-manifest", required=True, help="Path to sources/manifests/conversations.jsonl.")
    parser.add_argument("--chunk-root", required=True, help="Path to the chunk root directory.")
    parser.add_argument("--packets", required=True, help="Path to extraction_packets/packets.jsonl.")
    parser.add_argument("--out-dir", required=True, help="Directory that will receive the run plan.")
    parser.add_argument("--batch-size", required=True, type=int, help="Number of packet rows per planned batch.")
    parser.add_argument("--base-url", default="", help="Optional endpoint URL to include as a commented export.")
    parser.add_argument("--model", default="", help="Optional model name to include as a commented export.")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--retry-delay-seconds", type=float, default=DEFAULT_RETRY_DELAY_SECONDS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = write_run_plan(
            ingest_manifest=Path(args.ingest_manifest),
            chunk_root=Path(args.chunk_root),
            packets_path=Path(args.packets),
            out_dir=Path(args.out_dir),
            batch_size=args.batch_size,
            base_url=args.base_url,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
            max_tokens=args.max_tokens,
            retries=args.retries,
            retry_delay_seconds=args.retry_delay_seconds,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Conversations: {summary['conversation_count']}")
    print(f"Chunks: {summary['chunk_count']}")
    print(f"Packets: {summary['packet_count']}")
    print(f"Batches: {summary['batch_count']}")
    print(f"Run plan: {summary['outputs']['run_plan_summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
