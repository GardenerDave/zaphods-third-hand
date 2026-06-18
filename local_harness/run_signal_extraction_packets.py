#!/usr/bin/env python3
"""Run raw-signal extraction packets against an explicit model endpoint."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

import raw_signal_validate


SYSTEM_MESSAGE = "You return raw signal JSONL only. No prose. No markdown fences."
ENV_BASE_URL = "ZTH_SIGNAL_EXTRACT_BASE_URL"
ENV_API_KEY = "ZTH_SIGNAL_EXTRACT_API_KEY"
ENV_MODEL = "ZTH_SIGNAL_EXTRACT_MODEL"
ENV_TIMEOUT = "ZTH_SIGNAL_EXTRACT_TIMEOUT_SECONDS"
ENV_MAX_TOKENS = "ZTH_SIGNAL_EXTRACT_MAX_TOKENS"
ENV_TEMPERATURE = "ZTH_SIGNAL_EXTRACT_TEMPERATURE"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_TOKENS = 1200
DEFAULT_TEMPERATURE = 0.0
NORMALIZATION_STRATEGIES = (
    "jsonl",
    "json_object",
    "json_array",
    "markdown_fenced_json",
    "markdown_fenced_jsonl",
    "markdown_fenced_multi_json_objects",
    "markdown_fenced_multi_json_arrays",
    "markdown_fenced_multi_json_regions",
    "multi_json_objects",
    "multi_json_arrays",
    "multi_json_regions",
    "extracted_json",
    "failed",
)


@dataclass
class NormalizationResult:
    status: str
    strategy: str
    jsonl_text: str
    error: str = ""


def one_line(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(line.strip() for line in text.split("\n")).strip()
    return text or default


def safe_filename(value: Any, default: str = "packet") -> str:
    text = one_line(value, default)
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("._-")
    return text or default


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return int(value)


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return float(value)


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def compact_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)


def rows_from_json_value(value: Any, strategy: str) -> NormalizationResult:
    if isinstance(value, dict):
        return NormalizationResult(status="ok", strategy=strategy, jsonl_text=compact_jsonl([value]))
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            return NormalizationResult(
                status="error",
                strategy="failed",
                jsonl_text="",
                error="JSON array contains non-object items",
            )
        return NormalizationResult(status="ok", strategy=strategy, jsonl_text=compact_jsonl(value))
    return NormalizationResult(
        status="error",
        strategy="failed",
        jsonl_text="",
        error="JSON value is not an object or array of objects",
    )


def try_normalize_jsonl(text: str) -> NormalizationResult | None:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(value, dict):
            return None
        rows.append(value)
    if not rows:
        return None
    return NormalizationResult(status="ok", strategy="jsonl", jsonl_text=compact_jsonl(rows))


def try_parse_full_json(text: str, strategy: str) -> NormalizationResult | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(value, dict):
        return rows_from_json_value(value, strategy)
    if isinstance(value, list):
        return rows_from_json_value(value, "json_array" if strategy == "json_object" else strategy)
    return rows_from_json_value(value, strategy)


def with_strategy(result: NormalizationResult, strategy: str) -> NormalizationResult:
    return NormalizationResult(
        status=result.status,
        strategy=strategy if result.status == "ok" else result.strategy,
        jsonl_text=result.jsonl_text,
        error=result.error,
    )


def fenced_multi_strategy(strategy: str) -> str:
    if strategy == "multi_json_objects":
        return "markdown_fenced_multi_json_objects"
    if strategy == "multi_json_arrays":
        return "markdown_fenced_multi_json_arrays"
    if strategy == "multi_json_regions":
        return "markdown_fenced_multi_json_regions"
    return strategy


def try_parse_markdown_fence(text: str) -> NormalizationResult | None:
    if "```" not in text:
        return None

    match = re.fullmatch(
        r"\s*```(?:jsonl|json)?[ \t]*(?:\r?\n)?(.*?)(?:\r?\n)?```\s*",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return NormalizationResult(
            status="error",
            strategy="failed",
            jsonl_text="",
            error="Markdown fenced JSON must not include prose outside the fence",
        )

    inner = match.group(1)
    jsonl_result = try_normalize_jsonl(inner)
    if jsonl_result is not None:
        return with_strategy(jsonl_result, "markdown_fenced_jsonl")

    full_json_result = try_parse_full_json(inner, "markdown_fenced_json")
    if full_json_result is not None:
        return full_json_result

    multi_region_result = try_parse_multi_json_regions(inner)
    if multi_region_result is not None:
        return with_strategy(multi_region_result, fenced_multi_strategy(multi_region_result.strategy))

    return NormalizationResult(
        status="error",
        strategy="failed",
        jsonl_text="",
        error="Markdown fenced content is not parseable JSONL, JSON object, JSON array, or safe adjacent JSON regions",
    )


def skip_multi_json_separators(text: str, index: int) -> int:
    while index < len(text) and (text[index].isspace() or text[index] == ","):
        index += 1
    return index


def skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def multi_json_rows_from_regions(regions: list[Any]) -> NormalizationResult:
    rows: list[dict[str, Any]] = []
    region_types: set[str] = set()
    for value in regions:
        if isinstance(value, dict):
            region_types.add("object")
            rows.append(value)
            continue
        if isinstance(value, list):
            region_types.add("array")
            if not all(isinstance(item, dict) for item in value):
                return NormalizationResult(
                    status="error",
                    strategy="failed",
                    jsonl_text="",
                    error="JSON array contains non-object items",
                )
            rows.extend(value)
            continue
        return NormalizationResult(
            status="error",
            strategy="failed",
            jsonl_text="",
            error="Top-level JSON value is not an object or array of objects",
        )

    if not rows:
        return NormalizationResult(
            status="error",
            strategy="failed",
            jsonl_text="",
            error="No JSON object rows found",
        )
    if region_types == {"object"}:
        strategy = "multi_json_objects"
    elif region_types == {"array"}:
        strategy = "multi_json_arrays"
    else:
        strategy = "multi_json_regions"
    return NormalizationResult(status="ok", strategy=strategy, jsonl_text=compact_jsonl(rows))


def try_parse_multi_json_regions(text: str) -> NormalizationResult | None:
    stripped_start = skip_whitespace(text, 0)
    if stripped_start >= len(text):
        return None
    if text[stripped_start] not in "{[":
        if text[stripped_start] in '"-0123456789tfn':
            try:
                value, _ = json.JSONDecoder().raw_decode(text[stripped_start:])
            except json.JSONDecodeError:
                return None
            if not isinstance(value, (dict, list)):
                return NormalizationResult(
                    status="error",
                    strategy="failed",
                    jsonl_text="",
                    error="Top-level JSON value is not an object or array of objects",
                )
        return None

    decoder = json.JSONDecoder()
    index = stripped_start
    regions: list[Any] = []
    while index < len(text):
        if text[index] not in "{[":
            if regions:
                return NormalizationResult(
                    status="error",
                    strategy="failed",
                    jsonl_text="",
                    error="Unexpected text between JSON regions",
                )
            return None
        try:
            value, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            return NormalizationResult(
                status="error",
                strategy="failed",
                jsonl_text="",
                error="Incomplete trailing JSON region",
            )
        if not isinstance(value, (dict, list)):
            return NormalizationResult(
                status="error",
                strategy="failed",
                jsonl_text="",
                error="Top-level JSON value is not an object or array of objects",
            )
        regions.append(value)
        index = skip_multi_json_separators(text, index + end)
        if index >= len(text):
            break
        if text[index] not in "{[":
            return NormalizationResult(
                status="error",
                strategy="failed",
                jsonl_text="",
                error="Unexpected text between JSON regions",
            )

    if len(regions) < 2:
        return None
    return multi_json_rows_from_regions(regions)


def json_region_candidates(text: str) -> list[tuple[int, int, Any]]:
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, int, Any]] = []
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            value, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, (dict, list)):
            candidates.append((index, index + end, value))

    filtered: list[tuple[int, int, Any]] = []
    for candidate in candidates:
        start, end, _ = candidate
        contained = False
        for other_start, other_end, _ in candidates:
            if (other_start, other_end) == (start, end):
                continue
            if other_start <= start and end <= other_end:
                contained = True
                break
        if not contained:
            filtered.append(candidate)
    return filtered


def try_extract_single_json_region(text: str) -> NormalizationResult | None:
    candidates = json_region_candidates(text)
    if not candidates:
        return None
    if len(candidates) > 1:
        return NormalizationResult(
            status="error",
            strategy="failed",
            jsonl_text="",
            error="Multiple JSON object/array regions found",
        )
    _, _, value = candidates[0]
    return rows_from_json_value(value, "extracted_json")


def normalize_model_output(text: str) -> NormalizationResult:
    jsonl_result = try_normalize_jsonl(text)
    if jsonl_result is not None:
        return jsonl_result

    full_json_result = try_parse_full_json(text, "json_object")
    if full_json_result is not None:
        return full_json_result

    fenced_result = try_parse_markdown_fence(text)
    if fenced_result is not None:
        return fenced_result

    multi_region_result = try_parse_multi_json_regions(text)
    if multi_region_result is not None:
        return multi_region_result

    extracted_result = try_extract_single_json_region(text)
    if extracted_result is not None:
        return extracted_result

    return NormalizationResult(
        status="error",
        strategy="failed",
        jsonl_text="",
        error=(
            "Could not parse raw output as JSONL, JSON object, JSON array, fenced JSON, "
            "safe adjacent JSON regions, or one unambiguous JSON region"
        ),
    )


def select_packets(
    packets: list[dict[str, Any]],
    *,
    packet_id: str | None = None,
    limit: int | None = None,
    start_index: int | None = None,
    end_index: int | None = None,
) -> list[dict[str, Any]]:
    return [
        packet
        for _, packet in select_packet_entries(
            packets,
            packet_id=packet_id,
            limit=limit,
            start_index=start_index,
            end_index=end_index,
        )
    ]


def select_packet_entries(
    packets: list[dict[str, Any]],
    *,
    packet_id: str | None = None,
    limit: int | None = None,
    start_index: int | None = None,
    end_index: int | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    if start_index is not None and start_index < 1:
        raise ValueError("--start-index must be 1 or greater.")
    if end_index is not None and end_index < 1:
        raise ValueError("--end-index must be 1 or greater.")
    if start_index is not None and end_index is not None and start_index > end_index:
        raise ValueError("--start-index must be less than or equal to --end-index.")
    if limit is not None and limit < 0:
        raise ValueError("--limit must be 0 or greater.")

    entries = list(enumerate(packets, start=1))
    if start_index is not None:
        entries = [(index, packet) for index, packet in entries if index >= start_index]
    if end_index is not None:
        entries = [(index, packet) for index, packet in entries if index <= end_index]
    if packet_id:
        entries = [(index, packet) for index, packet in entries if str(packet.get("packet_id", "")) == packet_id]
    if limit is not None:
        entries = entries[:limit]
    return entries


def chat_completions_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/chat/completions"


def extract_content(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0]
    if not isinstance(choice, dict):
        return ""
    message = choice.get("message")
    if isinstance(message, dict) and message.get("content") is not None:
        return str(message.get("content"))
    if choice.get("text") is not None:
        return str(choice.get("text"))
    return ""


def call_openai_chat(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout_seconds: int,
    max_tokens: int,
    temperature: float,
) -> tuple[str, str]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        chat_completions_url(base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return ("", f"HTTP {exc.code}: {body}")
    except Exception as exc:
        return ("", str(exc))

    content = extract_content(result)
    if not content:
        return ("", "empty response content")
    return (content, "")


def manifest_row(
    packet: dict[str, Any],
    *,
    raw_output_path: str,
    normalized_output_path: str,
    model: str,
    base_url: str,
    status: str,
    error: str,
    response_chars: int,
    normalization_status: str,
    normalization_strategy: str,
    normalization_error: str,
    attempt_count: int,
    resume_skipped: bool,
    selected_index: int,
    resume_source: str = "",
) -> dict[str, Any]:
    return {
        "packet_id": str(packet.get("packet_id", "")),
        "conversation_id": str(packet.get("conversation_id", "")),
        "chunk_id": str(packet.get("chunk_id", "")),
        "chunk_pass": str(packet.get("chunk_pass", "")),
        "packet_path": str(packet.get("packet_path", "")),
        "raw_output_path": raw_output_path,
        "normalized_output_path": normalized_output_path,
        "model": model,
        "base_url": base_url,
        "status": status,
        "error": error,
        "response_chars": response_chars,
        "normalization_status": normalization_status,
        "normalization_strategy": normalization_strategy,
        "normalization_error": normalization_error,
        "attempt_count": attempt_count,
        "resume_skipped": resume_skipped,
        "selected_index": selected_index,
        "resume_source": resume_source,
    }


def load_existing_manifest(out_dir: Path) -> dict[str, dict[str, Any]]:
    manifest_path = out_dir / "run_manifest.jsonl"
    if not manifest_path.is_file():
        return {}
    rows = read_jsonl(manifest_path)
    by_packet_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        packet_id = str(row.get("packet_id", ""))
        if packet_id:
            by_packet_id[packet_id] = row
    return by_packet_id


def usable_raw_output_path(raw_output_path: Path) -> bool:
    return raw_output_path.is_file() and raw_output_path.stat().st_size > 0


def raw_output_path_for_packet(raw_outputs_dir: Path, packet_id_value: str) -> Path:
    return raw_outputs_dir / f"{safe_filename(packet_id_value)}.jsonl"


def normalized_output_path_for_packet(normalized_outputs_dir: Path, packet_id_value: str) -> Path:
    return normalized_outputs_dir / f"{safe_filename(packet_id_value)}.jsonl"


def resume_manifest_row(row: dict[str, Any], selected_index: int, resume_source: str) -> dict[str, Any]:
    resumed = dict(row)
    resumed.setdefault("normalized_output_path", "")
    resumed.setdefault("normalization_status", "not_run")
    resumed.setdefault("normalization_strategy", "")
    resumed.setdefault("normalization_error", "")
    resumed["attempt_count"] = 0
    resumed["resume_skipped"] = True
    resumed["selected_index"] = selected_index
    resumed["resume_source"] = resume_source
    return resumed


def build_resume_row_from_output(
    packet: dict[str, Any],
    *,
    raw_output_path: Path,
    normalized_output_path: Path,
    model: str,
    base_url: str,
    selected_index: int,
    validate: bool,
) -> dict[str, Any] | None:
    if not usable_raw_output_path(raw_output_path):
        return None

    raw_text = raw_output_path.read_text(encoding="utf-8")
    result = normalize_model_output(raw_text)
    if result.status != "ok":
        return None

    had_normalized_output = usable_raw_output_path(normalized_output_path)
    normalized_path_text = str(normalized_output_path) if had_normalized_output else ""
    normalization_status = result.status
    normalization_strategy = result.strategy
    normalization_error = result.error
    resume_source = "normalized_output" if had_normalized_output else "raw_output"

    if validate:
        normalized_output_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_output_path.write_text(result.jsonl_text, encoding="utf-8")
        normalized_path_text = str(normalized_output_path)
        resume_source = "normalized_output" if had_normalized_output else "raw_output"

    return manifest_row(
        packet,
        raw_output_path=str(raw_output_path),
        normalized_output_path=normalized_path_text,
        model=model,
        base_url=base_url,
        status="ok",
        error="",
        response_chars=len(raw_text),
        normalization_status=normalization_status,
        normalization_strategy=normalization_strategy,
        normalization_error=normalization_error,
        attempt_count=0,
        resume_skipped=True,
        selected_index=selected_index,
        resume_source=resume_source,
    )


def resume_row_for_packet(
    packet: dict[str, Any],
    *,
    existing_row: dict[str, Any] | None,
    raw_outputs_dir: Path,
    normalized_outputs_dir: Path,
    model: str,
    base_url: str,
    selected_index: int,
    validate: bool,
) -> dict[str, Any] | None:
    packet_id_value = str(packet.get("packet_id", ""))
    candidate_paths: list[tuple[Path, str]] = []
    if existing_row is not None and existing_row.get("status") == "ok":
        existing_raw_output_path = str(existing_row.get("raw_output_path", ""))
        if existing_raw_output_path:
            candidate_paths.append((Path(existing_raw_output_path), "manifest"))
    candidate_paths.append((raw_output_path_for_packet(raw_outputs_dir, packet_id_value), "raw_output"))

    seen_paths: set[str] = set()
    for raw_output_path, resume_source in candidate_paths:
        path_key = str(raw_output_path)
        if path_key in seen_paths:
            continue
        seen_paths.add(path_key)
        normalized_output_path = normalized_output_path_for_packet(normalized_outputs_dir, packet_id_value)
        row = build_resume_row_from_output(
            packet,
            raw_output_path=raw_output_path,
            normalized_output_path=normalized_output_path,
            model=model,
            base_url=base_url,
            selected_index=selected_index,
            validate=validate,
        )
        if row is not None:
            if resume_source == "manifest" and not validate:
                row = resume_manifest_row(row, selected_index, "manifest")
            return row
    return None


def short_error(error: str) -> str:
    return one_line(error, "unknown error")[:180]


def run_packets(
    *,
    packets_path: Path,
    out_dir: Path,
    base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    limit: int | None = None,
    packet_id: str | None = None,
    start_index: int | None = None,
    end_index: int | None = None,
    resume: bool = False,
    retries: int = 0,
    retry_delay_seconds: float = 0,
    dry_run: bool = False,
    validate: bool = False,
) -> dict[str, Any]:
    if not dry_run and not base_url:
        raise ValueError(f"Missing base URL. Set --base-url or {ENV_BASE_URL}.")
    if not dry_run and not model:
        raise ValueError(f"Missing model. Set --model or {ENV_MODEL}.")
    if retries < 0:
        raise ValueError("--retries must be 0 or greater.")
    if retry_delay_seconds < 0:
        raise ValueError("--retry-delay-seconds must be 0 or greater.")

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_outputs_dir = out_dir / "raw_outputs"
    normalized_outputs_dir = out_dir / "normalized_outputs"
    if not dry_run:
        raw_outputs_dir.mkdir(parents=True, exist_ok=True)

    packets = read_jsonl(packets_path)
    selected_entries = select_packet_entries(
        packets,
        packet_id=packet_id,
        limit=limit,
        start_index=start_index,
        end_index=end_index,
    )
    existing_by_packet_id = load_existing_manifest(out_dir) if resume and not dry_run else {}

    manifest_rows: list[dict[str, Any]] = []
    retry_count = 0
    total_selected = len(selected_entries)
    for selected_ordinal, (selected_index, packet) in enumerate(selected_entries, start=1):
        packet_path = Path(str(packet.get("packet_path", "")))
        packet_id_value = str(packet.get("packet_id", ""))
        existing_row = existing_by_packet_id.get(packet_id_value)
        raw_output_path = raw_output_path_for_packet(raw_outputs_dir, packet_id_value)
        if resume and not dry_run:
            resume_row = resume_row_for_packet(
                packet,
                existing_row=existing_row,
                raw_outputs_dir=raw_outputs_dir,
                normalized_outputs_dir=normalized_outputs_dir,
                model=model,
                base_url=base_url,
                selected_index=selected_index,
                validate=validate,
            )
        else:
            resume_row = None
        if resume_row is not None:
            print(f"SKIP packet {selected_ordinal}/{total_selected}: {packet_id_value} already completed")
            manifest_rows.append(resume_row)
            continue

        if dry_run:
            manifest_rows.append(
                manifest_row(
                    packet,
                    raw_output_path="",
                    normalized_output_path="",
                    model=model,
                    base_url=base_url,
                    status="dry_run",
                    error="",
                    response_chars=0,
                    normalization_status="not_run",
                    normalization_strategy="",
                    normalization_error="",
                    attempt_count=0,
                    resume_skipped=False,
                    selected_index=selected_index,
                )
            )
            continue

        print(f"Running packet {selected_ordinal}/{total_selected}: {packet_id_value}")
        try:
            packet_text = packet_path.read_text(encoding="utf-8")
        except Exception as exc:
            error = f"packet_read_error: {exc}"
            manifest_rows.append(
                manifest_row(
                    packet,
                    raw_output_path=str(raw_output_path),
                    normalized_output_path="",
                    model=model,
                    base_url=base_url,
                    status="error",
                    error=error,
                    response_chars=0,
                    normalization_status="not_run",
                    normalization_strategy="",
                    normalization_error="",
                    attempt_count=0,
                    resume_skipped=False,
                    selected_index=selected_index,
                )
            )
            print(f"ERROR packet {selected_ordinal}/{total_selected}: {packet_id_value}: {short_error(error)}")
            continue

        attempt_count = 0
        content = ""
        error = ""
        for attempt_number in range(retries + 1):
            attempt_count += 1
            content, error = call_openai_chat(
                base_url=base_url,
                api_key=api_key,
                model=model,
                prompt=packet_text,
                timeout_seconds=timeout_seconds,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if not error:
                break
            if attempt_number < retries:
                retry_count += 1
                if retry_delay_seconds:
                    time.sleep(retry_delay_seconds)

        if error:
            manifest_rows.append(
                manifest_row(
                    packet,
                    raw_output_path=str(raw_output_path),
                    normalized_output_path="",
                    model=model,
                    base_url=base_url,
                    status="error",
                    error=error,
                    response_chars=0,
                    normalization_status="not_run",
                    normalization_strategy="",
                    normalization_error="",
                    attempt_count=attempt_count,
                    resume_skipped=False,
                    selected_index=selected_index,
                )
            )
            print(f"ERROR packet {selected_ordinal}/{total_selected}: {packet_id_value}: {short_error(error)}")
            continue

        raw_output_path.write_text(content, encoding="utf-8")
        manifest_rows.append(
            manifest_row(
                packet,
                raw_output_path=str(raw_output_path),
                normalized_output_path="",
                model=model,
                base_url=base_url,
                status="ok",
                error="",
                response_chars=len(content),
                normalization_status="not_run",
                normalization_strategy="",
                normalization_error="",
                attempt_count=attempt_count,
                resume_skipped=False,
                selected_index=selected_index,
            )
        )
        print(f"OK packet {selected_ordinal}/{total_selected}: {packet_id_value}")

    validated = False
    validation_summary_path = ""
    combined_path = out_dir / "combined_raw_signals.jsonl"
    normalized_count = 0
    normalization_error_count = 0
    if validate:
        normalized_outputs_dir.mkdir(parents=True, exist_ok=True)
        strategy_counts = {strategy: 0 for strategy in NORMALIZATION_STRATEGIES}
        ok_rows = [row for row in manifest_rows if row["status"] == "ok"]
        combined_text_parts: list[str] = []
        for row in ok_rows:
            raw_path = Path(str(row["raw_output_path"]))
            if not raw_path.is_file():
                continue
            raw_text = raw_path.read_text(encoding="utf-8")
            result = normalize_model_output(raw_text)
            row["normalization_status"] = result.status
            row["normalization_strategy"] = result.strategy
            row["normalization_error"] = result.error
            strategy_counts[result.strategy] = strategy_counts.get(result.strategy, 0) + 1
            if result.status == "ok":
                normalized_path = normalized_outputs_dir / f"{safe_filename(row['packet_id'])}.jsonl"
                normalized_path.write_text(result.jsonl_text, encoding="utf-8")
                row["normalized_output_path"] = str(normalized_path)
                normalized_count += 1
                combined_text_parts.append(result.jsonl_text)
            else:
                normalization_error_count += 1
        combined_path.write_text("".join(combined_text_parts), encoding="utf-8")
        raw_signal_validate.validate_raw_signals(combined_path, out_dir / "validated")
        validated = True
        validation_summary_path = str(out_dir / "validated" / "validation_summary.json")
        normalization_summary = {
            "selected_packet_count": len(selected_entries),
            "ok_raw_output_count": len(ok_rows),
            "normalized_count": normalized_count,
            "normalization_error_count": normalization_error_count,
            "strategies": strategy_counts,
        }
        (out_dir / "normalization_summary.json").write_text(
            json.dumps(normalization_summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    manifest_path = out_dir / "run_manifest.jsonl"
    write_jsonl(manifest_path, manifest_rows)

    summary = {
        "selected_packet_count": len(selected_entries),
        "ok_count": sum(1 for row in manifest_rows if row["status"] == "ok"),
        "error_count": sum(1 for row in manifest_rows if row["status"] == "error"),
        "normalized_count": normalized_count,
        "normalization_error_count": normalization_error_count,
        "dry_run": dry_run,
        "validated": validated,
        "resume": resume,
        "resume_skipped_count": sum(1 for row in manifest_rows if row.get("resume_skipped")),
        "attempted_count": sum(
            1
            for row in manifest_rows
            if row.get("status") != "dry_run" and not row.get("resume_skipped")
        ),
        "retry_count": retry_count,
        "start_index": start_index,
        "end_index": end_index,
        "run_manifest_path": str(manifest_path),
        "combined_raw_signals_path": str(combined_path) if validate else "",
        "validation_summary_path": validation_summary_path,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run raw-signal extraction packets against an explicit endpoint.")
    parser.add_argument("--packets", required=True, help="Path to packets.jsonl.")
    parser.add_argument("--out-dir", required=True, help="Directory that will receive raw outputs and run manifests.")
    parser.add_argument("--base-url", default=os.environ.get(ENV_BASE_URL, ""), help=f"Override {ENV_BASE_URL}.")
    parser.add_argument("--api-key", default=os.environ.get(ENV_API_KEY, ""), help=f"Override {ENV_API_KEY}.")
    parser.add_argument("--model", default=os.environ.get(ENV_MODEL, ""), help=f"Override {ENV_MODEL}.")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=env_int(ENV_TIMEOUT, DEFAULT_TIMEOUT_SECONDS),
        help=f"HTTP timeout seconds. Defaults to {ENV_TIMEOUT} or {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=env_int(ENV_MAX_TOKENS, DEFAULT_MAX_TOKENS),
        help=f"Max response tokens. Defaults to {ENV_MAX_TOKENS} or {DEFAULT_MAX_TOKENS}.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=env_float(ENV_TEMPERATURE, DEFAULT_TEMPERATURE),
        help=f"Sampling temperature. Defaults to {ENV_TEMPERATURE} or {DEFAULT_TEMPERATURE}.",
    )
    parser.add_argument("--limit", type=int, help="Run only the first N selected packets.")
    parser.add_argument("--packet-id", help="Run only a specific packet id.")
    parser.add_argument("--start-index", type=int, help="Start at this 1-based packet position in packets.jsonl.")
    parser.add_argument("--end-index", type=int, help="End at this 1-based packet position in packets.jsonl, inclusive.")
    parser.add_argument("--resume", action="store_true", help="Skip already completed packets with existing raw outputs.")
    parser.add_argument("--retries", type=int, default=0, help="Endpoint retries per packet after the first failed attempt.")
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=0,
        help="Delay between endpoint retry attempts. Defaults to 0.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Write manifest and summary without endpoint calls.")
    parser.add_argument("--validate", action="store_true", help="Validate successful raw outputs after the run.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = run_packets(
            packets_path=Path(args.packets),
            out_dir=Path(args.out_dir),
            base_url=args.base_url.rstrip("/"),
            api_key=args.api_key,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            limit=args.limit,
            packet_id=args.packet_id,
            start_index=args.start_index,
            end_index=args.end_index,
            resume=args.resume,
            retries=args.retries,
            retry_delay_seconds=args.retry_delay_seconds,
            dry_run=args.dry_run,
            validate=args.validate,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Selected packets: {summary['selected_packet_count']}")
    print(f"OK: {summary['ok_count']}")
    print(f"Errors: {summary['error_count']}")
    print(f"Run manifest: {summary['run_manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
