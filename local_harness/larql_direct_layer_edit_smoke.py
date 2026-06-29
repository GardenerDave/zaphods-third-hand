#!/usr/bin/env python3
"""Create a bounded LARQL-core direct layer-edit smoke artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_direct_layer_edit_smoke.v0"
SOURCE_REPORT_TYPE = "larql_layer_edit_mechanism_selection.v0"
CONCRETE_MECHANISMS = {
    "single_module_projection_delta",
    "svd_low_rank_delta",
    "activation_direction_patch",
    "residual_stream_direction_bias",
}
MODULE_FAMILIES = {
    "attention_projection",
    "mlp_projection",
    "residual_stream",
}


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL direct layer-edit smoke requires explicit opt-in authorization")


def validate_selection(selection: dict[str, Any]) -> None:
    if selection.get("report_type") != SOURCE_REPORT_TYPE:
        raise ValueError("mechanism selection report_type mismatch")
    if selection.get("selection_status") != "held_for_direct_layer_edit_smoke_review":
        raise ValueError("selection_status must be held_for_direct_layer_edit_smoke_review")
    if selection.get("model_modification_method") != "LARQL":
        raise ValueError("model_modification_method must be LARQL")
    if selection.get("persistence_mechanism") != "direct_layer_weight_edit_candidate":
        raise ValueError("persistence_mechanism must be direct_layer_weight_edit_candidate")
    if selection.get("larql_core_path") is not True:
        raise ValueError("larql_core_path must be true")
    if selection.get("adapter_baseline_path") is not False:
        raise ValueError("adapter_baseline_path must be false")
    if selection.get("selected_mechanism") not in CONCRETE_MECHANISMS:
        raise ValueError("selected_mechanism must be concrete")
    if selection.get("selected_module_family") not in MODULE_FAMILIES:
        raise ValueError("selected_module_family must be concrete")
    if selection.get("layer_decomposition_selected") is not True:
        raise ValueError("layer_decomposition_selected must be true")
    if selection.get("weight_edit_performed") is not False:
        raise ValueError("source selection weight_edit_performed must be false")
    if selection.get("model_artifact_written") is not False:
        raise ValueError("source selection model_artifact_written must be false")
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
        if selection.get(key) is not False:
            raise ValueError(f"{key} must be false")
    if selection.get("required_next_step") != "supervised_direct_layer_edit_smoke":
        raise ValueError("required_next_step must be supervised_direct_layer_edit_smoke")


def family_match(module_family: str, tensor_key: str) -> bool:
    if module_family == "mlp_projection":
        return any(part in tensor_key for part in [".mlp.down_proj.", ".mlp.gate_proj.", ".mlp.up_proj."])
    if module_family == "attention_projection":
        return any(part in tensor_key for part in [".self_attn.q_proj.", ".self_attn.k_proj.", ".self_attn.v_proj.", ".self_attn.o_proj."])
    if module_family == "residual_stream":
        return any(part in tensor_key for part in [".input_layernorm.", ".post_attention_layernorm.", ".norm."])
    return False


def read_index_keys(base_model_path: Path) -> tuple[dict[str, str], Path | None]:
    index_path = base_model_path / "model.safetensors.index.json"
    if not index_path.exists():
        return {}, None
    index = load_json_object(index_path)
    weight_map = index.get("weight_map", {})
    if not isinstance(weight_map, dict):
        return {}, index_path
    return {str(k): str(v) for k, v in weight_map.items()}, index_path


def inspect_target_tensor(
    selection: dict[str, Any],
    base_model_path: Path,
    target_tensor_key: str,
) -> dict[str, Any]:
    selection_inventory_path = selection.get("module_inventory_path")
    inventory_keys: set[str] = set()
    if selection_inventory_path and Path(selection_inventory_path).exists():
        inv = load_json_object(Path(selection_inventory_path))
        for group in [
            "candidate_attention_projection_keys",
            "candidate_mlp_projection_keys",
            "candidate_residual_stream_keys",
        ]:
            values = inv.get(group, [])
            if isinstance(values, list):
                inventory_keys.update(v for v in values if isinstance(v, str))

    weight_map, _ = read_index_keys(base_model_path)
    tensor_located = target_tensor_key in inventory_keys or target_tensor_key in weight_map
    matched_family = family_match(selection["selected_module_family"], target_tensor_key)
    source_shard = str(base_model_path / weight_map[target_tensor_key]) if target_tensor_key in weight_map else None
    return {
        "target_tensor_key": target_tensor_key,
        "selected_module_family": selection["selected_module_family"],
        "selected_mechanism": selection["selected_mechanism"],
        "tensor_located": tensor_located,
        "source_shard_path": source_shard,
        "matched_selected_module_family": matched_family,
    }


def deterministic_seed_hash(
    selection_path: Path,
    selection: dict[str, Any],
    target_tensor_key: str,
) -> str:
    seed_material = "\n".join(
        [
            str(selection_path),
            selection["selected_mechanism"],
            selection["selected_module_family"],
            target_tensor_key,
            selection.get("source_direct_layer_candidate_path", ""),
        ]
    )
    return hashlib.sha256(seed_material.encode("utf-8")).hexdigest()


def tensor_stack_available() -> bool:
    return importlib.util.find_spec("torch") is not None and importlib.util.find_spec("safetensors") is not None


def create_direct_delta_artifact(
    *,
    base_model_path: Path,
    target_tensor_key: str,
    source_shard_path: Path,
    selected_mechanism: str,
    selected_module_family: str,
    delta_scale: float,
    seed_hash: str,
    out_dir: Path,
) -> dict[str, Any]:
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    tensor_name = target_tensor_key
    with safe_open(str(source_shard_path), framework="pt", device="cpu") as handle:
        tensor = handle.get_tensor(tensor_name)
    delta = torch.zeros_like(tensor)
    if delta.numel() == 0:
        raise ValueError("target tensor is empty")
    flat = delta.view(-1)
    flat[0] = float(delta_scale)
    delta_path = out_dir / "direct_delta.safetensors"
    save_file({tensor_name: delta}, str(delta_path))

    original_hash = hashlib.sha256(tensor.cpu().numpy().tobytes()).hexdigest()
    delta_hash = hashlib.sha256(delta.cpu().numpy().tobytes()).hexdigest()
    delta_norm = float(torch.linalg.vector_norm(delta).item())
    original_norm = float(torch.linalg.vector_norm(tensor).item())
    relative_norm = float(delta_norm / original_norm) if original_norm else None
    return {
        "tensor_shape": list(tensor.shape),
        "dtype": str(tensor.dtype).replace("torch.", ""),
        "original_tensor_hash": original_hash,
        "delta_hash": delta_hash,
        "delta_norm": delta_norm,
        "relative_delta_norm": relative_norm,
        "delta_artifact_path": str(delta_path),
        "target_tensor_key": target_tensor_key,
        "source_shard_path": str(source_shard_path),
        "selected_mechanism": selected_mechanism,
        "selected_module_family": selected_module_family,
        "delta_scale": delta_scale,
        "deterministic_seed_hash": seed_hash,
    }


def safe_link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def materialize_patched_model_copy(
    *,
    base_model_path: Path,
    source_shard_path: Path,
    delta_artifact_path: Path,
    target_tensor_key: str,
    patched_model_dir: Path,
) -> str:
    import torch
    from safetensors import safe_open
    from safetensors.torch import load_file, save_file

    patched_model_dir.mkdir(parents=True, exist_ok=True)

    for name in [
        "config.json",
        "generation_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "tokenizer.model",
        "model.safetensors.index.json",
    ]:
        src = base_model_path / name
        if src.exists():
            safe_link_or_copy(src, patched_model_dir / name)

    for src in base_model_path.glob("*.safetensors"):
        if src.resolve() == source_shard_path.resolve():
            continue
        safe_link_or_copy(src, patched_model_dir / src.name)

    with safe_open(str(source_shard_path), framework="pt", device="cpu") as handle:
        target = handle.get_tensor(target_tensor_key)
        tensors = {key: handle.get_tensor(key) for key in handle.keys()}
    delta_tensors = load_file(str(delta_artifact_path))
    tensors[target_tensor_key] = target + delta_tensors[target_tensor_key]
    patched_shard_path = patched_model_dir / source_shard_path.name
    save_file(tensors, str(patched_shard_path))
    return str(patched_model_dir)


def render_reaudition_plan() -> str:
    return "\n".join(
        [
            "# Reaudition Plan",
            "",
            "1. Run the base model.",
            "2. Run the patched model.",
            "3. Use the same LARQL behavior prompt.",
            "4. Add an adjacent-file anti-overfit probe.",
            "5. Add an all-files-authorized anti-overfit probe.",
            "6. Add an unrelated task regression probe.",
            "7. Treat pass/fail as evidence, not authority.",
            "8. The first delta smoke is not expected to prove behavioral improvement by itself.",
        ]
    ).rstrip() + "\n"


def build_manifest_base(
    *,
    target_tensor_key: str,
    source_shard_path: str | None,
    selected_mechanism: str,
    selected_module_family: str,
    delta_scale: float,
    seed_hash: str,
) -> dict[str, Any]:
    return {
        "target_tensor_key": target_tensor_key,
        "source_shard": source_shard_path,
        "selected_mechanism": selected_mechanism,
        "selected_module_family": selected_module_family,
        "delta_scale": delta_scale,
        "deterministic_seed_hash": seed_hash,
        "tensor_shape": None,
        "dtype": None,
        "delta_artifact_path": None,
        "delta_norm": None,
        "relative_delta_norm": None,
        "original_tensor_hash": None,
        "delta_hash": None,
        "not_lora": True,
        "not_training": True,
        "not_adapter": True,
    }


def build_patch_bundle(
    *,
    base_model_path: Path,
    target_tensor_key: str,
    source_shard_path: str | None,
    direct_delta_path: str | None,
    patched_model_path: str | None,
) -> dict[str, Any]:
    return {
        "source_model_path": str(base_model_path),
        "target_tensor_key": target_tensor_key,
        "source_shard": source_shard_path,
        "direct_delta_artifact_path": direct_delta_path,
        "inverse_operation_description": "subtract the stored direct delta from the patched tensor or discard the patched copy and delta artifact",
        "patched_model_path": patched_model_path,
        "base_model_overwrite": False,
        "irreversible_patch": False,
        "audit_metadata": {
            "not_lora": True,
            "not_training": True,
            "not_adapter": True,
        },
        "reaudition_requirements": [
            "base model run",
            "patched model run",
            "same LARQL behavior prompt",
            "adjacent-file anti-overfit probe",
            "all-files-authorized anti-overfit probe",
            "unrelated task regression probe",
        ],
    }


def build_smoke_record(
    *,
    status: str,
    selection: dict[str, Any],
    base_model_path: Path,
    target_tensor_key: str,
    direct_delta_path: str | None,
    patched_model_path: str | None,
    patch_bundle_path: Path,
    direct_delta_artifact_written: bool,
    model_artifact_written: bool,
) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "smoke_status": status,
        "model_modification_method": "LARQL",
        "persistence_mechanism": "direct_layer_weight_edit",
        "selected_mechanism": selection["selected_mechanism"],
        "selected_module_family": selection["selected_module_family"],
        "target_tensor_key": target_tensor_key,
        "direct_delta_artifact_written": direct_delta_artifact_written,
        "weight_edit_performed": direct_delta_artifact_written,
        "model_artifact_written": model_artifact_written,
        "base_model_path": str(base_model_path),
        "patched_model_path": patched_model_path,
        "direct_delta_path": direct_delta_path,
        "reversible_patch_bundle_path": str(patch_bundle_path),
        "base_model_overwrite_authorized": False,
        "irreversible_patch_authorized": False,
        "adapter_merge_authorized": False,
        "production_deployment_authorized": False,
        "runtime_rule_install_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "dataset_release_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": "supervised_direct_layer_edit_reaudition",
    }


def write_smoke(
    mechanism_selection_path: Path,
    run_id: str,
    out_root: Path,
    *,
    base_model_path: Path,
    target_tensor_key: str,
    authorize_larql_direct_layer_edit_smoke: bool,
    delta_scale: float = 1e-6,
    materialize_patched_model: bool = False,
    authorize_patched_model_copy: bool = False,
) -> dict[str, Any]:
    require_authorization(authorize_larql_direct_layer_edit_smoke)
    selection = load_json_object(mechanism_selection_path)
    validate_selection(selection)

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    seed_hash = deterministic_seed_hash(mechanism_selection_path, selection, target_tensor_key)
    target_report = inspect_target_tensor(selection, base_model_path, target_tensor_key)
    source_shard_path = target_report["source_shard_path"]
    if not target_report["matched_selected_module_family"]:
        raise ValueError("target tensor key does not match selected module family")
    target_report_path = out_dir / "target_tensor_report.json"
    target_report_path.write_text(json.dumps(target_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = build_manifest_base(
        target_tensor_key=target_tensor_key,
        source_shard_path=source_shard_path,
        selected_mechanism=selection["selected_mechanism"],
        selected_module_family=selection["selected_module_family"],
        delta_scale=delta_scale,
        seed_hash=seed_hash,
    )
    patch_bundle_path = out_dir / "reversible_patch_bundle.json"
    manifest_path = out_dir / "direct_delta_manifest.json"

    status = "failed_direct_layer_edit_exception"
    direct_delta_path: str | None = None
    patched_model_path: str | None = None
    direct_delta_artifact_written = False
    model_artifact_written = False

    try:
        if not base_model_path.exists():
            status = "blocked_missing_base_model"
        elif not target_report["tensor_located"] or not source_shard_path:
            status = "blocked_target_tensor_not_found"
        elif not tensor_stack_available():
            status = "blocked_missing_tensor_stack"
        else:
            delta_info = create_direct_delta_artifact(
                base_model_path=base_model_path,
                target_tensor_key=target_tensor_key,
                source_shard_path=Path(source_shard_path),
                selected_mechanism=selection["selected_mechanism"],
                selected_module_family=selection["selected_module_family"],
                delta_scale=delta_scale,
                seed_hash=seed_hash,
                out_dir=out_dir,
            )
            manifest.update(delta_info)
            direct_delta_path = delta_info["delta_artifact_path"]
            direct_delta_artifact_written = True
            status = "completed_direct_delta_artifact"

            if materialize_patched_model:
                if not authorize_patched_model_copy:
                    status = "blocked_patched_model_copy_not_authorized"
                else:
                    patched_model_path = materialize_patched_model_copy(
                        base_model_path=base_model_path,
                        source_shard_path=Path(source_shard_path),
                        delta_artifact_path=Path(direct_delta_path),
                        target_tensor_key=target_tensor_key,
                        patched_model_dir=out_dir / "patched_model",
                    )
                    model_artifact_written = True
                    status = "completed_patched_model_copy"
    except Exception as exc:
        manifest["exception"] = f"{type(exc).__name__}: {exc}"
        status = "failed_direct_layer_edit_exception"

    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    patch_bundle = build_patch_bundle(
        base_model_path=base_model_path,
        target_tensor_key=target_tensor_key,
        source_shard_path=source_shard_path,
        direct_delta_path=direct_delta_path,
        patched_model_path=patched_model_path,
    )
    patch_bundle_path.write_text(json.dumps(patch_bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "reaudition_plan.md").write_text(render_reaudition_plan(), encoding="utf-8")

    smoke = build_smoke_record(
        status=status,
        selection=selection,
        base_model_path=base_model_path,
        target_tensor_key=target_tensor_key,
        direct_delta_path=direct_delta_path,
        patched_model_path=patched_model_path,
        patch_bundle_path=patch_bundle_path,
        direct_delta_artifact_written=direct_delta_artifact_written,
        model_artifact_written=model_artifact_written,
    )
    (out_dir / "larql_direct_layer_edit_smoke.json").write_text(
        json.dumps(smoke, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return smoke


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanism-selection", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--base-model-path", required=True, type=Path)
    parser.add_argument("--target-tensor-key", required=True)
    parser.add_argument("--delta-scale", type=float, default=1e-6)
    parser.add_argument("--materialize-patched-model", action="store_true")
    parser.add_argument("--authorize-patched-model-copy", action="store_true")
    parser.add_argument("--authorize-larql-direct-layer-edit-smoke", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_smoke(
            args.mechanism_selection,
            args.run_id,
            args.out_root,
            base_model_path=args.base_model_path,
            target_tensor_key=args.target_tensor_key,
            authorize_larql_direct_layer_edit_smoke=args.authorize_larql_direct_layer_edit_smoke,
            delta_scale=args.delta_scale,
            materialize_patched_model=args.materialize_patched_model,
            authorize_patched_model_copy=args.authorize_patched_model_copy,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
