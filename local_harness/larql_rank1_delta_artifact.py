#!/usr/bin/env python3
"""Write a standalone gated LARQL rank-1 delta artifact from a reviewed design packet."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import pickle
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_rank1_delta_artifact.v0"
REQUIRED_NEXT_STEP = "supervised_delta_artifact_review"
FILE_SCOPE_PROBES = [
    "original_larql_behavior_replay",
    "adjacent_file_anti_overfit",
    "all_files_authorized_control",
]


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL rank1 delta artifact requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"{path}: expected JSON object rows")
        rows.append(item)
    return rows


def vector_subtract(a: list[float], b: list[float]) -> list[float]:
    if len(a) != len(b):
        raise ValueError("vector length mismatch")
    return [float(x) - float(y) for x, y in zip(a, b)]


def vector_norm(vec: list[float]) -> float:
    return math.sqrt(sum(float(x) * float(x) for x in vec))


def average_vectors(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        raise ValueError("expected non-empty vectors")
    length = len(vectors[0])
    if any(len(vec) != length for vec in vectors):
        raise ValueError("vector length mismatch across rows")
    return [sum(float(vec[i]) for vec in vectors) / len(vectors) for i in range(length)]


def normalize_vector(vec: list[float]) -> tuple[list[float], float]:
    norm = vector_norm(vec)
    if norm <= 0.0:
        raise ValueError("vector norm must be positive")
    return [float(x) / norm for x in vec], norm


def outer_product(left: list[float], right: list[float], scale: float) -> list[list[float]]:
    return [[scale * l * r for r in right] for l in left]


def tensor_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_vector_fields(source: str) -> tuple[str, str]:
    if source == "prompt_last_token":
        return "prompt_last_token_vector", "prompt_last_token_input_vector"
    if source == "prompt_mean_pool":
        return "prompt_mean_pool_vector", "prompt_mean_pool_input_vector"
    raise ValueError("selected vector source must be prompt_last_token or prompt_mean_pool")


def validate_inputs(
    *,
    delta_design_packet: dict[str, Any],
    rank1_delta_design: dict[str, Any],
    source_capture_record: dict[str, Any],
) -> None:
    if delta_design_packet.get("report_type") != "larql_delta_design_packet.v0":
        raise ValueError("delta design packet report_type mismatch")
    if delta_design_packet.get("delta_design_status") != "delta_design_reviewable":
        raise ValueError("delta design packet must be reviewable")
    if rank1_delta_design.get("rank") != 1:
        raise ValueError("rank1 delta design must have rank 1")
    if source_capture_record.get("report_type") != "larql_activation_capture_probe.v0":
        raise ValueError("source activation capture report_type mismatch")
    if source_capture_record.get("compact_vectors_written") is not True:
        raise ValueError("source activation capture must have compact vectors written")


def group_rows(compact_rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in compact_rows:
        grouped.setdefault(str(row.get("probe_id")), {})[str(row.get("side"))] = row
    return grouped


def recompute_vectors(
    *,
    compact_rows: list[dict[str, Any]],
    selected_vector_source: str,
) -> tuple[list[float], float, list[float], float]:
    output_field, input_field = select_vector_fields(selected_vector_source)
    grouped = group_rows(compact_rows)
    output_directions: list[list[float]] = []
    input_basis_vectors: list[list[float]] = []
    for probe_id in FILE_SCOPE_PROBES:
        pair = grouped.get(probe_id, {})
        failure = pair.get("failure")
        correction = pair.get("correction")
        if failure is None or correction is None:
            raise ValueError(f"missing failure/correction rows for {probe_id}")
        try:
            failure_output = [float(v) for v in failure[output_field]]
            correction_output = [float(v) for v in correction[output_field]]
            failure_input = [float(v) for v in failure[input_field]]
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"malformed vectors for {probe_id}")
        output_directions.append(vector_subtract(correction_output, failure_output))
        input_basis_vectors.append(failure_input)
    avg_output_direction = average_vectors(output_directions)
    avg_input_basis = average_vectors(input_basis_vectors)
    output_unit, output_norm = normalize_vector(avg_output_direction)
    input_unit, input_norm = normalize_vector(avg_input_basis)
    return output_unit, output_norm, input_unit, input_norm


def write_artifact(
    *,
    out_dir: Path,
    target_module: str,
    delta_tensor: list[list[float]],
) -> tuple[Path, str]:
    if importlib.util.find_spec("safetensors") is not None:
        from safetensors.numpy import save_file  # type: ignore
        import numpy as np  # type: ignore

        artifact_path = out_dir / "rank1_delta.safetensors"
        save_file({"delta": np.array(delta_tensor, dtype=np.float32)}, str(artifact_path), metadata={"target_module": target_module})
        return artifact_path, "safetensors"

    artifact_path = out_dir / "rank1_delta.pt"
    artifact_path.write_bytes(
        pickle.dumps(
            {
                "target_module": target_module,
                "delta": delta_tensor,
            },
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    )
    return artifact_path, "pt"


def render_review_packet(record: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Rank-1 Delta Artifact Review Packet",
            "",
            "- this is the first separately authorized tensor artifact stage;",
            "- it writes a standalone delta artifact only;",
            "- it does not apply the delta to any model;",
            "- it does not overwrite base weights;",
            "- it does not promote or deploy anything;",
            "- patched model materialization and reaudition remain separate gates.",
            "",
            f"- target module: `{record['target_module']}`;",
            f"- selected vector source: `{record['selected_vector_source']}`;",
            f"- delta shape: `{record['delta_shape']}`;",
            f"- artifact format: `{record['artifact_format']}`;",
            "",
            f"Next step: `{REQUIRED_NEXT_STEP}`",
        ]
    ).rstrip() + "\n"


def write_record(
    *,
    run_id: str,
    out_root: Path,
    compact_vectors_path: Path,
    delta_design_packet_path: Path,
    rank1_delta_design_path: Path,
    source_activation_capture_record_path: Path,
    delta_scale: float,
    authorize_larql_rank1_delta_artifact: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_rank1_delta_artifact)
    if delta_scale <= 0.0:
        raise ValueError("delta scale must be positive")

    compact_rows = load_jsonl(compact_vectors_path)
    delta_design_packet = load_json_object(delta_design_packet_path)
    rank1_delta_design = load_json_object(rank1_delta_design_path)
    source_capture_record = load_json_object(source_activation_capture_record_path)
    validate_inputs(
        delta_design_packet=delta_design_packet,
        rank1_delta_design=rank1_delta_design,
        source_capture_record=source_capture_record,
    )

    selected_vector_source = str(delta_design_packet.get("selected_vector_source", "none"))
    target_module = str(delta_design_packet["target_module"])
    target_layer = str(delta_design_packet["target_layer"])
    target_module_family = str(delta_design_packet["target_module_family"])

    output_unit, output_norm, input_unit, input_norm = recompute_vectors(
        compact_rows=compact_rows,
        selected_vector_source=selected_vector_source,
    )
    delta_tensor = outer_product(output_unit, input_unit, delta_scale)
    delta_shape = [len(delta_tensor), len(delta_tensor[0]) if delta_tensor else 0]
    delta_tensor_norm = math.sqrt(sum(value * value for row in delta_tensor for value in row))

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_path, artifact_format = write_artifact(
        out_dir=out_dir,
        target_module=target_module,
        delta_tensor=delta_tensor,
    )
    artifact_hash = tensor_sha256(artifact_path)

    record = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_delta_design_packet_path": str(delta_design_packet_path),
        "source_rank1_delta_design_path": str(rank1_delta_design_path),
        "source_activation_capture_record_path": str(source_activation_capture_record_path),
        "compact_vectors_path": str(compact_vectors_path),
        "rank1_delta_artifact_authorized": True,
        "selected_vector_source": selected_vector_source,
        "target_module": target_module,
        "target_layer": target_layer,
        "target_module_family": target_module_family,
        "delta_scale": delta_scale,
        "output_vector_length": len(output_unit),
        "input_vector_length": len(input_unit),
        "delta_shape": delta_shape,
        "delta_rank": 1,
        "output_direction_norm": output_norm,
        "input_basis_norm": input_norm,
        "delta_tensor_norm": delta_tensor_norm,
        "artifact_path": str(artifact_path),
        "artifact_format": artifact_format,
        "artifact_sha256": artifact_hash,
        "conservative_scale_warning": delta_scale > 1e-2,
        "bf16_rounding_note": "BF16 rounding previously made 1e-6 ineffective",
        "model_inference_performed": False,
        "weight_edit_performed": False,
        "delta_artifact_written": True,
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
    (out_dir / "larql_rank1_delta_artifact_record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "rank1_delta_artifact_review_packet.md").write_text(
        render_review_packet(record),
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--compact-vectors", required=True, type=Path)
    parser.add_argument("--delta-design-packet", required=True, type=Path)
    parser.add_argument("--rank1-delta-design", required=True, type=Path)
    parser.add_argument("--source-activation-capture-record", required=True, type=Path)
    parser.add_argument("--delta-scale", required=True, type=float)
    parser.add_argument("--authorize-larql-rank1-delta-artifact", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_record(
            run_id=args.run_id,
            out_root=args.out_root,
            compact_vectors_path=args.compact_vectors,
            delta_design_packet_path=args.delta_design_packet,
            rank1_delta_design_path=args.rank1_delta_design,
            source_activation_capture_record_path=args.source_activation_capture_record,
            delta_scale=args.delta_scale,
            authorize_larql_rank1_delta_artifact=args.authorize_larql_rank1_delta_artifact,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
