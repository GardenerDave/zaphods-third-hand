from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "export_prompt_patch_ab_fixture_candidate.py"
LIVE_RUN_DIR = ROOT / ".work" / "prompt_patch_ab_live" / "20260716_211808"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _make_run_dir(root: Path, *, live_record: dict, cases: dict, harness_result: dict | None = None, review_bundle: dict | None = None) -> Path:
    run_dir = root / "run"
    evidence_dir = run_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    _write_json(evidence_dir / "prompt_patch_ab_live_record.json", live_record)
    _write_json(evidence_dir / "prompt_patch_ab_cases.json", cases)
    if harness_result is not None:
        _write_json(run_dir / "harness_result.json", harness_result)
    if review_bundle is not None:
        _write_json(run_dir / "prompt_patch_ab_review_bundle.json", review_bundle)
    return run_dir


def _valid_live_record() -> dict:
    return {
        "generated_case_status": "harness_valid",
        "review_required": True,
        "execution_mode": "explicit_operator_invoked",
        "case_id": "scope_boundary_live_smoke_005",
        "failure_mode": "scope_boundary",
        "prompt_patch_id": "scope_boundary_v1+output_contract_v1",
        "task_summary": "Keep allowed and held targets separated.",
        "model": "test-model",
        "base_url_present": True,
        "runtime_settings": {"temperature": 0.0, "max_tokens": 512, "timeout_seconds": 30},
        "baseline_prompt_sha256": "a" * 64,
        "patched_prompt_sha256": "b" * 64,
        "baseline_response_sha256": "c" * 64,
        "patched_response_sha256": "d" * 64,
        "generated_cases_path": "evidence/prompt_patch_ab_cases.json",
        "diagnostics": [],
        "authority_boundary": [
            "evidence_only",
            "explicit_operator_invoked",
            "no_cron_watchdog_integration",
            "no_auto_promotion",
            "no_training_capture",
            "no_merge_authority",
            "no_deployment_authority",
            "no_downstream_use_authority",
        ],
    }


def _valid_cases() -> dict:
    return {
        "harness_schema": "prompt_patch_ab_cases_v1",
        "cases": [
            {
                "case_id": "scope_boundary_live_smoke_005",
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
                "baseline_output": {
                    "allowed_targets": ["docs/", "project note", "Training changes"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "reason": "The requested work involves updating documentation with project notes and training changes, which are clearly defined and achievable tasks. All components are within the scope of documentation and training activities.",
                },
                "patched_output": {
                    "allowed_targets": ["docs/"],
                    "held_targets": ["training/"],
                    "scope_expansion_required": False,
                    "reason": "Only the docs/ target is explicitly authorized for this request. The training/ target is mentioned as relevant but not authorized, so it must be placed in held_targets.",
                },
            }
        ],
    }


def _valid_harness_result() -> dict:
    return {
        "harness_schema": "prompt_patch_ab_result_v1",
        "cases_total": 1,
        "improved_total": 1,
        "unchanged_pass_total": 0,
        "unchanged_fail_total": 0,
        "regressed_total": 0,
        "results": [],
        "diagnostics": [],
    }


def _valid_review_bundle() -> dict:
    return {
        "downstream_use_status": "prohibited_until_review",
    }


def test_successful_export_writes_candidate_fixture_with_expected_fields(tmp_path: Path) -> None:
    run_dir = _make_run_dir(
        tmp_path,
        live_record=_valid_live_record(),
        cases=_valid_cases(),
        harness_result=_valid_harness_result(),
        review_bundle=_valid_review_bundle(),
    )
    out = tmp_path / "candidate.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "scope_boundary_output_contract_combined_candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["candidate_schema"] == "prompt_patch_ab_fixture_candidate_v1"
    assert payload["review_status"] == "not_reviewed"
    assert payload["import_status"] == "not_imported"
    assert payload["promotion_status"] == "not_promoted"
    assert payload["downstream_use_status"] == "prohibited_until_review"
    assert payload["candidate_case"]["case_id"] == "scope_boundary_output_contract_combined_candidate_001"
    assert payload["source"]["run_dir"] == str(run_dir)
    assert payload["source"]["harness_result_sha256"] is not None
    assert payload["source"]["review_bundle_sha256"] is not None
    assert ".work" not in json.dumps(payload["candidate_case"])
    assert "baseline_response.raw.json" not in json.dumps(payload["candidate_case"])
    assert "patched_response.raw.json" not in json.dumps(payload["candidate_case"])


def test_exporter_overrides_case_id(tmp_path: Path) -> None:
    run_dir = _make_run_dir(tmp_path, live_record=_valid_live_record(), cases=_valid_cases())
    out = tmp_path / "candidate.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "override_candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["candidate_case"]["case_id"] == "override_candidate_001"


def test_missing_live_record_fails(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "evidence").mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "evidence" / "prompt_patch_ab_cases.json", _valid_cases())
    out = tmp_path / "candidate.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not out.exists()


def test_generated_case_status_other_than_harness_valid_fails(tmp_path: Path) -> None:
    live = _valid_live_record()
    live["generated_case_status"] = "harness_invalid"
    run_dir = _make_run_dir(tmp_path, live_record=live, cases=_valid_cases())
    out = tmp_path / "candidate.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not out.exists()


def test_missing_generated_cases_file_fails(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "evidence").mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "evidence" / "prompt_patch_ab_live_record.json", _valid_live_record())
    out = tmp_path / "candidate.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not out.exists()


def test_multiple_generated_cases_fail(tmp_path: Path) -> None:
    cases = _valid_cases()
    cases["cases"].append(dict(cases["cases"][0], case_id="second_case"))
    run_dir = _make_run_dir(tmp_path, live_record=_valid_live_record(), cases=cases)
    out = tmp_path / "candidate.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not out.exists()


def test_malformed_harness_result_if_present_fails(tmp_path: Path) -> None:
    run_dir = _make_run_dir(
        tmp_path,
        live_record=_valid_live_record(),
        cases=_valid_cases(),
    )
    (run_dir / "harness_result.json").write_text("{not json}\n", encoding="utf-8")
    out = tmp_path / "candidate.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not out.exists()


def test_review_bundle_with_bad_downstream_use_fails(tmp_path: Path) -> None:
    run_dir = _make_run_dir(
        tmp_path,
        live_record=_valid_live_record(),
        cases=_valid_cases(),
        review_bundle={"downstream_use_status": "allowed"},
    )
    out = tmp_path / "candidate.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not out.exists()


def test_exporter_does_not_embed_raw_model_responses_or_work_paths(tmp_path: Path) -> None:
    run_dir = _make_run_dir(
        tmp_path,
        live_record=_valid_live_record(),
        cases=_valid_cases(),
        harness_result=_valid_harness_result(),
        review_bundle=_valid_review_bundle(),
    )
    out = tmp_path / "candidate.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    candidate_text = json.dumps(payload["candidate_case"])
    assert "baseline_response.raw.json" not in candidate_text
    assert "patched_response.raw.json" not in candidate_text
    assert ".work" not in candidate_text
    assert str(run_dir) not in candidate_text


def test_work_paths_appear_only_in_source_run_dir_not_candidate_case(tmp_path: Path) -> None:
    run_dir = LIVE_RUN_DIR
    if not run_dir.exists():
        pytest.skip("live evidence run directory is unavailable")
    out = tmp_path / "candidate.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--case-id",
            "scope_boundary_output_contract_combined_candidate_001",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert ".work/" in payload["source"]["run_dir"]
    candidate_text = json.dumps(payload["candidate_case"])
    assert ".work/" not in candidate_text
