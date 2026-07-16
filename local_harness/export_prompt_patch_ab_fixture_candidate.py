#!/usr/bin/env python3
"""Supervised exporter from live prompt patch A/B evidence to a reviewable fixture candidate draft."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.run_prompt_patch_ab_harness import (  # noqa: E402
    PromptPatchABHarnessError,
    run_prompt_patch_ab_harness,
)


SCHEMA_NAME = "prompt_patch_ab_fixture_candidate_v1"


class PromptPatchABFixtureCandidateError(ValueError):
    """Raised when a fixture candidate cannot be exported safely."""


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromptPatchABFixtureCandidateError(f"missing {kind}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PromptPatchABFixtureCandidateError(f"invalid JSON in {kind}: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise PromptPatchABFixtureCandidateError(f"{kind} must be a JSON object: {path}")
    return payload


def _load_optional_json(path: Path, *, kind: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _load_json(path, kind=kind)


def _build_candidate_case(*, case_id: str, generated_case: dict[str, Any]) -> dict[str, Any]:
    required_keys = [
        "baseline_output",
        "patched_output",
        "expected_contract",
        "failure_mode",
        "prompt_patch_id",
        "task_summary",
    ]
    missing = [key for key in required_keys if key not in generated_case]
    if missing:
        raise PromptPatchABFixtureCandidateError(
            "generated case missing required fields: " + ", ".join(missing)
        )

    candidate_case = {
        "case_id": case_id,
        "failure_mode": generated_case["failure_mode"],
        "prompt_patch_id": generated_case["prompt_patch_id"],
        "task_summary": generated_case["task_summary"],
        "expected_contract": generated_case["expected_contract"],
        "baseline_output": generated_case["baseline_output"],
        "patched_output": generated_case["patched_output"],
    }
    return candidate_case


def export_prompt_patch_ab_fixture_candidate(
    *,
    run_dir: Path,
    case_id: str,
    out: Path,
) -> dict[str, Any]:
    live_record_path = run_dir / "evidence" / "prompt_patch_ab_live_record.json"
    generated_cases_path = run_dir / "evidence" / "prompt_patch_ab_cases.json"
    harness_result_path = run_dir / "harness_result.json"
    review_bundle_path = run_dir / "prompt_patch_ab_review_bundle.json"

    live_record = _load_json(live_record_path, kind="live record")
    if live_record.get("generated_case_status") != "harness_valid":
        raise PromptPatchABFixtureCandidateError(
            "live record generated_case_status must be 'harness_valid'"
        )

    generated_cases = _load_json(generated_cases_path, kind="generated cases")
    if generated_cases.get("harness_schema") != "prompt_patch_ab_cases_v1":
        raise PromptPatchABFixtureCandidateError(
            "generated cases harness_schema must be 'prompt_patch_ab_cases_v1'"
        )
    cases = generated_cases.get("cases")
    if not isinstance(cases, list):
        raise PromptPatchABFixtureCandidateError("generated cases must contain a cases list")
    if len(cases) != 1:
        raise PromptPatchABFixtureCandidateError("generated cases must contain exactly one case")

    generated_case = cases[0]
    if not isinstance(generated_case, dict):
        raise PromptPatchABFixtureCandidateError("generated case must be a JSON object")

    if generated_case.get("case_id") != case_id:
        # Preserve the evidence but require a new tracked candidate identity.
        pass

    harness_result: dict[str, Any] | None = None
    harness_result_sha256: str | None = None
    if harness_result_path.exists():
        harness_result = _load_json(harness_result_path, kind="harness result")
        if harness_result.get("cases_total") != 1:
            raise PromptPatchABFixtureCandidateError("harness result cases_total must be 1")
        harness_result_sha256 = _sha256_bytes(harness_result_path)

    review_bundle: dict[str, Any] | None = None
    review_bundle_sha256: str | None = None
    if review_bundle_path.exists():
        review_bundle = _load_json(review_bundle_path, kind="review bundle")
        if review_bundle.get("downstream_use_status") != "prohibited_until_review":
            raise PromptPatchABFixtureCandidateError(
                "review bundle downstream_use_status must be 'prohibited_until_review'"
            )
        review_bundle_sha256 = _sha256_bytes(review_bundle_path)

    candidate_case = _build_candidate_case(case_id=case_id, generated_case=generated_case)
    candidate = {
        "candidate_schema": SCHEMA_NAME,
        "review_status": "not_reviewed",
        "import_status": "not_imported",
        "promotion_status": "not_promoted",
        "downstream_use_status": "prohibited_until_review",
        "source": {
            "run_dir": str(run_dir),
            "live_record_sha256": _sha256_bytes(live_record_path),
            "generated_cases_sha256": _sha256_bytes(generated_cases_path),
            "harness_result_sha256": harness_result_sha256,
            "review_bundle_sha256": review_bundle_sha256,
        },
        "candidate_case": candidate_case,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(candidate, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    return candidate


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        candidate = export_prompt_patch_ab_fixture_candidate(
            run_dir=args.run_dir,
            case_id=args.case_id,
            out=args.out,
        )
    except (PromptPatchABFixtureCandidateError, PromptPatchABHarnessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = {
        "candidate_status": "written",
        "out": str(args.out),
        "case_id": candidate["candidate_case"]["case_id"],
        "source_run_dir": str(args.run_dir),
        "review_status": candidate["review_status"],
        "import_status": candidate["import_status"],
    }
    json.dump(summary, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
