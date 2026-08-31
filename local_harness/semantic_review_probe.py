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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
    prompt_text = _build_prompt(evidence_text=evidence_text, candidate_text=candidate_text)
    response = _call_local(endpoint, model, prompt_text, max_tokens, temperature, timeout_seconds)
    raw_output = _extract_content(response)
    (out_dir / "review_prompt.md").write_text(prompt_text, encoding="utf-8")
    (out_dir / "review_candidate.txt").write_text(candidate_text, encoding="utf-8")
    (out_dir / "review_evidence.txt").write_text(evidence_text, encoding="utf-8")
    (out_dir / "review_raw_output.txt").write_text(raw_output, encoding="utf-8")
    (out_dir / "review_model_call.json").write_text(json.dumps({
        "endpoint": endpoint,
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "prompt_sha256": _sha256_text(prompt_text),
        "raw_output_sha256": _sha256_text(raw_output),
        "response_body_sha256": hashlib.sha256(json.dumps(response, sort_keys=True).encode("utf-8")).hexdigest(),
        "endpoint_response": response,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
