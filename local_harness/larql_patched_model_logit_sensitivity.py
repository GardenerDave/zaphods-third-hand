#!/usr/bin/env python3
"""Run a gated LARQL patched-model logit sensitivity probe."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

_REAUDITION_SPEC = importlib.util.spec_from_file_location(
    "larql_patched_model_reaudition",
    Path(__file__).with_name("larql_patched_model_reaudition.py"),
)
if _REAUDITION_SPEC is None or _REAUDITION_SPEC.loader is None:
    raise RuntimeError("failed to load larql_patched_model_reaudition.py")
_REAUDITION_MODULE = importlib.util.module_from_spec(_REAUDITION_SPEC)
_REAUDITION_SPEC.loader.exec_module(_REAUDITION_MODULE)

build_model_prompt = _REAUDITION_MODULE.build_model_prompt
build_probe_set = _REAUDITION_MODULE.build_probe_set
validate_materialization_record = _REAUDITION_MODULE.validate_materialization_record


REPORT_TYPE = "larql_patched_model_logit_sensitivity.v0"
EPSILON = 1e-7


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL patched model logit sensitivity requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def inference_stack_available() -> bool:
    return importlib.util.find_spec("torch") is not None and importlib.util.find_spec("transformers") is not None


def top_k_indices(values: list[float], top_k: int) -> list[int]:
    limit = max(1, min(top_k, len(values)))
    return sorted(range(len(values)), key=lambda idx: values[idx], reverse=True)[:limit]


def cosine_similarity(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    norm_a = math.sqrt(sum(float(x) * float(x) for x in a))
    norm_b = math.sqrt(sum(float(y) * float(y) for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return None
    return dot / (norm_a * norm_b)


def compare_logits(base_logits: list[float], patched_logits: list[float], top_k: int) -> dict[str, Any]:
    if len(base_logits) != len(patched_logits):
        raise ValueError("base and patched logits length mismatch")
    if not base_logits:
        raise ValueError("logits vector must be non-empty")
    diffs = [float(p) - float(b) for b, p in zip(base_logits, patched_logits)]
    abs_diffs = [abs(diff) for diff in diffs]
    base_top = top_k_indices(base_logits, top_k)
    patched_top = top_k_indices(patched_logits, top_k)
    top_overlap = len(set(base_top).intersection(patched_top))
    return {
        "max_abs_logit_diff": max(abs_diffs),
        "mean_abs_logit_diff": sum(abs_diffs) / len(abs_diffs),
        "l2_logit_diff": math.sqrt(sum(diff * diff for diff in diffs)),
        "cosine_similarity": cosine_similarity(base_logits, patched_logits),
        "top_k_base_token_ids": base_top,
        "top_k_patched_token_ids": patched_top,
        "top1_token_changed": bool(base_top and patched_top and base_top[0] != patched_top[0]),
        "top_k_overlap_count": top_overlap,
        "logit_vector_length": len(base_logits),
    }


def classify_logit_sensitivity(probes: list[dict[str, Any]]) -> str:
    if not probes:
        return "logit_sensitivity_inconclusive"
    if any("exception" in probe for probe in probes):
        return "logit_sensitivity_inconclusive"
    if any(
        probe["max_abs_logit_diff"] > EPSILON
        or probe["top1_token_changed"]
        or probe["top_k_overlap_count"] < min(len(probe["top_k_base_token_ids"]), len(probe["top_k_patched_token_ids"]))
        for probe in probes
    ):
        return "logit_sensitivity_detected"
    return "logit_sensitivity_not_detected"


def run_logit_inference(
    *,
    model_path: Path,
    probe_set: list[dict[str, Any]],
    top_k: int,
    device: str,
) -> list[dict[str, Any]]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    device_map = "auto" if device == "auto" else device
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        local_files_only=True,
        torch_dtype="auto",
        device_map=device_map,
    )
    rows: list[dict[str, Any]] = []
    for probe in probe_set:
        prompt = build_model_prompt(tokenizer, probe)
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        logits = outputs.logits[0, -1, :].detach().float().cpu().tolist()
        rows.append({"probe_id": probe["probe_id"], "final_prompt_logits": logits, "top_k": top_k})
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def build_comparison(
    probe_set: list[dict[str, Any]],
    base_rows: list[dict[str, Any]],
    patched_rows: list[dict[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    base_by_id = {row["probe_id"]: row for row in base_rows}
    patched_by_id = {row["probe_id"]: row for row in patched_rows}
    probes: list[dict[str, Any]] = []
    for probe in probe_set:
        probe_id = probe["probe_id"]
        if probe_id not in base_by_id or probe_id not in patched_by_id:
            probes.append({"probe_id": probe_id, "exception": "missing probe logits"})
            continue
        metrics = compare_logits(
            base_by_id[probe_id]["final_prompt_logits"],
            patched_by_id[probe_id]["final_prompt_logits"],
            top_k,
        )
        probes.append({"probe_id": probe_id, **metrics})

    valid_probes = [probe for probe in probes if "exception" not in probe]
    summary = {
        "probe_count": len(probe_set),
        "max_abs_logit_diff_max": max((probe["max_abs_logit_diff"] for probe in valid_probes), default=0.0),
        "mean_abs_logit_diff_mean": (
            sum(probe["mean_abs_logit_diff"] for probe in valid_probes) / len(valid_probes)
            if valid_probes
            else 0.0
        ),
        "l2_logit_diff_mean": (
            sum(probe["l2_logit_diff"] for probe in valid_probes) / len(valid_probes)
            if valid_probes
            else 0.0
        ),
        "top1_changed_count": sum(1 for probe in valid_probes if probe["top1_token_changed"]),
        "topk_overlap_mean": (
            sum(probe["top_k_overlap_count"] for probe in valid_probes) / len(valid_probes)
            if valid_probes
            else 0.0
        ),
    }
    return {
        "evidence_only": True,
        "promotion_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "summary": summary,
        "probes": probes,
    }


def render_review_packet(record: dict[str, Any], comparison: dict[str, Any]) -> str:
    summary = comparison["summary"]
    return "\n".join(
        [
            "# LARQL Patched Model Logit Sensitivity Review Packet",
            "",
            "- this is a diagnostic stage after unchanged behavioral reauditions;",
            "- it checks whether the patched copy changes logits even when greedy outputs are unchanged;",
            "- it does not train, patch, generate, promote, or deploy;",
            "- the result is evidence, not authority.",
            "",
            f"- target module: `{record['target_module']}`;",
            f"- delta scale: `{record['delta_scale']}`;",
            f"- logit sensitivity status: `{record['logit_sensitivity_status']}`;",
            f"- max abs logit diff max: `{summary['max_abs_logit_diff_max']}`;",
            f"- top-1 changed count: `{summary['top1_changed_count']}`;",
            "",
            "Next step: `supervised_logit_sensitivity_review`",
        ]
    ).rstrip() + "\n"


def write_patched_model_logit_sensitivity(
    *,
    run_id: str,
    out_root: Path,
    materialization_record_path: Path,
    authorize_larql_patched_model_logit_sensitivity: bool,
    device: str,
    top_k: int,
) -> dict[str, Any]:
    require_authorization(authorize_larql_patched_model_logit_sensitivity)
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    materialization_record = load_json_object(materialization_record_path)
    validate_materialization_record(materialization_record)
    if not inference_stack_available():
        raise ValueError("torch and transformers are required for patched-model logit sensitivity")

    base_model_path = Path(materialization_record["base_model_path"])
    patched_model_path = Path(materialization_record["patched_model_path"])
    if not base_model_path.exists():
        raise ValueError("base model path does not exist")
    if not patched_model_path.exists():
        raise ValueError("patched model path does not exist")

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    probe_set = build_probe_set()
    base_rows = run_logit_inference(
        model_path=base_model_path,
        probe_set=probe_set,
        top_k=top_k,
        device=device,
    )
    patched_rows = run_logit_inference(
        model_path=patched_model_path,
        probe_set=probe_set,
        top_k=top_k,
        device=device,
    )
    base_outputs_path = out_dir / "base_outputs.jsonl"
    patched_outputs_path = out_dir / "patched_outputs.jsonl"
    write_jsonl(base_outputs_path, base_rows)
    write_jsonl(patched_outputs_path, patched_rows)

    comparison = build_comparison(probe_set, base_rows, patched_rows, top_k)
    comparison_path = out_dir / "logit_sensitivity_comparison.json"
    comparison_path.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = classify_logit_sensitivity(comparison["probes"])
    record = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_materialization_record_path": str(materialization_record_path),
        "base_model_path": str(base_model_path),
        "patched_model_path": str(patched_model_path),
        "target_module": str(materialization_record["target_module"]),
        "target_layer": str(materialization_record["target_layer"]),
        "target_module_family": str(materialization_record["target_module_family"]),
        "delta_scale": float(materialization_record["delta_scale"]),
        "base_tensor_sha256_before": str(materialization_record["base_tensor_sha256_before"]),
        "patched_tensor_sha256_after": str(materialization_record["patched_tensor_sha256_after"]),
        "model_inference_performed": True,
        "base_model_inference_performed": True,
        "patched_model_inference_performed": True,
        "generation_performed": False,
        "training_performed": False,
        "adapter_baseline_path": False,
        "larql_core_path": True,
        "weight_edit_performed": False,
        "delta_artifact_written": False,
        "patched_model_materialized": False,
        "base_model_overwrite_authorized": False,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "logit_sensitivity_status": status,
        "required_next_step": "supervised_logit_sensitivity_review",
    }
    record_path = out_dir / "larql_patched_model_logit_sensitivity_record.json"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "patched_model_logit_sensitivity_review_packet.md").write_text(
        render_review_packet(record, comparison),
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--materialization-record", required=True, type=Path)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--authorize-larql-patched-model-logit-sensitivity", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_patched_model_logit_sensitivity(
            run_id=args.run_id,
            out_root=args.out_root,
            materialization_record_path=args.materialization_record,
            authorize_larql_patched_model_logit_sensitivity=args.authorize_larql_patched_model_logit_sensitivity,
            device=args.device,
            top_k=args.top_k,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
