from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_correction_delta_plan.py"


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def reaudition_payload(*, status: str = "completed_model_comparison") -> dict:
    return {
        "report_type": "larql_direct_layer_edit_reaudition.v0",
        "reaudition_status": status,
        "model_modification_method": "LARQL",
        "persistence_mechanism": "direct_layer_weight_edit",
        "larql_core_path": True,
        "adapter_baseline_path": False,
        "model_inference_performed": True,
        "promotion_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
    }


def scoring_payload(
    *,
    improved: int = 0,
    regressed: int = 0,
    base_norm: int = 4,
    patched_norm: int = 4,
    outputs_equal: int = 4,
) -> dict:
    return {
        "summary": {
            "patched_normalized_improved_probe_count": improved,
            "patched_normalized_regressed_probe_count": regressed,
            "base_normalized_probe_pass_count": base_norm,
            "patched_normalized_probe_pass_count": patched_norm,
            "outputs_equal_count": outputs_equal,
        }
    }


def comparison_payload(normalized_equal: list[bool]) -> dict:
    return {
        "probes": [
            {"probe_id": f"probe_{idx}", "normalized_outputs_equal": value}
            for idx, value in enumerate(normalized_equal)
        ]
    }


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


def test_missing_authorization_exits_nonzero_and_writes_no_packet_files(tmp_path):
    out_root = tmp_path / "out"
    result = run_script("--run-id", "plan_001", "--out-root", out_root)
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "plan_001/larql_correction_delta_plan.json").exists()


def test_authorized_packet_only_run_writes_all_required_files(tmp_path):
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "plan_002",
        "--out-root", out_root,
        "--authorize-larql-correction-delta-planning",
    )
    assert result.returncode == 0
    out_dir = out_root / "plan_002"
    for name in [
        "larql_correction_delta_plan.json",
        "candidate_methods.json",
        "activation_contrast_probe_pairs.json",
        "delta_selection_plan.json",
        "risk_register.md",
        "review_packet.md",
    ]:
        assert (out_dir / name).exists()


def test_output_json_has_required_boundary_fields(tmp_path):
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "plan_003",
        "--out-root", out_root,
        "--authorize-larql-correction-delta-planning",
    )
    assert result.returncode == 0
    payload = json.loads((out_root / "plan_003/larql_correction_delta_plan.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "larql_correction_delta_plan.v0"
    assert payload["larql_core_path"] is True
    assert payload["model_inference_performed"] is False
    assert payload["weight_edit_performed"] is False
    assert payload["delta_artifact_written"] is False
    assert payload["patched_model_materialized"] is False
    assert payload["training_performed"] is False
    assert payload["adapter_baseline_path"] is False
    assert payload["promotion_authorized"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False


def test_candidate_methods_include_all_required_methods(tmp_path):
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "plan_004",
        "--out-root", out_root,
        "--authorize-larql-correction-delta-planning",
    )
    methods = json.loads((out_root / "plan_004/candidate_methods.json").read_text(encoding="utf-8"))
    ids = {item["method_id"] for item in methods}
    assert {
        "activation_difference_direction",
        "contrast_prompt_steering_vector",
        "layer_local_least_squares_delta",
        "representation_probe_only",
    } <= ids


def test_selected_method_is_activation_difference_direction(tmp_path):
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "plan_005",
        "--out-root", out_root,
        "--authorize-larql-correction-delta-planning",
    )
    plan = json.loads((out_root / "plan_005/delta_selection_plan.json").read_text(encoding="utf-8"))
    assert plan["recommended_method"] == "activation_difference_direction"


def test_activation_contrast_probe_pairs_include_all_required_probe_ids(tmp_path):
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "plan_006",
        "--out-root", out_root,
        "--authorize-larql-correction-delta-planning",
    )
    pairs = json.loads((out_root / "plan_006/activation_contrast_probe_pairs.json").read_text(encoding="utf-8"))
    ids = {item["probe_id"] for item in pairs}
    assert {
        "original_larql_behavior_replay",
        "adjacent_file_anti_overfit",
        "all_files_authorized_control",
        "unrelated_task_regression",
    } <= ids


def test_file_scope_probe_pairs_forbid_install_and_registry_mutation(tmp_path):
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "plan_007",
        "--out-root", out_root,
        "--authorize-larql-correction-delta-planning",
    )
    pairs = json.loads((out_root / "plan_007/activation_contrast_probe_pairs.json").read_text(encoding="utf-8"))
    by_id = {item["probe_id"]: item for item in pairs}
    for probe_id in [
        "original_larql_behavior_replay",
        "adjacent_file_anti_overfit",
        "all_files_authorized_control",
    ]:
        assert by_id[probe_id]["must_not_authorize_install"] is True
        assert by_id[probe_id]["must_not_authorize_registry_mutation"] is True


def test_unrelated_regression_pair_is_marked_as_regression_guard(tmp_path):
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "plan_008",
        "--out-root", out_root,
        "--authorize-larql-correction-delta-planning",
    )
    pairs = json.loads((out_root / "plan_008/activation_contrast_probe_pairs.json").read_text(encoding="utf-8"))
    item = next(pair for pair in pairs if pair["probe_id"] == "unrelated_task_regression")
    assert item["regression_guard"] is True


def test_missing_source_reaudition_is_not_treated_as_behavioral_improvement(tmp_path):
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "plan_009",
        "--out-root", out_root,
        "--source-reaudition", tmp_path / "missing.json",
        "--authorize-larql-correction-delta-planning",
    )
    assert result.returncode == 0
    payload = json.loads((out_root / "plan_009/larql_correction_delta_plan.json").read_text(encoding="utf-8"))
    assert payload["source_reaudition_status"] == "missing"
    assert payload["behavioral_improvement_observed"] is False


def test_failed_source_reaudition_is_not_treated_as_behavioral_improvement(tmp_path):
    source = write_json(tmp_path / "reaudition.json", reaudition_payload(status="failed_reaudition_exception"))
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "plan_010",
        "--out-root", out_root,
        "--source-reaudition", source,
        "--authorize-larql-correction-delta-planning",
    )
    assert result.returncode == 0
    payload = json.loads((out_root / "plan_010/larql_correction_delta_plan.json").read_text(encoding="utf-8"))
    assert payload["source_reaudition_status"] == "failed_reaudition_exception"
    assert payload["behavioral_improvement_observed"] is False


def test_successful_source_reaudition_with_no_improvement_stays_false(tmp_path):
    source = write_json(tmp_path / "reaudition.json", reaudition_payload())
    scoring = write_json(tmp_path / "scoring.json", scoring_payload(improved=0, regressed=0))
    comparison = write_json(tmp_path / "comparison.json", comparison_payload([True, True, True, True]))
    payload = reaudition_payload()
    payload["scoring_report_path"] = str(scoring)
    payload["comparison_report_path"] = str(comparison)
    source = write_json(tmp_path / "reaudition.json", payload)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "plan_011",
        "--out-root", out_root,
        "--source-reaudition", source,
        "--authorize-larql-correction-delta-planning",
    )
    assert result.returncode == 0
    plan = json.loads((out_root / "plan_011/larql_correction_delta_plan.json").read_text(encoding="utf-8"))
    assert plan["source_outputs_equal_count"] == 4
    assert plan["source_normalized_outputs_equal_count"] == 4
    assert plan["behavioral_improvement_observed"] is False


def test_planner_does_not_import_model_stack_modules():
    script_text = SCRIPT.read_text(encoding="utf-8")
    forbidden = ["import torch", "from torch", "import transformers", "from transformers", "import safetensors", "from safetensors", "import peft", "from peft", "import datasets", "from datasets"]
    for token in forbidden:
        assert token not in script_text
