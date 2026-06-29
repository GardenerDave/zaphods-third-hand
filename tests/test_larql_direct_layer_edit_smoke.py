from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_direct_layer_edit_smoke.py"


def mechanism_selection_payload() -> dict:
    return {
        "report_type": "larql_layer_edit_mechanism_selection.v0",
        "selection_status": "held_for_direct_layer_edit_smoke_review",
        "model_modification_method": "LARQL",
        "persistence_mechanism": "direct_layer_weight_edit_candidate",
        "larql_core_path": True,
        "adapter_baseline_path": False,
        "selected_mechanism": "single_module_projection_delta",
        "selected_module_family": "mlp_projection",
        "layer_decomposition_selected": True,
        "weight_edit_performed": False,
        "model_artifact_written": False,
        "base_model_overwrite_authorized": False,
        "irreversible_patch_authorized": False,
        "adapter_merge_authorized": False,
        "production_deployment_authorized": False,
        "runtime_rule_install_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "dataset_release_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": "supervised_direct_layer_edit_smoke",
        "module_inventory_path": "REPLACE_ME",
    }


def module_inventory_payload(key: str = "model.layers.0.mlp.up_proj.weight") -> dict:
    return {
        "candidate_attention_projection_keys": [],
        "candidate_mlp_projection_keys": [key],
        "candidate_residual_stream_keys": [],
        "inspection_status": "inspected",
    }


def write_json(path: Path, payload: dict) -> Path:
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


def write_selection_fixture(tmp_path: Path, key: str = "model.layers.0.mlp.up_proj.weight") -> Path:
    inventory_path = tmp_path / "module_inventory.json"
    write_json(inventory_path, module_inventory_payload(key))
    payload = mechanism_selection_payload()
    payload["module_inventory_path"] = str(inventory_path)
    return write_json(tmp_path / "selection.json", payload)


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_missing_authorization_exits_nonzero_and_writes_no_files(tmp_path):
    selection = write_selection_fixture(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--mechanism-selection", selection,
        "--run-id", "smoke_001",
        "--out-root", out_root,
        "--base-model-path", tmp_path / "missing_model",
        "--target-tensor-key", "model.layers.0.mlp.up_proj.weight",
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "smoke_001/larql_direct_layer_edit_smoke.json").exists()


def test_rejects_undecided_or_invalid_source_selection(tmp_path):
    bad = mechanism_selection_payload()
    bad["selected_mechanism"] = "undecided_pending_review"
    bad["selected_module_family"] = "undecided"
    bad["layer_decomposition_selected"] = False
    bad["module_inventory_path"] = str(write_json(tmp_path / "inventory.json", module_inventory_payload()))
    selection = write_json(tmp_path / "bad.json", bad)
    result = run_script(
        "--mechanism-selection", selection,
        "--run-id", "smoke_bad",
        "--out-root", tmp_path / "out",
        "--base-model-path", tmp_path / "missing_model",
        "--target-tensor-key", "model.layers.0.mlp.up_proj.weight",
        "--authorize-larql-direct-layer-edit-smoke",
    )
    assert result.returncode != 0


def test_rejects_source_selection_with_weight_edit_model_artifact_or_install(tmp_path):
    for field in ["weight_edit_performed", "model_artifact_written", "install_authorized"]:
        bad = mechanism_selection_payload()
        bad[field] = True
        bad["module_inventory_path"] = str(write_json(tmp_path / f"{field}_inventory.json", module_inventory_payload()))
        selection = write_json(tmp_path / f"{field}.json", bad)
        result = run_script(
            "--mechanism-selection", selection,
            "--run-id", f"smoke_{field}",
            "--out-root", tmp_path / "out",
            "--base-model-path", tmp_path / "missing_model",
            "--target-tensor-key", "model.layers.0.mlp.up_proj.weight",
            "--authorize-larql-direct-layer-edit-smoke",
        )
        assert result.returncode != 0


def test_rejects_target_tensor_key_outside_selected_module_family(tmp_path):
    selection = write_selection_fixture(tmp_path, key="model.layers.0.mlp.up_proj.weight")
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    result = run_script(
        "--mechanism-selection", selection,
        "--run-id", "smoke_002",
        "--out-root", tmp_path / "out",
        "--base-model-path", model_dir,
        "--target-tensor-key", "model.layers.0.self_attn.q_proj.weight",
        "--authorize-larql-direct-layer-edit-smoke",
    )
    assert result.returncode != 0


def test_blocked_missing_base_model_writes_useful_status(tmp_path):
    selection = write_selection_fixture(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--mechanism-selection", selection,
        "--run-id", "smoke_003",
        "--out-root", out_root,
        "--base-model-path", tmp_path / "missing_model",
        "--target-tensor-key", "model.layers.0.mlp.up_proj.weight",
        "--authorize-larql-direct-layer-edit-smoke",
    )
    assert result.returncode == 0
    smoke = json.loads((out_root / "smoke_003/larql_direct_layer_edit_smoke.json").read_text(encoding="utf-8"))
    assert smoke["smoke_status"] == "blocked_missing_base_model"


def test_blocked_target_tensor_not_found_writes_useful_status(tmp_path):
    from local_harness.larql_direct_layer_edit_smoke import write_smoke

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    write_json(model_dir / "model.safetensors.index.json", {"weight_map": {}})
    smoke = write_smoke(
        write_selection_fixture(tmp_path),
        "smoke_004",
        tmp_path / "out",
        base_model_path=model_dir,
        target_tensor_key="model.layers.0.mlp.up_proj.weight",
        authorize_larql_direct_layer_edit_smoke=True,
    )
    assert smoke["smoke_status"] == "blocked_target_tensor_not_found"


def test_successful_mocked_delta_creation_without_patched_model(tmp_path, monkeypatch):
    from local_harness import larql_direct_layer_edit_smoke as mod

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    shard = model_dir / "model-00001-of-00001.safetensors"
    shard.write_bytes(b"placeholder")
    write_json(model_dir / "model.safetensors.index.json", {
        "weight_map": {"model.layers.0.mlp.up_proj.weight": shard.name}
    })

    def fake_stack() -> bool:
        return True

    def fake_delta(**kwargs):
        delta_path = kwargs["out_dir"] / "direct_delta.safetensors"
        delta_path.write_bytes(b"delta")
        return {
            "tensor_shape": [2, 2],
            "dtype": "float32",
            "original_tensor_hash": "orig",
            "delta_hash": "delta",
            "delta_norm": 1e-6,
            "relative_delta_norm": 1e-6,
            "delta_artifact_path": str(delta_path),
            "target_tensor_key": kwargs["target_tensor_key"],
            "source_shard_path": str(kwargs["source_shard_path"]),
            "selected_mechanism": kwargs["selected_mechanism"],
            "selected_module_family": kwargs["selected_module_family"],
            "delta_scale": kwargs["delta_scale"],
            "deterministic_seed_hash": kwargs["seed_hash"],
        }

    monkeypatch.setattr(mod, "tensor_stack_available", fake_stack)
    monkeypatch.setattr(mod, "create_direct_delta_artifact", fake_delta)

    smoke = mod.write_smoke(
        write_selection_fixture(tmp_path),
        "smoke_005",
        tmp_path / "out",
        base_model_path=model_dir,
        target_tensor_key="model.layers.0.mlp.up_proj.weight",
        authorize_larql_direct_layer_edit_smoke=True,
    )
    assert smoke["smoke_status"] == "completed_direct_delta_artifact"
    assert smoke["direct_delta_artifact_written"] is True
    assert smoke["model_artifact_written"] is False
    manifest = json.loads((tmp_path / "out/smoke_005/direct_delta_manifest.json").read_text(encoding="utf-8"))
    assert manifest["not_lora"] is True
    assert manifest["not_training"] is True
    assert manifest["not_adapter"] is True


def test_materialize_patched_model_without_authorization_blocks(tmp_path, monkeypatch):
    from local_harness import larql_direct_layer_edit_smoke as mod

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    shard = model_dir / "model-00001-of-00001.safetensors"
    shard.write_bytes(b"placeholder")
    write_json(model_dir / "model.safetensors.index.json", {
        "weight_map": {"model.layers.0.mlp.up_proj.weight": shard.name}
    })

    monkeypatch.setattr(mod, "tensor_stack_available", lambda: True)
    monkeypatch.setattr(mod, "create_direct_delta_artifact", lambda **kwargs: {
        "tensor_shape": [2, 2],
        "dtype": "float32",
        "original_tensor_hash": "orig",
        "delta_hash": "delta",
        "delta_norm": 1e-6,
        "relative_delta_norm": 1e-6,
        "delta_artifact_path": str(kwargs["out_dir"] / "direct_delta.safetensors"),
        "target_tensor_key": kwargs["target_tensor_key"],
        "source_shard_path": str(kwargs["source_shard_path"]),
        "selected_mechanism": kwargs["selected_mechanism"],
        "selected_module_family": kwargs["selected_module_family"],
        "delta_scale": kwargs["delta_scale"],
        "deterministic_seed_hash": kwargs["seed_hash"],
    })

    smoke = mod.write_smoke(
        write_selection_fixture(tmp_path),
        "smoke_006",
        tmp_path / "out",
        base_model_path=model_dir,
        target_tensor_key="model.layers.0.mlp.up_proj.weight",
        authorize_larql_direct_layer_edit_smoke=True,
        materialize_patched_model=True,
        authorize_patched_model_copy=False,
    )
    assert smoke["smoke_status"] == "blocked_patched_model_copy_not_authorized"


def test_mocked_patched_model_copy_sets_model_artifact_written(tmp_path, monkeypatch):
    from local_harness import larql_direct_layer_edit_smoke as mod

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    shard = model_dir / "model-00001-of-00001.safetensors"
    shard.write_bytes(b"placeholder")
    write_json(model_dir / "model.safetensors.index.json", {
        "weight_map": {"model.layers.0.mlp.up_proj.weight": shard.name}
    })

    monkeypatch.setattr(mod, "tensor_stack_available", lambda: True)

    def fake_delta(**kwargs):
        delta_path = kwargs["out_dir"] / "direct_delta.safetensors"
        delta_path.write_bytes(b"delta")
        return {
            "tensor_shape": [2, 2],
            "dtype": "float32",
            "original_tensor_hash": "orig",
            "delta_hash": "delta",
            "delta_norm": 1e-6,
            "relative_delta_norm": 1e-6,
            "delta_artifact_path": str(delta_path),
            "target_tensor_key": kwargs["target_tensor_key"],
            "source_shard_path": str(kwargs["source_shard_path"]),
            "selected_mechanism": kwargs["selected_mechanism"],
            "selected_module_family": kwargs["selected_module_family"],
            "delta_scale": kwargs["delta_scale"],
            "deterministic_seed_hash": kwargs["seed_hash"],
        }

    def fake_materialize(**kwargs):
        patched_dir = kwargs["patched_model_dir"]
        patched_dir.mkdir(parents=True, exist_ok=True)
        return str(patched_dir)

    monkeypatch.setattr(mod, "create_direct_delta_artifact", fake_delta)
    monkeypatch.setattr(mod, "materialize_patched_model_copy", fake_materialize)

    smoke = mod.write_smoke(
        write_selection_fixture(tmp_path),
        "smoke_007",
        tmp_path / "out",
        base_model_path=model_dir,
        target_tensor_key="model.layers.0.mlp.up_proj.weight",
        authorize_larql_direct_layer_edit_smoke=True,
        materialize_patched_model=True,
        authorize_patched_model_copy=True,
    )
    assert smoke["smoke_status"] == "completed_patched_model_copy"
    assert smoke["model_artifact_written"] is True
    for key in [
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
        assert smoke[key] is False


def test_bfloat16_audit_helpers_if_torch_available():
    torch = pytest.importorskip("torch")
    from local_harness.larql_direct_layer_edit_smoke import tensor_audit_hash, tensor_norm_float32

    tensor = torch.tensor([[1.0, -2.0], [3.0, 0.5]], dtype=torch.bfloat16)
    digest = tensor_audit_hash(tensor)
    norm = tensor_norm_float32(tensor)

    assert isinstance(digest, str)
    assert digest
    assert isinstance(norm, float)
