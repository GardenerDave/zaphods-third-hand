from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_layer_edit_mechanism_selection.py"


def direct_layer_candidate_payload() -> dict:
    return {
        "report_type": "larql_direct_layer_edit_candidate.v0",
        "candidate_status": "held_for_direct_layer_edit_mechanism_review",
        "model_modification_method": "LARQL",
        "persistence_mechanism": "direct_layer_weight_edit_candidate",
        "larql_core_path": True,
        "adapter_baseline_path": False,
        "prior_adapter_smoke_classification": "adapter_baseline_or_fallback_only",
        "layer_decomposition_selected": False,
        "layer_decomposition_method": "undecided_pending_review",
        "weight_edit_performed": False,
        "model_artifact_written": False,
        "base_model_overwrite_authorized": False,
        "adapter_merge_authorized": False,
        "production_deployment_authorized": False,
        "runtime_rule_install_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "dataset_release_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": "supervised_layer_edit_mechanism_selection",
    }


def write_json(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


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


def test_missing_authorization_exits_nonzero_and_writes_no_files(tmp_path):
    candidate = write_json(tmp_path, "candidate.json", direct_layer_candidate_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--direct-layer-candidate", candidate,
        "--run-id", "selection_001",
        "--out-root", out_root,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "selection_001/larql_layer_edit_mechanism_selection.json").exists()


def test_authorized_undecided_run_writes_all_expected_files(tmp_path):
    candidate = write_json(tmp_path, "candidate.json", direct_layer_candidate_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--direct-layer-candidate", candidate,
        "--run-id", "selection_001",
        "--out-root", out_root,
        "--select-mechanism", "undecided_pending_review",
        "--select-module-family", "undecided",
        "--authorize-larql-layer-edit-mechanism-selection",
    )
    assert result.returncode == 0
    out_dir = out_root / "selection_001"
    for name in [
        "larql_layer_edit_mechanism_selection.json",
        "module_inventory.json",
        "selected_mechanism_plan.md",
        "reversible_patch_format.md",
        "layer_edit_boundary.md",
        "reaudition_plan.md",
    ]:
        assert (out_dir / name).exists()


def test_authorized_concrete_run_writes_all_expected_files(tmp_path):
    candidate = write_json(tmp_path, "candidate.json", direct_layer_candidate_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--direct-layer-candidate", candidate,
        "--run-id", "selection_002",
        "--out-root", out_root,
        "--select-mechanism", "single_module_projection_delta",
        "--select-module-family", "mlp_projection",
        "--authorize-larql-layer-edit-mechanism-selection",
    )
    assert result.returncode == 0
    data = json.loads(
        (out_root / "selection_002/larql_layer_edit_mechanism_selection.json").read_text(encoding="utf-8")
    )
    assert data["selected_mechanism"] == "single_module_projection_delta"
    assert data["selected_module_family"] == "mlp_projection"
    assert data["layer_decomposition_selected"] is True


def test_validates_source_candidate_fields_and_rejects_bad_values(tmp_path):
    bad_cases = [
        ("model_modification_method", "wrong"),
        ("larql_core_path", False),
        ("adapter_baseline_path", True),
        ("weight_edit_performed", True),
        ("model_artifact_written", True),
        ("install_authorized", True),
    ]
    for index, (field, value) in enumerate(bad_cases, start=1):
        payload = direct_layer_candidate_payload()
        payload[field] = value
        result = run_script(
            "--direct-layer-candidate", write_json(tmp_path, f"bad_{index}.json", payload),
            "--run-id", f"selection_bad_{index}",
            "--out-root", tmp_path / "out",
            "--authorize-larql-layer-edit-mechanism-selection",
        )
        assert result.returncode != 0


def test_undecided_selection_keeps_layer_decomposition_selected_false(tmp_path):
    from local_harness.larql_layer_edit_mechanism_selection import write_selection

    record = write_selection(
        write_json(tmp_path, "candidate.json", direct_layer_candidate_payload()),
        "selection_003",
        tmp_path / "out",
        authorize_larql_layer_edit_mechanism_selection=True,
        select_mechanism="undecided_pending_review",
        select_module_family="undecided",
    )
    assert record["layer_decomposition_selected"] is False
    assert record["weight_edit_performed"] is False
    assert record["model_artifact_written"] is False


def test_output_authority_flags_remain_false(tmp_path):
    from local_harness.larql_layer_edit_mechanism_selection import write_selection

    record = write_selection(
        write_json(tmp_path, "candidate.json", direct_layer_candidate_payload()),
        "selection_004",
        tmp_path / "out",
        authorize_larql_layer_edit_mechanism_selection=True,
        select_mechanism="svd_low_rank_delta",
        select_module_family="attention_projection",
    )
    for key in [
        "weight_edit_performed",
        "model_artifact_written",
        "base_model_overwrite_authorized",
        "irreversible_patch_authorized",
        "adapter_merge_authorized",
        "production_deployment_authorized",
        "runtime_rule_install_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "dataset_release_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        assert record[key] is False


def test_module_inventory_works_when_base_model_path_absent(tmp_path):
    result = run_script(
        "--direct-layer-candidate", write_json(tmp_path, "candidate.json", direct_layer_candidate_payload()),
        "--run-id", "selection_005",
        "--out-root", tmp_path / "out",
        "--authorize-larql-layer-edit-mechanism-selection",
    )
    assert result.returncode == 0
    inventory = json.loads((tmp_path / "out/selection_005/module_inventory.json").read_text(encoding="utf-8"))
    assert inventory["inspection_status"] == "base_model_not_provided"


def test_module_inventory_reads_fake_config_and_index(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text(
        json.dumps({"model_type": "qwen", "num_hidden_layers": 28}) + "\n",
        encoding="utf-8",
    )
    (model_dir / "model.safetensors.index.json").write_text(
        json.dumps(
            {
                "weight_map": {
                    "model.layers.0.self_attn.q_proj.weight": "model-00001-of-00002.safetensors",
                    "model.layers.0.mlp.up_proj.weight": "model-00001-of-00002.safetensors",
                    "model.layers.0.input_layernorm.weight": "model-00001-of-00002.safetensors",
                }
            }
        ) + "\n",
        encoding="utf-8",
    )
    result = run_script(
        "--direct-layer-candidate", write_json(tmp_path, "candidate.json", direct_layer_candidate_payload()),
        "--run-id", "selection_006",
        "--out-root", tmp_path / "out",
        "--base-model-path", model_dir,
        "--select-mechanism", "single_module_projection_delta",
        "--select-module-family", "mlp_projection",
        "--authorize-larql-layer-edit-mechanism-selection",
    )
    assert result.returncode == 0
    inventory = json.loads((tmp_path / "out/selection_006/module_inventory.json").read_text(encoding="utf-8"))
    assert inventory["config_json_exists"] is True
    assert inventory["model_safetensors_index_exists"] is True
    assert inventory["model_type"] == "qwen"
    assert inventory["num_hidden_layers"] == 28
    assert inventory["candidate_attention_projection_keys"]
    assert inventory["candidate_mlp_projection_keys"]
    assert inventory["candidate_residual_stream_keys"]
