#!/usr/bin/env python3
"""Materialize a patched model copy from a reviewed LARQL rank-1 delta artifact."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import pickle
import shutil
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_patched_model_materialization.v0"
REQUIRED_NEXT_STEP = "supervised_patched_model_materialization_review"


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL patched model materialization requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
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


def validate_artifact_record(record: dict[str, Any]) -> None:
    if record.get("report_type") != "larql_rank1_delta_artifact.v0":
        raise ValueError("rank1 delta artifact record report_type mismatch")
    if record.get("delta_artifact_written") is not True:
        raise ValueError("rank1 delta artifact record must have delta_artifact_written true")
    if record.get("patched_model_materialized") is not False:
        raise ValueError("rank1 delta artifact record must have patched_model_materialized false")
    if record.get("base_model_overwrite_authorized") is not False:
        raise ValueError("base_model_overwrite_authorized must be false")
    if record.get("promotion_authorized") is not False:
        raise ValueError("promotion_authorized must be false")


def verify_artifact_hash(record: dict[str, Any]) -> Path:
    artifact_path = Path(record["artifact_path"])
    if not artifact_path.exists():
        raise ValueError("rank1 delta artifact path does not exist")
    actual = file_sha256(artifact_path)
    expected = str(record["artifact_sha256"])
    if actual != expected:
        raise ValueError("rank1 delta artifact sha256 mismatch")
    return artifact_path


def load_delta_artifact(artifact_path: Path, artifact_format: str) -> list[list[float]]:
    if artifact_format == "safetensors":
        if importlib.util.find_spec("safetensors") is None:
            raise ValueError("safetensors artifact present but safetensors is unavailable")
        if importlib.util.find_spec("torch") is None:
            raise ValueError("safetensors artifact present but torch is unavailable")
        from safetensors.torch import load_file  # type: ignore

        tensor_map = load_file(str(artifact_path))
        if "delta" not in tensor_map:
            raise ValueError("safetensors artifact missing delta tensor")
        delta = tensor_map["delta"]
        return [[float(value) for value in row] for row in delta.detach().float().cpu().tolist()]

    if artifact_format == "pt":
        payload = pickle.loads(artifact_path.read_bytes())
        delta = payload.get("delta")
        if not isinstance(delta, list):
            raise ValueError("pt artifact missing delta tensor")
        return delta

    raise ValueError(f"unsupported artifact format: {artifact_format}")


def resolve_target_shard(base_model_path: Path, target_module: str) -> Path:
    index_path = base_model_path / "model.safetensors.index.json"
    if index_path.exists():
        payload = load_json_object(index_path)
        weight_map = payload.get("weight_map")
        if not isinstance(weight_map, dict) or target_module not in weight_map:
            raise ValueError("target tensor missing from model.safetensors.index.json")
        return base_model_path / str(weight_map[target_module])

    pt_state = base_model_path / "model_state.pt"
    if pt_state.exists():
        return pt_state

    raise ValueError("unsupported base model layout; expected model.safetensors.index.json or model_state.pt")


def load_shard_tensor(shard_path: Path, target_module: str) -> tuple[list[list[float]], str]:
    if shard_path.suffix == ".safetensors":
        if importlib.util.find_spec("safetensors") is None:
            raise ValueError("safetensors shard present but safetensors is unavailable")
        if importlib.util.find_spec("torch") is None:
            raise ValueError("safetensors shard present but torch is unavailable")
        from safetensors.torch import load_file  # type: ignore

        tensor_map = load_file(str(shard_path))
        if target_module not in tensor_map:
            raise ValueError("target tensor missing from safetensors shard")
        tensor = tensor_map[target_module]
        return [[float(value) for value in row] for row in tensor.detach().float().cpu().tolist()], str(tensor.dtype)

    payload = pickle.loads(shard_path.read_bytes())
    if not isinstance(payload, dict) or target_module not in payload:
        raise ValueError("target tensor missing from pt shard")
    tensor = payload[target_module]
    if not isinstance(tensor, list):
        raise ValueError("pt shard target tensor malformed")
    return tensor, "float32"


def apply_delta_preserving_dtype(
    base_tensor: list[list[float]],
    delta_tensor: list[list[float]],
    *,
    base_dtype: str,
) -> tuple[list[list[float]], str]:
    patched_tensor = add_tensors(copy.deepcopy(base_tensor), delta_tensor)
    return patched_tensor, base_dtype


def write_shard_tensor(
    *,
    shard_path: Path,
    target_module: str,
    patched_tensor: list[list[float]],
    target_dtype: str,
) -> None:
    if shard_path.suffix == ".safetensors":
        if importlib.util.find_spec("safetensors") is None:
            raise ValueError("safetensors shard present but safetensors is unavailable")
        if importlib.util.find_spec("torch") is None:
            raise ValueError("safetensors shard present but torch is unavailable")
        from safetensors.torch import load_file, save_file  # type: ignore
        import torch  # type: ignore

        tensor_map = load_file(str(shard_path))
        if target_module not in tensor_map:
            raise ValueError("target tensor missing from safetensors shard")
        target_tensor = tensor_map[target_module]
        dtype = target_tensor.dtype
        patched = torch.tensor(patched_tensor, dtype=torch.float32)
        tensor_map[target_module] = patched.to(dtype=dtype)
        save_file(tensor_map, str(shard_path))
        return

    payload = pickle.loads(shard_path.read_bytes())
    payload[target_module] = patched_tensor
    shard_path.write_bytes(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))


def render_review_packet(record: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Patched Model Materialization Review Packet",
            "",
            "- this is the first separately authorized patched-copy stage;",
            "- it applies the reviewed delta artifact to a copied model directory only;",
            "- it does not overwrite the base model;",
            "- it does not run inference or reaudition;",
            "- promotion and deployment remain unauthorized.",
            "",
            f"- target module: `{record['target_module']}`;",
            f"- patched model path: `{record['patched_model_path']}`;",
            f"- effective delta norm: `{record['effective_delta_norm']}`;",
            "",
            f"Next step: `{REQUIRED_NEXT_STEP}`",
        ]
    ).rstrip() + "\n"


def materialize_patched_model(
    *,
    run_id: str,
    out_root: Path,
    base_model_path: Path,
    rank1_delta_artifact_record_path: Path,
    authorize_larql_patched_model_materialization: bool,
    patched_model_dir_name: str,
) -> dict[str, Any]:
    require_authorization(authorize_larql_patched_model_materialization)
    if not base_model_path.exists():
        raise ValueError("base model path does not exist")

    record = load_json_object(rank1_delta_artifact_record_path)
    validate_artifact_record(record)
    artifact_path = verify_artifact_hash(record)
    delta_tensor = load_delta_artifact(artifact_path, str(record["artifact_format"]))

    target_module = str(record["target_module"])
    expected_shape = list(record["delta_shape"])
    if tensor_shape(delta_tensor) != expected_shape:
        raise ValueError("delta tensor shape does not match artifact record")

    out_dir = out_root / run_id
    patched_model_path = out_dir / patched_model_dir_name
    base_shard_path = resolve_target_shard(base_model_path, target_module)
    base_tensor, base_dtype = load_shard_tensor(base_shard_path, target_module)
    if tensor_shape(base_tensor) != expected_shape:
        raise ValueError("target tensor shape does not match delta shape")
    base_tensor_sha = tensor_data_sha256(base_tensor)
    patched_tensor, patched_dtype = apply_delta_preserving_dtype(
        base_tensor,
        delta_tensor,
        base_dtype=base_dtype,
    )
    patched_tensor_sha = tensor_data_sha256(patched_tensor)

    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base_model_path, patched_model_path)
    patched_shard_path = patched_model_path / base_shard_path.relative_to(base_model_path)
    write_shard_tensor(
        shard_path=patched_shard_path,
        target_module=target_module,
        patched_tensor=patched_tensor,
        target_dtype=patched_dtype,
    )

    materialization_record = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "base_model_path": str(base_model_path),
        "patched_model_path": str(patched_model_path),
        "source_rank1_delta_artifact_record_path": str(rank1_delta_artifact_record_path),
        "rank1_delta_artifact_path": str(artifact_path),
        "rank1_delta_artifact_sha256": str(record["artifact_sha256"]),
        "rank1_delta_artifact_hash_verified": True,
        "target_module": target_module,
        "target_layer": str(record["target_layer"]),
        "target_module_family": str(record["target_module_family"]),
        "delta_scale": float(record["delta_scale"]),
        "delta_shape": expected_shape,
        "base_tensor_shape": tensor_shape(base_tensor),
        "patched_tensor_shape": tensor_shape(patched_tensor),
        "base_tensor_dtype": base_dtype,
        "patched_tensor_dtype": patched_dtype,
        "base_tensor_sha256_before": base_tensor_sha,
        "patched_tensor_sha256_after": patched_tensor_sha,
        "effective_delta_norm": tensor_norm(delta_tensor),
        "effective_delta_nonzero": tensor_norm(delta_tensor) > 0.0,
        "model_inference_performed": False,
        "weight_edit_performed": True,
        "delta_artifact_written": False,
        "patched_model_materialized": True,
        "base_model_overwrite_authorized": False,
        "base_model_overwritten": False,
        "training_performed": False,
        "adapter_baseline_path": False,
        "larql_core_path": True,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": REQUIRED_NEXT_STEP,
    }
    (out_dir / "larql_patched_model_materialization_record.json").write_text(
        json.dumps(materialization_record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "patched_model_review_packet.md").write_text(
        render_review_packet(materialization_record),
        encoding="utf-8",
    )
    return materialization_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--base-model-path", required=True, type=Path)
    parser.add_argument("--rank1-delta-artifact-record", required=True, type=Path)
    parser.add_argument("--patched-model-dir-name", default="patched_model")
    parser.add_argument("--authorize-larql-patched-model-materialization", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        materialize_patched_model(
            run_id=args.run_id,
            out_root=args.out_root,
            base_model_path=args.base_model_path,
            rank1_delta_artifact_record_path=args.rank1_delta_artifact_record,
            authorize_larql_patched_model_materialization=args.authorize_larql_patched_model_materialization,
            patched_model_dir_name=args.patched_model_dir_name,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError, pickle.PickleError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
