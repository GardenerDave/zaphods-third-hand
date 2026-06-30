from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_likelihood_result_summarizer.py"
SPEC = importlib.util.spec_from_file_location("larql_likelihood_result_summarizer", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def comparison_fixture(tmp_path: Path, *, scale_label: str, margins: dict[str, float]) -> Path:
    probes = [
        {"probe_id": probe_id, "margin_delta": margin}
        for probe_id, margin in margins.items()
    ]
    return write_json(
        tmp_path / f"teacher_forced_likelihood_{scale_label}" / "teacher_forced_likelihood_comparison.json",
        {
            "evidence_only": True,
            "promotion_authorized": False,
            "automatic_failure_to_curriculum_capture_authorized": False,
            "summary": {},
            "probes": probes,
        },
    )


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_missing_authorization_exits_nonzero_and_writes_no_output(tmp_path):
    first = comparison_fixture(
        tmp_path,
        scale_label="1e-3",
        margins={
            "original_larql_behavior_replay": 0.1,
            "adjacent_file_anti_overfit": 0.1,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    second = comparison_fixture(
        tmp_path,
        scale_label="1e-2",
        margins={
            "original_larql_behavior_replay": 0.2,
            "adjacent_file_anti_overfit": 0.2,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "summary_001",
        "--out-root", out_root,
        "--comparison", first,
        "--comparison", second,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "summary_001").exists()


def test_authorized_run_writes_outputs(tmp_path):
    first = comparison_fixture(
        tmp_path,
        scale_label="1e-3",
        margins={
            "original_larql_behavior_replay": 0.1,
            "adjacent_file_anti_overfit": 0.2,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    second = comparison_fixture(
        tmp_path,
        scale_label="1e-2",
        margins={
            "original_larql_behavior_replay": 0.3,
            "adjacent_file_anti_overfit": 0.4,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    out_root = tmp_path / "out"
    result = MODULE.write_likelihood_result_summary(
        run_id="summary_002",
        out_root=out_root,
        comparison_paths=[first, second],
        authorize_larql_likelihood_result_summarization=True,
    )
    out_dir = out_root / "summary_002"
    assert (out_dir / "scale_comparison.json").exists()
    assert (out_dir / "scale_comparison_review_packet.md").exists()
    assert result["report_type"] == "larql_likelihood_scale_comparison.v0"


def test_per_probe_margin_deltas_by_scale_are_recorded(tmp_path):
    first = comparison_fixture(
        tmp_path,
        scale_label="1e-3",
        margins={
            "original_larql_behavior_replay": 0.1,
            "adjacent_file_anti_overfit": 0.2,
            "all_files_authorized_control": -0.1,
            "unrelated_task_regression": 0.0,
        },
    )
    second = comparison_fixture(
        tmp_path,
        scale_label="1e-2",
        margins={
            "original_larql_behavior_replay": 0.15,
            "adjacent_file_anti_overfit": 0.25,
            "all_files_authorized_control": -0.2,
            "unrelated_task_regression": -0.1,
        },
    )
    result = MODULE.build_scale_comparison([first, second])
    assert result["runs"][0]["per_probe_margin_delta"]["original_larql_behavior_replay"] == 0.1
    assert result["runs"][1]["per_probe_margin_delta"]["adjacent_file_anti_overfit"] == 0.25


def test_target_and_control_aggregates_and_monotonic_flags(tmp_path):
    first = comparison_fixture(
        tmp_path,
        scale_label="1e-3",
        margins={
            "original_larql_behavior_replay": 0.1,
            "adjacent_file_anti_overfit": 0.2,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    second = comparison_fixture(
        tmp_path,
        scale_label="1e-2",
        margins={
            "original_larql_behavior_replay": 0.3,
            "adjacent_file_anti_overfit": 0.4,
            "all_files_authorized_control": -0.1,
            "unrelated_task_regression": -0.1,
        },
    )
    result = MODULE.build_scale_comparison([first, second])
    assert result["target_probes_aggregate"]["target_improvement_monotonic"] is True
    assert result["control_regression_probes_aggregate"]["control_regression_monotonic"] is True


def test_recommendation_do_not_scale_blindly(tmp_path):
    first = comparison_fixture(
        tmp_path,
        scale_label="1e-3",
        margins={
            "original_larql_behavior_replay": 0.1,
            "adjacent_file_anti_overfit": 0.2,
            "all_files_authorized_control": -0.1,
            "unrelated_task_regression": -0.1,
        },
    )
    second = comparison_fixture(
        tmp_path,
        scale_label="1e-2",
        margins={
            "original_larql_behavior_replay": 0.2,
            "adjacent_file_anti_overfit": 0.3,
            "all_files_authorized_control": -0.2,
            "unrelated_task_regression": -0.2,
        },
    )
    result = MODULE.build_scale_comparison([first, second])
    assert result["recommended_next_step"] == "do_not_scale_blindly"


def test_recommendation_test_alternate_direction(tmp_path):
    first = comparison_fixture(
        tmp_path,
        scale_label="1e-3",
        margins={
            "original_larql_behavior_replay": -0.1,
            "adjacent_file_anti_overfit": -0.2,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    second = comparison_fixture(
        tmp_path,
        scale_label="1e-2",
        margins={
            "original_larql_behavior_replay": -0.15,
            "adjacent_file_anti_overfit": -0.25,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    result = MODULE.build_scale_comparison([first, second])
    assert result["recommended_next_step"] == "test_alternate_direction"


def test_recommendation_reaudition_behavior_only_if_margin_flips(tmp_path):
    first = comparison_fixture(
        tmp_path,
        scale_label="1e-3",
        margins={
            "original_larql_behavior_replay": 0.1,
            "adjacent_file_anti_overfit": 0.2,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    second = comparison_fixture(
        tmp_path,
        scale_label="1e-2",
        margins={
            "original_larql_behavior_replay": 0.3,
            "adjacent_file_anti_overfit": 0.4,
            "all_files_authorized_control": 0.1,
            "unrelated_task_regression": 0.0,
        },
    )
    result = MODULE.build_scale_comparison([first, second])
    assert result["recommended_next_step"] == "reaudition_behavior_only_if_margin_flips"


def test_recommendation_test_alternate_layer(tmp_path):
    first = comparison_fixture(
        tmp_path,
        scale_label="1e-3",
        margins={
            "original_larql_behavior_replay": 0.2,
            "adjacent_file_anti_overfit": -0.1,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    second = comparison_fixture(
        tmp_path,
        scale_label="1e-2",
        margins={
            "original_larql_behavior_replay": -0.2,
            "adjacent_file_anti_overfit": 0.1,
            "all_files_authorized_control": 0.0,
            "unrelated_task_regression": 0.0,
        },
    )
    result = MODULE.build_scale_comparison([first, second])
    assert result["recommended_next_step"] == "test_alternate_layer"


def test_no_model_inference_or_training_or_promotion():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "transformers" not in script_text
    assert "torch" not in script_text
