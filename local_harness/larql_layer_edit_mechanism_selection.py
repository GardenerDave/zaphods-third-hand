#!/usr/bin/env python3
"""Prepare a held LARQL-core layer-edit mechanism selection artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_layer_edit_mechanism_selection.v0"
SOURCE_REPORT_TYPE = "larql_direct_layer_edit_candidate.v0"
MECHANISMS = {
    "single_module_projection_delta",
    "svd_low_rank_delta",
    "activation_direction_patch",
    "residual_stream_direction_bias",
    "undecided_pending_review",
}
MODULE_FAMILIES = {
    "attention_projection",
    "mlp_projection",
    "residual_stream",
    "undecided",
}


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError(
            "LARQL layer-edit mechanism selection requires explicit opt-in authorization"
        )


def validate_direct_layer_candidate(candidate: dict[str, Any]) -> None:
    if candidate.get("report_type") != SOURCE_REPORT_TYPE:
        raise ValueError("direct layer candidate report_type mismatch")
    if candidate.get("candidate_status") != "held_for_direct_layer_edit_mechanism_review":
        raise ValueError("candidate_status must be held_for_direct_layer_edit_mechanism_review")
    if candidate.get("model_modification_method") != "LARQL":
        raise ValueError("model_modification_method must be LARQL")
    if candidate.get("persistence_mechanism") != "direct_layer_weight_edit_candidate":
        raise ValueError("persistence_mechanism must be direct_layer_weight_edit_candidate")
    if candidate.get("larql_core_path") is not True:
        raise ValueError("larql_core_path must be true")
    if candidate.get("adapter_baseline_path") is not False:
        raise ValueError("adapter_baseline_path must be false")
    if candidate.get("prior_adapter_smoke_classification") != "adapter_baseline_or_fallback_only":
        raise ValueError("prior_adapter_smoke_classification mismatch")
    if candidate.get("layer_decomposition_selected") is not False:
        raise ValueError("layer_decomposition_selected must be false")
    if candidate.get("layer_decomposition_method") != "undecided_pending_review":
        raise ValueError("layer_decomposition_method must be undecided_pending_review")
    if candidate.get("weight_edit_performed") is not False:
        raise ValueError("weight_edit_performed must be false")
    if candidate.get("model_artifact_written") is not False:
        raise ValueError("model_artifact_written must be false")
    for key in [
        "base_model_overwrite_authorized",
        "adapter_merge_authorized",
        "production_deployment_authorized",
        "runtime_rule_install_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "dataset_release_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        if candidate.get(key) is not False:
            raise ValueError(f"{key} must be false")
    if candidate.get("required_next_step") != "supervised_layer_edit_mechanism_selection":
        raise ValueError("required_next_step must be supervised_layer_edit_mechanism_selection")


def inspect_base_model(base_model_path: Path | None) -> dict[str, Any]:
    inventory: dict[str, Any] = {
        "base_model_path": str(base_model_path) if base_model_path is not None else None,
        "base_model_path_exists": False,
        "config_json_exists": False,
        "model_safetensors_index_exists": False,
        "model_type": None,
        "num_hidden_layers": None,
        "candidate_attention_projection_keys": [],
        "candidate_mlp_projection_keys": [],
        "candidate_residual_stream_keys": [],
        "inspection_status": "base_model_not_provided",
    }
    if base_model_path is None:
        return inventory

    inventory["base_model_path_exists"] = base_model_path.exists()
    if not base_model_path.exists():
        inventory["inspection_status"] = "base_model_path_missing"
        return inventory

    config_path = base_model_path / "config.json"
    index_path = base_model_path / "model.safetensors.index.json"
    inventory["config_json_exists"] = config_path.exists()
    inventory["model_safetensors_index_exists"] = index_path.exists()

    if config_path.exists():
        try:
            config = load_json_object(config_path)
            inventory["model_type"] = config.get("model_type")
            inventory["num_hidden_layers"] = config.get("num_hidden_layers")
        except Exception:
            inventory["inspection_status"] = "config_read_error"
            return inventory

    if index_path.exists():
        try:
            index = load_json_object(index_path)
            weight_map = index.get("weight_map", {})
            if isinstance(weight_map, dict):
                keys = sorted(weight_map.keys())
                inventory["candidate_attention_projection_keys"] = [
                    key for key in keys if any(part in key for part in [".q_proj", ".k_proj", ".v_proj", ".o_proj"])
                ]
                inventory["candidate_mlp_projection_keys"] = [
                    key for key in keys if any(part in key for part in [".gate_proj", ".up_proj", ".down_proj"])
                ]
                inventory["candidate_residual_stream_keys"] = [
                    key for key in keys if any(part in key for part in [".input_layernorm", ".post_attention_layernorm", ".norm"])
                ]
        except Exception:
            inventory["inspection_status"] = "index_read_error"
            return inventory

    inventory["inspection_status"] = "inspected"
    return inventory


def build_selection_rationale(selected_mechanism: str) -> list[str]:
    if selected_mechanism == "single_module_projection_delta":
        return [
            "first smoke is bounded to one module family",
            "direct reversible patch artifact is preferred over adapter training",
            "this is not LoRA",
            "no weights are edited in this step",
        ]
    if selected_mechanism == "svd_low_rank_delta":
        return [
            "low-rank describes the direct delta representation",
            "this is not PEFT/LoRA training",
            "no adapter is trained or merged",
            "no weights are edited in this step",
        ]
    if selected_mechanism == "activation_direction_patch":
        return [
            "activation-space patch remains bounded to a reviewed mechanism candidate",
            "this is not adapter training",
            "no weights are edited in this step",
        ]
    if selected_mechanism == "residual_stream_direction_bias":
        return [
            "residual-stream bias remains a direct reversible patch candidate",
            "this is not adapter training",
            "no weights are edited in this step",
        ]
    return [
        "mechanism remains held pending supervised review",
        "no weights are edited in this step",
        "no concrete decomposition path is selected yet",
    ]


def build_selection_record(
    direct_layer_candidate_path: Path,
    module_inventory_path: Path,
    reversible_patch_format_path: Path,
    *,
    base_model_path: Path | None,
    selected_mechanism: str,
    selected_module_family: str,
) -> dict[str, Any]:
    concrete = selected_mechanism != "undecided_pending_review"
    return {
        "report_type": REPORT_TYPE,
        "selection_status": "held_for_direct_layer_edit_smoke_review",
        "model_modification_method": "LARQL",
        "persistence_mechanism": "direct_layer_weight_edit_candidate",
        "larql_core_path": True,
        "adapter_baseline_path": False,
        "selected_mechanism": selected_mechanism,
        "selected_module_family": selected_module_family,
        "layer_decomposition_selected": concrete,
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
        "source_direct_layer_candidate_path": str(direct_layer_candidate_path),
        "base_model_path": str(base_model_path) if base_model_path is not None else None,
        "module_inventory_path": str(module_inventory_path),
        "reversible_patch_format_path": str(reversible_patch_format_path),
        "selection_rationale": build_selection_rationale(selected_mechanism),
        "blocked_authorities": [
            "base_model_overwrite",
            "irreversible_patch",
            "adapter_merge",
            "production_deployment",
            "runtime_rule_install",
            "registry_mutation",
            "install_authorization",
            "dataset_release",
            "automatic_failure_to_curriculum_capture",
        ],
    }


def render_selected_mechanism_plan(selected_mechanism: str, selected_module_family: str) -> str:
    return "\n".join(
        [
            "# Selected Mechanism Plan",
            "",
            "LARQL-core direct layer edit remains the main path.",
            "Adapter/LoRA remains fallback only.",
            f"This step selects or holds the mechanism for review: `{selected_mechanism}`.",
            f"Selected module family placeholder: `{selected_module_family}`.",
            "No weight edit occurred.",
            "No model artifact was written.",
            "Next step is supervised direct layer-edit smoke.",
        ]
    ).rstrip() + "\n"


def render_reversible_patch_format(selected_mechanism: str, selected_module_family: str) -> str:
    bundle = {
        "source_model_identity_or_path": "<to be recorded in a later authorized step>",
        "selected_module_family": selected_module_family,
        "selected_mechanism": selected_mechanism,
        "target_tensor_keys": [],
        "delta_tensor_references": [],
        "norm_cap": "<pending review>",
        "rank_cap": "<pending review>",
        "inverse_revert_metadata": {
            "revert_supported": True,
            "inverse_artifact_required": True,
        },
        "audit_metadata": {
            "larql_core_path": True,
            "adapter_baseline_path": False,
            "weight_edit_performed": False,
        },
        "reaudition_requirements": [
            "base model replay",
            "direct-edited model replay",
            "adjacent-file anti-overfit probe",
            "all-files-authorized anti-overfit probe",
            "unrelated task regression probe",
        ],
    }
    return "# Reversible Patch Format\n\n```json\n" + json.dumps(bundle, indent=2) + "\n```\n"


def render_layer_edit_boundary() -> str:
    return "\n".join(
        [
            "# Layer Edit Boundary",
            "",
            "Forbidden in this stage:",
            "",
            "- base model overwrite;",
            "- irreversible patch;",
            "- adapter merge;",
            "- production deployment;",
            "- registry mutation;",
            "- install authorization;",
            "- dataset release;",
            "- automatic failure-to-curriculum capture.",
        ]
    ).rstrip() + "\n"


def render_reaudition_plan() -> str:
    return "\n".join(
        [
            "# Reaudition Plan",
            "",
            "1. Run the base model test.",
            "2. Run the direct-edited model test.",
            "3. Reuse the same LARQL behavior prompt.",
            "4. Add an adjacent-file anti-overfit probe.",
            "5. Add an all-files-authorized anti-overfit probe.",
            "6. Add an unrelated task regression probe.",
            "7. Treat pass/fail as evidence, not authority.",
        ]
    ).rstrip() + "\n"


def write_selection(
    direct_layer_candidate_path: Path,
    run_id: str,
    out_root: Path,
    *,
    authorize_larql_layer_edit_mechanism_selection: bool,
    base_model_path: Path | None = None,
    select_mechanism: str = "undecided_pending_review",
    select_module_family: str = "undecided",
) -> dict[str, Any]:
    require_authorization(authorize_larql_layer_edit_mechanism_selection)
    if select_mechanism not in MECHANISMS:
        raise ValueError(f"unsupported selected mechanism: {select_mechanism}")
    if select_module_family not in MODULE_FAMILIES:
        raise ValueError(f"unsupported selected module family: {select_module_family}")

    candidate = load_json_object(direct_layer_candidate_path)
    validate_direct_layer_candidate(candidate)

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory = inspect_base_model(base_model_path)
    module_inventory_path = out_dir / "module_inventory.json"
    module_inventory_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    reversible_patch_format_path = out_dir / "reversible_patch_format.md"
    reversible_patch_format_path.write_text(
        render_reversible_patch_format(select_mechanism, select_module_family),
        encoding="utf-8",
    )

    record = build_selection_record(
        direct_layer_candidate_path,
        module_inventory_path,
        reversible_patch_format_path,
        base_model_path=base_model_path,
        selected_mechanism=select_mechanism,
        selected_module_family=select_module_family,
    )
    (out_dir / "larql_layer_edit_mechanism_selection.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "selected_mechanism_plan.md").write_text(
        render_selected_mechanism_plan(select_mechanism, select_module_family),
        encoding="utf-8",
    )
    (out_dir / "layer_edit_boundary.md").write_text(
        render_layer_edit_boundary(),
        encoding="utf-8",
    )
    (out_dir / "reaudition_plan.md").write_text(
        render_reaudition_plan(),
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direct-layer-candidate", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--base-model-path", type=Path)
    parser.add_argument(
        "--select-mechanism",
        choices=sorted(MECHANISMS),
        default="undecided_pending_review",
    )
    parser.add_argument(
        "--select-module-family",
        choices=sorted(MODULE_FAMILIES),
        default="undecided",
    )
    parser.add_argument("--authorize-larql-layer-edit-mechanism-selection", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_selection(
            args.direct_layer_candidate,
            args.run_id,
            args.out_root,
            authorize_larql_layer_edit_mechanism_selection=args.authorize_larql_layer_edit_mechanism_selection,
            base_model_path=args.base_model_path,
            select_mechanism=args.select_mechanism,
            select_module_family=args.select_module_family,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
