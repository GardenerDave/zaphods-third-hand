#!/usr/bin/env python3
"""Deterministic review guardrails for prompt patch A/B fixture candidate drafts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.run_prompt_patch_ab_harness import (  # noqa: E402
    PromptPatchABHarnessError,
    run_prompt_patch_ab_harness,
)


REVIEW_SCHEMA = "prompt_patch_ab_fixture_candidate_review_v1"
EXPECTED_CANDIDATE_SCHEMA = "prompt_patch_ab_fixture_candidate_v1"


class PromptPatchABFixtureCandidateReviewError(ValueError):
    """Raised when a fixture candidate cannot be reviewed safely."""


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromptPatchABFixtureCandidateReviewError(f"missing {kind}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PromptPatchABFixtureCandidateReviewError(f"invalid JSON in {kind}: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise PromptPatchABFixtureCandidateReviewError(f"{kind} must be a JSON object: {path}")
    return payload


def _require_str(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PromptPatchABFixtureCandidateReviewError(f"{context} must be a non-empty string")
    return value


def _require_status(value: Any, *, context: str, expected: str) -> None:
    if value != expected:
        raise PromptPatchABFixtureCandidateReviewError(f"{context} must be {expected!r}")


def _validate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    _require_status(candidate.get("candidate_schema"), context="candidate_schema", expected=EXPECTED_CANDIDATE_SCHEMA)
    _require_status(candidate.get("review_status"), context="review_status", expected="not_reviewed")
    _require_status(candidate.get("import_status"), context="import_status", expected="not_imported")
    _require_status(candidate.get("promotion_status"), context="promotion_status", expected="not_promoted")
    _require_status(
        candidate.get("downstream_use_status"),
        context="downstream_use_status",
        expected="prohibited_until_review",
    )

    source = candidate.get("source")
    if not isinstance(source, dict):
        raise PromptPatchABFixtureCandidateReviewError("source must be a JSON object")
    _require_str(source.get("run_dir"), context="source.run_dir")
    _require_str(source.get("live_record_sha256"), context="source.live_record_sha256")
    _require_str(source.get("generated_cases_sha256"), context="source.generated_cases_sha256")

    candidate_case = candidate.get("candidate_case")
    if not isinstance(candidate_case, dict):
        raise PromptPatchABFixtureCandidateReviewError("candidate_case must be a JSON object")
    required_case_fields = [
        "case_id",
        "failure_mode",
        "prompt_patch_id",
        "task_summary",
        "expected_contract",
        "baseline_output",
        "patched_output",
    ]
    missing = [key for key in required_case_fields if key not in candidate_case]
    if missing:
        raise PromptPatchABFixtureCandidateReviewError(
            "candidate_case missing required fields: " + ", ".join(missing)
        )
    for key in ("case_id", "failure_mode", "prompt_patch_id", "task_summary"):
        _require_str(candidate_case.get(key), context=f"candidate_case.{key}")
    for key in ("expected_contract", "baseline_output", "patched_output"):
        if not isinstance(candidate_case.get(key), dict):
            raise PromptPatchABFixtureCandidateReviewError(f"candidate_case.{key} must be a JSON object")

    return candidate_case


def review_prompt_patch_ab_fixture_candidate(*, candidate_path: Path, out: Path) -> dict[str, Any]:
    candidate = _load_json(candidate_path, kind="candidate")
    candidate_case = _validate_candidate(candidate)

    temp_dir = Path(tempfile.mkdtemp(prefix="prompt_patch_ab_candidate_review_"))
    try:
        cases_path = temp_dir / "cases.json"
        cases_payload = {"harness_schema": "prompt_patch_ab_cases_v1", "cases": [candidate_case]}
        cases_path.write_text(json.dumps(cases_payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        try:
            harness_result = run_prompt_patch_ab_harness(cases_path)
        except PromptPatchABHarnessError as exc:
            raise PromptPatchABFixtureCandidateReviewError(f"candidate harness validation failed: {exc}") from exc

        result = harness_result["results"][0] if harness_result.get("results") else {}
        harness_result_name = result.get("result")
        reviewable = harness_result["cases_total"] == 1 and harness_result["regressed_total"] == 0 and harness_result_name in {
            "improved",
            "unchanged_pass",
        }
        if harness_result_name == "unchanged_fail":
            reviewable = False
        if harness_result["regressed_total"] > 0:
            raise PromptPatchABFixtureCandidateReviewError("candidate harness result contains regression")

        checklist = [
            {"item": "candidate schema valid", "status": "passed"},
            {"item": "candidate statuses held", "status": "passed"},
            {"item": "candidate case structurally complete", "status": "passed"},
            {
                "item": "harness result reviewed",
                "status": "passed" if harness_result_name in {"improved", "unchanged_pass", "unchanged_fail"} else "failed",
            },
            {
                "item": "candidate reviewable",
                "status": "passed" if reviewable else "failed",
            },
        ]

        report = {
            "candidate_review_schema": REVIEW_SCHEMA,
            "candidate_path": str(candidate_path),
            "candidate_sha256": _sha256_bytes(candidate_path),
            "review_status": "review_required",
            "import_status": "not_imported",
            "promotion_status": "not_promoted",
            "downstream_use_status": "prohibited_until_review",
            "reviewable": reviewable,
            "harness_result": harness_result,
            "review_checklist": checklist,
            "manual_next_steps": [
                "Review candidate_case semantics.",
                "If accepted, manually copy candidate_case into the tracked fixture pack.",
                "Run the deterministic harness and review-bundle checks.",
                "Commit only tracked fixture/test/doc changes.",
            ],
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = review_prompt_patch_ab_fixture_candidate(candidate_path=args.candidate, out=args.out)
    except (PromptPatchABFixtureCandidateReviewError, PromptPatchABHarnessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = {
        "candidate_review_status": "written",
        "out": str(args.out),
        "reviewable": report["reviewable"],
        "case_id": report["harness_result"]["results"][0]["case_id"] if report["harness_result"]["results"] else "",
        "harness_result": report["harness_result"]["results"][0]["result"] if report["harness_result"]["results"] else "",
    }
    json.dump(summary, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0 if report["reviewable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
