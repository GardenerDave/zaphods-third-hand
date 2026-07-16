#!/usr/bin/env python3
"""Explicit-operator live prompt patch A/B evidence producer."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


SCHEMA_NAME = "prompt_patch_ab_cases_v1"
LIVE_RECORD_SCHEMA = "prompt_patch_ab_live_record_v1"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TIMEOUT_SECONDS = 30


class PromptPatchABLiveError(ValueError):
    """Raised when live A/B evidence cannot be produced safely."""


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise PromptPatchABLiveError(f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def _load_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromptPatchABLiveError(f"missing {kind}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PromptPatchABLiveError(f"invalid JSON in {kind}: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise PromptPatchABLiveError(f"{kind} must be a JSON object: {path}")
    return payload


def _load_expected_contract(path: Path) -> dict[str, Any]:
    payload = _load_json(path, kind="expected contract")
    return payload


def _request_payload(*, prompt_text: str, model: str, temperature: float, max_tokens: int) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def _call_live_endpoint(
    *,
    base_url: str,
    model: str,
    prompt_path: Path,
    temperature: float,
    max_tokens: int,
    timeout_seconds: float,
) -> tuple[dict[str, Any], str]:
    prompt_text = _read_text(prompt_path)
    request_payload = _request_payload(
        prompt_text=prompt_text,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_text = response.read().decode("utf-8")
    except (socket.timeout, TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise PromptPatchABLiveError(
            f"live endpoint call failed for {prompt_path.name}: {exc.__class__.__name__}"
        ) from exc

    try:
        response_payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise PromptPatchABLiveError(
            f"live endpoint response is not valid JSON for {prompt_path.name}: {exc.msg}"
        ) from exc
    if not isinstance(response_payload, dict):
        raise PromptPatchABLiveError(f"live endpoint response must be a JSON object for {prompt_path.name}")
    return response_payload, response_text


def _extract_assistant_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise PromptPatchABLiveError("live endpoint response missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise PromptPatchABLiveError("live endpoint response choices[0] must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise PromptPatchABLiveError("live endpoint response choices[0].message must be an object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise PromptPatchABLiveError("live endpoint response missing assistant content")
    return content


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _parse_response_content(response_payload: dict[str, Any], *, prompt_label: str) -> dict[str, Any]:
    content = _extract_assistant_content(response_payload)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise PromptPatchABLiveError(
            f"assistant content for {prompt_label} is not valid JSON: {exc.msg}"
        ) from exc
    if not isinstance(parsed, dict):
        raise PromptPatchABLiveError(f"assistant content for {prompt_label} must be a JSON object")
    return parsed


def _build_case(
    *,
    case_id: str,
    failure_mode: str,
    prompt_patch_id: str,
    task_summary: str,
    expected_contract: dict[str, Any],
    baseline_output: dict[str, Any],
    patched_output: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "failure_mode": failure_mode,
        "prompt_patch_id": prompt_patch_id,
        "task_summary": task_summary,
        "expected_contract": expected_contract,
        "baseline_output": baseline_output,
        "patched_output": patched_output,
    }


def run_prompt_patch_ab_live(
    *,
    case_id: str,
    failure_mode: str,
    prompt_patch_id: str,
    task_summary: str,
    expected_contract_path: Path,
    baseline_prompt_path: Path,
    patched_prompt_path: Path,
    base_url: str,
    model: str,
    out_dir: Path,
    temperature: float = 0.0,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    expected_contract = _load_expected_contract(expected_contract_path)
    baseline_prompt_text = _read_text(baseline_prompt_path)
    patched_prompt_text = _read_text(patched_prompt_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    baseline_prompt_out = out_dir / "baseline_prompt.txt"
    patched_prompt_out = out_dir / "patched_prompt.txt"
    expected_contract_out = out_dir / "expected_contract.json"
    baseline_response_raw = out_dir / "baseline_response.raw.json"
    patched_response_raw = out_dir / "patched_response.raw.json"
    live_record_path = out_dir / "prompt_patch_ab_live_record.json"
    cases_path = out_dir / "prompt_patch_ab_cases.json"

    baseline_prompt_out.write_text(baseline_prompt_text, encoding="utf-8")
    patched_prompt_out.write_text(patched_prompt_text, encoding="utf-8")
    _write_json(expected_contract_out, expected_contract)

    live_record: dict[str, Any] = {
        "record_schema": LIVE_RECORD_SCHEMA,
        "review_required": True,
        "execution_mode": "explicit_operator_invoked",
        "case_id": case_id,
        "failure_mode": failure_mode,
        "prompt_patch_id": prompt_patch_id,
        "task_summary": task_summary,
        "model": model,
        "base_url_present": bool(base_url.strip()),
        "runtime_settings": {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout_seconds": timeout_seconds,
        },
        "baseline_prompt_sha256": _sha256_bytes(baseline_prompt_out),
        "patched_prompt_sha256": _sha256_bytes(patched_prompt_out),
        "baseline_response_sha256": "",
        "patched_response_sha256": "",
        "generated_cases_path": str(cases_path),
        "diagnostics": [],
        "authority_boundary": [
            "evidence_only",
            "explicit_operator_invoked",
            "no_cron_watchdog_integration",
            "no_auto_promotion",
            "no_training_capture",
            "no_merge_authority",
            "no_deployment_authority",
            "no_downstream_use_authority",
        ],
    }

    baseline_response_payload: dict[str, Any] | None = None
    patched_response_payload: dict[str, Any] | None = None
    baseline_content: dict[str, Any] | None = None
    patched_content: dict[str, Any] | None = None

    try:
        baseline_response_payload, baseline_response_text = _call_live_endpoint(
            base_url=base_url,
            model=model,
            prompt_path=baseline_prompt_path,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        baseline_response_raw.write_text(baseline_response_text, encoding="utf-8")
        live_record["baseline_response_sha256"] = _sha256_bytes(baseline_response_raw)
        baseline_content = _parse_response_content(baseline_response_payload, prompt_label="baseline")
    except Exception as exc:
        live_record["diagnostics"].append(str(exc))

    try:
        patched_response_payload, patched_response_text = _call_live_endpoint(
            base_url=base_url,
            model=model,
            prompt_path=patched_prompt_path,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
        patched_response_raw.write_text(patched_response_text, encoding="utf-8")
        live_record["patched_response_sha256"] = _sha256_bytes(patched_response_raw)
        patched_content = _parse_response_content(patched_response_payload, prompt_label="patched")
    except Exception as exc:
        live_record["diagnostics"].append(str(exc))

    if baseline_content is not None and patched_content is not None:
        case = _build_case(
            case_id=case_id,
            failure_mode=failure_mode,
            prompt_patch_id=prompt_patch_id,
            task_summary=task_summary,
            expected_contract=expected_contract,
            baseline_output=baseline_content,
            patched_output=patched_content,
        )
        cases_payload = {"harness_schema": SCHEMA_NAME, "cases": [case]}
        _write_json(cases_path, cases_payload)
        live_record["generated_cases_path"] = str(cases_path)
    else:
        live_record["diagnostics"].append("harness-compatible case file not written because one or more responses were invalid")

    _write_json(live_record_path, live_record)
    return live_record


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--failure-mode", required=True)
    parser.add_argument("--prompt-patch-id", required=True)
    parser.add_argument("--task-summary", required=True)
    parser.add_argument("--expected-contract", required=True, type=Path)
    parser.add_argument("--baseline-prompt", required=True, type=Path)
    parser.add_argument("--patched-prompt", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        live_record = run_prompt_patch_ab_live(
            case_id=args.case_id,
            failure_mode=args.failure_mode,
            prompt_patch_id=args.prompt_patch_id,
            task_summary=args.task_summary,
            expected_contract_path=args.expected_contract,
            baseline_prompt_path=args.baseline_prompt,
            patched_prompt_path=args.patched_prompt,
            base_url=args.base_url,
            model=args.model,
            out_dir=args.out_dir,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout_seconds,
        )
    except PromptPatchABLiveError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    json.dump(live_record, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0 if not live_record["diagnostics"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
