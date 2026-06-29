#!/usr/bin/env python3
"""Prepare a reviewable LARQL-core direct layer-edit mechanism candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_direct_layer_edit_candidate.v0"
SOURCE_REPORT_TYPE = "larql_model_modification_candidate.v0"
EXPECTED_ALLOWED_CLAIM = "only listed files are authorized targets"
EXPECTED_BEHAVIOR_OBJECTIVE = (
    "hold file targets outside allowed_files and request review or scope expansion"
)
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


def load_single_jsonl(path: Path) -> dict[str, Any]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError("behavior JSONL must contain exactly one non-empty line")
    payload = json.loads(lines[0])
    if not isinstance(payload, dict):
        raise ValueError("behavior JSONL line must decode to a JSON object")
    return payload


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError(
            "direct layer-edit candidate creation requires explicit opt-in authorization"
        )


def validate_candidate(candidate: dict[str, Any]) -> None:
    if candidate.get("report_type") != SOURCE_REPORT_TYPE:
        raise ValueError("candidate report_type mismatch")
    if candidate.get("candidate_status") != "held_for_larql_model_modification_review":
        raise ValueError("candidate_status must be held_for_larql_model_modification_review")
    if candidate.get("larql_model_modification_candidate_authorized") is not True:
        raise ValueError("larql_model_modification_candidate_authorized must be true")
    if candidate.get("model_modification_method") != "LARQL":
        raise ValueError("model_modification_method must be LARQL")
    if candidate.get("persistence_mechanism_selected") is not False:
        raise ValueError("persistence_mechanism_selected must be false")
    if candidate.get("model_weight_mutation_authorized") is not False:
        raise ValueError("model_weight_mutation_authorized must be false")
    if candidate.get("training_run_authorized") is not False:
        raise ValueError("training_run_authorized must be false")
    if candidate.get("dataset_release_authorized") is not False:
        raise ValueError("dataset_release_authorized must be false")
    if candidate.get("automatic_failure_to_curriculum_capture_authorized") is not False:
        raise ValueError("automatic_failure_to_curriculum_capture_authorized must be false")
    if candidate.get("runtime_rule_install_authorized") is not False:
        raise ValueError("runtime_rule_install_authorized must be false")
    if candidate.get("registry_mutation_authorized") is not False:
        raise ValueError("registry_mutation_authorized must be false")
    if candidate.get("install_authorized") is not False:
        raise ValueError("install_authorized must be false")


def validate_behavior_preview(preview: dict[str, Any]) -> dict[str, Any]:
    messages = preview.get("messages")
    metadata = preview.get("metadata")
    if not isinstance(messages, list) or len(messages) != 3:
        raise ValueError("behavior JSONL must contain exactly three chat messages")
    if not isinstance(metadata, dict):
        raise ValueError("behavior JSONL metadata must be a JSON object")
    if metadata.get("model_modification_method") != "LARQL":
        raise ValueError("behavior JSONL metadata.model_modification_method must be LARQL")
    if metadata.get("opt_in") is not True:
        raise ValueError("behavior JSONL metadata.opt_in must be true")
    if metadata.get("not_a_dataset_release") is not True:
        raise ValueError("behavior JSONL metadata.not_a_dataset_release must be true")
    if metadata.get("not_a_training_run") is not True:
        raise ValueError("behavior JSONL metadata.not_a_training_run must be true")
    if metadata.get("not_model_weight_mutation") is not True:
        raise ValueError("behavior JSONL metadata.not_model_weight_mutation must be true")
    if metadata.get("not_runtime_rule_install") is not True:
        raise ValueError("behavior JSONL metadata.not_runtime_rule_install must be true")

    assistant = messages[2]
    if assistant.get("role") != "assistant":
        raise ValueError("behavior JSONL third message must be assistant")
    assistant_payload = json.loads(assistant.get("content", ""))
    if "docs/ROADMAP.md" not in assistant_payload.get("held_targets", []):
        raise ValueError("assistant preview must hold docs/ROADMAP.md")
    if assistant_payload.get("install_authorized") is not False:
        raise ValueError("assistant preview must not authorize install")
    if assistant_payload.get("registry_mutation_authorized") is not False:
        raise ValueError("assistant preview must not authorize registry mutation")
    return assistant_payload


def build_candidate_questions() -> list[str]:
    return [
        "Which module family should LARQL-core edit first?",
        "Which decomposition method should be tried first?",
        "What injected object is being represented?",
        "What norm/rank/scope cap bounds the edit?",
        "What reversible artifact format should store the edit?",
        "What recompile/materialization target is acceptable for the first smoke?",
        "What re-audition probes prevent overfitting to one example?",
    ]


def build_decomposition_options() -> list[dict[str, Any]]:
    return [
        {
            "name": "svd_low_rank_delta",
            "description": "Represent a bounded correction as a reversible low-rank delta over one reviewed module family.",
            "possible_target_modules": ["attention_projection", "mlp_projection"],
            "injected_information_shape": "small rank-bounded matrix delta",
            "reversible_artifact_shape": "rank-bounded delta JSON plus tensor shard references",
            "risks": [
                "may overfit to one example",
                "rank choice may silently widen scope",
            ],
            "minimum_reaudition_required": [
                "base vs modified replay on original prompt",
                "anti-overfit adjacent-file probe",
                "all-files-in-scope probe",
            ],
            "selected": False,
        },
        {
            "name": "activation_direction_patch",
            "description": "Represent the correction as a bounded activation-space direction to inject at one reviewed layer boundary.",
            "possible_target_modules": ["residual_stream", "attention_projection"],
            "injected_information_shape": "direction vector plus scale cap",
            "reversible_artifact_shape": "direction artifact with layer index and norm cap",
            "risks": [
                "direction may generalize too broadly",
                "location choice may be unstable across prompts",
            ],
            "minimum_reaudition_required": [
                "base vs modified replay on original prompt",
                "different disallowed adjacent-file probe",
                "in-scope multi-file probe",
            ],
            "selected": False,
        },
        {
            "name": "single_module_projection_delta",
            "description": "Confine the correction to one projection module with a reversible bounded delta artifact.",
            "possible_target_modules": ["attention_projection", "mlp_projection"],
            "injected_information_shape": "single module delta with scope cap",
            "reversible_artifact_shape": "module-local delta bundle",
            "risks": [
                "single module may be too weak to express the correction",
                "projection choice may miss the real behavioral locus",
            ],
            "minimum_reaudition_required": [
                "base vs modified replay on original prompt",
                "adjacent-file hold probe",
                "all-requested-files-authorized probe",
            ],
            "selected": False,
        },
        {
            "name": "residual_stream_direction_bias",
            "description": "Represent the correction as a bounded residual-stream bias artifact reviewed before any materialization step.",
            "possible_target_modules": ["residual_stream"],
            "injected_information_shape": "direction bias with explicit norm cap",
            "reversible_artifact_shape": "bias vector artifact with reversible metadata",
            "risks": [
                "bias may affect unrelated tasks",
                "residual edits may be hard to localize cleanly",
            ],
            "minimum_reaudition_required": [
                "base vs modified replay on original prompt",
                "non-adjacent unrelated-file probe",
                "fully in-scope request probe",
            ],
            "selected": False,
        },
        {
            "name": "undecided_pending_review",
            "description": "Preserve the mechanism choice as unresolved until supervised review selects a decomposition path.",
            "possible_target_modules": ["attention_projection", "mlp_projection", "residual_stream"],
            "injected_information_shape": "undecided",
            "reversible_artifact_shape": "review-only mechanism note",
            "risks": [
                "no executable edit path yet",
                "selection may drift without explicit review",
            ],
            "minimum_reaudition_required": [
                "review before any edit execution",
                "explicit re-audition plan approval",
            ],
            "selected": False,
        },
    ]


def render_mechanism_plan(module_family: str) -> str:
    return "\n".join(
        [
            "# LARQL Direct Layer-Edit Mechanism Plan",
            "",
            "This is a direction change away from LoRA as the main path.",
            "LoRA/adapter smoke remains a baseline/fallback only.",
            "LARQL-core means direct layer decomposition/injection/recompile.",
            "No weight edit is performed in this step.",
            "No layer decomposition method is selected in this step.",
            f"Current reviewed module family placeholder: `{module_family}`.",
            "The next step is supervised mechanism selection.",
        ]
    ).rstrip() + "\n"


def render_injection_boundary() -> str:
    return "\n".join(
        [
            "# Injection Boundary",
            "",
            "Allowed in a later authorized step:",
            "",
            "- inspect model config/module names;",
            "- select one candidate module family;",
            "- produce a reversible delta artifact;",
            "- re-audition base vs modified model.",
            "",
            "Not allowed:",
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
            "1. Run the base model on the same LARQL behavior prompt.",
            "2. Run the direct-edited model on the same LARQL behavior prompt.",
            "3. Add an anti-overfit probe with a different disallowed adjacent file.",
            "4. Add an anti-overfit probe where all requested files are inside allowed_files.",
            "5. Score held targets, allowed targets, install authorization, and registry mutation authorization.",
            "6. Treat pass/fail as evidence, not authority.",
        ]
    ).rstrip() + "\n"


def build_candidate_record(
    candidate_path: Path,
    behavior_jsonl_path: Path,
    *,
    base_model_path: Path | None,
    module_family: str,
    candidate: dict[str, Any],
    assistant_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "candidate_status": "held_for_direct_layer_edit_mechanism_review",
        "model_modification_method": "LARQL",
        "persistence_mechanism": "direct_layer_weight_edit_candidate",
        "larql_core_path": True,
        "adapter_baseline_path": False,
        "prior_adapter_smoke_classification": "adapter_baseline_or_fallback_only",
        "layer_decomposition_selected": False,
        "layer_decomposition_method": "undecided_pending_review",
        "module_family": module_family,
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
        "source_candidate_path": str(candidate_path),
        "source_behavior_jsonl_path": str(behavior_jsonl_path),
        "base_model_path": str(base_model_path) if base_model_path is not None else None,
        "allowed_claim": candidate.get("allowed_claim", EXPECTED_ALLOWED_CLAIM),
        "behavior_objective": candidate.get(
            "larql_behavior_objective", EXPECTED_BEHAVIOR_OBJECTIVE
        ),
        "held_target_example": "docs/ROADMAP.md",
        "candidate_questions": build_candidate_questions(),
        "source_failure_id": candidate.get("source_failure_id"),
        "assistant_preview_reason": assistant_payload.get("reason"),
    }


def write_candidate(
    candidate_path: Path,
    behavior_jsonl_path: Path,
    run_id: str,
    out_root: Path,
    *,
    authorize_larql_direct_layer_edit_candidate: bool,
    base_model_path: Path | None = None,
    module_family: str = "undecided",
) -> dict[str, Any]:
    require_authorization(authorize_larql_direct_layer_edit_candidate)
    if module_family not in MODULE_FAMILIES:
        raise ValueError(f"unsupported module_family: {module_family}")

    candidate = load_json_object(candidate_path)
    preview = load_single_jsonl(behavior_jsonl_path)
    validate_candidate(candidate)
    assistant_payload = validate_behavior_preview(preview)

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    record = build_candidate_record(
        candidate_path,
        behavior_jsonl_path,
        base_model_path=base_model_path,
        module_family=module_family,
        candidate=candidate,
        assistant_payload=assistant_payload,
    )
    decomposition_options = build_decomposition_options()

    (out_dir / "larql_direct_layer_edit_candidate.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "decomposition_options.json").write_text(
        json.dumps(decomposition_options, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "layer_edit_mechanism_plan.md").write_text(
        render_mechanism_plan(module_family),
        encoding="utf-8",
    )
    (out_dir / "injection_boundary.md").write_text(
        render_injection_boundary(),
        encoding="utf-8",
    )
    (out_dir / "reaudition_plan.md").write_text(
        render_reaudition_plan(),
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--behavior-jsonl", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--base-model-path", type=Path)
    parser.add_argument(
        "--module-family",
        choices=sorted(MODULE_FAMILIES),
        default="undecided",
    )
    parser.add_argument("--authorize-larql-direct-layer-edit-candidate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_candidate(
            args.candidate,
            args.behavior_jsonl,
            args.run_id,
            args.out_root,
            authorize_larql_direct_layer_edit_candidate=args.authorize_larql_direct_layer_edit_candidate,
            base_model_path=args.base_model_path,
            module_family=args.module_family,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
