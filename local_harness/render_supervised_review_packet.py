#!/usr/bin/env python3
"""Render a supervised review packet for a correction-aware model attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence


OUTPUT_JSON = "supervised_review_packet.json"
OUTPUT_MD = "supervised_review_packet.md"
REPORT_TYPE = "correction_aware_supervised_review_packet.v1"


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short_excerpt(text: str, limit: int = 320) -> str:
    cleaned = " ".join(text.split())
    return cleaned[:limit]


def build_review_packet(
    *,
    model_attempt_record: dict[str, Any],
    raw_output_text: str,
    validation_report: dict[str, Any],
    job_packet: dict[str, Any],
    prompt_packet: dict[str, Any],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    parsed_output = validation_report.get("parsed_output")
    review_decision_options = [
        "accept_as_corrected_output",
        "reject",
        "needs_prompt_revision",
        "needs_validator_revision",
        "needs_human_scope_decision",
    ]
    validation_status = str(validation_report.get("validation_status", "validation_failed"))
    recommended_review = (
        "supervised_review_required" if validation_status == "validation_passed" else "supervised_review_required"
    )
    return {
        "report_type": REPORT_TYPE,
        "source_model_attempt_dir": source_paths["model_attempt_dir"],
        "source_model_attempt_record": source_paths["model_attempt_record"],
        "source_raw_output": source_paths["raw_output"],
        "source_validation_report": source_paths["validation_report"],
        "source_job_packet": source_paths["job_packet"],
        "source_prompt_packet": source_paths["prompt_packet"],
        "source_model_attempt_record_sha256": sha256_text(
            json.dumps(model_attempt_record, sort_keys=True, separators=(",", ":"))
        ),
        "source_raw_output_sha256": sha256_text(raw_output_text),
        "source_validation_report_sha256": sha256_text(
            json.dumps(validation_report, sort_keys=True, separators=(",", ":"))
        ),
        "validation_status": validation_status,
        "findings": validation_report.get("findings") or [],
        "parsed_output": parsed_output,
        "raw_output_excerpt": short_excerpt(raw_output_text),
        "authority_flags": {
            "model_inference_performed": False,
            "generation_performed": False,
            "training_performed": False,
            "delta_written": False,
            "patched_model_materialized": False,
            "promotion_authorized": False,
            "supervised_acceptance_performed": False,
            "automatic_failure_curriculum_capture_authorized": False,
        },
        "review_decision_options": review_decision_options,
        "recommended_next_step": recommended_review,
        "no_auto_acceptance": True,
        "packet_level_only": True,
        "job_packet_summary": job_packet.get("task_summary"),
        "prompt_packet_summary": prompt_packet.get("task_summary"),
    }


def render_markdown(review_packet: dict[str, Any]) -> str:
    lines = [
        "# Correction-Aware Supervised Review Packet",
        "",
        "## Sources",
        f"- model attempt record: `{review_packet['source_model_attempt_record']}`",
        f"- raw output: `{review_packet['source_raw_output']}`",
        f"- validation report: `{review_packet['source_validation_report']}`",
        f"- job packet: `{review_packet['source_job_packet']}`",
        f"- prompt packet: `{review_packet['source_prompt_packet']}`",
        "",
        "## Validation",
        f"- validation status: `{review_packet['validation_status']}`",
        "",
        "## Findings",
    ]
    findings = review_packet.get("findings") or []
    lines.extend(f"- {finding}" for finding in findings) if findings else lines.append("- <none>")
    lines.extend(
        [
            "",
            "## Parsed output",
            f"```json\n{json.dumps(review_packet.get('parsed_output'), indent=2, sort_keys=True)}\n```",
            "",
            "## Raw output excerpt",
            review_packet.get("raw_output_excerpt") or "<empty>",
            "",
            "## Authority flags",
        ]
    )
    for key, value in review_packet["authority_flags"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Review decision options",
        ]
    )
    lines.extend(f"- {item}" for item in review_packet["review_decision_options"])
    lines.extend(
        [
            "",
            "## Required review posture",
            f"- recommended next step: `{review_packet['recommended_next_step']}`",
            "- this packet does not accept outputs",
            "- this packet does not promote outputs",
            "- this packet does not train",
            "- this packet does not write deltas",
            "- this packet does not materialize models",
            "- this packet does not capture failures for curriculum",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_review_packet(
    *,
    model_attempt_dir: Path,
    job_packet_path: Path,
    prompt_packet_path: Path,
    validation_report_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    if out_dir.exists():
        raise ValueError(f"output directory already exists: {out_dir}")

    model_attempt_record = load_json(model_attempt_dir / "model_attempt_record.json", "model attempt record")
    raw_output_path = model_attempt_dir / "raw_model_output.txt"
    if not raw_output_path.exists():
        raise ValueError(f"missing raw output: {raw_output_path}")
    raw_output_text = raw_output_path.read_text(encoding="utf-8")

    validation_report = load_json(validation_report_path, "validation report")
    job_packet = load_json(job_packet_path, "job packet")
    prompt_packet = load_json(prompt_packet_path, "prompt packet")

    review_packet = build_review_packet(
        model_attempt_record=model_attempt_record,
        raw_output_text=raw_output_text,
        validation_report=validation_report,
        job_packet=job_packet,
        prompt_packet=prompt_packet,
        source_paths={
            "model_attempt_dir": str(model_attempt_dir),
            "model_attempt_record": str(model_attempt_dir / "model_attempt_record.json"),
            "raw_output": str(raw_output_path),
            "validation_report": str(validation_report_path),
            "job_packet": str(job_packet_path),
            "prompt_packet": str(prompt_packet_path),
        },
    )

    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / OUTPUT_JSON).write_text(
        json.dumps(review_packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / OUTPUT_MD).write_text(render_markdown(review_packet), encoding="utf-8")
    return review_packet


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a supervised review packet for a correction-aware attempt.")
    parser.add_argument("--model-attempt-dir", required=True, type=Path)
    parser.add_argument("--job-packet", required=True, type=Path)
    parser.add_argument("--prompt-packet", required=True, type=Path)
    parser.add_argument("--validation-report", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        write_review_packet(
            model_attempt_dir=args.model_attempt_dir,
            job_packet_path=args.job_packet,
            prompt_packet_path=args.prompt_packet,
            validation_report_path=args.validation_report,
            out_dir=args.out_dir,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
