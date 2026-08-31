#!/usr/bin/env python3
"""Advisory semantic review probe over frozen candidate outputs."""

from __future__ import annotations

import argparse
import json
import hashlib
import sys
import urllib.request
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.validate_semantic_review_output import validate as validate_semantic_review_output


REVIEW_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "review_semantic_escalation_output_schema.json"
REVIEW_SCHEMA = json.loads(REVIEW_SCHEMA_PATH.read_text(encoding="utf-8"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _call_local(endpoint: str, model: str, prompt: str, max_tokens: int, temperature: float, timeout_seconds: int) -> dict[str, Any]:
    url = endpoint.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    request_body = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "zth_semantic_review_output",
                "strict": True,
                "schema": REVIEW_SCHEMA,
            },
        },
    }
    request = urllib.request.Request(url, data=json.dumps(request_body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_content(response: dict[str, Any]) -> str:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("response missing assistant content")
    return content


def _build_prompt(*, evidence_text: str, candidate_text: str) -> str:
    return (
        "# ZTH Advisory Semantic Review Packet\n\n"
        "## Role\n"
        "You are a bounded reviewer evaluating whether a candidate output stays within the evidence boundary.\n\n"
        "## Instructions\n"
        "Judge only the candidate's claims against the supplied evidence.\n"
        "Do not rewrite the candidate.\n"
        "Do not generate replacement findings.\n"
        "Return JSON only.\n\n"
        "## Evidence\n"
        f"```text\n{evidence_text}\n```\n\n"
        "## Candidate Output\n"
        f"```json\n{candidate_text}\n```\n\n"
        "## Output Contract\n"
        "Return JSON with keys verdict, unsupported_claims, internal_consistency, review_reason.\n"
        "verdict must be pass_review or hold.\n"
        "unsupported_claims is an array of objects with claim, reason, and evidence.\n"
        "internal_consistency must be consistent or inconsistent.\n"
        "review_reason must be non-empty.\n"
    )


def _load_projected_paths(evidence_path: Path) -> set[str]:
    if evidence_path.suffix != ".md":
        return {str(evidence_path)}
    candidate = evidence_path.with_suffix(".json")
    if not candidate.is_file():
        return {str(evidence_path)}
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    sources = payload.get("evidence_sources")
    projected: set[str] = set()
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, dict):
                path = source.get("path")
                if isinstance(path, str) and path.strip():
                    projected.add(path)
    return projected or {str(evidence_path)}


def run_probe(
    *,
    candidate_path: Path,
    evidence_path: Path,
    out_dir: Path,
    endpoint: str,
    model: str,
    max_tokens: int = 512,
    temperature: float = 0.0,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=False)
    candidate_text = _read_text(candidate_path)
    evidence_text = _read_text(evidence_path)
    projected_paths = _load_projected_paths(evidence_path)
    prompt_text = _build_prompt(evidence_text=evidence_text, candidate_text=candidate_text)
    response = _call_local(endpoint, model, prompt_text, max_tokens, temperature, timeout_seconds)
    raw_output = _extract_content(response)
    validation_problems: list[str]
    try:
        parsed_output = json.loads(raw_output)
        if not isinstance(parsed_output, dict):
            raise ValueError("review output must be a JSON object")
        validation_problems = validate_semantic_review_output(parsed_output, projected_paths)
    except json.JSONDecodeError as exc:
        parsed_output = None
        validation_problems = [f"JSON parse failed: {exc.msg} at line {exc.lineno}, column {exc.colno}"]
    except ValueError as exc:
        parsed_output = None
        validation_problems = [str(exc)]
    (out_dir / "review_prompt.md").write_text(prompt_text, encoding="utf-8")
    (out_dir / "review_candidate.txt").write_text(candidate_text, encoding="utf-8")
    (out_dir / "review_evidence.txt").write_text(evidence_text, encoding="utf-8")
    (out_dir / "review_raw_output.txt").write_text(raw_output, encoding="utf-8")
    request_body = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt_text}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "zth_semantic_review_output",
                "strict": True,
                "schema": REVIEW_SCHEMA,
            },
        },
    }
    endpoint_response = response
    response_body_sha256 = hashlib.sha256(json.dumps(endpoint_response, sort_keys=True).encode("utf-8")).hexdigest()
    endpoint_telemetry = {}
    choice = (endpoint_response.get("choices") or [{}])[0]
    if isinstance(choice, dict) and choice.get("finish_reason") is not None:
        endpoint_telemetry["finish_reason"] = choice.get("finish_reason")
    usage = endpoint_response.get("usage")
    if isinstance(usage, dict):
        usage_payload = {
            field: usage.get(field)
            for field in ("prompt_tokens", "completion_tokens", "total_tokens")
            if usage.get(field) is not None
        }
        if usage_payload:
            endpoint_telemetry["usage"] = usage_payload
    review_model_call = {
        "endpoint": endpoint,
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "schema_source_path": str(REVIEW_SCHEMA_PATH),
        "schema_sha256": _sha256_file(REVIEW_SCHEMA_PATH),
        "schema_artifact": REVIEW_SCHEMA,
        "prompt_sha256": _sha256_text(prompt_text),
        "request_body_sha256": _sha256_text(json.dumps(request_body, sort_keys=True)),
        "raw_output_sha256": _sha256_text(raw_output),
        "response_body_sha256": response_body_sha256,
        "endpoint_response": endpoint_response,
        "endpoint_telemetry": endpoint_telemetry,
        "projected_evidence_paths": sorted(projected_paths),
    }
    (out_dir / "review_model_call.json").write_text(json.dumps(review_model_call, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review_validation = {
        "parse_status": "passed" if parsed_output is not None else "failed",
        "schema_status": "passed" if not validation_problems else "failed",
        "grounding_status": "passed" if not any("not projected" in item for item in validation_problems) else "failed",
        "diagnostics": validation_problems,
        "overall_validation_status": "passed" if not validation_problems else "failed",
        "projected_evidence_paths": sorted(projected_paths),
        "schema_source_path": str(REVIEW_SCHEMA_PATH),
        "schema_sha256": _sha256_file(REVIEW_SCHEMA_PATH),
    }
    (out_dir / "review_validation.json").write_text(json.dumps(review_validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "prompt_sha256": _sha256_text(prompt_text),
        "raw_output": raw_output,
        "response": response,
        "run_dir": out_dir,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run_probe(
            candidate_path=args.candidate,
            evidence_path=args.evidence,
            out_dir=args.out_dir,
            endpoint=args.endpoint,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            timeout_seconds=args.timeout_seconds,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"run_dir: {result['run_dir']}")
    print(f"prompt_sha256: {result['prompt_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
