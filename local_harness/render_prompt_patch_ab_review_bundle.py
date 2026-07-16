#!/usr/bin/env python3
"""Model-free review bundle renderer for prompt patch A/B fixture results."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.run_prompt_patch_ab_harness import (
    PromptPatchABHarnessError,
    run_prompt_patch_ab_harness,
)


BUNDLE_SCHEMA = "prompt_patch_ab_review_bundle_v1"


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_prompt_patch_ab_review_bundle(*, cases_path: Path) -> dict[str, Any]:
    harness_result = run_prompt_patch_ab_harness(cases_path)
    payload = {
        "bundle_schema": BUNDLE_SCHEMA,
        "cases_path": str(cases_path),
        "cases_sha256": _sha256_bytes(cases_path),
        "harness_result": harness_result,
        "review_status": "not_reviewed",
        "prompt_patch_promotion_status": "not_promoted",
        "downstream_use_status": "prohibited_until_review",
        "authority_boundary": [
            "fixture_based_only",
            "no_live_model_execution",
            "no_auto_promotion",
            "no_training_capture",
            "no_merge_authority",
            "no_deployment_authority",
            "no_downstream_use_authority",
        ],
        "diagnostics": list(harness_result.get("diagnostics", [])),
    }
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        bundle = render_prompt_patch_ab_review_bundle(cases_path=args.cases)
    except PromptPatchABHarnessError as exc:
        bundle = {
            "bundle_schema": BUNDLE_SCHEMA,
            "cases_path": str(args.cases),
            "cases_sha256": "",
            "harness_result": {
                "harness_schema": "prompt_patch_ab_result_v1",
                "cases_total": 0,
                "improved_total": 0,
                "unchanged_pass_total": 0,
                "unchanged_fail_total": 0,
                "regressed_total": 0,
                "results": [],
                "diagnostics": [str(exc)],
            },
            "review_status": "not_reviewed",
            "prompt_patch_promotion_status": "not_promoted",
            "downstream_use_status": "prohibited_until_review",
            "authority_boundary": [
                "fixture_based_only",
                "no_live_model_execution",
                "no_auto_promotion",
                "no_training_capture",
                "no_merge_authority",
                "no_deployment_authority",
                "no_downstream_use_authority",
            ],
            "diagnostics": [str(exc)],
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(bundle, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        json.dump(bundle, sys.stdout, sort_keys=True, indent=2)
        sys.stdout.write("\n")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    json.dump(bundle, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0 if bundle["harness_result"]["regressed_total"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
