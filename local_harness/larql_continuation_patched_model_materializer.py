#!/usr/bin/env python3
"""Materialize a patched model copy from a reviewed LARQL continuation rank-1 delta artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import pickle
import shutil
import struct
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_continuation_patched_model_materialization.v0"
REQUIRED_NEXT_STEP = "supervised_patched_model_materialization_review"
RECOMMENDED_NEXT_STEP = "supervised_patched_model_reaudition"
TARGET_PARAMETER_SUFFIX = ".weight"


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL continuation patched model materialization requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"{path}: required file path does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tensor_data_sha256(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def tensor_shape(data: Any) -> list[int]:
    if hasattr(data, "shape"):
        shape = list(int(x) for x in data.shape)  # type: ignore[attr-defined]
        return shape
    if not isinstance(data, list):
        return []
    if data and isinstance(data[0], list):
        return [len(data), len(data[0])]
    return [len(data)]


def tensor_norm(data: list[list[float]]) -> float:
    return math.sqrt(sum(float(value) * float(value) for row in data for value in row))


def add_tensors(base: list[list[float]], delta: list[list[float]]) -> list[list[float]]:
    if len(base) != len(delta):
        raise ValueError("base tensor and delta tensor row count mismatch")
    result: list[list[float]] = []
    for base_row, delta_row in zip(base, delta):
        if len(base_row) != len(delta_row):
            raise ValueError("base tensor and delta tensor column count mismatch")
        result.append([float(b) + float(d) for b, d in zip(base_row, delta_row)])
    return result


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("report_type") != "larql_continuation_rank1_delta_artifact.v0":
        raise ValueError("continuation delta artifact manifest report_type mismatch")
    if manifest.get("artifact_format") != "safetensors":
        raise ValueError("continuation delta artifact manifest artifact_format must be safetensors")
    if manifest.get("delta_artifact_written") is not True:
        raise ValueError("continuation delta artifact manifest must have delta_artifact_written true")
    if manifest.get("patched_model_materialized") is not False:
        raise ValueError("continuation delta artifact manifest must have patched_model_materialized false")
    if manifest.get("base_model_overwritten") is not False:
        raise ValueError("base_model_overwritten must be false")
    if manifest.get("promotion_authorized") is not False:
        raise ValueError("promotion_authorized must be false")
    if manifest.get("automatic_failure_to_curriculum_capture_authorized") is not False:
        raise ValueError("automatic_failure_to_curriculum_capture_authorized must be false")
    if manifest.get("target_parameter") in (None, ""):
        raise ValueError("target_parameter missing")
    if manifest.get("target_module") in (None, ""):
        raise ValueError("target_module missing")
    if manifest.get("target_module_family") != "mlp_projection":
        raise ValueError("target_module_family must be mlp_projection")
    if manifest.get("vector_source") != "continuation_prediction_position":
        raise ValueError("vector_source must be continuation_prediction_position")
    shape = manifest.get("delta_shape")
    if not isinstance(shape, list) or len(shape) != 2 or not all(isinstance(x, int) and x > 0 for x in shape):
        raise ValueError("delta_shape missing or invalid")
    if not math.isfinite(float(manifest.get("delta_scale", float("nan")))) or float(manifest["delta_scale"]) <= 0.0:
        raise ValueError("delta_scale must be positive and finite")
    for field in [
        "model_inference_performed",
        "generation_performed",
        "training_performed",
        "lora_or_peft_used",
        "patched_model_materialized",
        "base_model_overwritten",
        "promotion_authorized",
        "production_deployment_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        if manifest.get(field) is not False:
            raise ValueError(f"{field} must be false")


def verify_artifacts_match(
    *,
    manifest: dict[str, Any],
    delta_artifact_path: Path,
    reviewed_artifact_sha256: str,
) -> tuple[str, dict[str, Any]]:
    if not delta_artifact_path.exists():
        raise ValueError("delta artifact path does not exist")
    actual_sha = file_sha256(delta_artifact_path)
    expected_sha = str(manifest["artifact_sha256"])
    if actual_sha != expected_sha:
        raise ValueError("delta artifact sha256 mismatch")
    if reviewed_artifact_sha256 != expected_sha or reviewed_artifact_sha256 != actual_sha:
        raise ValueError("reviewed_artifact_sha256 mismatch")
    return actual_sha, parse_safetensors_single_tensor(delta_artifact_path)


def parse_safetensors_single_tensor(path: Path) -> dict[str, Any]:
    blob = path.read_bytes()
    if len(blob) < 8:
        raise ValueError("safetensors artifact malformed")
    header_len = struct.unpack("<Q", blob[:8])[0]
    header_bytes = blob[8 : 8 + header_len]
    if len(header_bytes) != header_len:
        raise ValueError("safetensors artifact malformed header")
    header = json.loads(header_bytes.decode("utf-8"))
    if not isinstance(header, dict) or len(header) != 1:
        raise ValueError("safetensors artifact must contain exactly one tensor")
    tensor_key = next(iter(header))
    tensor_meta = header[tensor_key]
    if not isinstance(tensor_meta, dict):
        raise ValueError("safetensors tensor metadata malformed")
    dtype = str(tensor_meta.get("dtype"))
    shape = tensor_meta.get("shape")
    offsets = tensor_meta.get("data_offsets")
    if dtype not in {"F32", "float32"}:
        raise ValueError("delta artifact dtype must be F32/float32")
    if not isinstance(shape, list) or len(shape) != 2 or not all(isinstance(x, int) for x in shape):
        raise ValueError("delta artifact tensor shape malformed")
    if not isinstance(offsets, list) or len(offsets) != 2 or not all(isinstance(x, int) for x in offsets):
        raise ValueError("delta artifact tensor offsets malformed")
    data = blob[8 + header_len :]
    if len(data) != offsets[1] - offsets[0]:
        raise ValueError("delta artifact tensor data length mismatch")
    if len(data) != shape[0] * shape[1] * 4:
        raise ValueError("delta artifact tensor byte length mismatch")
    return {
        "tensor_key": tensor_key,
        "dtype": dtype,
        "shape": shape,
        "data_offsets": offsets,
        "data": data,
        "tensor_count": 1,
    }


def tensor_bytes_to_nested_f32(data: bytes, shape: list[int]) -> list[list[float]]:
    rows, cols = shape
    floats = list(struct.unpack("<" + "f" * (rows * cols), data))
    return [floats[i * cols : (i + 1) * cols] for i in range(rows)]


def nested_f32_to_bytes(values: list[list[float]]) -> bytes:
    flat = [float(value) for row in values for value in row]
    return struct.pack("<" + "f" * len(flat), *flat)


def encode_safetensors_single_tensor(tensor_key: str, values: list[list[float]]) -> bytes:
    rows = len(values)
    cols = len(values[0]) if values else 0
    data = nested_f32_to_bytes(values)
    header = {
        tensor_key: {
            "dtype": "F32",
            "shape": [rows, cols],
            "data_offsets": [0, len(data)],
        }
    }
    header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return struct.pack("<Q", len(header_bytes)) + header_bytes + data


def resolve_target_shard(base_model_path: Path, target_parameter: str) -> Path:
    index_path = base_model_path / "model.safetensors.index.json"
    if index_path.exists():
        payload = load_json_object(index_path)
        weight_map = payload.get("weight_map")
        if not isinstance(weight_map, dict) or target_parameter not in weight_map:
            raise ValueError("target parameter missing from model.safetensors.index.json")
        return base_model_path / str(weight_map[target_parameter])

    if (base_model_path / "model.safetensors").exists():
        return base_model_path / "model.safetensors"
    if (base_model_path / "model_state.pt").exists():
        return base_model_path / "model_state.pt"

    raise ValueError("unsupported base model layout; expected model.safetensors.index.json, model.safetensors, or model_state.pt")


def load_target_tensor_from_shard(shard_path: Path, target_parameter: str) -> tuple[Any, str]:
    if shard_path.suffix == ".safetensors":
        if importlib.util.find_spec("torch") is None or importlib.util.find_spec("safetensors") is None:
            raise ValueError("required safetensors/torch capability is unavailable for real materialization")
        from safetensors.torch import load_file  # type: ignore

        tensor_map = load_file(str(shard_path))
        if target_parameter not in tensor_map:
            raise ValueError("target parameter missing from safetensors shard")
        tensor = tensor_map[target_parameter]
        return tensor, str(tensor.dtype)

    payload = pickle.loads(shard_path.read_bytes())
    if not isinstance(payload, dict) or target_parameter not in payload:
        raise ValueError("target parameter missing from pt shard")
    tensor = payload[target_parameter]
    return tensor, "float32"


def tensor_to_floats(data: Any) -> list[list[float]]:
    if hasattr(data, "detach"):
        return [[float(value) for value in row] for row in data.detach().cpu().tolist()]
    if isinstance(data, list):
        return [[float(value) for value in row] for row in data]
    raise ValueError("unsupported tensor data format")


def apply_delta(base_tensor: Any, delta_tensor: list[list[float]], base_dtype: str) -> tuple[Any, str]:
    if hasattr(base_tensor, "detach"):
        if importlib.util.find_spec("torch") is None:
            raise ValueError("required safetensors/torch capability is unavailable for real materialization")
        import torch  # type: ignore

        patched = torch.tensor(base_tensor.detach().cpu().tolist(), dtype=torch.float32) + torch.tensor(
            delta_tensor, dtype=torch.float32
        )
        return patched.to(dtype=base_tensor.dtype), str(base_tensor.dtype)

    base_list = tensor_to_floats(base_tensor)
    patched = add_tensors(base_list, delta_tensor)
    return patched, base_dtype


def write_shard(
    *,
    shard_path: Path,
    target_parameter: str,
    patched_tensor: Any,
) -> None:
    if shard_path.suffix == ".safetensors":
        if importlib.util.find_spec("torch") is None or importlib.util.find_spec("safetensors") is None:
            raise ValueError("required safetensors/torch capability is unavailable for real materialization")
        from safetensors.torch import load_file, save_file  # type: ignore

        tensor_map = load_file(str(shard_path))
        if target_parameter not in tensor_map:
            raise ValueError("target parameter missing from safetensors shard")
        tensor_map[target_parameter] = patched_tensor
        save_file(tensor_map, str(shard_path))
        return

    payload = pickle.loads(shard_path.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError("pt shard payload malformed")
    payload[target_parameter] = patched_tensor
    shard_path.write_bytes(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))


def render_review_packet(record: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Continuation Patched Model Materialization Review Packet",
            "",
            f"- base model path: `{record['source_base_model_path']}`;",
            f"- patched model path: `{record['patched_model_path']}`;",
            f"- source delta artifact path: `{record['source_delta_artifact_path']}`;",
            f"- reviewed artifact sha256: `{record['reviewed_artifact_sha256']}`;",
            f"- target parameter: `{record['target_parameter']}`;",
            f"- target shard: `{record['target_shard_relative_path']}`;",
            f"- base dtype/shape: `{record['base_weight_dtype']}` / `{record['base_weight_shape']}`;",
            f"- patched dtype/shape: `{record['patched_weight_dtype']}` / `{record['patched_weight_shape']}`;",
            f"- shard hash before/after: `{record['target_shard_sha256_before']}` / `{record['target_shard_sha256_after']}`;",
            "",
            f"- required review step: `{REQUIRED_NEXT_STEP}`;",
            f"- recommended next reaudition step: `{RECOMMENDED_NEXT_STEP}`;",
            "",
            "## Claim Boundary",
            "",
            "- this packet writes a patched model copy only;",
            "- it does not overwrite the base model;",
            "- it does not run inference, generation, training, LoRA/PEFT, promotion, install, or deployment;",
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


def validate_safe_model_record(manifest: dict[str, Any]) -> None:
    for field in [
        "model_inference_performed",
        "generation_performed",
        "training_performed",
        "lora_or_peft_used",
        "patched_model_materialized",
        "base_model_overwritten",
        "promotion_authorized",
        "production_deployment_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        if manifest.get(field) is not False:
            raise ValueError(f"{field} must be false")


def materialize_patched_model(
    *,
    run_id: str,
    out_root: Path,
    base_model_path: Path,
    delta_artifact_manifest: Path,
    delta_artifact_path: Path,
    reviewed_artifact_sha256: str,
    authorize_larql_continuation_patched_model_materialization: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_continuation_patched_model_materialization)
    if not base_model_path.exists() or not base_model_path.is_dir():
        raise ValueError("base model path does not exist or is not a directory")

    out_dir = out_root / run_id
    patched_model_path = out_dir / "patched_model"
    if patched_model_path.resolve().is_relative_to(base_model_path.resolve()):  # type: ignore[attr-defined]
        raise ValueError("output path must not be inside the base model path")
    if out_dir.exists():
        raise ValueError("output directory already exists")

    manifest = load_json_object(delta_artifact_manifest)
    if not delta_artifact_path.exists():
        raise ValueError("delta artifact path does not exist")
    validate_manifest(manifest)
    validate_safe_model_record(manifest)
    if reviewed_artifact_sha256 != str(manifest.get("artifact_sha256")):
        raise ValueError("reviewed_artifact_sha256 mismatch")
    actual_artifact_sha = file_sha256(delta_artifact_path)
    if actual_artifact_sha != str(manifest.get("artifact_sha256")):
        raise ValueError("artifact sha256 mismatch")
    if reviewed_artifact_sha256 != actual_artifact_sha:
        raise ValueError("reviewed_artifact_sha256 mismatch")
    artifact_info = parse_safetensors_single_tensor(delta_artifact_path)
    if artifact_info["tensor_key"] != manifest["target_parameter"]:
        raise ValueError("delta artifact tensor key does not equal manifest target_parameter")
    if artifact_info["shape"] != list(manifest["delta_shape"]):
        raise ValueError("delta artifact tensor shape does not equal manifest delta_shape")
    if artifact_info["dtype"] not in {"F32", "float32"}:
        raise ValueError("delta artifact dtype must be F32/float32")

    target_parameter = str(manifest["target_parameter"])
    target_shard_path = resolve_target_shard(base_model_path, target_parameter)
    base_tensor, base_dtype = load_target_tensor_from_shard(target_shard_path, target_parameter)
    base_shape = tensor_shape(base_tensor)
    if base_shape != list(manifest["delta_shape"]):
        raise ValueError("target base tensor shape does not match delta shape")
    base_tensor_sha = file_sha256(target_shard_path)
    delta_tensor = tensor_bytes_to_nested_f32(artifact_info["data"], artifact_info["shape"])
    patched_tensor, patched_dtype = apply_delta(base_tensor, delta_tensor, base_dtype)

    out_dir.mkdir(parents=True, exist_ok=False)
    shutil.copytree(base_model_path, patched_model_path)
    copied_shard_path = patched_model_path / target_shard_path.relative_to(base_model_path)
    write_shard(
        shard_path=copied_shard_path,
        target_parameter=target_parameter,
        patched_tensor=patched_tensor,
    )
    target_shard_sha_after = file_sha256(copied_shard_path)
    patched_model_file_count = sum(1 for path in patched_model_path.rglob("*") if path.is_file())

    record = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_base_model_path": str(base_model_path),
        "patched_model_path": str(patched_model_path),
        "source_delta_artifact_manifest_path": str(delta_artifact_manifest),
        "source_delta_artifact_path": str(delta_artifact_path),
        "reviewed_artifact_sha256": reviewed_artifact_sha256,
        "delta_artifact_sha256": actual_artifact_sha,
        "target_module": str(manifest["target_module"]),
        "target_parameter": target_parameter,
        "target_module_family": str(manifest["target_module_family"]),
        "vector_source": str(manifest["vector_source"]),
        "delta_shape": list(manifest["delta_shape"]),
        "delta_dtype": str(manifest.get("delta_dtype", "float32")),
        "base_weight_dtype": base_dtype,
        "patched_weight_dtype": patched_dtype,
        "base_weight_shape": base_shape,
        "patched_weight_shape": base_shape,
        "target_shard_relative_path": str(target_shard_path.relative_to(base_model_path)),
        "target_shard_sha256_before": base_tensor_sha,
        "target_shard_sha256_after": target_shard_sha_after,
        "patched_model_file_count": patched_model_file_count,
        "recommended_next_step": RECOMMENDED_NEXT_STEP,
        "required_next_step": REQUIRED_NEXT_STEP,
        "claim_boundary": {
            "writes_patched_model_copy_only": True,
            "no_base_model_overwrite": True,
            "no_inference": True,
            "no_generation": True,
            "no_training": True,
            "no_lora_or_peft": True,
            "no_promotion": True,
            "no_install": True,
            "no_deployment": True,
            "evidence_not_authority": True,
        },
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "lora_or_peft_used": False,
        "weight_edit_performed": True,
        "delta_artifact_written": False,
        "patched_model_materialized": True,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
    }
    (out_dir / "larql_continuation_patched_model_materialization_record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "continuation_patched_model_manifest.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "continuation_patched_model_review_packet.md").write_text(
        render_review_packet(record),
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--base-model-path", required=True, type=Path)
    parser.add_argument("--delta-artifact-manifest", required=True, type=Path)
    parser.add_argument("--delta-artifact", required=True, type=Path)
    parser.add_argument("--reviewed-artifact-sha256", required=True)
    parser.add_argument("--authorize-larql-continuation-patched-model-materialization", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        materialize_patched_model(
            run_id=args.run_id,
            out_root=args.out_root,
            base_model_path=args.base_model_path,
            delta_artifact_manifest=args.delta_artifact_manifest,
            delta_artifact_path=args.delta_artifact,
            reviewed_artifact_sha256=args.reviewed_artifact_sha256,
            authorize_larql_continuation_patched_model_materialization=args.authorize_larql_continuation_patched_model_materialization,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError, pickle.PickleError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
