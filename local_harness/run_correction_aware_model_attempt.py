#!/usr/bin/env python3
"""Run one authorized model attempt from a correction-aware prompt packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.failure_training.status import StatusWriter


REPORT_TYPE = "correction_aware_model_attempt.v1"
RECOMMENDED_NEXT_STEP = "supervised_validation_or_review"
PROTECTED_FALSE_FIELDS = (
    "model_inference_performed",
    "generation_performed",
    "training_performed",
    "delta_written",
    "patched_model_materialized",
    "promotion_authorized",
    "automatic_failure_curriculum_capture_authorized",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact_endpoint_url(url: str) -> str:
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" in rest:
        rest = rest.split("@", 1)[1]
    return f"{scheme}://{rest}"


def read_json_object(path: Path, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing {kind}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {kind}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{kind} must be a JSON object")
    return payload


def prompt_text_from_packet(packet_path: Path) -> tuple[dict[str, Any] | None, str]:
    if packet_path.suffix.lower() == ".json":
        packet = read_json_object(packet_path, "prompt packet")
        if packet.get("report_type") != "correction_aware_prompt_packet.v1":
            raise ValueError("prompt packet report_type must be correction_aware_prompt_packet.v1")
        for field in PROTECTED_FALSE_FIELDS:
            if packet.get(field) is not False:
                raise ValueError(f"prompt packet {field} must be false")
        text = "\n".join(
            [
                "# Correction-Aware Prompt Packet",
                "",
                f"Task summary: {packet.get('task_summary', '')}",
                f"Allowed files: {', '.join(packet.get('allowed_files') or [])}",
                f"Behavior corrections: {', '.join(packet.get('behavior_corrections') or [])}",
                "",
                "Behavior correction guidance:",
            ]
        )
        for section, payload in (packet.get("rendered_prompt_sections") or {}).items():
            text += f"\n## {section}\n{json.dumps(payload, indent=2, sort_keys=True)}"
        return packet, text + "\n"

    text = packet_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("prompt packet is empty")
    return None, text


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def call_openai_compatible(
    *,
    endpoint_url: str,
    model: str,
    prompt_text: str,
    max_tokens: int,
    temperature: float,
    timeout_seconds: int,
) -> dict[str, Any]:
    url = endpoint_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    request_body = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt_text}],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_raw_text(response: dict[str, Any]) -> str:
    try:
        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        return json.dumps(content, sort_keys=True)
    except Exception:
        return ""


def validate_prompt_packet_json(packet: dict[str, Any]) -> None:
    if packet.get("report_type") != "correction_aware_prompt_packet.v1":
        raise ValueError("prompt packet report_type must be correction_aware_prompt_packet.v1")
    for field in PROTECTED_FALSE_FIELDS:
        if packet.get(field) is not False:
            raise ValueError(f"prompt packet {field} must be false")


def run_attempt(
    *,
    prompt_packet: Path,
    out_dir: Path,
    endpoint_url: str,
    model: str,
    max_tokens: int,
    temperature: float,
    timeout_seconds: int,
    authorized: bool,
    client: Any = call_openai_compatible,
) -> dict[str, Any]:
    if not authorized:
        raise ValueError("model attempt requires explicit authorization")
    if out_dir.exists():
        raise ValueError(f"output directory already exists: {out_dir}")
    if not prompt_packet.exists():
        raise ValueError(f"missing prompt packet: {prompt_packet}")

    out_dir.mkdir(parents=True, exist_ok=False)
    status = StatusWriter(out_dir, out_dir.name)
    status.event("RUN_START", "start", prompt_packet=str(prompt_packet))

    try:
        packet_json, prompt_text = prompt_text_from_packet(prompt_packet)
        if packet_json is not None:
            validate_prompt_packet_json(packet_json)
        status.event("PROMPT_PACKET_READ", "complete", prompt_packet=str(prompt_packet))
        status.event("MODEL_CALL_START", "start", model=model)

        response = client(
            endpoint_url=endpoint_url,
            model=model,
            prompt_text=prompt_text,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
        raw_output = extract_raw_text(response)

        raw_output_path = out_dir / "raw_model_output.txt"
        raw_output_path.write_text(raw_output, encoding="utf-8")

        prompt_sha256 = sha256_text(prompt_text)
        raw_output_sha256 = sha256_text(raw_output)
        record = {
            "report_type": REPORT_TYPE,
            "source_prompt_packet": str(prompt_packet),
            "endpoint_url": redact_endpoint_url(endpoint_url),
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timeout_seconds": timeout_seconds,
            "prompt_sha256": prompt_sha256,
            "raw_output_sha256": raw_output_sha256,
            "raw_output_path": str(raw_output_path),
            "status_log_path": str(out_dir / "status.log"),
            "status_events_path": str(out_dir / "status_events.jsonl"),
            "model_inference_performed": True,
            "generation_performed": True,
            "training_performed": False,
            "delta_written": False,
            "patched_model_materialized": False,
            "promotion_authorized": False,
            "validation_performed": False,
            "supervised_acceptance_performed": False,
            "automatic_failure_curriculum_capture_authorized": False,
        }
        summary = {
            "run_status": "completed",
            "source_prompt_packet": str(prompt_packet),
            "model": model,
            "prompt_sha256": prompt_sha256,
            "raw_output_sha256": raw_output_sha256,
            "output_excerpt": raw_output[:240],
            "recommended_next_step": RECOMMENDED_NEXT_STEP,
        }
        write_json(out_dir / "model_attempt_record.json", record)
        write_json(out_dir / "model_attempt_summary.json", summary)
        status.event("MODEL_CALL_COMPLETE", "complete", raw_output_sha256=raw_output_sha256)
        status.event("ARTIFACTS_WRITTEN", "complete")
        status.event("RUN_COMPLETE", "complete", run_status="completed")
        return {"record": record, "summary": summary, "raw_output": raw_output}
    except Exception as exc:
        status.event("RUN_FAILED", "failed", error=str(exc))
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one correction-aware model attempt.")
    parser.add_argument("--prompt-packet", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--authorize-model-attempt", action="store_true")
    args = parser.parse_args(argv)

    try:
        run_attempt(
            prompt_packet=args.prompt_packet,
            out_dir=args.out_dir,
            endpoint_url=args.endpoint_url,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            timeout_seconds=args.timeout_seconds,
            authorized=bool(args.authorize_model_attempt),
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
