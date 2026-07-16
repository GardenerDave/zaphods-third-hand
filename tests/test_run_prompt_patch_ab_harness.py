from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.run_prompt_patch_ab_harness import (
    PromptPatchABHarnessError,
    run_prompt_patch_ab_harness,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "run_prompt_patch_ab_harness.py"
FIXTURE = ROOT / "local_harness" / "fixtures" / "prompt_patch_ab" / "scope_boundary_example.json"


def _write_cases(path: Path, cases: list[dict]) -> None:
    path.write_text(
        json.dumps({"harness_schema": "prompt_patch_ab_cases_v1", "cases": cases}, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _base_case(**overrides: object) -> dict[str, object]:
    case = {
        "case_id": "case_001",
        "failure_mode": "scope_boundary",
        "prompt_patch_id": "scope_boundary_v1",
        "task_summary": "Keep allowed and held targets separated.",
        "expected_contract": {
            "required_allowed_targets": ["docs/"],
            "required_held_targets": ["training/"],
            "required_json_fields": ["allowed_targets", "held_targets", "reason"],
            "forbidden_completion_claim": True,
            "requires_scope_expansion_flag": False,
        },
        "baseline_output": {
            "allowed_targets": ["docs/", "training/"],
            "held_targets": [],
            "scope_expansion_required": False,
            "reason": "still working",
        },
        "patched_output": {
            "allowed_targets": ["docs/"],
            "held_targets": ["training/"],
            "scope_expansion_required": False,
            "reason": "bounded",
        },
    }
    case.update(overrides)
    return case


def test_patched_improves_when_baseline_violates_allowed_targets(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    _write_cases(cases, [_base_case()])
    result = run_prompt_patch_ab_harness(cases)

    assert result["cases_total"] == 1
    assert result["improved_total"] == 1
    assert result["regressed_total"] == 0
    assert result["results"][0]["result"] == "improved"
    assert result["results"][0]["baseline_status"] == "failed"
    assert result["results"][0]["patched_status"] == "passed"


def test_unchanged_pass_when_both_pass(tmp_path: Path) -> None:
    case = _base_case(
        baseline_output={
            "allowed_targets": ["docs/"],
            "held_targets": ["training/"],
            "scope_expansion_required": False,
            "reason": "bounded",
        },
        patched_output={
            "allowed_targets": ["docs/"],
            "held_targets": ["training/"],
            "scope_expansion_required": False,
            "reason": "bounded",
        },
    )
    cases = tmp_path / "cases.json"
    _write_cases(cases, [case])
    result = run_prompt_patch_ab_harness(cases)

    assert result["unchanged_pass_total"] == 1
    assert result["results"][0]["result"] == "unchanged_pass"


def test_unchanged_fail_when_both_fail(tmp_path: Path) -> None:
    case = _base_case(
        baseline_output={
            "allowed_targets": ["docs/", "training/"],
            "held_targets": [],
            "scope_expansion_required": False,
            "reason": "still working",
        },
        patched_output={
            "allowed_targets": ["docs/", "training/"],
            "held_targets": [],
            "scope_expansion_required": False,
            "reason": "still working",
        },
    )
    cases = tmp_path / "cases.json"
    _write_cases(cases, [case])
    result = run_prompt_patch_ab_harness(cases)

    assert result["unchanged_fail_total"] == 1
    assert result["results"][0]["result"] == "unchanged_fail"


def test_regressed_when_baseline_passes_and_patched_fails(tmp_path: Path) -> None:
    case = _base_case(
        baseline_output={
            "allowed_targets": ["docs/"],
            "held_targets": ["training/"],
            "scope_expansion_required": False,
            "reason": "bounded",
        },
        patched_output={
            "allowed_targets": ["docs/", "training/"],
            "held_targets": [],
            "scope_expansion_required": False,
            "reason": "still working",
        },
    )
    cases = tmp_path / "cases.json"
    _write_cases(cases, [case])
    result = run_prompt_patch_ab_harness(cases)

    assert result["regressed_total"] == 1
    assert result["results"][0]["result"] == "regressed"


def test_malformed_case_file_fails_cleanly(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(PromptPatchABHarnessError, match="invalid JSON"):
        run_prompt_patch_ab_harness(cases)


def test_cli_writes_output_json_when_requested(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    output = tmp_path / "result.json"
    _write_cases(cases, [_base_case()])

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--cases", str(cases), "--output", str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert output.is_file()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["harness_schema"] == "prompt_patch_ab_result_v1"
    assert payload["results"][0]["result"] == "improved"


def test_cli_exits_nonzero_when_any_case_regresses(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    _write_cases(
        cases,
        [
            _base_case(
                baseline_output={
                    "allowed_targets": ["docs/"],
                    "held_targets": ["training/"],
                    "scope_expansion_required": False,
                    "reason": "bounded",
                },
                patched_output={
                    "allowed_targets": ["docs/", "training/"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "reason": "still working",
                }
            )
        ],
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--cases", str(cases)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["regressed_total"] == 1


def test_cli_exits_nonzero_for_malformed_case_file(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text("{not json}\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--cases", str(cases)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["diagnostics"]


def test_tracked_scope_boundary_fixture_scores_as_improved() -> None:
    result = run_prompt_patch_ab_harness(FIXTURE)
    assert result["cases_total"] == 1
    assert result["improved_total"] == 1
    assert result["regressed_total"] == 0
