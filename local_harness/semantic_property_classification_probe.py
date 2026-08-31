#!/usr/bin/env python3
"""Candidate-side per-property semantic classification probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.validate_semantic_property_classification_output import validate as validate_classification_output


SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "semantic_property_classification_output_schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

ALLOWED_PROPERTIES = [
    "transport_qualification",
    "bounded_handoff_success",
    "semantic_capability",
    "raw_response_integrity",
    "semantic_acceptance",
]
ALLOWED_STATUSES = ["established", "not_established", "not_asserted"]


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
                "name": "zth_property_classification_output",
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
        return json.loads(response.read().decode("utf-8")), request_body


def _extract_content(response: dict[str, Any]) -> str:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("response missing assistant content")
    return content


def _build_prompt(*, candidate_text: str, property_name: str, evidence_id: str) -> str:
    return (
        "# ZTH Per-Property Semantic Classification\n\n"
        "## Role\n"
        "Classify what the candidate text says about exactly one queried property.\n\n"
        "## Instructions\n"
        "Use assertion_status=established if the candidate says the queried property is established.\n"
        "Use assertion_status=not_established if the candidate explicitly says the queried property is not established.\n"
        "Use assertion_status=not_asserted if the candidate does not make either assertion about the queried property.\n"
        "Do not infer correctness.\n"
        "Do not explain your answer.\n"
        "Return JSON only.\n\n"
        "## Queried Property\n"
        f"{property_name}\n\n"
        "## Allowed Statuses\n"
        + "\n".join(f"- {item}" for item in ALLOWED_STATUSES)
        + "\n\n"
        "## Evidence Reference\n"
        f"Evidence ID: {evidence_id}\n\n"
        "## Candidate Output\n"
        f"```json\n{candidate_text}\n```\n"
    )


@dataclass(frozen=True)
class ClassificationCase:
    case_id: str
    candidate_path: Path
    property_name: str
    gold_status: str
    evidence_id: str


def run_case(
    *,
    case: ClassificationCase,
    endpoint: str,
    model: str,
    out_dir: Path,
    max_tokens: int,
    temperature: float,
    timeout_seconds: int,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=False)
    candidate_text = _read_text(case.candidate_path)
    prompt_text = _build_prompt(candidate_text=candidate_text, property_name=case.property_name, evidence_id=case.evidence_id)
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
            raise ValueError("classification output must be a JSON object")
        validation_problems = validate_classification_output(parsed_output, expected_property=case.property_name)
    except json.JSONDecodeError as exc:
        parsed_output = None
        validation_problems = [f"JSON parse failed: {exc.msg} at line {exc.lineno}, column {exc.colno}"]
    except ValueError as exc:
        parsed_output = None
        validation_problems = [str(exc)]

    choice = (response.get("choices") or [{}])[0]
    telemetry: dict[str, Any] = {}
    if isinstance(choice, dict) and choice.get("finish_reason") is not None:
        telemetry["finish_reason"] = choice.get("finish_reason")
    usage = response.get("usage")
    if isinstance(usage, dict):
        usage_payload = {field: usage.get(field) for field in ("prompt_tokens", "completion_tokens", "total_tokens") if usage.get(field) is not None}
        if usage_payload:
            telemetry["usage"] = usage_payload

    validation_status = "passed" if not validation_problems else "failed"
    semantic_score_status = "scored" if validation_status == "passed" else "not_scored"
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
        "candidate_sha256": _sha256_file(case.candidate_path),
        "property_name": case.property_name,
        "gold_status": case.gold_status,
        "evidence_id": case.evidence_id,
        "prompt_sha256": _sha256_text(prompt_text),
        "request_body_sha256": _sha256_text(json.dumps(request_body, sort_keys=True)),
        "raw_output_sha256": _sha256_text(raw_output),
        "response_body_sha256": _sha256_text(json.dumps(response, sort_keys=True)),
        "endpoint_response": response,
        "endpoint_telemetry": telemetry,
        "request_body": request_body,
        "parsed_output": parsed_output,
    }
    validation = {
        "case_id": case.case_id,
        "parse_status": "passed" if parsed_output is not None else "failed",
        "schema_status": "passed" if not validation_problems else "failed",
        "overall_validation_status": validation_status,
        "semantic_score_status": semantic_score_status,
        "semantic_score_reason": "semantic_comparison_completed" if validation_status == "passed" else "mechanical_output_failure",
        "diagnostics": validation_problems,
        "schema_source_path": str(SCHEMA_PATH),
        "schema_sha256": _sha256_file(SCHEMA_PATH),
    }
    (out_dir / "candidate.txt").write_text(candidate_text, encoding="utf-8")
    (out_dir / "prompt.txt").write_text(prompt_text, encoding="utf-8")
    (out_dir / "raw_output.txt").write_text(raw_output, encoding="utf-8")
    (out_dir / "model_call.json").write_text(json.dumps(model_call, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "validation.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "case_id": case.case_id,
        "prompt_sha256": model_call["prompt_sha256"],
        "request_body_sha256": model_call["request_body_sha256"],
        "raw_output_sha256": model_call["raw_output_sha256"],
        "validation": validation,
    }


def compile_classification_to_typed_assertions(
    *,
    property_name: str,
    assertion_status: str,
    evidence_id: str,
) -> list[dict[str, Any]]:
    if assertion_status == "not_asserted":
        return []
    if assertion_status not in {"established", "not_established"}:
        raise ValueError("unsupported assertion_status")
    return [
        {
            "property": property_name,
            "epistemic_status": assertion_status,
            "evidence_refs": [evidence_id],
        }
    ]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    cases = load_default_cases()
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


def load_default_cases() -> list[ClassificationCase]:
    root = Path(__file__).resolve().parents[1]
    corpus = root / "docs" / "reports" / "semantic_property_classification_20260831"
    return [
        ClassificationCase(
            case_id="p1_semantic_capability_established",
            candidate_path=corpus / "candidates/p1.txt",
            property_name="semantic_capability",
            gold_status="established",
            evidence_id="case_p1_evidence",
        ),
        ClassificationCase(
            case_id="p2_transport_not_asserted",
            candidate_path=corpus / "candidates/p1.txt",
            property_name="transport_qualification",
            gold_status="not_asserted",
            evidence_id="case_p2_evidence",
        ),
        ClassificationCase(
            case_id="p3_semantic_capability_not_established",
            candidate_path=corpus / "candidates/p3.txt",
            property_name="semantic_capability",
            gold_status="not_established",
            evidence_id="case_p3_evidence",
        ),
        ClassificationCase(
            case_id="p4_transport_established",
            candidate_path=corpus / "candidates/p4.txt",
            property_name="transport_qualification",
            gold_status="established",
            evidence_id="case_p4_evidence",
        ),
        ClassificationCase(
            case_id="p5_semantic_capability_not_asserted",
            candidate_path=corpus / "candidates/p4.txt",
            property_name="semantic_capability",
            gold_status="not_asserted",
            evidence_id="case_p5_evidence",
        ),
        ClassificationCase(
            case_id="p6_transport_established",
            candidate_path=corpus / "candidates/p6.txt",
            property_name="transport_qualification",
            gold_status="established",
            evidence_id="case_p6_transport_evidence",
        ),
        ClassificationCase(
            case_id="p6_semantic_not_established",
            candidate_path=corpus / "candidates/p6.txt",
            property_name="semantic_capability",
            gold_status="not_established",
            evidence_id="case_p6_semantic_evidence",
        ),
        ClassificationCase(
            case_id="a1_semantic_capability_established",
            candidate_path=root / ".work/semantic_claim_discipline_final_20260831/task_a/baseline/20260831T133000Z/raw_model_output.txt",
            property_name="semantic_capability",
            gold_status="established",
            evidence_id="case_a1_evidence",
        ),
        ClassificationCase(
            case_id="a2_semantic_capability_established",
            candidate_path=root / ".work/epistemic_schema_experiment_20260831_abs_fresh/20260831T040000Z/raw_model_output.txt",
            property_name="semantic_capability",
            gold_status="established",
            evidence_id="case_a2_evidence",
        ),
        ClassificationCase(
            case_id="a3_raw_response_integrity_established",
            candidate_path=root / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/raw_model_output.txt",
            property_name="raw_response_integrity",
            gold_status="established",
            evidence_id="case_a3_evidence",
        ),
        ClassificationCase(
            case_id="a3_semantic_acceptance_not_established",
            candidate_path=root / ".work/semantic_claim_discipline_final_20260831/task_b/baseline/20260831T133000Z/raw_model_output.txt",
            property_name="semantic_acceptance",
            gold_status="not_established",
            evidence_id="case_a3_evidence",
        ),
    ]


if __name__ == "__main__":
    raise SystemExit(main())
