#!/usr/bin/env python3
"""Build a model-free LARQL continuation rank-1 delta design packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_continuation_rank1_delta_design.v0"
RECOMMENDED_NEXT_STEP = "continuation_rank1_delta_artifact"
REQUIRED_NEXT_STEP = "supervised_continuation_rank1_delta_design_review"


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL continuation rank1 delta design requires explicit opt-in authorization")


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


def validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("report_type") != "larql_continuation_direction_packet.v0":
        raise ValueError("source continuation direction packet report_type mismatch")
    if packet.get("evidence_only") is not True:
        raise ValueError("source continuation direction packet must be evidence_only true")
    if packet.get("model_free_packet") is not True:
        raise ValueError("source continuation direction packet must be model_free_packet true")
    if packet.get("recommended_next_step") != "continuation_rank1_delta_design":
        raise ValueError("source continuation direction packet recommended_next_step must be continuation_rank1_delta_design")
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
    if packet.get("target_module") in (None, ""):
        raise ValueError("target_module missing")
    if packet.get("target_module_family") != "mlp_projection":
        raise ValueError("target_module_family must be mlp_projection")
    if packet.get("vector_source") != "continuation_prediction_position":
        raise ValueError("vector_source must be continuation_prediction_position")


def validate_vectors(packet: dict[str, Any], vectors: dict[str, Any], delta_scale: float) -> None:
    if vectors.get("report_type") != "larql_continuation_direction_vectors.v0":
        raise ValueError("source continuation direction vectors report_type mismatch")
    for field in ["target_module", "target_module_family", "vector_source"]:
        if vectors.get(field) != packet.get(field):
            raise ValueError(f"{field} mismatch between packet and vectors")
    output_direction = vectors.get("continuation_output_direction")
    input_direction = vectors.get("continuation_input_direction")
    if not isinstance(output_direction, list) or not output_direction:
        raise ValueError("continuation_output_direction missing")
    if not isinstance(input_direction, list) or not input_direction:
        raise ValueError("continuation_input_direction missing")
    if len(output_direction) != int(packet["output_vector_length"]):
        raise ValueError("output direction length does not match packet")
    if len(input_direction) != int(packet["input_vector_length"]):
        raise ValueError("input direction length does not match packet")
    output_norm = l2_norm(output_direction)
    input_norm = l2_norm(input_direction)
    if not math.isfinite(output_norm) or output_norm <= 0.0:
        raise ValueError("output direction norm is zero or non-finite")
    if not math.isfinite(input_norm) or input_norm <= 0.0:
        raise ValueError("input direction norm is zero or non-finite")
    if abs(output_norm - 1.0) > 1e-4 or abs(input_norm - 1.0) > 1e-4:
        raise ValueError("input/output direction norms are not approximately 1.0")
    if not math.isfinite(delta_scale) or delta_scale <= 0.0:
        raise ValueError("delta_scale must be positive and finite")


def validate_source_capture_record(record: dict[str, Any], packet: dict[str, Any]) -> None:
    if "model_inference_performed" in record and record.get("model_inference_performed") is not True:
        raise ValueError("model_inference_performed must be true in source capture record when present")
    for field in [
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
        if record.get(field) is not False:
            raise ValueError(f"{field} must be false")
    if record.get("target_module") not in (None, packet["target_module"]):
        raise ValueError("target_module in source capture record does not match packet")
    if record.get("target_module_family") not in (None, packet["target_module_family"]):
        raise ValueError("target_module_family in source capture record does not match packet")


def write_continuation_rank1_delta_design(
    *,
    run_id: str,
    out_root: Path,
    continuation_direction_packet: Path,
    continuation_direction_vectors: Path,
    delta_scale: float,
    authorize_larql_continuation_rank1_delta_design: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_continuation_rank1_delta_design)
    out_dir = out_root / run_id
    if out_dir.exists():
        raise ValueError("output directory already exists")
    out_dir.mkdir(parents=True, exist_ok=False)

    packet = load_json_object(continuation_direction_packet)
    vectors = load_json_object(continuation_direction_vectors)
    validate_packet(packet)
    validate_vectors(packet, vectors, delta_scale)

    if packet.get("source_capture_record_path"):
        source_capture_record = load_json_object(Path(packet["source_capture_record_path"]))
        validate_source_capture_record(source_capture_record, packet)

    output_direction = [float(v) for v in vectors["continuation_output_direction"]]
    input_direction = [float(v) for v in vectors["continuation_input_direction"]]
    output_norm = l2_norm(output_direction)
    input_norm = l2_norm(input_direction)
    if abs(output_norm - 1.0) > 1e-4 or abs(input_norm - 1.0) > 1e-4:
        raise ValueError("input/output direction norms are not approximately 1.0")

    packet_record = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "evidence_only": True,
        "model_free_packet": True,
        "delta_design_only": True,
        "source_continuation_direction_packet_path": str(continuation_direction_packet),
        "source_continuation_direction_vectors_path": str(continuation_direction_vectors),
        "target_module": packet["target_module"],
        "target_module_family": packet["target_module_family"],
        "vector_source": packet["vector_source"],
        "rank": 1,
        "delta_scale": delta_scale,
        "proposed_delta_shape": [int(packet["output_vector_length"]), int(packet["input_vector_length"])],
        "output_vector_length": int(packet["output_vector_length"]),
        "input_vector_length": int(packet["input_vector_length"]),
        "output_direction_norm": output_norm,
        "input_direction_norm": input_norm,
        "expected_delta_frobenius_norm": delta_scale,
        "expected_nonzero_count": int(packet["output_vector_length"]) * int(packet["input_vector_length"]),
        "continuation_output_direction_sha256": stable_vector_hash(output_direction),
        "continuation_input_direction_sha256": stable_vector_hash(input_direction),
        "recommended_next_step": RECOMMENDED_NEXT_STEP,
        "claim_boundary": {
            "packet_designs_rank1_delta_only": True,
            "no_inference": True,
            "no_generation": True,
            "no_training": True,
            "no_lora_or_peft": True,
            "no_weight_edit": True,
            "no_delta_artifact_written": True,
            "no_materialization": True,
            "no_promotion": True,
            "evidence_not_authority": True,
        },
        "model_inference_performed": False,
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
    }

    (out_dir / "larql_continuation_rank1_delta_design_record.json").write_text(
        json.dumps(packet_record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "continuation_rank1_delta_design_packet.json").write_text(
        json.dumps(packet_record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "continuation_rank1_delta_design_review_packet.md").write_text(
        "\n".join(
            [
                "# LARQL Continuation Rank-1 Delta Design Review Packet",
                "",
                f"- source direction packet path: `{continuation_direction_packet}`;",
                f"- target module: `{packet['target_module']}`;",
                f"- vector source: `{packet['vector_source']}`;",
                f"- rank: `{packet_record['rank']}`;",
                f"- delta scale: `{delta_scale}`;",
                f"- proposed delta shape: `{packet_record['proposed_delta_shape']}`;",
                f"- expected frobenius norm: `{packet_record['expected_delta_frobenius_norm']}`;",
                f"- output direction sha256: `{packet_record['continuation_output_direction_sha256']}`;",
                f"- input direction sha256: `{packet_record['continuation_input_direction_sha256']}`;",
                "",
                f"- recommended next construction step: `{RECOMMENDED_NEXT_STEP}`;",
                f"- required review step: `{REQUIRED_NEXT_STEP}`;",
                "",
                "## Claim Boundary",
                "",
                "- this packet designs rank-1 delta only;",
                "- it does not run inference, generation, training, weight edits, delta artifacts, materialization, or promotion;",
                "- evidence, not authority.",
                "",
                "## Authority Flags",
                "",
                f"- model_inference_performed: `{packet_record['model_inference_performed']}`;",
                f"- generation_performed: `{packet_record['generation_performed']}`;",
                f"- training_performed: `{packet_record['training_performed']}`;",
                f"- lora_or_peft_used: `{packet_record['lora_or_peft_used']}`;",
                f"- weight_edit_performed: `{packet_record['weight_edit_performed']}`;",
                f"- delta_artifact_written: `{packet_record['delta_artifact_written']}`;",
                f"- patched_model_materialized: `{packet_record['patched_model_materialized']}`;",
                f"- promotion_authorized: `{packet_record['promotion_authorized']}`;",
                f"- automatic_failure_to_curriculum_capture_authorized: `{packet_record['automatic_failure_to_curriculum_capture_authorized']}`;",
            ]
        ).rstrip()
        + "\n",
        encoding="utf-8",
    )
    return packet_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--continuation-direction-packet", required=True, type=Path)
    parser.add_argument("--continuation-direction-vectors", required=True, type=Path)
    parser.add_argument("--delta-scale", type=float, default=1e-2)
    parser.add_argument("--authorize-larql-continuation-rank1-delta-design", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_continuation_rank1_delta_design(
            run_id=args.run_id,
            out_root=args.out_root,
            continuation_direction_packet=args.continuation_direction_packet,
            continuation_direction_vectors=args.continuation_direction_vectors,
            delta_scale=args.delta_scale,
            authorize_larql_continuation_rank1_delta_design=args.authorize_larql_continuation_rank1_delta_design,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
