#!/usr/bin/env python3
"""Run a gated teacher-forced activation capture over selected LARQL continuations."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


_TF_SPEC = importlib.util.spec_from_file_location(
    "larql_patched_model_teacher_forced_likelihood",
    Path(__file__).with_name("larql_patched_model_teacher_forced_likelihood.py"),
)
if _TF_SPEC is None or _TF_SPEC.loader is None:
    raise RuntimeError("failed to load larql_patched_model_teacher_forced_likelihood.py")
_TF_MODULE = importlib.util.module_from_spec(_TF_SPEC)
_TF_SPEC.loader.exec_module(_TF_MODULE)

build_probe_set = _TF_MODULE.build_probe_set
build_candidate_answers = _TF_MODULE.build_candidate_answers
build_model_prompt = _TF_MODULE.build_model_prompt


REPORT_TYPE = "larql_continuation_activation_capture.v0"
REQUIRED_NEXT_STEP = "supervised_continuation_activation_capture_review"
ALLOWED_CONTINUATIONS = {"corrected", "failure"}
TARGET_MODULE_FAMILY = "mlp_projection"


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL continuation activation capture requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"{path}: required file path does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"{path}: required file path does not exist")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: expected JSON object line")
        rows.append(payload)
    return rows


def validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("evidence_only") is not True:
        raise ValueError("multi-token target packet must be evidence_only true")
    if packet.get("model_free_packet") is not True:
        raise ValueError("multi-token target packet must be model_free_packet true")
    if packet.get("recommended_next_step") != "continuation_activation_capture":
        raise ValueError("multi-token target packet recommended_next_step must be continuation_activation_capture")
    for field in [
        "automatic_failure_to_curriculum_capture_authorized",
        "promotion_authorized",
        "training_performed",
    ]:
        if packet.get(field) is not False:
            raise ValueError(f"{field} must be false")
    for field in ["selected_boost_tokens", "selected_suppress_tokens", "selected_control_protection_tokens"]:
        if not isinstance(packet.get(field), list) or not packet.get(field):
            raise ValueError(f"multi-token target packet missing {field}")


def validate_source_provenance(packet: dict[str, Any]) -> None:
    for field in [
        "training_performed",
        "promotion_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "base_model_overwritten",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        if packet.get(field) is not False:
            raise ValueError(f"{field} must be false")


def resolve_module(model: Any, target_module: str) -> Any:
    module_obj: Any = model
    for part in target_module.split("."):
        if not part:
            continue
        module_obj = getattr(module_obj, part)
    return module_obj


def normalize_tensor_shape(tensor: Any) -> list[int]:
    shape = list(getattr(tensor, "shape", []))
    if not shape:
        raise ValueError("activation tensor shape is not supported")
    return [int(dim) for dim in shape]


def extract_position_vector(tensor: Any, *, position: int) -> list[float]:
    shape = normalize_tensor_shape(tensor)
    if len(shape) == 3:
        if position < 0 or position >= shape[1]:
            raise ValueError("selected token prediction position is out of range")
        return [float(x) for x in tensor[0, position, :].detach().float().cpu().tolist()]
    if len(shape) == 2:
        if position < 0 or position >= shape[0]:
            raise ValueError("selected token prediction position is out of range")
        return [float(x) for x in tensor[position, :].detach().float().cpu().tolist()]
    if len(shape) == 1:
        if position not in (0,):
            raise ValueError("selected token prediction position is out of range")
        return [float(x) for x in tensor.detach().float().cpu().tolist()]
    raise ValueError("activation tensor shape is not supported")


def capture_selected_vectors(
    *,
    model: Any,
    tokenizer: Any,
    module_obj: Any,
    prompt: str,
    candidate_text: str,
    selected_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    import torch

    prompt_ids = tokenizer(prompt, return_tensors="pt")["input_ids"]
    candidate_ids = tokenizer(candidate_text, return_tensors="pt", add_special_tokens=False)["input_ids"]
    if candidate_ids.shape[-1] == 0:
        raise ValueError("candidate continuation must not be empty")
    full_ids = torch.cat([prompt_ids, candidate_ids], dim=1)
    captured: dict[str, Any] = {}

    def hook(_module: Any, inputs: Any, output: Any) -> None:
        captured["input"] = inputs[0] if isinstance(inputs, tuple) and inputs else None
        captured["output"] = output[0] if isinstance(output, tuple) else output

    handle = module_obj.register_forward_hook(hook)
    try:
        with torch.no_grad():
            model(input_ids=full_ids)
    finally:
        handle.remove()

    if "output" not in captured:
        raise ValueError("activation hook captured no outputs")
    module_input = captured.get("input")
    module_output = captured.get("output")
    if module_output is None:
        raise ValueError("activation hook captured no outputs")

    rows: list[dict[str, Any]] = []
    prompt_len = int(prompt_ids.shape[-1])
    special_token_ids = set(getattr(tokenizer, "all_special_ids", []) or [])
    for row in selected_rows:
        token_index = int(row["token_index"])
        prediction_position = prompt_len + token_index - 1
        continuation_token_position = prompt_len + token_index
        output_vector = extract_position_vector(module_output, position=prediction_position)
        input_vector = None
        if module_input is not None:
            try:
                input_vector = extract_position_vector(module_input, position=prediction_position)
            except ValueError:
                input_vector = None
        token_text = str(row["token_text"])
        decoded = tokenizer.decode([int(row["token_id"])], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if decoded != token_text and decoded.strip() != token_text.strip():
            warning = "decoded token text differs from selected token text"
        else:
            warning = ""
        rows.append(
            {
                "probe_id": row["probe_id"],
                "continuation_type": row["continuation_type"],
                "token_index": token_index,
                "token_id": int(row["token_id"]),
                "token_text": token_text,
                "selection_action": row["selection_action"],
                "selection_reason": row["selection_reason"],
                "token_category": row["token_category"],
                "prediction_position": prediction_position,
                "continuation_token_position": continuation_token_position,
                "prompt_len": prompt_len,
                "target_module": row.get("target_module"),
                "target_module_family": TARGET_MODULE_FAMILY,
                "module_output_vector": output_vector,
                "module_input_vector": input_vector,
                "vector_length": len(output_vector),
                "token_is_special": int(row["token_id"]) in special_token_ids,
                "token_warning": warning,
            }
        )
    return rows


def build_review_packet(record: dict[str, Any], summary: dict[str, Any]) -> str:
    lines = [
        "# LARQL Continuation Activation Capture Review Packet",
        "",
        f"- source packet path: `{record['source_multi_token_target_packet_path']}`;",
        f"- target module: `{record['target_module']}`;",
        f"- selected count: `{record['selected_token_count']}`;",
        f"- captured count: `{record['captured_vector_count']}`;",
        f"- capture status: `{summary['capture_status']}`;",
        "",
        "## Prediction Position Explanation",
        "",
        "- continuation token index 0 is predicted from the last prompt token position;",
        "- continuation token index N is predicted from prompt_len + N - 1;",
        "- this runner captures module activations at the prediction position, not the consumed token position.",
        "",
        "## Claim Boundary",
        "",
        "- this runner is teacher-forced and model-free with respect to generation;",
        "- it does not train, write a delta, materialize a patched model, or promote anything;",
        "- evidence, not authority.",
        "",
        "## Authority Flags",
        "",
        f"- model_inference_performed: `{record['model_inference_performed']}`;",
        f"- generation_performed: `{record['generation_performed']}`;",
        f"- training_performed: `{record['training_performed']}`;",
        f"- lora_or_peft_used: `{record['lora_or_peft_used']}`;",
        f"- weight_edit_performed: `{record['weight_edit_performed']}`;",
        f"- delta_artifact_written: `{record['delta_artifact_written']}`;",
        f"- patched_model_materialized: `{record['patched_model_materialized']}`;",
        f"- promotion_authorized: `{record['promotion_authorized']}`;",
        f"- automatic_failure_to_curriculum_capture_authorized: `{record['automatic_failure_to_curriculum_capture_authorized']}`;",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_continuation_activation_capture(
    *,
    run_id: str,
    out_root: Path,
    base_model_path: Path,
    multi_token_target_packet_path: Path,
    target_module: str,
    device: str,
    max_selected_tokens: int | None,
    authorize_larql_continuation_activation_capture: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_continuation_activation_capture)
    out_dir = out_root / run_id
    if out_dir.exists():
        raise ValueError("output directory already exists")
    out_dir.mkdir(parents=True, exist_ok=False)
    if not base_model_path.exists():
        raise ValueError("base model path does not exist")

    packet = load_json_object(multi_token_target_packet_path)
    validate_packet(packet)
    validate_source_provenance(packet)

    source_rows = (
        list(packet.get("selected_boost_tokens", []))
        + list(packet.get("selected_suppress_tokens", []))
        + list(packet.get("selected_control_protection_tokens", []))
    )
    if not source_rows:
        raise ValueError("multi-token target packet missing selected token lists")
    if max_selected_tokens is not None and max_selected_tokens <= 0:
        raise ValueError("max_selected_tokens must be positive")
    if max_selected_tokens is not None:
        source_rows = source_rows[:max_selected_tokens]

    probe_set = build_probe_set()
    probe_map = {probe["probe_id"]: probe for probe in probe_set}
    selected_probe_ids = sorted({str(row["probe_id"]) for row in source_rows})
    if any(probe_id not in probe_map for probe_id in selected_probe_ids):
        raise ValueError("selected probe id is not in the bounded probe set")
    if any(str(row.get("continuation_type")) not in ALLOWED_CONTINUATIONS for row in source_rows):
        raise ValueError("selected continuation type is not corrected/failure")

    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(base_model_path), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(base_model_path),
        local_files_only=True,
        torch_dtype="auto",
        device_map="cpu" if device == "cpu" else device,
    )
    model.eval()
    module_obj = resolve_module(model, target_module)

    selected_rows = []
    for probe in probe_set:
        probe_id = probe["probe_id"]
        if probe_id not in selected_probe_ids:
            continue
        candidates = build_candidate_answers()[probe_id]
        for continuation_type, candidate_key in [("corrected", "corrected_candidate_json"), ("failure", "failure_candidate_json")]:
            rows_for_pair = [row for row in source_rows if row["probe_id"] == probe_id and row["continuation_type"] == continuation_type]
            if not rows_for_pair:
                continue
            prompt = build_model_prompt(tokenizer, probe)
            candidate_text = candidates[candidate_key]
            candidate_ids = tokenizer(candidate_text, return_tensors="pt", add_special_tokens=False)["input_ids"]
            if candidate_ids.shape[-1] == 0:
                raise ValueError("candidate continuation must not be empty")
            for row in rows_for_pair:
                token_index = int(row["token_index"])
                if token_index < 0 or token_index >= candidate_ids.shape[-1]:
                    raise ValueError("selected token prediction position is out of range")
                token_id = int(candidate_ids[0, token_index])
                if token_id != int(row["token_id"]):
                    raise ValueError("tokenization/label alignment is invalid")
                if row["token_text"] != tokenizer.decode([token_id], skip_special_tokens=False, clean_up_tokenization_spaces=False) and row["token_text"].strip() != tokenizer.decode([token_id], skip_special_tokens=False, clean_up_tokenization_spaces=False).strip():
                    warning = "decoded token text differs from selected token text"
                else:
                    warning = ""
                selected_rows.append(
                    {
                        **row,
                        "probe_id": probe_id,
                        "continuation_type": continuation_type,
                        "token_index": token_index,
                        "token_id": token_id,
                        "selection_action": row["selection_action"],
                        "selection_reason": row["selection_reason"],
                        "token_category": row["token_category"],
                        "token_warning": warning,
                    }
                )

    if not selected_rows:
        raise ValueError("selected token lists are empty")

    vectors: list[dict[str, Any]] = []
    selected_tokens_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in selected_rows:
        selected_tokens_by_pair.setdefault((row["probe_id"], row["continuation_type"]), []).append(row)

    for probe in probe_set:
        probe_id = probe["probe_id"]
        for continuation_type, candidate_key in [("corrected", "corrected_candidate_json"), ("failure", "failure_candidate_json")]:
            rows_for_pair = selected_tokens_by_pair.get((probe_id, continuation_type), [])
            if not rows_for_pair:
                continue
            candidates = build_candidate_answers()[probe_id]
            prompt = build_model_prompt(tokenizer, probe)
            pair_vectors = capture_selected_vectors(
                model=model,
                tokenizer=tokenizer,
                module_obj=module_obj,
                prompt=prompt,
                candidate_text=candidates[candidate_key],
                selected_rows=rows_for_pair,
            )
            vectors.extend(pair_vectors)

    records_path = out_dir / "continuation_activation_vectors.jsonl"
    records_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in vectors) + "\n",
        encoding="utf-8",
    )

    captured_boost_count = sum(1 for row in vectors if row["selection_action"] == "boost_corrected_semantic_token")
    captured_suppress_count = sum(1 for row in vectors if row["selection_action"] == "suppress_failure_semantic_token")
    captured_control_protection_count = sum(
        1 for row in vectors if row["selection_action"] in {"protect_control_corrected_token", "protect_control_failure_token"}
    )
    unique_probe_count = len({row["probe_id"] for row in vectors})
    unique_probe_continuation_pair_count = len({(row["probe_id"], row["continuation_type"]) for row in vectors})
    prediction_positions = [int(row["prediction_position"]) for row in vectors]
    summary = {
        "selected_boost_count": sum(1 for row in selected_rows if row["selection_action"] == "boost_corrected_semantic_token"),
        "selected_suppress_count": sum(1 for row in selected_rows if row["selection_action"] == "suppress_failure_semantic_token"),
        "selected_control_protection_count": sum(
            1 for row in selected_rows if row["selection_action"] in {"protect_control_corrected_token", "protect_control_failure_token"}
        ),
        "captured_boost_count": captured_boost_count,
        "captured_suppress_count": captured_suppress_count,
        "captured_control_protection_count": captured_control_protection_count,
        "unique_probe_count": unique_probe_count,
        "unique_probe_continuation_pair_count": unique_probe_continuation_pair_count,
        "prediction_position_min": min(prediction_positions),
        "prediction_position_max": max(prediction_positions),
        "vector_source": "continuation_prediction_position",
        "capture_status": "completed",
    }
    (out_dir / "continuation_activation_capture_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    record = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_multi_token_target_packet_path": str(multi_token_target_packet_path),
        "base_model_path": str(base_model_path),
        "target_module": target_module,
        "target_module_family": TARGET_MODULE_FAMILY,
        "selected_token_count": len(selected_rows),
        "captured_vector_count": len(vectors),
        "model_inference_performed": True,
        "generation_performed": False,
        "training_performed": False,
        "lora_or_peft_used": False,
        "weight_edit_performed": False,
        "delta_artifact_written": False,
        "patched_model_materialized": False,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": REQUIRED_NEXT_STEP,
        **summary,
    }
    (out_dir / "larql_continuation_activation_capture_record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "continuation_activation_capture_review_packet.md").write_text(
        build_review_packet(record, summary),
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--base-model-path", required=True, type=Path)
    parser.add_argument("--multi-token-target-packet", required=True, type=Path)
    parser.add_argument("--target-module", default="model.layers.0.mlp.down_proj")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-selected-tokens", type=int)
    parser.add_argument("--authorize-larql-continuation-activation-capture", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_continuation_activation_capture(
            run_id=args.run_id,
            out_root=args.out_root,
            base_model_path=args.base_model_path,
            multi_token_target_packet_path=args.multi_token_target_packet,
            target_module=args.target_module,
            device=args.device,
            max_selected_tokens=args.max_selected_tokens,
            authorize_larql_continuation_activation_capture=args.authorize_larql_continuation_activation_capture,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
