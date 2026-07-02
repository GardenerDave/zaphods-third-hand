#!/usr/bin/env python3
"""Build a model-free LARQL continuation direction packet."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_continuation_direction_packet.v0"
VECTOR_REPORT_TYPE = "larql_continuation_direction_vectors.v0"
RECOMMENDED_NEXT_STEP = "continuation_rank1_delta_design"
REQUIRED_NEXT_STEP = "supervised_continuation_direction_review"
ALLOWED_DIRECTION_MODES = {"target_minus_control"}
REQUIRED_SELECTION_ACTIONS = {
    "boost_corrected_semantic_token",
    "suppress_failure_semantic_token",
    "protect_control_corrected_token",
    "protect_control_failure_token",
}


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL continuation direction packet requires explicit opt-in authorization")


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


def dot(a: list[float], b: list[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def mean_vectors(rows: list[dict[str, Any]], field: str) -> list[float]:
    vectors = [row[field] for row in rows]
    if not vectors:
        raise ValueError("no vectors available")
    length = len(vectors[0])
    if any(len(vec) != length for vec in vectors):
        raise ValueError("vector lengths are inconsistent")
    return [sum(vec[i] for vec in vectors) / len(vectors) for i in range(length)]


def subtract(a: list[float], b: list[float]) -> list[float]:
    if len(a) != len(b):
        raise ValueError("vector lengths are inconsistent")
    return [float(x) - float(y) for x, y in zip(a, b)]


def normalize(vec: list[float]) -> list[float]:
    norm = l2_norm(vec)
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError("direction norm is zero or non-finite")
    return [float(x) / norm for x in vec]


def cosine(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b):
        return None
    na = l2_norm(a)
    nb = l2_norm(b)
    if na <= 0.0 or nb <= 0.0 or not math.isfinite(na) or not math.isfinite(nb):
        return None
    return dot(a, b) / (na * nb)


def validate_source_record(record: dict[str, Any]) -> None:
    for field in [
        "training_performed",
        "generation_performed",
        "promotion_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "base_model_overwritten",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        if record.get(field) is not False:
            raise ValueError(f"{field} must be false")
    for field in ["target_module", "target_module_family"]:
        if record.get(field) in (None, ""):
            raise ValueError(f"{field} must be present in source capture record")


def validate_optional_count_match(name: str, summary_value: Any, count_value: int) -> None:
    if summary_value is None:
        return
    if summary_value != count_value:
        raise ValueError(f"{name} does not match row count")


def validate_summary(summary: dict[str, Any]) -> None:
    if summary.get("capture_status") not in {"completed", "completed_with_warnings"}:
        raise ValueError("capture_status must be completed or completed_with_warnings")
    if summary.get("vector_source") != "continuation_prediction_position":
        raise ValueError("vector_source must be continuation_prediction_position")


def build_grouped_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    boost_rows = [row for row in rows if row.get("selection_action") == "boost_corrected_semantic_token"]
    suppress_rows = [row for row in rows if row.get("selection_action") == "suppress_failure_semantic_token"]
    control_rows = [
        row
        for row in rows
        if row.get("selection_action") in {"protect_control_corrected_token", "protect_control_failure_token"}
    ]
    return boost_rows, suppress_rows, control_rows


def validate_rows(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    if not rows:
        raise ValueError("no vector rows")
    boost_rows, suppress_rows, control_rows = build_grouped_rows(rows)
    if not boost_rows:
        raise ValueError("missing boost rows")
    if not suppress_rows:
        raise ValueError("missing suppress rows")
    if not control_rows:
        raise ValueError("missing control rows")
    target_modules = {row.get("target_module") for row in rows}
    target_families = {row.get("target_module_family") for row in rows}
    if len(target_modules) != 1 or next(iter(target_modules)) in (None, ""):
        raise ValueError("target_module is missing or inconsistent across rows")
    if len(target_families) != 1 or next(iter(target_families)) in (None, ""):
        raise ValueError("target_module_family is missing or inconsistent across rows")
    input_lengths = {len(row["module_input_vector"]) for row in rows if isinstance(row.get("module_input_vector"), list)}
    output_lengths = {len(row["module_output_vector"]) for row in rows if isinstance(row.get("module_output_vector"), list)}
    if len(input_lengths) != 1:
        raise ValueError("module_input_vector lengths are inconsistent")
    if len(output_lengths) != 1:
        raise ValueError("module_output_vector lengths are inconsistent")
    if any(row.get("prediction_position") is None for row in rows):
        raise ValueError("prediction positions missing")
    for row in rows:
        if "vector_source" in row and row.get("vector_source") != "continuation_prediction_position":
            raise ValueError("vector_source must be continuation_prediction_position")
    if any(row.get("selection_action") not in REQUIRED_SELECTION_ACTIONS for row in rows):
        raise ValueError("unexpected selection action")


def build_direction_vectors(rows: list[dict[str, Any]]) -> dict[str, Any]:
    boost_rows, suppress_rows, control_rows = build_grouped_rows(rows)
    boost_output_mean = mean_vectors(boost_rows, "module_output_vector")
    suppress_output_mean = mean_vectors(suppress_rows, "module_output_vector")
    control_output_mean = mean_vectors(control_rows, "module_output_vector")
    boost_input_mean = mean_vectors(boost_rows, "module_input_vector")
    suppress_input_mean = mean_vectors(suppress_rows, "module_input_vector")
    control_input_mean = mean_vectors(control_rows, "module_input_vector")
    target_output_mean = [(x + y) / 2.0 for x, y in zip(boost_output_mean, suppress_output_mean)]
    target_input_mean = [(x + y) / 2.0 for x, y in zip(boost_input_mean, suppress_input_mean)]
    output_delta = subtract(target_output_mean, control_output_mean)
    input_delta = subtract(target_input_mean, control_input_mean)
    output_norm = l2_norm(output_delta)
    input_norm = l2_norm(input_delta)
    if not math.isfinite(output_norm) or output_norm <= 0.0:
        raise ValueError("zero-norm output direction")
    if not math.isfinite(input_norm) or input_norm <= 0.0:
        raise ValueError("zero-norm input direction")
    output_cosine = cosine(target_output_mean, control_output_mean)
    input_cosine = cosine(target_input_mean, control_input_mean)
    return {
        "boost_output_mean": boost_output_mean,
        "suppress_output_mean": suppress_output_mean,
        "control_output_mean": control_output_mean,
        "boost_input_mean": boost_input_mean,
        "suppress_input_mean": suppress_input_mean,
        "control_input_mean": control_input_mean,
        "continuation_output_direction": normalize(output_delta),
        "continuation_input_direction": normalize(input_delta),
        "output_direction_norm_before_normalization": output_norm,
        "input_direction_norm_before_normalization": input_norm,
        "output_cosine_target_control": output_cosine,
        "input_cosine_target_control": input_cosine,
    }


def write_continuation_direction_packet(
    *,
    run_id: str,
    out_root: Path,
    continuation_activation_vectors: Path,
    continuation_activation_summary: Path,
    source_capture_record: Path | None,
    direction_mode: str,
    authorize_larql_continuation_direction_packet: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_continuation_direction_packet)
    if direction_mode not in ALLOWED_DIRECTION_MODES:
        raise ValueError("unsupported direction mode")
    out_dir = out_root / run_id
    if out_dir.exists():
        raise ValueError("output directory already exists")
    out_dir.mkdir(parents=True, exist_ok=False)

    rows = load_jsonl_rows(continuation_activation_vectors)
    summary = load_json_object(continuation_activation_summary)
    validate_summary(summary)
    validate_rows(rows, summary)
    validate_optional_count_match("selected_token_count", summary.get("selected_token_count"), len(rows))
    validate_optional_count_match("captured_vector_count", summary.get("captured_vector_count"), len(rows))
    if source_capture_record is not None:
        capture_record = load_json_object(source_capture_record)
        validate_source_record(capture_record)
        if "vector_source" in capture_record and capture_record.get("vector_source") != "continuation_prediction_position":
            raise ValueError("vector_source in source capture record must be continuation_prediction_position")
        if capture_record.get("target_module") not in (None, "", rows[0]["target_module"]):
            raise ValueError("target_module in source capture record does not match vector rows")
        if capture_record.get("target_module_family") not in (None, "", rows[0]["target_module_family"]):
            raise ValueError("target_module_family in source capture record does not match vector rows")
        if capture_record.get("captured_vector_count") not in (None, len(rows)):
            raise ValueError("captured_vector_count in source capture record does not match row count")
    else:
        capture_record = None

    boost_rows, suppress_rows, control_rows = build_grouped_rows(rows)
    vectors = build_direction_vectors(rows)

    packet = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "evidence_only": True,
        "model_free_packet": True,
        "direction_mode": direction_mode,
        "source_continuation_activation_vectors_path": str(continuation_activation_vectors),
        "source_continuation_activation_summary_path": str(continuation_activation_summary),
        "source_capture_record_path": str(source_capture_record) if source_capture_record is not None else None,
        "target_module": next(iter({row["target_module"] for row in rows})),
        "target_module_family": next(iter({row["target_module_family"] for row in rows})),
        "vector_source": "continuation_prediction_position",
        "boost_count": len(boost_rows),
        "suppress_count": len(suppress_rows),
        "control_count": len(control_rows),
        "input_vector_length": len(vectors["continuation_input_direction"]),
        "output_vector_length": len(vectors["continuation_output_direction"]),
        "output_direction_norm_before_normalization": vectors["output_direction_norm_before_normalization"],
        "input_direction_norm_before_normalization": vectors["input_direction_norm_before_normalization"],
        "recommended_next_step": RECOMMENDED_NEXT_STEP,
        "claim_boundary": {
            "packet_designs_direction_only": True,
            "no_inference": True,
            "no_generation": True,
            "no_training": True,
            "no_weight_edit": True,
            "no_delta_artifact": True,
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
        "source_capture_record_missing_warning": capture_record is None,
    }

    vector_payload = {
        "report_type": VECTOR_REPORT_TYPE,
        "run_id": run_id,
        "target_module": next(iter({row["target_module"] for row in rows})),
        "target_module_family": next(iter({row["target_module_family"] for row in rows})),
        "vector_source": "continuation_prediction_position",
        "continuation_output_direction": vectors["continuation_output_direction"],
        "continuation_input_direction": vectors["continuation_input_direction"],
        "boost_output_mean": vectors["boost_output_mean"],
        "suppress_output_mean": vectors["suppress_output_mean"],
        "control_output_mean": vectors["control_output_mean"],
        "boost_input_mean": vectors["boost_input_mean"],
        "suppress_input_mean": vectors["suppress_input_mean"],
        "control_input_mean": vectors["control_input_mean"],
    }

    (out_dir / "larql_continuation_direction_packet_record.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "continuation_direction_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "continuation_direction_vectors.json").write_text(
        json.dumps(vector_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    review = "\n".join(
        [
            "# LARQL Continuation Direction Packet Review",
            "",
            f"- source vectors path: `{continuation_activation_vectors}`;",
            f"- target module: `{packet['target_module']}`;",
            f"- vector source: `{packet['vector_source']}`;",
            f"- boost count: `{packet['boost_count']}`;",
            f"- suppress count: `{packet['suppress_count']}`;",
            f"- control count: `{packet['control_count']}`;",
            f"- input vector length: `{packet['input_vector_length']}`;",
            f"- output vector length: `{packet['output_vector_length']}`;",
            f"- output direction norm before normalization: `{packet['output_direction_norm_before_normalization']}`;",
            f"- input direction norm before normalization: `{packet['input_direction_norm_before_normalization']}`;",
            "",
            f"- recommended next construction step: `{RECOMMENDED_NEXT_STEP}`;",
            f"- required review step: `{REQUIRED_NEXT_STEP}`;",
            f"- source capture record missing warning: `{packet['source_capture_record_missing_warning']}`;",
            "",
            "## Claim Boundary",
            "",
            "- this packet designs direction only;",
            "- it does not run inference, generation, training, weight edits, delta artifacts, materialization, or promotion;",
            "- evidence, not authority.",
            "",
            "## Authority Flags",
            "",
            f"- model_inference_performed: `{packet['model_inference_performed']}`;",
            f"- generation_performed: `{packet['generation_performed']}`;",
            f"- training_performed: `{packet['training_performed']}`;",
            f"- lora_or_peft_used: `{packet['lora_or_peft_used']}`;",
            f"- weight_edit_performed: `{packet['weight_edit_performed']}`;",
            f"- delta_artifact_written: `{packet['delta_artifact_written']}`;",
            f"- patched_model_materialized: `{packet['patched_model_materialized']}`;",
            f"- promotion_authorized: `{packet['promotion_authorized']}`;",
            f"- automatic_failure_to_curriculum_capture_authorized: `{packet['automatic_failure_to_curriculum_capture_authorized']}`;",
            "",
            f"Next step: `{REQUIRED_NEXT_STEP}`",
        ]
    ).rstrip() + "\n"
    (out_dir / "continuation_direction_review_packet.md").write_text(review, encoding="utf-8")
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--continuation-activation-vectors", required=True, type=Path)
    parser.add_argument("--continuation-activation-summary", required=True, type=Path)
    parser.add_argument("--source-capture-record", type=Path)
    parser.add_argument("--direction-mode", default="target_minus_control")
    parser.add_argument("--authorize-larql-continuation-direction-packet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_continuation_direction_packet(
            run_id=args.run_id,
            out_root=args.out_root,
            continuation_activation_vectors=args.continuation_activation_vectors,
            continuation_activation_summary=args.continuation_activation_summary,
            source_capture_record=args.source_capture_record,
            direction_mode=args.direction_mode,
            authorize_larql_continuation_direction_packet=args.authorize_larql_continuation_direction_packet,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
