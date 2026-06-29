#!/usr/bin/env python3
"""Prepare an explicit opt-in LARQL weight-persistence smoke."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_weight_persistence_smoke.v0"
CANDIDATE_REPORT_TYPE = "larql_model_modification_candidate.v0"
EXPECTED_ALLOWED_CLAIM = "only listed files are authorized targets"


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
        raise ValueError("LARQL weight-persistence smoke requires explicit opt-in authorization")


def validate_candidate(candidate: dict[str, Any]) -> None:
    if candidate.get("report_type") != CANDIDATE_REPORT_TYPE:
        raise ValueError("candidate report_type mismatch")
    if candidate.get("candidate_status") != "held_for_larql_model_modification_review":
        raise ValueError("candidate_status must be held_for_larql_model_modification_review")
    if candidate.get("larql_model_modification_candidate_authorized") is not True:
        raise ValueError("larql_model_modification_candidate_authorized must be true")
    if candidate.get("model_modification_method") != "LARQL":
        raise ValueError("model_modification_method must be LARQL")
    if candidate.get("persistence_mechanism_selected") is not False:
        raise ValueError("persistence_mechanism_selected must be false")
    if candidate.get("persistence_mechanism") != "unspecified_pending_review":
        raise ValueError("persistence_mechanism must be unspecified_pending_review")
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
        raise ValueError("behavior preview must contain exactly three chat messages")
    if not isinstance(metadata, dict):
        raise ValueError("behavior preview metadata must be a JSON object")
    if metadata.get("model_modification_method") != "LARQL":
        raise ValueError("behavior preview metadata.model_modification_method must be LARQL")
    if metadata.get("opt_in") is not True:
        raise ValueError("behavior preview metadata.opt_in must be true")
    if metadata.get("not_a_dataset_release") is not True:
        raise ValueError("behavior preview metadata.not_a_dataset_release must be true")
    if metadata.get("not_a_training_run") is not True:
        raise ValueError("behavior preview metadata.not_a_training_run must be true")
    if metadata.get("not_model_weight_mutation") is not True:
        raise ValueError("behavior preview metadata.not_model_weight_mutation must be true")
    assistant = messages[2]
    if assistant.get("role") != "assistant":
        raise ValueError("behavior preview third message must be assistant")
    assistant_payload = json.loads(assistant.get("content", ""))
    if "docs/ROADMAP.md" not in assistant_payload.get("held_targets", []):
        raise ValueError("assistant preview must hold docs/ROADMAP.md")
    if assistant_payload.get("install_authorized") is not False:
        raise ValueError("assistant preview must not authorize install")
    if assistant_payload.get("registry_mutation_authorized") is not False:
        raise ValueError("assistant preview must not authorize registry mutation")
    return assistant_payload


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def build_training_stack_preflight(base_model_path: Path | None) -> dict[str, Any]:
    preflight = {
        "torch_available": module_available("torch"),
        "transformers_available": module_available("transformers"),
        "datasets_available": module_available("datasets"),
        "peft_available": module_available("peft"),
        "trl_available": module_available("trl"),
        "base_model_path_provided": base_model_path is not None,
        "base_model_path_exists": False,
        "base_model_config_exists": False,
    }
    if base_model_path is not None:
        preflight["base_model_path_exists"] = base_model_path.exists()
        preflight["base_model_config_exists"] = (base_model_path / "config.json").exists()
    return preflight


def build_training_input(preview: dict[str, Any]) -> str:
    return json.dumps(preview, sort_keys=True) + "\n"


def render_handoff(preflight: dict[str, Any], training_run_requested: bool) -> str:
    next_command = (
        "python3 local_harness/larql_weight_persistence_smoke.py "
        "--candidate <candidate.json> "
        "--behavior-jsonl <larql_behavior_example_preview.jsonl> "
        "--run-id <run_id> "
        "--out-root .work/larql_weight_persistence_smokes "
        "--base-model-path <base_model_dir> "
        "--authorize-larql-weight-persistence-smoke "
        "--run-training"
    )
    status_line = (
        "Training stack preflight is ready for an explicit training run."
        if preflight["torch_available"]
        and preflight["transformers_available"]
        and preflight["datasets_available"]
        and preflight["peft_available"]
        else "Training stack preflight is blocked until the required local stack is available."
    )
    return "\n".join(
        [
            "# LARQL Weight-Persistence Handoff",
            "",
            "LARQL is the behavioral modification method.",
            "Adapter/weight-delta is the selected smoke persistence mechanism.",
            "This is explicitly opt-in.",
            "This is one example only.",
            "This is not a dataset release.",
            "This is not production training.",
            "Base model overwrite is not authorized.",
            "Adapter merge is not authorized.",
            "Deployment is not authorized.",
            "Success requires re-audition.",
            "",
            status_line,
            f"Training run requested in this invocation: `{str(training_run_requested).lower()}`",
            "",
            "Next command if a valid base model path and training stack are available:",
            "",
            f"`{next_command}`",
        ]
    ).rstrip() + "\n"


def render_reaudition_plan() -> str:
    return "\n".join(
        [
            "# Reaudition Plan",
            "",
            "1. Run the base model on the same messy allowed_files prompt.",
            "2. Run the adapter/modified model on the same messy allowed_files prompt.",
            "3. Reuse the same strict scorer used by the live replay where practical.",
            "4. Compare base vs modified behavior on allowed targets, held targets, install authorization, and registry mutation authorization.",
            "5. Treat pass/fail as evidence, not authority.",
        ]
    ).rstrip() + "\n"


def build_smoke_record(
    candidate_path: Path,
    behavior_jsonl_path: Path,
    out_dir: Path,
    *,
    training_run_requested: bool,
    training_run_performed: bool,
    base_model_path: Path | None,
    adapter_artifact: str | None,
) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "smoke_status": "held_for_training_environment_or_reaudition",
        "model_modification_method": "LARQL",
        "persistence_mechanism": "adapter_weight_delta_smoke",
        "persistence_mechanism_selected": True,
        "persistence_mechanism_selection_scope": "single smoke run only",
        "source_candidate_path": str(candidate_path),
        "source_behavior_jsonl_path": str(behavior_jsonl_path),
        "training_input_path": str(out_dir / "training_input.jsonl"),
        "training_run_requested": training_run_requested,
        "training_run_performed": training_run_performed,
        "base_model_path": str(base_model_path) if base_model_path is not None else None,
        "adapter_or_weight_delta_artifact": adapter_artifact,
        "required_next_step": "supervised_weight_persistence_reaudition",
        "runtime_rule_install_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "dataset_release_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "base_model_overwrite_authorized": False,
        "adapter_merge_authorized": False,
        "production_deployment_authorized": False,
    }


def maybe_write_training_run_summary(
    out_dir: Path,
    preflight: dict[str, Any],
    *,
    run_training: bool,
    base_model_path: Path | None,
) -> tuple[bool, str | None]:
    if not run_training:
        return False, None

    summary: dict[str, Any]
    if base_model_path is None or not preflight["base_model_path_exists"] or not preflight["base_model_config_exists"]:
        summary = {
            "status": "blocked_missing_base_model",
            "training_run_performed": False,
        }
    elif not (
        preflight["torch_available"]
        and preflight["transformers_available"]
        and preflight["datasets_available"]
        and preflight["peft_available"]
    ):
        summary = {
            "status": "blocked_missing_training_stack",
            "training_run_performed": False,
        }
    else:
        summary = {
            "status": "ready_but_not_executed_in_this_repo_smoke",
            "training_run_performed": False,
            "note": "Training execution path is intentionally left minimal and unperformed in this environment unless a local stack and base model are both available and explicitly wired.",
        }
    (out_dir / "training_run_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return False, None


def write_smoke(
    candidate_path: Path,
    behavior_jsonl_path: Path,
    run_id: str,
    out_root: Path,
    *,
    authorize_larql_weight_persistence_smoke: bool,
    base_model_path: Path | None = None,
    run_training: bool = False,
) -> dict[str, Any]:
    require_authorization(authorize_larql_weight_persistence_smoke)
    candidate = load_json_object(candidate_path)
    preview = load_single_jsonl(behavior_jsonl_path)
    validate_candidate(candidate)
    validate_behavior_preview(preview)

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    training_input = build_training_input(preview)
    (out_dir / "training_input.jsonl").write_text(training_input, encoding="utf-8")

    preflight = build_training_stack_preflight(base_model_path)
    (out_dir / "training_stack_preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    training_run_performed, adapter_artifact = maybe_write_training_run_summary(
        out_dir, preflight, run_training=run_training, base_model_path=base_model_path
    )

    smoke = build_smoke_record(
        candidate_path,
        behavior_jsonl_path,
        out_dir,
        training_run_requested=run_training,
        training_run_performed=training_run_performed,
        base_model_path=base_model_path,
        adapter_artifact=adapter_artifact,
    )

    (out_dir / "larql_weight_persistence_smoke.json").write_text(
        json.dumps(smoke, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "weight_persistence_handoff.md").write_text(
        render_handoff(preflight, run_training),
        encoding="utf-8",
    )
    (out_dir / "reaudition_plan.md").write_text(render_reaudition_plan(), encoding="utf-8")
    return smoke


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--behavior-jsonl", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--base-model-path", type=Path)
    parser.add_argument("--run-training", action="store_true")
    parser.add_argument("--authorize-larql-weight-persistence-smoke", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_smoke(
            args.candidate,
            args.behavior_jsonl,
            args.run_id,
            args.out_root,
            authorize_larql_weight_persistence_smoke=args.authorize_larql_weight_persistence_smoke,
            base_model_path=args.base_model_path,
            run_training=args.run_training,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
