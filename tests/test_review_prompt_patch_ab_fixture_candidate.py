from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "review_prompt_patch_ab_fixture_candidate.py"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _valid_candidate(*, case_id: str = "candidate_case_001", result: str = "improved") -> dict:
    if result == "improved":
        baseline_output = {
            "allowed_targets": ["docs/", "project note", "Training changes"],
            "held_targets": [],
            "scope_expansion_required": False,
            "reason": "The requested work involves updating documentation with project notes and training changes, which are clearly defined and achievable tasks. All components are within the scope of documentation and training activities.",
        }
        patched_output = {
            "allowed_targets": ["docs/"],
            "held_targets": ["training/"],
            "scope_expansion_required": False,
            "reason": "Only the docs/ target is explicitly authorized for this request. The training/ target is mentioned as relevant but not authorized, so it must be placed in held_targets.",
        }
    elif result == "unchanged_pass":
        baseline_output = patched_output = {
            "allowed_targets": ["docs/"],
            "held_targets": ["training/"],
            "scope_expansion_required": False,
            "reason": "bounded",
        }
    elif result == "unchanged_fail":
        baseline_output = patched_output = {
            "allowed_targets": ["docs/", "training/"],
            "held_targets": [],
            "scope_expansion_required": False,
            "reason": "still working",
        }
    else:
        baseline_output = {
            "allowed_targets": ["docs/"],
            "held_targets": ["training/"],
            "scope_expansion_required": False,
            "reason": "bounded",
        }
        patched_output = {
            "allowed_targets": ["docs/", "training/"],
            "held_targets": [],
            "scope_expansion_required": False,
            "reason": "still working",
        }

    return {
        "candidate_schema": "prompt_patch_ab_fixture_candidate_v1",
        "review_status": "not_reviewed",
        "import_status": "not_imported",
        "promotion_status": "not_promoted",
        "downstream_use_status": "prohibited_until_review",
        "source": {
            "run_dir": "/tmp/example/.work/prompt_patch_ab_live/20260716_211808",
            "live_record_sha256": "a" * 64,
            "generated_cases_sha256": "b" * 64,
            "harness_result_sha256": "c" * 64,
            "review_bundle_sha256": "d" * 64,
        },
        "candidate_case": {
            "case_id": case_id,
            "failure_mode": "scope_boundary",
            "prompt_patch_id": "scope_boundary_v1+output_contract_v1",
            "task_summary": "Keep allowed and held targets separated.",
            "expected_contract": {
                "required_allowed_targets": ["docs/"],
                "forbidden_allowed_targets": ["training/"],
                "required_held_targets": ["training/"],
                "required_json_fields": ["allowed_targets", "held_targets", "reason"],
                "forbidden_completion_claim": True,
                "requires_scope_expansion_flag": False,
            },
            "baseline_output": baseline_output,
            "patched_output": patched_output,
        },
    }


def _write_candidate(path: Path, payload: dict) -> None:
    _write_json(path, payload)


def test_valid_improved_candidate_writes_review_report_with_reviewable_true(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "review.json"
    payload = _valid_candidate(result="improved")
    _write_candidate(candidate, payload)
    before = candidate.read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(candidate), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert candidate.read_text(encoding="utf-8") == before
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["candidate_review_schema"] == "prompt_patch_ab_fixture_candidate_review_v1"
    assert payload["review_status"] == "review_required"
    assert payload["reviewable"] is True
    assert payload["harness_result"]["results"][0]["result"] == "improved"


def test_valid_unchanged_pass_candidate_writes_review_report_with_reviewable_true(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "review.json"
    _write_candidate(candidate, _valid_candidate(case_id="candidate_unchanged_pass", result="unchanged_pass"))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(candidate), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["reviewable"] is True
    assert payload["harness_result"]["results"][0]["result"] == "unchanged_pass"


def test_unchanged_fail_candidate_writes_review_report_with_reviewable_false(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "review.json"
    _write_candidate(candidate, _valid_candidate(case_id="candidate_unchanged_fail", result="unchanged_fail"))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(candidate), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["reviewable"] is False
    assert payload["harness_result"]["results"][0]["result"] == "unchanged_fail"


def test_regressed_candidate_fails_closed(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "review.json"
    _write_candidate(candidate, _valid_candidate(case_id="candidate_regressed", result="regressed"))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(candidate), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not out.exists()


def test_missing_candidate_file_fails(tmp_path: Path) -> None:
    out = tmp_path / "review.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(tmp_path / "missing.json"), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert not out.exists()


def test_bad_candidate_schema_fails(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "review.json"
    payload = _valid_candidate()
    payload["candidate_schema"] = "wrong"
    _write_candidate(candidate, payload)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(candidate), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert not out.exists()


def test_bad_status_values_fail(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "review.json"
    payload = _valid_candidate()
    payload["review_status"] = "reviewed"
    _write_candidate(candidate, payload)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(candidate), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert not out.exists()


def test_missing_candidate_case_required_field_fails(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "review.json"
    payload = _valid_candidate()
    del payload["candidate_case"]["expected_contract"]
    _write_candidate(candidate, payload)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(candidate), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert not out.exists()


def test_review_does_not_modify_candidate_and_does_not_write_tracked_fixture_files(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "review.json"
    _write_candidate(candidate, _valid_candidate())
    before = candidate.read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(candidate), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert candidate.read_text(encoding="utf-8") == before
    assert out.is_file()


def test_stdout_summary_includes_case_id_and_harness_result(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    out = tmp_path / "review.json"
    _write_candidate(candidate, _valid_candidate(case_id="summary_case"))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(candidate), "--out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["case_id"] == "summary_case"
    assert summary["harness_result"] == "improved"
