#!/usr/bin/env python3
"""Write a gated LARQL continuation rank-1 delta artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_continuation_rank1_delta_artifact.v0"
REQUIRED_NEXT_STEP = "supervised_continuation_delta_artifact_review"
DEFAULT_ARTIFACT_FORMAT = "safetensors"
TARGET_PARAMETER_SUFFIX = ".weight"


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL continuation rank1 delta artifact requires explicit opt-in authorization")


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


def l2_norm(values: list[float]) -> float:
    return math.sqrt(sum(float(v) * float(v) for v in values))


def stable_vector_hash(values: list[float]) -> str:
    payload = json.dumps([float(v) for v in values], separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def tensor_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outer_product(left: list[float], right: list[float], scale: float) -> list[list[float]]:
    return [[float(scale) * float(l) * float(r) for r in right] for l in left]


def encode_safetensors_f32_tensor(tensor: list[list[float]], tensor_name: str) -> bytes:
    rows = len(tensor)
    cols = len(tensor[0]) if tensor else 0
    flat: list[float] = [float(value) for row in tensor for value in row]
    data = b"".join(struct.pack("<f", value) for value in flat)
    header = {
        tensor_name: {
            "dtype": "F32",
            "shape": [rows, cols],
            "data_offsets": [0, len(data)],
        }
    }
    header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return struct.pack("<Q", len(header_bytes)) + header_bytes + data


def validate_design_packet(packet: dict[str, Any]) -> None:
    if packet.get("report_type") != "larql_continuation_rank1_delta_design.v0":
        raise ValueError("continuation rank1 delta design report_type mismatch")
    if packet.get("evidence_only") is not True:
        raise ValueError("continuation rank1 delta design must be evidence_only true")
    if packet.get("model_free_packet") is not True:
        raise ValueError("continuation rank1 delta design must be model_free_packet true")
    if packet.get("delta_design_only") is not True:
        raise ValueError("continuation rank1 delta design must be delta_design_only true")
    if packet.get("recommended_next_step") != "continuation_rank1_delta_artifact":
        raise ValueError("continuation rank1 delta design recommended_next_step must be continuation_rank1_delta_artifact")
    if packet.get("target_module") in (None, ""):
        raise ValueError("target_module missing")
    if packet.get("target_module_family") != "mlp_projection":
        raise ValueError("target_module_family must be mlp_projection")
    if packet.get("vector_source") != "continuation_prediction_position":
        raise ValueError("vector_source must be continuation_prediction_position")
    if packet.get("rank") != 1:
        raise ValueError("rank must be 1")
    try:
        delta_scale = float(packet["delta_scale"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("delta_scale must be positive and finite") from exc
    if not math.isfinite(delta_scale) or delta_scale <= 0.0:
        raise ValueError("delta_scale must be positive and finite")
    shape = packet.get("proposed_delta_shape")
    if not isinstance(shape, list) or len(shape) != 2 or not all(isinstance(x, int) and x > 0 for x in shape):
        raise ValueError("proposed_delta_shape missing or invalid")
    for field in [
        "model_inference_performed",
        "generation_performed",
        "training_performed",
        "lora_or_peft_used",
        "weight_edit_performed",
        "delta_artifact_written",
        "patched_model_materialized",
        "base_model_overwritten",
        "promotion_authorized",
        "production_deployment_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        if packet.get(field) is not False:
            raise ValueError(f"{field} must be false")


def validate_vectors(packet: dict[str, Any], vectors: dict[str, Any]) -> tuple[list[float], list[float]]:
    if vectors.get("target_module") != packet.get("target_module"):
        raise ValueError("target_module mismatch between design packet and vectors")
    if vectors.get("target_module_family") != packet.get("target_module_family"):
        raise ValueError("target_module_family mismatch between design packet and vectors")
    if vectors.get("vector_source") != packet.get("vector_source"):
        raise ValueError("vector_source mismatch between design packet and vectors")
    output_direction = vectors.get("continuation_output_direction")
    input_direction = vectors.get("continuation_input_direction")
    if not isinstance(output_direction, list) or not output_direction:
        raise ValueError("continuation_output_direction missing")
    if not isinstance(input_direction, list) or not input_direction:
        raise ValueError("continuation_input_direction missing")
    if len(output_direction) != int(packet["output_vector_length"]):
        raise ValueError("output direction length does not match design packet")
    if len(input_direction) != int(packet["input_vector_length"]):
        raise ValueError("input direction length does not match design packet")
    output_norm = l2_norm([float(v) for v in output_direction])
    input_norm = l2_norm([float(v) for v in input_direction])
    if not math.isfinite(output_norm) or abs(output_norm - 1.0) > 1e-4:
        raise ValueError("output direction norm is zero, non-finite, or not approximately 1.0")
    if not math.isfinite(input_norm) or abs(input_norm - 1.0) > 1e-4:
        raise ValueError("input direction norm is zero, non-finite, or not approximately 1.0")
    if stable_vector_hash([float(v) for v in output_direction]) != packet.get("continuation_output_direction_sha256"):
        raise ValueError("continuation output direction hash mismatch")
    if stable_vector_hash([float(v) for v in input_direction]) != packet.get("continuation_input_direction_sha256"):
        raise ValueError("continuation input direction hash mismatch")
    return [float(v) for v in output_direction], [float(v) for v in input_direction]


def write_artifact(
    *,
    out_dir: Path,
    target_parameter: str,
    delta_tensor: list[list[float]],
    artifact_format: str,
) -> Path:
    if artifact_format != "safetensors":
        raise ValueError("unsupported artifact format")
    artifact_path = out_dir / "rank1_delta.safetensors"
    artifact_path.write_bytes(encode_safetensors_f32_tensor(delta_tensor, target_parameter))
    return artifact_path


def render_review_packet(record: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Continuation Rank-1 Delta Artifact Review Packet",
            "",
            f"- source design packet path: `{record['source_continuation_rank1_delta_design_path']}`;",
            f"- source vectors path: `{record['source_continuation_direction_vectors_path']}`;",
            f"- artifact path: `{record['artifact_path']}`;",
            f"- artifact sha256: `{record['artifact_sha256']}`;",
            f"- target parameter key: `{record['target_parameter']}`;",
            f"- delta shape: `{record['delta_shape']}`;",
            f"- dtype: `{record['delta_dtype']}`;",
            f"- rank: `{record['rank']}`;",
            f"- scale: `{record['delta_scale']}`;",
            f"- frobenius norm: `{record['delta_frobenius_norm']}`;",
            f"- nonzero count: `{record['nonzero_count']}`;",
            "",
            f"- next required review step: `{record['required_next_step']}`;",
            "",
            "## Claim Boundary",
            "",
            "- this packet writes a delta artifact only;",
            "- it does not run inference, generation, training, LoRA/PEFT, base-model overwrite, patched model materialization, or promotion;",
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
            f"- base_model_overwritten: `{record['base_model_overwritten']}`;",
            f"- promotion_authorized: `{record['promotion_authorized']}`;",
            f"- production_deployment_authorized: `{record['production_deployment_authorized']}`;",
            f"- registry_mutation_authorized: `{record['registry_mutation_authorized']}`;",
            f"- install_authorized: `{record['install_authorized']}`;",
            f"- automatic_failure_to_curriculum_capture_authorized: `{record['automatic_failure_to_curriculum_capture_authorized']}`;",
        ]
    ).rstrip() + "\n"


def write_rank1_delta_artifact(
    *,
    run_id: str,
    out_root: Path,
    continuation_rank1_delta_design: Path,
    continuation_direction_vectors: Path,
    artifact_format: str,
    authorize_larql_continuation_rank1_delta_artifact: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_continuation_rank1_delta_artifact)
    out_dir = out_root / run_id
    if out_dir.exists():
        raise ValueError("output directory already exists")

    design_packet = load_json_object(continuation_rank1_delta_design)
    vectors = load_json_object(continuation_direction_vectors)
    validate_design_packet(design_packet)
    output_direction, input_direction = validate_vectors(design_packet, vectors)

    delta_scale = float(design_packet["delta_scale"])
    delta_tensor = outer_product(output_direction, input_direction, delta_scale)
    delta_shape = [len(delta_tensor), len(delta_tensor[0]) if delta_tensor else 0]
    expected_shape = [int(design_packet["output_vector_length"]), int(design_packet["input_vector_length"])]
    if delta_shape != expected_shape:
        raise ValueError("computed delta tensor shape does not match design packet")
    out_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = write_artifact(
        out_dir=out_dir,
        target_parameter=f"{design_packet['target_module']}.weight",
        delta_tensor=delta_tensor,
        artifact_format=artifact_format,
    )
    artifact_hash = tensor_sha256(artifact_path)
    delta_frobenius_norm = math.sqrt(sum(value * value for row in delta_tensor for value in row))
    nonzero_count = sum(1 for row in delta_tensor for value in row if float(value) != 0.0)

    record = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_continuation_rank1_delta_design_path": str(continuation_rank1_delta_design),
        "source_continuation_direction_vectors_path": str(continuation_direction_vectors),
        "artifact_format": artifact_format,
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_hash,
        "target_module": str(design_packet["target_module"]),
        "target_parameter": f"{design_packet['target_module']}.weight",
        "target_module_family": str(design_packet["target_module_family"]),
        "vector_source": str(design_packet["vector_source"]),
        "rank": 1,
        "delta_scale": delta_scale,
        "delta_shape": delta_shape,
        "delta_dtype": "float32",
        "delta_frobenius_norm": delta_frobenius_norm,
        "expected_delta_frobenius_norm": delta_scale,
        "nonzero_count": nonzero_count,
        "expected_nonzero_count": int(design_packet["output_vector_length"]) * int(design_packet["input_vector_length"]),
        "continuation_output_direction_sha256": str(design_packet["continuation_output_direction_sha256"]),
        "continuation_input_direction_sha256": str(design_packet["continuation_input_direction_sha256"]),
        "recommended_next_step": "supervised_continuation_delta_artifact_review",
        "required_next_step": "supervised_continuation_delta_artifact_review",
        "claim_boundary": {
            "writes_delta_artifact_only": True,
            "no_inference": True,
            "no_generation": True,
            "no_training": True,
            "no_lora_or_peft": True,
            "no_base_model_overwrite": True,
            "no_patched_model_materialization": True,
            "no_promotion": True,
            "evidence_not_authority": True,
        },
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "lora_or_peft_used": False,
        "weight_edit_performed": False,
        "delta_artifact_written": True,
        "patched_model_materialized": False,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
    }
    (out_dir / "larql_continuation_rank1_delta_artifact_record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "continuation_rank1_delta_artifact_manifest.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "continuation_rank1_delta_artifact_review_packet.md").write_text(
        render_review_packet(record),
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--continuation-rank1-delta-design", required=True, type=Path)
    parser.add_argument("--continuation-direction-vectors", required=True, type=Path)
    parser.add_argument("--artifact-format", default=DEFAULT_ARTIFACT_FORMAT)
    parser.add_argument("--authorize-larql-continuation-rank1-delta-artifact", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_rank1_delta_artifact(
            run_id=args.run_id,
            out_root=args.out_root,
            continuation_rank1_delta_design=args.continuation_rank1_delta_design,
            continuation_direction_vectors=args.continuation_direction_vectors,
            artifact_format=args.artifact_format,
            authorize_larql_continuation_rank1_delta_artifact=args.authorize_larql_continuation_rank1_delta_artifact,
        )
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
