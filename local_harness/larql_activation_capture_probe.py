#!/usr/bin/env python3
"""Prepare an authorized LARQL activation capture probe packet."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_activation_capture_probe.v0"
SOURCE_REPORT_TYPE = "larql_correction_delta_plan.v0"
REQUIRED_NEXT_STEP = "supervised_activation_capture_review"


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError(
            "LARQL activation capture probe requires explicit opt-in authorization"
        )


def inference_stack_available() -> bool:
    return importlib.util.find_spec("torch") is not None and importlib.util.find_spec("transformers") is not None


def normalize_module_name(target_module: str) -> str:
    return target_module[:-7] if target_module.endswith(".weight") else target_module


def validate_correction_delta_plan(plan: dict[str, Any]) -> None:
    if plan.get("report_type") != SOURCE_REPORT_TYPE:
        raise ValueError("source correction delta plan report_type mismatch")
    if plan.get("planning_authorized") is not True:
        raise ValueError("source correction delta plan must be authorized")
    if plan.get("required_next_step") != "supervised_correction_delta_plan_review":
        raise ValueError("source correction delta plan required_next_step mismatch")
    if plan.get("larql_core_path") is not True:
        raise ValueError("source correction delta plan must keep larql_core_path true")
    if plan.get("adapter_baseline_path") is not False:
        raise ValueError("source correction delta plan must keep adapter_baseline_path false")
    for key in [
        "promotion_authorized",
        "base_model_overwrite_authorized",
        "production_deployment_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        if plan.get(key) is not False:
            raise ValueError(f"{key} must be false in source correction delta plan")


def load_probe_pairs(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        raise ValueError("probe pairs path is required")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected JSON array")
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"{path}: expected JSON object entries")
    return payload


def _scalar_summary(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("values must be non-empty")
    count = len(values)
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / count
    norm = math.sqrt(sum(value * value for value in values))
    return {
        "norm": norm,
        "mean": mean,
        "std": math.sqrt(variance),
        "abs_max": max(abs(value) for value in values),
    }


def summarize_prompt_side_vectors(
    tensor_data: Any,
    *,
    dtype: str = "mock_float",
) -> dict[str, Any]:
    if not isinstance(tensor_data, list) or not tensor_data:
        raise ValueError("tensor_data must be a non-empty list")

    if isinstance(tensor_data[0], list):
        if tensor_data and isinstance(tensor_data[0], list) and tensor_data[0] and isinstance(tensor_data[0][0], list):
            batch = tensor_data
            batch_size = len(batch)
            seq_len = len(batch[0])
            hidden_size = len(batch[0][0])
            last_token_values = list(batch[0][-1])
            mean_pool_values = [
                sum(batch[0][seq_idx][hidden_idx] for seq_idx in range(seq_len)) / seq_len
                for hidden_idx in range(hidden_size)
            ]
            shape = [batch_size, seq_len, hidden_size]
            prompt_sequence_length = seq_len
        else:
            batch = tensor_data
            batch_size = len(batch)
            hidden_size = len(batch[0])
            last_token_values = list(batch[0])
            mean_pool_values = list(batch[0])
            shape = [batch_size, hidden_size]
            prompt_sequence_length = 1
    else:
        hidden_size = len(tensor_data)
        last_token_values = list(tensor_data)
        mean_pool_values = list(tensor_data)
        shape = [hidden_size]
        prompt_sequence_length = 1

    last_stats = _scalar_summary([float(value) for value in last_token_values])
    mean_stats = _scalar_summary([float(value) for value in mean_pool_values])
    full_stats = _scalar_summary([float(value) for value in last_token_values])
    return {
        "activation_shape": shape,
        "activation_dtype": dtype,
        "activation_norm": full_stats["norm"],
        "activation_mean": full_stats["mean"],
        "activation_std": full_stats["std"],
        "activation_abs_max": full_stats["abs_max"],
        "prompt_sequence_length": prompt_sequence_length,
        "prompt_last_token_norm": last_stats["norm"],
        "prompt_last_token_mean": last_stats["mean"],
        "prompt_last_token_std": last_stats["std"],
        "prompt_last_token_abs_max": last_stats["abs_max"],
        "prompt_mean_pool_norm": mean_stats["norm"],
        "prompt_mean_pool_mean": mean_stats["mean"],
        "prompt_mean_pool_std": mean_stats["std"],
        "prompt_mean_pool_abs_max": mean_stats["abs_max"],
    }


def cosine_similarity(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    dot = sum(x * y for x, y in zip(a, b))
    a_norm = math.sqrt(sum(x * x for x in a))
    b_norm = math.sqrt(sum(y * y for y in b))
    if a_norm == 0.0 or b_norm == 0.0:
        return None
    return dot / (a_norm * b_norm)


def compare_probe_pair(failure: dict[str, Any], correction: dict[str, Any]) -> dict[str, Any]:
    last_cos = None
    mean_cos = None
    if isinstance(failure.get("_prompt_last_token_vector"), list) and isinstance(correction.get("_prompt_last_token_vector"), list):
        last_cos = cosine_similarity(
            [float(v) for v in failure["_prompt_last_token_vector"]],
            [float(v) for v in correction["_prompt_last_token_vector"]],
        )
    if isinstance(failure.get("_prompt_mean_pool_vector"), list) and isinstance(correction.get("_prompt_mean_pool_vector"), list):
        mean_cos = cosine_similarity(
            [float(v) for v in failure["_prompt_mean_pool_vector"]],
            [float(v) for v in correction["_prompt_mean_pool_vector"]],
        )

    prompt_side_ok = bool(failure.get("prompt_side_activation_captured")) and bool(correction.get("prompt_side_activation_captured"))
    evidence_quality = "failed_prompt_capture"
    if prompt_side_ok:
        if last_cos is not None or mean_cos is not None:
            evidence_quality = "usable_prompt_signal"
        else:
            evidence_quality = "unclear_prompt_signal"
    return {
        "probe_id": failure["probe_id"],
        "prompt_last_token_norm_difference": abs(float(correction["prompt_last_token_norm"]) - float(failure["prompt_last_token_norm"])),
        "prompt_last_token_cosine_similarity": last_cos,
        "prompt_mean_pool_norm_difference": abs(float(correction["prompt_mean_pool_norm"]) - float(failure["prompt_mean_pool_norm"])),
        "prompt_mean_pool_cosine_similarity": mean_cos,
        "prompt_sequence_length_difference": abs(int(correction["prompt_sequence_length"]) - int(failure["prompt_sequence_length"])),
        "evidence_quality": evidence_quality,
    }


def classify_prompt_signal(per_probe: list[dict[str, Any]]) -> dict[str, Any]:
    usable = sum(1 for item in per_probe if item.get("evidence_quality") == "usable_prompt_signal")
    unclear = sum(1 for item in per_probe if item.get("evidence_quality") == "unclear_prompt_signal")
    failed = sum(1 for item in per_probe if item.get("evidence_quality") == "failed_prompt_capture")
    if usable > 0:
        status = "prompt_signal_detected"
    elif unclear > 0:
        status = "prompt_signal_unclear"
    else:
        status = "prompt_capture_failed"
    return {
        "usable_prompt_signal_count": usable,
        "unclear_prompt_signal_count": unclear,
        "failed_prompt_capture_count": failed,
        "selected_candidate_direction_status": status,
    }


def build_activation_capture_plan(
    *,
    selected_method: str,
    probe_pairs: list[dict[str, Any]],
    target_module: str,
    target_layer: str,
    target_module_family: str,
) -> dict[str, Any]:
    return {
        "selected_method": selected_method,
        "probe_ids": [pair["probe_id"] for pair in probe_pairs],
        "failure_correction_pair_count": len(probe_pairs),
        "target_module": target_module,
        "target_layer": target_layer,
        "target_module_family": target_module_family,
        "intended_capture_point": normalize_module_name(target_module),
        "default_capture_mode": "prompt_forward",
        "available_capture_modes": ["prompt_forward", "generation_step"],
        "generation_output_role": "audit_text_only",
        "delta_evidence_source": "prompt_side_activation",
        "model_inference_authorization_required": True,
        "weight_mutation_authorized": False,
        "delta_artifact_authorized": False,
    }


def summarize_activation_stats(values: list[float], *, dtype: str = "mock_float") -> dict[str, Any]:
    if not values:
        raise ValueError("activation values must be non-empty")
    n = len(values)
    mean = sum(values) / n
    variance = sum((value - mean) ** 2 for value in values) / n
    norm = math.sqrt(sum(value * value for value in values))
    return {
        "activation_shape": [n],
        "activation_dtype": dtype,
        "activation_norm": norm,
        "activation_mean": mean,
        "activation_std": math.sqrt(variance),
        "activation_abs_max": max(abs(value) for value in values),
    }


def render_boundary_md() -> str:
    return "\n".join(
        [
            "# Activation Capture Boundary",
            "",
            "- no model inference without separate explicit authorization;",
            "- no weight edit;",
            "- no delta artifact writing;",
            "- no patched model materialization;",
            "- no training;",
            "- no promotion;",
            "- no base model overwrite;",
            "- no production deployment;",
            "- no registry mutation;",
            "- no install authorization;",
            "- no automatic failure-to-curriculum capture.",
        ]
    ).rstrip() + "\n"


def render_review_packet(
    *,
    source_plan_status: str,
    selected_method: str,
    target_module: str,
    target_layer: str,
    target_module_family: str,
    probe_pair_count: int,
) -> str:
    return "\n".join(
        [
            "# LARQL Activation Capture Review Packet",
            "",
            f"Source plan status: `{source_plan_status}`",
            f"Selected method: `{selected_method}`",
            f"Target module: `{target_module}`",
            f"Target layer: `{target_layer}`",
            f"Target module family: `{target_module_family}`",
            f"Probe pair count: `{probe_pair_count}`",
            "",
            "Why activation capture follows the correction delta plan:",
            "",
            "- the deterministic direct delta was mechanically valid but behaviorally unchanged;",
            "- the next bounded step is to capture failure-versus-correction activation evidence at the selected layer or module;",
            "- this still does not authorize a weight edit.",
            "",
            "What evidence will be captured in a later authorized run:",
            "",
            "- per-probe failure and correction activation summary statistics;",
            "- prompt token counts;",
            "- generated output text preserved as raw audit evidence;",
            "- aggregate activation differences across probe pairs.",
            "",
            "What is not authorized:",
            "",
            "- no weight edit;",
            "- no safetensors delta writing;",
            "- no patched model materialization;",
            "- no promotion, install, deployment, registry mutation, or automatic failure-to-curriculum capture.",
            "",
            "Expected next review step:",
            "",
            f"`{REQUIRED_NEXT_STEP}`",
        ]
    ).rstrip() + "\n"


def build_probe_record(
    *,
    run_id: str,
    source_plan_path: Path,
    source_plan_status: str,
    selected_method: str,
    target_module: str,
    target_layer: str,
    target_module_family: str,
    model_inference_requested: bool,
    model_inference_performed: bool,
    activation_records_written: bool,
    activation_summary_written: bool,
    capture_mode: str,
    prompt_side_activation_captured: bool,
    generation_step_activation_captured: bool,
) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_correction_delta_plan_path": str(source_plan_path),
        "source_plan_status": source_plan_status,
        "selected_method": selected_method,
        "target_module": target_module,
        "target_layer": target_layer,
        "target_module_family": target_module_family,
        "activation_capture_authorized": True,
        "capture_mode": capture_mode,
        "prompt_side_activation_captured": prompt_side_activation_captured,
        "generation_step_activation_captured": generation_step_activation_captured,
        "model_inference_requested": model_inference_requested,
        "model_inference_performed": model_inference_performed,
        "activation_records_written": activation_records_written,
        "activation_summary_written": activation_summary_written,
        "weight_edit_performed": False,
        "delta_artifact_written": False,
        "patched_model_materialized": False,
        "training_performed": False,
        "adapter_baseline_path": False,
        "larql_core_path": True,
        "promotion_authorized": False,
        "base_model_overwrite_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": REQUIRED_NEXT_STEP,
    }


def resolve_targets(
    *,
    plan_path: Path,
    target_module: str | None,
    target_layer: str | None,
    target_module_family: str | None,
) -> tuple[str, str, str]:
    plan_dir = plan_path.parent
    selection_plan_path = plan_dir / "delta_selection_plan.json"
    selection_plan = load_json_object(selection_plan_path) if selection_plan_path.exists() else {}
    resolved_module = target_module or selection_plan.get("target_module") or "undecided"
    resolved_layer = target_layer or selection_plan.get("target_layer") or "undecided"
    resolved_family = target_module_family or selection_plan.get("target_module_family") or "undecided"
    return str(resolved_module), str(resolved_layer), str(resolved_family)


def load_selected_method(plan_path: Path) -> str:
    selection_plan_path = plan_path.parent / "delta_selection_plan.json"
    if not selection_plan_path.exists():
        return "undecided"
    selection_plan = load_json_object(selection_plan_path)
    return str(selection_plan.get("recommended_method", "undecided"))


def generate_audit_text(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
) -> str:
    import torch

    inputs = tokenizer(prompt, return_tensors="pt")
    generate_kwargs = {
        **inputs,
        "do_sample": False,
        "max_new_tokens": 256,
    }
    eos_token_id = getattr(tokenizer, "eos_token_id", None)
    if eos_token_id is not None:
        generate_kwargs["pad_token_id"] = eos_token_id
    with torch.no_grad():
        output_ids = model.generate(**generate_kwargs)
    input_len = inputs["input_ids"].shape[-1]
    new_tokens = output_ids[0][input_len:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def extract_captured_tensor_record(captured: list[dict[str, Any]]) -> dict[str, Any]:
    if not captured:
        raise ValueError("activation hook captured no outputs")
    latest = captured[-1]
    return {
        "shape": list(latest["shape"]),
        "dtype": str(latest["dtype"]),
        "tensor": latest["tensor"].clone() if hasattr(latest["tensor"], "clone") else latest["tensor"],
    }


def capture_prompt_forward_activation(
    *,
    model: Any,
    inputs: Any,
    module_obj: Any,
) -> dict[str, Any]:
    captured: list[dict[str, Any]] = []

    def hook(_module: Any, _inputs: Any, output: Any) -> None:
        tensor = output[0] if isinstance(output, tuple) else output
        if hasattr(tensor, "detach"):
            tensor = tensor.detach().float().cpu()
            captured.append(
                {
                    "shape": list(tensor.shape),
                    "dtype": str(tensor.dtype).replace("torch.", ""),
                    "tensor": tensor,
                }
            )

    handle = module_obj.register_forward_hook(hook)
    try:
        model(**inputs)
        return extract_captured_tensor_record(captured)
    finally:
        handle.remove()


def capture_generation_step_activation(
    *,
    model: Any,
    tokenizer: Any,
    prompt: str,
    module_obj: Any,
) -> tuple[dict[str, Any], str]:
    import torch

    captured: list[dict[str, Any]] = []

    def hook(_module: Any, _inputs: Any, output: Any) -> None:
        tensor = output[0] if isinstance(output, tuple) else output
        if hasattr(tensor, "detach"):
            tensor = tensor.detach().float().cpu()
            captured.append(
                {
                    "shape": list(tensor.shape),
                    "dtype": str(tensor.dtype).replace("torch.", ""),
                    "tensor": tensor,
                }
            )

    handle = module_obj.register_forward_hook(hook)
    try:
        text = generate_audit_text(model=model, tokenizer=tokenizer, prompt=prompt)
        return extract_captured_tensor_record(captured), text
    finally:
        handle.remove()


def perform_activation_capture(
    *,
    base_model_path: Path,
    target_module: str,
    target_layer: str,
    target_module_family: str,
    probe_pairs: list[dict[str, Any]],
    records_path: Path,
    summary_path: Path,
    capture_mode: str,
) -> tuple[bool, bool]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(base_model_path), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(base_model_path),
        local_files_only=True,
        torch_dtype="auto",
        device_map="cpu",
    )
    model.eval()

    module_path = normalize_module_name(target_module)
    module_obj: Any = model
    for part in module_path.split("."):
        if not part:
            continue
        module_obj = getattr(module_obj, part)

    rows: list[dict[str, Any]] = []

    for pair in probe_pairs:
        for side_key, prompt_key in [("failure", "failure_prompt"), ("correction", "correction_prompt")]:
            prompt = str(pair[prompt_key])
            inputs = tokenizer(prompt, return_tensors="pt")
            text = ""
            prompt_side_activation_captured = False
            generation_step_activation_captured = False
            activation_source = capture_mode
            generation_output_role = "audit_text_only" if capture_mode == "prompt_forward" else "activation_source"
            delta_evidence_source = "prompt_side_activation" if capture_mode == "prompt_forward" else "generation_step_activation"
            if capture_mode == "prompt_forward":
                prompt_capture = capture_prompt_forward_activation(
                    model=model,
                    inputs=inputs,
                    module_obj=module_obj,
                )
                prompt_side_activation_captured = True
                text = generate_audit_text(model=model, tokenizer=tokenizer, prompt=prompt)
                stats = prompt_capture
            elif capture_mode == "generation_step":
                generation_capture, text = capture_generation_step_activation(
                    model=model,
                    tokenizer=tokenizer,
                    prompt=prompt,
                    module_obj=module_obj,
                )
                generation_step_activation_captured = True
                stats = generation_capture
            else:
                raise ValueError(f"unsupported capture mode: {capture_mode}")
            tensor = stats["tensor"]
            nested = tensor.tolist()
            vector_stats = summarize_prompt_side_vectors(
                nested,
                dtype=stats["dtype"],
            )
            if len(vector_stats["activation_shape"]) == 3:
                seq_len = len(nested[0])
                hidden = len(nested[0][0])
                prompt_last_token_vector = list(nested[0][-1])
                prompt_mean_pool_vector = [
                    sum(float(nested[0][seq_idx][hidden_idx]) for seq_idx in range(seq_len)) / seq_len
                    for hidden_idx in range(hidden)
                ]
            elif len(vector_stats["activation_shape"]) == 2:
                prompt_last_token_vector = list(nested[0])
                prompt_mean_pool_vector = list(nested[0])
            else:
                prompt_last_token_vector = list(nested)
                prompt_mean_pool_vector = list(nested)
            row = {
                "probe_id": pair["probe_id"],
                "side": side_key,
                "target_module": target_module,
                "target_layer": target_layer,
                "activation_shape": vector_stats["activation_shape"],
                "activation_dtype": vector_stats["activation_dtype"],
                "activation_norm": vector_stats["activation_norm"],
                "activation_mean": vector_stats["activation_mean"],
                "activation_std": vector_stats["activation_std"],
                "activation_abs_max": vector_stats["activation_abs_max"],
                "capture_mode": capture_mode,
                "activation_source": activation_source,
                "generation_output_role": generation_output_role,
                "delta_evidence_source": delta_evidence_source,
                "prompt_side_activation_captured": prompt_side_activation_captured,
                "generation_step_activation_captured": generation_step_activation_captured,
                "prompt_sequence_length": vector_stats["prompt_sequence_length"],
                "prompt_last_token_norm": vector_stats["prompt_last_token_norm"],
                "prompt_last_token_mean": vector_stats["prompt_last_token_mean"],
                "prompt_last_token_std": vector_stats["prompt_last_token_std"],
                "prompt_last_token_abs_max": vector_stats["prompt_last_token_abs_max"],
                "prompt_mean_pool_norm": vector_stats["prompt_mean_pool_norm"],
                "prompt_mean_pool_mean": vector_stats["prompt_mean_pool_mean"],
                "prompt_mean_pool_std": vector_stats["prompt_mean_pool_std"],
                "prompt_mean_pool_abs_max": vector_stats["prompt_mean_pool_abs_max"],
                "prompt_token_count": int(inputs["input_ids"].shape[-1]),
                "model_output_text": text,
                "raw_output_preserved": True,
                "_prompt_last_token_vector": prompt_last_token_vector,
                "_prompt_mean_pool_vector": prompt_mean_pool_vector,
            }
            rows.append(row)

    records_path.write_text(
        "\n".join(
            json.dumps({k: v for k, v in row.items() if not k.startswith("_")}, sort_keys=True)
            for row in rows
        ) + "\n",
        encoding="utf-8",
    )

    by_probe: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_probe.setdefault(row["probe_id"], {})[row["side"]] = row
    per_probe = []
    last_norm_diffs: list[float] = []
    mean_norm_diffs: list[float] = []
    last_cosines: list[float] = []
    mean_cosines: list[float] = []
    for probe_id, pair_rows in by_probe.items():
        failure = pair_rows.get("failure")
        correction = pair_rows.get("correction")
        if failure is None or correction is None:
            continue
        comparison = compare_probe_pair(failure, correction)
        per_probe.append(comparison)
        last_norm_diffs.append(float(comparison["prompt_last_token_norm_difference"]))
        mean_norm_diffs.append(float(comparison["prompt_mean_pool_norm_difference"]))
        if comparison["prompt_last_token_cosine_similarity"] is not None:
            last_cosines.append(float(comparison["prompt_last_token_cosine_similarity"]))
        if comparison["prompt_mean_pool_cosine_similarity"] is not None:
            mean_cosines.append(float(comparison["prompt_mean_pool_cosine_similarity"]))
    classification = classify_prompt_signal(per_probe)
    summary = {
        "selected_method": "activation_difference_direction",
        "target_module": target_module,
        "target_layer": target_layer,
        "target_module_family": target_module_family,
        "per_probe_differences": per_probe,
        "aggregate_mean_difference": sum(last_norm_diffs) / len(last_norm_diffs) if last_norm_diffs else 0.0,
        "aggregate_cosine_similarity": sum(last_cosines) / len(last_cosines) if last_cosines else None,
        "prompt_last_token_mean_norm_difference": (
            sum(last_norm_diffs) / len(last_norm_diffs) if last_norm_diffs else 0.0
        ),
        "prompt_mean_pool_mean_norm_difference": (
            sum(mean_norm_diffs) / len(mean_norm_diffs) if mean_norm_diffs else 0.0
        ),
        "prompt_last_token_mean_cosine_similarity": (
            sum(last_cosines) / len(last_cosines) if last_cosines else None
        ),
        "prompt_mean_pool_mean_cosine_similarity": (
            sum(mean_cosines) / len(mean_cosines) if mean_cosines else None
        ),
        **classification,
        "delta_artifact_recommended": False,
        "required_next_step": REQUIRED_NEXT_STEP,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True, True


def write_probe(
    *,
    run_id: str,
    out_root: Path,
    correction_delta_plan_path: Path,
    base_model_path: Path | None,
    target_module: str | None,
    target_layer: str | None,
    target_module_family: str | None,
    probe_pairs_path: Path | None,
    authorize_larql_activation_capture_probe: bool,
    run_inference: bool,
    authorize_model_inference: bool,
    capture_mode: str = "prompt_forward",
) -> dict[str, Any]:
    require_authorization(authorize_larql_activation_capture_probe)

    plan = load_json_object(correction_delta_plan_path)
    validate_correction_delta_plan(plan)

    plan_dir = correction_delta_plan_path.parent
    selected_method = load_selected_method(correction_delta_plan_path)
    target_module_resolved, target_layer_resolved, target_family_resolved = resolve_targets(
        plan_path=correction_delta_plan_path,
        target_module=target_module,
        target_layer=target_layer,
        target_module_family=target_module_family,
    )
    probe_pairs = load_probe_pairs(probe_pairs_path or (plan_dir / "activation_contrast_probe_pairs.json"))

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    activation_capture_plan = build_activation_capture_plan(
        selected_method=selected_method,
        probe_pairs=probe_pairs,
        target_module=target_module_resolved,
        target_layer=target_layer_resolved,
        target_module_family=target_family_resolved,
    )
    (out_dir / "activation_capture_plan.json").write_text(
        json.dumps(activation_capture_plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "activation_capture_boundary.md").write_text(render_boundary_md(), encoding="utf-8")
    (out_dir / "activation_capture_review_packet.md").write_text(
        render_review_packet(
            source_plan_status=str(plan.get("source_reaudition_status", "unknown")),
            selected_method=selected_method,
            target_module=target_module_resolved,
            target_layer=target_layer_resolved,
            target_module_family=target_family_resolved,
            probe_pair_count=len(probe_pairs),
        ),
        encoding="utf-8",
    )

    activation_records_path = out_dir / "activation_records.jsonl"
    activation_summary_path = out_dir / "activation_summary.json"
    model_inference_performed = False
    activation_records_written = False
    activation_summary_written = False
    source_plan_status = str(plan.get("source_reaudition_status", "unknown"))

    if run_inference:
        if not authorize_model_inference:
            raise ValueError("model inference requires explicit authorization")
        if not inference_stack_available():
            source_plan_status = "blocked_missing_model_stack"
        elif base_model_path is None or not base_model_path.exists():
            source_plan_status = "blocked_missing_model_path"
        else:
            activation_records_written, activation_summary_written = perform_activation_capture(
                base_model_path=base_model_path,
                target_module=target_module_resolved,
                target_layer=target_layer_resolved,
                target_module_family=target_family_resolved,
                probe_pairs=probe_pairs,
                records_path=activation_records_path,
                summary_path=activation_summary_path,
                capture_mode=capture_mode,
            )
            model_inference_performed = activation_records_written and activation_summary_written

    prompt_side_activation_captured = False
    generation_step_activation_captured = False
    if model_inference_performed:
        if capture_mode == "prompt_forward":
            prompt_side_activation_captured = True
        elif capture_mode == "generation_step":
            generation_step_activation_captured = True

    record = build_probe_record(
        run_id=run_id,
        source_plan_path=correction_delta_plan_path,
        source_plan_status=source_plan_status,
        selected_method=selected_method,
        target_module=target_module_resolved,
        target_layer=target_layer_resolved,
        target_module_family=target_family_resolved,
        model_inference_requested=run_inference,
        model_inference_performed=model_inference_performed,
        activation_records_written=activation_records_written,
        activation_summary_written=activation_summary_written,
        capture_mode=capture_mode,
        prompt_side_activation_captured=prompt_side_activation_captured,
        generation_step_activation_captured=generation_step_activation_captured,
    )
    (out_dir / "larql_activation_capture_probe.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--correction-delta-plan", required=True, type=Path)
    parser.add_argument("--base-model-path", type=Path)
    parser.add_argument("--target-module")
    parser.add_argument("--target-layer")
    parser.add_argument("--target-module-family")
    parser.add_argument("--probe-pairs-path", type=Path)
    parser.add_argument(
        "--capture-mode",
        choices=["prompt_forward", "generation_step"],
        default="prompt_forward",
    )
    parser.add_argument("--authorize-larql-activation-capture-probe", action="store_true")
    parser.add_argument("--run-inference", action="store_true")
    parser.add_argument("--authorize-model-inference", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_probe(
            run_id=args.run_id,
            out_root=args.out_root,
            correction_delta_plan_path=args.correction_delta_plan,
            base_model_path=args.base_model_path,
            target_module=args.target_module,
            target_layer=args.target_layer,
            target_module_family=args.target_module_family,
            probe_pairs_path=args.probe_pairs_path,
            authorize_larql_activation_capture_probe=args.authorize_larql_activation_capture_probe,
            run_inference=args.run_inference,
            authorize_model_inference=args.authorize_model_inference,
            capture_mode=args.capture_mode,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
