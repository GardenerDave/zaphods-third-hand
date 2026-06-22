#!/usr/bin/env python3
"""Produce ZTH-owned verified-YAML smoke evidence from one local endpoint."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


PRODUCER_ID = "zth_smoke_probe"
PRODUCER_CONTRACT_VERSION = "zth.llm_probe_smoke_probe.v0.1"
VERIFIED_YAML_SCHEMA_VERSION = "llm_probe.verified_yaml.v1"
LOCAL_API_KEY_SENTINELS = {"", "not-needed-for-local"}
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_TOKENS = 120
VISIBLE_REASONING_PATTERN = re.compile(
    r"<\s*/?\s*think\b|reasoning_content|(?:^|\n)\s*(?:analysis|reasoning)\s*:",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ProbeDefinition:
    probe_id: str
    prompt: str
    required_keys: tuple[str, ...] = ()
    allow_embedded_json: bool = False
    expected_exact_text: str | None = None


@dataclass(frozen=True)
class ProducerConfig:
    base_url: str
    model: str
    out_dir: Path
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_tokens: int = DEFAULT_MAX_TOKENS
    api_key: str = "not-needed-for-local"
    producer_run_id: str | None = None


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    status: str
    passed: bool
    duration_ms: int
    http_status: int | None
    visible_response_text: str
    response_payload: Any
    finish_reason: str | None
    failures: tuple[str, ...]
    diagnostics: tuple[str, ...]
    evaluation: dict[str, Any]


HttpClient = Callable[
    [str, dict[str, Any], dict[str, str], int],
    tuple[int, Any],
]


PROBES = (
    ProbeDefinition(
        probe_id="tool_call_basic",
        prompt=(
            "[probe_id: tool_call_basic]\n"
            "Return one compact JSON object with exactly these keys: "
            "route, confidence, next_action. Use route \"smoke\", a numeric "
            "confidence, and next_action \"review\". Return no prose."
        ),
        required_keys=("route", "confidence", "next_action"),
        allow_embedded_json=True,
    ),
    ProbeDefinition(
        probe_id="json_schema_basic",
        prompt=(
            "[probe_id: json_schema_basic]\n"
            "Return strict JSON only with exactly these keys: status, checks, "
            "next_action. Use status \"ok\", checks as an array, and "
            "next_action \"review\". No Markdown fences or prose."
        ),
        required_keys=("status", "checks", "next_action"),
    ),
    ProbeDefinition(
        probe_id="think_block_leak",
        prompt=(
            "[probe_id: think_block_leak]\n"
            "Return the final answer only. Reply exactly READY. Do not include "
            "analysis, reasoning, hidden-chain markers, or XML-style tags."
        ),
        expected_exact_text="READY",
    ),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def default_run_id(value: datetime) -> str:
    return f"zth-smoke-probe-{value.strftime('%Y%m%dT%H%M%SZ')}"


def endpoint_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def request_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key not in LOCAL_API_KEY_SENTINELS:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def default_http_client(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
        return int(response.status), json.loads(body)


def response_text(payload: Any) -> tuple[str, str | None]:
    if not isinstance(payload, dict):
        raise ValueError("response_payload_is_not_object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("response_choices_missing")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise ValueError("response_choice_is_not_object")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("response_message_is_not_object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("visible_response_text_missing")
    finish_reason = choice.get("finish_reason")
    return content, str(finish_reason) if finish_reason is not None else None


def parse_json_object(
    text: str,
    *,
    allow_embedded: bool,
) -> tuple[dict[str, Any] | None, bool]:
    try:
        parsed = json.loads(text)
        return (parsed if isinstance(parsed, dict) else None, True)
    except json.JSONDecodeError:
        if not allow_embedded:
            return None, False

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None, False
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None, False
    return (parsed if isinstance(parsed, dict) else None, False)


def evaluate_visible_response(
    probe: ProbeDefinition,
    text: str,
) -> tuple[bool, tuple[str, ...], tuple[str, ...], dict[str, Any]]:
    failures: list[str] = []
    diagnostics: list[str] = []
    evaluation: dict[str, Any] = {}

    if probe.required_keys:
        parsed, strict_json = parse_json_object(
            text,
            allow_embedded=probe.allow_embedded_json,
        )
        evaluation["json_object_parsed"] = parsed is not None
        evaluation["strict_json"] = strict_json
        if parsed is None:
            failures.append("invalid_json_object")
            evaluation["required_keys_present"] = []
            evaluation["missing_required_keys"] = list(probe.required_keys)
        else:
            present = [key for key in probe.required_keys if key in parsed]
            missing = [key for key in probe.required_keys if key not in parsed]
            evaluation["required_keys_present"] = present
            evaluation["missing_required_keys"] = missing
            if missing:
                failures.append("missing_required_keys")
            if not strict_json:
                diagnostics.append("json_object_was_embedded_in_extra_text")

    if probe.expected_exact_text is not None:
        leaked = bool(VISIBLE_REASONING_PATTERN.search(text))
        exact_match = text.strip() == probe.expected_exact_text
        evaluation["visible_reasoning_marker_leaked"] = leaked
        evaluation["exact_text_match"] = exact_match
        if leaked:
            failures.append("visible_reasoning_marker_leak")
        if not exact_match:
            failures.append("unexpected_final_text")

    return not failures, tuple(failures), tuple(diagnostics), evaluation


def request_payload(
    config: ProducerConfig,
    probe: ProbeDefinition,
) -> dict[str, Any]:
    return {
        "model": config.model,
        "messages": [{"role": "user", "content": probe.prompt}],
        "temperature": 0,
        "max_tokens": config.max_tokens,
        "stream": False,
    }


def execute_probe(
    config: ProducerConfig,
    probe: ProbeDefinition,
    *,
    client: HttpClient = default_http_client,
) -> ProbeResult:
    started = time.monotonic()
    payload = request_payload(config, probe)
    http_status: int | None = None
    response_payload: Any = None
    visible_text = ""
    finish_reason: str | None = None
    failures: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    evaluation: dict[str, Any] = {}
    status = "error"
    passed = False

    try:
        http_status, response_payload = client(
            endpoint_url(config.base_url),
            payload,
            request_headers(config.api_key),
            config.timeout_seconds,
        )
        visible_text, finish_reason = response_text(response_payload)
        passed, failures, diagnostics, evaluation = evaluate_visible_response(
            probe,
            visible_text,
        )
        status = "pass" if passed else "fail"
    except urllib.error.HTTPError as exc:
        http_status = int(exc.code)
        body = exc.read().decode("utf-8", errors="replace")
        response_payload = {"http_error_body": body}
        failures = ("http_error",)
        diagnostics = (f"HTTP {exc.code}",)
    except TimeoutError as exc:
        failures = ("timeout_error",)
        diagnostics = (str(exc) or "request timed out",)
    except urllib.error.URLError as exc:
        failures = ("transport_error",)
        diagnostics = (str(exc.reason),)
    except ValueError as exc:
        failures = ("malformed_response",)
        diagnostics = (str(exc),)
    except Exception as exc:
        failures = ("transport_error",)
        diagnostics = (str(exc),)

    duration_ms = max(0, round((time.monotonic() - started) * 1000))
    return ProbeResult(
        probe_id=probe.probe_id,
        status=status,
        passed=passed,
        duration_ms=duration_ms,
        http_status=http_status,
        visible_response_text=visible_text,
        response_payload=response_payload,
        finish_reason=finish_reason,
        failures=failures,
        diagnostics=diagnostics,
        evaluation=evaluation,
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_verified_yaml(
    *,
    config: ProducerConfig,
    run_id: str,
    created_at: datetime,
    results: Sequence[ProbeResult],
) -> str:
    average_ms = (
        round(sum(result.duration_ms for result in results) / len(results))
        if results
        else 0
    )
    result_by_id = {result.probe_id: result for result in results}
    tool_result = result_by_id["tool_call_basic"]
    think_result = result_by_id["think_block_leak"]
    lines = [
        f"producer: {yaml_string(PRODUCER_ID)}",
        f"producer_contract_version: {yaml_string(PRODUCER_CONTRACT_VERSION)}",
        f"schema_version: {yaml_string(VERIFIED_YAML_SCHEMA_VERSION)}",
        f"provider: {yaml_string(PRODUCER_ID)}",
        f"last_run: {yaml_string(created_at.date().isoformat())}",
        f"producer_run_id: {yaml_string(run_id)}",
        "models:",
        f"  - id: {yaml_string(config.model)}",
        f"    tool_call: {yaml_string(tool_result.status)}",
        (
            "    think_blocks: "
            + yaml_string(
                "none"
                if think_result.passed
                else ("error" if think_result.status == "error" else "leaked")
            )
        ),
        f"    avg_response_ms: {average_ms}",
        "    tests:",
    ]
    for result in results:
        lines.extend(
            [
                f"      {result.probe_id}:",
                f"        passed: {'true' if result.passed else 'false'}",
                f"        pass_rate: {yaml_string('1/1' if result.passed else '0/1')}",
                f"        status: {yaml_string(result.status)}",
                f"        duration_ms: {result.duration_ms}",
                "        failures: "
                + json.dumps(list(result.failures), ensure_ascii=False),
                "        diagnostics: "
                + json.dumps(list(result.diagnostics), ensure_ascii=False),
            ]
        )
    lines.append(f"    last_tested: {yaml_string(created_at.date().isoformat())}")
    return "\n".join(lines) + "\n"


def raw_result_payload(
    *,
    config: ProducerConfig,
    run_id: str,
    probe: ProbeDefinition,
    result: ProbeResult,
) -> dict[str, Any]:
    return {
        "producer": PRODUCER_ID,
        "producer_contract_version": PRODUCER_CONTRACT_VERSION,
        "producer_run_id": run_id,
        "probe_id": result.probe_id,
        "model_id_requested": config.model,
        "request": {
            "messages": [{"role": "user", "content": probe.prompt}],
            "temperature": 0,
            "max_tokens": config.max_tokens,
        },
        "transport": {
            "endpoint": "<redacted>",
            "path": "/chat/completions",
            "http_status": result.http_status,
            "duration_ms": result.duration_ms,
        },
        "status": result.status,
        "passed": result.passed,
        "visible_response_text": result.visible_response_text,
        "finish_reason": result.finish_reason,
        "response": result.response_payload,
        "failures": list(result.failures),
        "diagnostics": list(result.diagnostics),
        "evaluation": result.evaluation,
    }


def run_metadata_payload(
    *,
    config: ProducerConfig,
    run_id: str,
    created_at: datetime,
    results: Sequence[ProbeResult],
) -> dict[str, Any]:
    status_counts = Counter(result.status for result in results)
    return {
        "producer": PRODUCER_ID,
        "producer_contract_version": PRODUCER_CONTRACT_VERSION,
        "verified_yaml_schema_version": VERIFIED_YAML_SCHEMA_VERSION,
        "producer_run_id": run_id,
        "created_at_utc": utc_iso(created_at),
        "model_id_requested": config.model,
        "endpoint": "<redacted>",
        "endpoint_path": "/chat/completions",
        "timeout_seconds": config.timeout_seconds,
        "max_tokens": config.max_tokens,
        "probe_ids": [probe.probe_id for probe in PROBES],
        "probe_count": len(results),
        "status_counts": dict(sorted(status_counts.items())),
        "all_required_probes_passed": bool(results)
        and all(result.passed for result in results),
        "requires_human_review": True,
        "promotion_performed": False,
        "outputs": {
            "verified_yaml": "verified/zth-smoke-probe.yaml",
            "raw_directory": "raw",
        },
        "safety_notes": [
            "This producer does not start or configure endpoints.",
            "This producer does not upload data or delete evidence.",
            "Probe evidence does not promote, rank, route, approve, or assign a model.",
            "Passing probes are evidence, not authority.",
        ],
    }


def validate_config(config: ProducerConfig) -> None:
    if not config.base_url.strip():
        raise ValueError("--base-url must be non-empty")
    if not config.model.strip():
        raise ValueError("--model must be non-empty")
    if config.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be greater than zero")
    if config.max_tokens <= 0:
        raise ValueError("--max-tokens must be greater than zero")
    if config.out_dir.exists():
        raise FileExistsError(
            f"refusing to overwrite existing output path: {config.out_dir}"
        )


def produce_smoke_evidence(
    config: ProducerConfig,
    *,
    client: HttpClient = default_http_client,
    now: datetime | None = None,
) -> dict[str, Any]:
    validate_config(config)
    created_at = now or utc_now()
    run_id = config.producer_run_id or default_run_id(created_at)

    verified_dir = config.out_dir / "verified"
    raw_dir = config.out_dir / "raw"
    verified_dir.mkdir(parents=True)
    raw_dir.mkdir()

    results: list[ProbeResult] = []
    for probe in PROBES:
        result = execute_probe(config, probe, client=client)
        results.append(result)
        write_json(
            raw_dir / f"{probe.probe_id}.json",
            raw_result_payload(
                config=config,
                run_id=run_id,
                probe=probe,
                result=result,
            ),
        )

    verified_path = verified_dir / "zth-smoke-probe.yaml"
    verified_path.write_text(
        render_verified_yaml(
            config=config,
            run_id=run_id,
            created_at=created_at,
            results=results,
        ),
        encoding="utf-8",
    )
    metadata = run_metadata_payload(
        config=config,
        run_id=run_id,
        created_at=created_at,
        results=results,
    )
    write_json(config.out_dir / "run_metadata.json", metadata)
    return metadata


def plan_payload(config: ProducerConfig) -> dict[str, Any]:
    return {
        "producer": PRODUCER_ID,
        "producer_contract_version": PRODUCER_CONTRACT_VERSION,
        "mode": "plan_only",
        "model_id_requested": config.model,
        "endpoint": "<redacted>",
        "endpoint_path": "/chat/completions",
        "out_dir": str(config.out_dir),
        "timeout_seconds": config.timeout_seconds,
        "max_tokens": config.max_tokens,
        "probe_ids": [probe.probe_id for probe in PROBES],
        "would_write": [
            str(config.out_dir / "verified" / "zth-smoke-probe.yaml"),
            str(config.out_dir / "run_metadata.json"),
            *[
                str(config.out_dir / "raw" / f"{probe.probe_id}.json")
                for probe in PROBES
            ],
        ],
        "network_calls_performed": 0,
        "files_written": 0,
        "safety_notes": [
            "Plan mode does not contact the endpoint or write files.",
            "The producer never starts, stops, or configures endpoints.",
            "Probe output is preflight evidence, not authority.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
    )
    parser.add_argument(
        "--api-key",
        default="not-needed-for-local",
        help="Optional API key. Local sentinel values do not add an auth header.",
    )
    parser.add_argument("--producer-run-id")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a redacted plan without network calls or file writes.",
    )
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="Alias for --dry-run.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ProducerConfig(
        base_url=args.base_url,
        model=args.model,
        out_dir=Path(args.out_dir),
        timeout_seconds=args.timeout_seconds,
        max_tokens=args.max_tokens,
        api_key=args.api_key,
        producer_run_id=args.producer_run_id,
    )
    try:
        validate_config(config)
        if args.dry_run or args.print_plan:
            print(json.dumps(plan_payload(config), indent=2, sort_keys=True))
            return 0
        metadata = produce_smoke_evidence(config)
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Producer: {PRODUCER_ID}")
    print(f"Run ID: {metadata['producer_run_id']}")
    print(f"Probe status counts: {metadata['status_counts']}")
    print(
        "Verified output: "
        f"{config.out_dir / 'verified' / 'zth-smoke-probe.yaml'}"
    )
    print("Endpoint details: redacted")
    print("Boundary: probe output is evidence, not authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
