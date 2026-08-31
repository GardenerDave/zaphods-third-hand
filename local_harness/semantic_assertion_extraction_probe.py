#!/usr/bin/env python3
"""Candidate-side semantic assertion extraction probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.validate_semantic_assertion_extraction_output import validate as validate_extraction_output


SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "semantic_assertion_extraction_output_schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _call_local(
    *,
    endpoint: str,
    model: str,
    prompt_text: str,
    max_tokens: int,
    temperature: float,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    url = endpoint.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    request_body = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt_text}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "zth_candidate_assertion_extraction_output",
                "strict": True,
                "schema": SCHEMA,
            },
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = json.loads(response.read().decode("utf-8"))
        return body, request_body


def _extract_content(response: dict[str, Any]) -> str:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("response missing assistant content")
    return content


CONTROLLED_PROPERTIES = [
    "transport_qualification",
    "bounded_handoff_success",
    "semantic_capability",
    "raw_response_integrity",
    "semantic_acceptance",
]
CONTROLLED_EPISTEMIC_STATUSES = ["established", "not_established"]


def _build_prompt(*, candidate_text: str, evidence_id: str) -> str:
    return (
        "# ZTH Candidate Assertion Extraction\n\n"
        "## Role\n"
        "Extract what the candidate text asserts. Do not judge whether it is correct.\n\n"
        "## Instructions\n"
        "Map each relevant assertion onto the supplied controlled vocabulary.\n"
        "Return each distinct property + epistemic-status proposition expressed by the candidate at most once.\n"
        "Use established when the candidate asserts the property is established.\n"
        "Use not_established when the candidate explicitly says the property is not established by the evidence/context.\n"
        "Do not infer correctness.\n"
        "Do not repair the candidate.\n"
        "Do not apply policy.\n"
        "Return JSON only.\n\n"
        "## Controlled Vocabulary\n"
        "Properties:\n"
        + "\n".join(f"- {item}" for item in CONTROLLED_PROPERTIES)
        + "\n\n"
        "Epistemic status:\n"
        + "\n".join(f"- {item}" for item in CONTROLLED_EPISTEMIC_STATUSES)
        + "\n\n"
        "## Evidence Reference\n"
        f"Evidence ID: {evidence_id}\n\n"
        "## Candidate Output\n"
        f"```json\n{candidate_text}\n```\n\n"
        "## Output Contract\n"
        "Return JSON with a single key assertions.\n"
        "Each assertion must contain property, epistemic_status, and evidence_refs.\n"
        "Evidence refs must use the supplied evidence ID exactly once per assertion.\n"
    )


@dataclass(frozen=True)
class ExtractionCase:
    case_id: str
    candidate_path: Path
    evidence_path: Path
    evidence_id: str
    gold_path: Path


def _load_gold(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"gold must be a JSON object: {path}")
    return payload


def _semantic_score_status(validation_status: str) -> str:
    return "scored" if validation_status == "passed" else "not_scored"


def _semantic_score_reason(validation_status: str) -> str:
    return "semantic_comparison_completed" if validation_status == "passed" else "mechanical_output_failure"


def run_case(
    *,
    case: ExtractionCase,
    endpoint: str,
    model: str,
    out_dir: Path,
    max_tokens: int,
    temperature: float,
    timeout_seconds: int,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=False)
    candidate_text = _read_text(case.candidate_path)
    prompt_text = _build_prompt(
        candidate_text=candidate_text,
        evidence_id=case.evidence_id,
    )
    response, request_body = _call_local(
        endpoint=endpoint,
        model=model,
        prompt_text=prompt_text,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
    )
    raw_output = _extract_content(response)
    try:
        parsed_output = json.loads(raw_output)
        if not isinstance(parsed_output, dict):
            raise ValueError("extraction output must be a JSON object")
        validation_problems = validate_extraction_output(parsed_output, expected_evidence_id=case.evidence_id)
    except json.JSONDecodeError as exc:
        parsed_output = None
        validation_problems = [f"JSON parse failed: {exc.msg} at line {exc.lineno}, column {exc.colno}"]
    except ValueError as exc:
        parsed_output = None
        validation_problems = [str(exc)]

    candidate_gold = _load_gold(case.gold_path)
    expected_assertions = candidate_gold.get("assertions", [])
    extracted_assertions = [] if parsed_output is None else parsed_output.get("assertions", [])

    choice = (response.get("choices") or [{}])[0]
    telemetry: dict[str, Any] = {}
    if isinstance(choice, dict) and choice.get("finish_reason") is not None:
        telemetry["finish_reason"] = choice.get("finish_reason")
    usage = response.get("usage")
    if isinstance(usage, dict):
        usage_payload = {key: usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens") if usage.get(key) is not None}
        if usage_payload:
            telemetry["usage"] = usage_payload

    response_body_sha256 = _sha256_text(json.dumps(response, sort_keys=True))
    request_body_sha256 = _sha256_text(json.dumps(request_body, sort_keys=True))
    prompt_sha256 = _sha256_text(prompt_text)
    raw_output_sha256 = _sha256_text(raw_output)
    candidate_sha256 = _sha256_file(case.candidate_path)
    evidence_sha256 = _sha256_file(case.evidence_path)

    model_call = {
        "case_id": case.case_id,
        "endpoint": endpoint,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "schema_source_path": str(SCHEMA_PATH),
        "schema_sha256": _sha256_file(SCHEMA_PATH),
        "schema_artifact": SCHEMA,
        "candidate_path": str(case.candidate_path),
        "candidate_sha256": candidate_sha256,
        "evidence_path": str(case.evidence_path),
        "evidence_sha256": evidence_sha256,
        "evidence_id": case.evidence_id,
        "gold_path": str(case.gold_path),
        "gold_sha256": _sha256_file(case.gold_path),
        "prompt_sha256": prompt_sha256,
        "request_body_sha256": request_body_sha256,
        "raw_output_sha256": raw_output_sha256,
        "response_body_sha256": response_body_sha256,
        "endpoint_response": response,
        "endpoint_telemetry": telemetry,
        "candidate_assertions": extracted_assertions,
        "gold_assertions": expected_assertions,
        "request_body": request_body,
    }
    validation_status = "passed" if not validation_problems else "failed"
    semantic_score_status = _semantic_score_status(validation_status)
    semantic_score_reason = _semantic_score_reason(validation_status)
    validation = {
        "case_id": case.case_id,
        "parse_status": "passed" if parsed_output is not None else "failed",
        "schema_status": "passed" if not validation_problems else "failed",
        "grounding_status": "passed" if not any("evidence_refs" in problem or "must equal expected evidence id" in problem for problem in validation_problems) else "failed",
        "diagnostics": validation_problems,
        "overall_validation_status": validation_status,
        "semantic_score_status": semantic_score_status,
        "semantic_score_reason": semantic_score_reason,
        "schema_source_path": str(SCHEMA_PATH),
        "schema_sha256": _sha256_file(SCHEMA_PATH),
        "expected_evidence_id": case.evidence_id,
    }
    (out_dir / "candidate.txt").write_text(candidate_text, encoding="utf-8")
    (out_dir / "evidence.txt").write_text(_read_text(case.evidence_path), encoding="utf-8")
    (out_dir / "gold.json").write_text(json.dumps(candidate_gold, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "prompt.txt").write_text(prompt_text, encoding="utf-8")
    (out_dir / "raw_output.txt").write_text(raw_output, encoding="utf-8")
    (out_dir / "model_call.json").write_text(json.dumps(model_call, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "validation.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "case_id": case.case_id,
        "prompt_sha256": prompt_sha256,
        "request_body_sha256": request_body_sha256,
        "raw_output_sha256": raw_output_sha256,
        "response_body_sha256": response_body_sha256,
        "validation": validation,
        "model_call": model_call,
    }


def _default_cases() -> list[ExtractionCase]:
    root = Path(__file__).resolve().parents[1]
    gold_root = root / "docs" / "reports" / "semantic_assertion_extraction_20260831" / "gold"
    synthetic_root = root / "docs" / "reports" / "semantic_assertion_extraction_20260831"
    return [
        ExtractionCase(
            case_id="a1_bad_current_contract",
            candidate_path=root / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/raw_model_output.txt",
            evidence_path=root / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/evidence_projection.md",
            evidence_id="case_a1_evidence",
            gold_path=gold_root / "a1.json",
        ),
        ExtractionCase(
            case_id="a2_bad_epistemic_schema",
            candidate_path=root / ".work/epistemic_schema_experiment_20260831_abs_fresh/20260831T040000Z/raw_model_output.txt",
            evidence_path=root / ".work/epistemic_schema_experiment_20260831_abs_fresh/20260831T040000Z/evidence_projection.md",
            evidence_id="case_a2_evidence",
            gold_path=gold_root / "a2.json",
        ),
        ExtractionCase(
            case_id="a3_good_control",
            candidate_path=root / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/raw_model_output.txt",
            evidence_path=root / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/evidence_projection.md",
            evidence_id="case_a3_evidence",
            gold_path=gold_root / "a3.json",
        ),
        ExtractionCase(
            case_id="x1_positive_capability",
            candidate_path=synthetic_root / "candidates/x1.txt",
            evidence_path=synthetic_root / "evidence/x1.txt",
            evidence_id="case_x1_evidence",
            gold_path=gold_root / "x1.json",
        ),
        ExtractionCase(
            case_id="x2_negative_capability",
            candidate_path=synthetic_root / "candidates/x2.txt",
            evidence_path=synthetic_root / "evidence/x2.txt",
            evidence_id="case_x2_evidence",
            gold_path=gold_root / "x2.json",
        ),
        ExtractionCase(
            case_id="x3_positive_transport",
            candidate_path=synthetic_root / "candidates/x3.txt",
            evidence_path=synthetic_root / "evidence/x3.txt",
            evidence_id="case_x3_evidence",
            gold_path=gold_root / "x3.json",
        ),
        ExtractionCase(
            case_id="x4_mixed",
            candidate_path=synthetic_root / "candidates/x4.txt",
            evidence_path=synthetic_root / "evidence/x4.txt",
            evidence_id="case_x4_evidence",
            gold_path=gold_root / "x4.json",
        ),
    ]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--case", action="append", help="Optional case id filter; may be repeated.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    cases = _default_cases()
    if args.case:
        allowed = {item.strip() for item in args.case if item.strip()}
        cases = [case for case in cases if case.case_id in allowed]
    if not cases:
        print("no cases selected", file=sys.stderr)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report: list[dict[str, Any]] = []
    for case in cases:
        case_out = args.out_dir / case.case_id
        if case_out.exists():
            raise ValueError(f"case out-dir already exists: {case_out}")
        result = run_case(
            case=case,
            endpoint=args.endpoint,
            model=args.model,
            out_dir=case_out,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            timeout_seconds=args.timeout_seconds,
        )
        report.append(result)
        print(f"{case.case_id}: {case_out}")
    (args.out_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
