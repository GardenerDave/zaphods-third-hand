from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.render_prompt_patch_ab_review_bundle import (
    render_prompt_patch_ab_review_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "render_prompt_patch_ab_review_bundle.py"
FIXTURE = ROOT / "local_harness" / "fixtures" / "prompt_patch_ab" / "known_failure_modes_v1.json"


def test_valid_fixture_writes_bundle(tmp_path: Path) -> None:
    out = tmp_path / "bundle.json"
    bundle = render_prompt_patch_ab_review_bundle(cases_path=FIXTURE)
    out.write_text(json.dumps(bundle, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["bundle_schema"] == "prompt_patch_ab_review_bundle_v1"
    assert payload["review_status"] == "not_reviewed"
    assert payload["prompt_patch_promotion_status"] == "not_promoted"
    assert payload["downstream_use_status"] == "prohibited_until_review"
    assert payload["harness_result"]["cases_total"] == 5
    assert payload["harness_result"]["improved_total"] == 5


def test_bundle_includes_case_file_hash() -> None:
    bundle = render_prompt_patch_ab_review_bundle(cases_path=FIXTURE)
    expected = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert bundle["cases_sha256"] == expected


def test_review_status_is_always_not_reviewed() -> None:
    bundle = render_prompt_patch_ab_review_bundle(cases_path=FIXTURE)
    assert bundle["review_status"] == "not_reviewed"


def test_promotion_status_is_always_not_promoted() -> None:
    bundle = render_prompt_patch_ab_review_bundle(cases_path=FIXTURE)
    assert bundle["prompt_patch_promotion_status"] == "not_promoted"


def test_downstream_use_status_is_prohibited_until_review() -> None:
    bundle = render_prompt_patch_ab_review_bundle(cases_path=FIXTURE)
    assert bundle["downstream_use_status"] == "prohibited_until_review"


def test_cli_exits_nonzero_on_regression(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            {
                "harness_schema": "prompt_patch_ab_cases_v1",
                "cases": [
                    {
                        "case_id": "regress_001",
                        "failure_mode": "scope_boundary",
                        "prompt_patch_id": "scope_boundary_v1",
                        "task_summary": "Regression fixture.",
                        "expected_contract": {
                            "required_allowed_targets": ["docs/"],
                            "required_held_targets": ["training/"],
                            "required_json_fields": ["allowed_targets", "held_targets", "reason"],
                            "forbidden_completion_claim": True,
                            "requires_scope_expansion_flag": False,
                        },
                        "baseline_output": {
                            "allowed_targets": ["docs/"],
                            "held_targets": ["training/"],
                            "scope_expansion_required": False,
                            "reason": "bounded",
                        },
                        "patched_output": {
                            "allowed_targets": ["docs/", "training/"],
                            "held_targets": [],
                            "scope_expansion_required": False,
                            "reason": "still working",
                        },
                    }
                ],
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "bundle.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--cases", str(cases), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["harness_result"]["regressed_total"] == 1


def test_malformed_case_file_writes_failure_shaped_bundle(tmp_path: Path) -> None:
    cases = tmp_path / "bad.json"
    cases.write_text("{not json}\n", encoding="utf-8")
    out = tmp_path / "bundle.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--cases", str(cases), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["review_status"] == "not_reviewed"
    assert payload["diagnostics"]
    assert payload["harness_result"]["diagnostics"]
