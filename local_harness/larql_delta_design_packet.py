#!/usr/bin/env python3
"""Prepare a packet-only LARQL rank-1 delta design review artifact."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_delta_design_packet.v0"
REQUIRED_NEXT_STEP = "supervised_delta_design_review"
FILE_SCOPE_PROBES = [
    "original_larql_behavior_replay",
    "adjacent_file_anti_overfit",
    "all_files_authorized_control",
]
REGRESSION_GUARD_PROBE = "unrelated_task_regression"


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL delta design packet requires explicit opt-in authorization")


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


def cosine_similarity(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    a_norm = vector_norm(a)
    b_norm = vector_norm(b)
    if a_norm == 0.0 or b_norm == 0.0:
        return None
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    return dot / (a_norm * b_norm)


def average_vectors(vectors: list[list[float]]) -> list[float] | None:
    if not vectors:
        return None
    length = len(vectors[0])
    if any(len(vec) != length for vec in vectors):
        return None
    return [sum(float(vec[i]) for vec in vectors) / len(vectors) for i in range(length)]


def validate_inputs(
    *,
    direction_packet: dict[str, Any],
    source_capture_record: dict[str, Any],
    compact_rows: list[dict[str, Any]],
) -> None:
    if direction_packet.get("report_type") != "larql_prompt_activation_direction_packet.v0":
        raise ValueError("direction packet report_type mismatch")
    if source_capture_record.get("report_type") != "larql_activation_capture_probe.v0":
        raise ValueError("source activation capture report_type mismatch")
    if source_capture_record.get("compact_vectors_written") is not True:
        raise ValueError("source activation capture must have compact vectors written")
    if source_capture_record.get("capture_mode") != "prompt_forward":
        raise ValueError("source activation capture must use prompt_forward mode")
    if source_capture_record.get("larql_core_path") is not True:
        raise ValueError("source activation capture must keep larql_core_path true")
    if source_capture_record.get("adapter_baseline_path") is not False:
        raise ValueError("source activation capture must keep adapter_baseline_path false")
    if not compact_rows:
        raise ValueError("compact vector rows are required")


def resolve_target_metadata(
    direction_packet: dict[str, Any],
    source_capture_record: dict[str, Any],
    compact_rows: list[dict[str, Any]],
) -> tuple[str, str, str]:
    compact_target_module = None
    compact_target_layer = None
    compact_target_family = None
    for row in compact_rows:
        module = row.get("target_module")
        layer = row.get("target_layer")
        family = row.get("target_module_family")
        if module is not None:
            compact_target_module = str(module)
        if layer is not None:
            compact_target_layer = str(layer)
        if family is not None:
            compact_target_family = str(family)
        if compact_target_module and compact_target_layer and compact_target_family:
            break

    resolved: dict[str, str] = {}
    for key, compact_value in [
        ("target_module", compact_target_module),
        ("target_layer", compact_target_layer),
        ("target_module_family", compact_target_family),
    ]:
        candidates: list[tuple[str, str]] = []
        packet_value = direction_packet.get(key)
        if packet_value not in (None, "", "unknown"):
            candidates.append(("direction_packet", str(packet_value)))
        capture_value = source_capture_record.get(key)
        if capture_value not in (None, "", "unknown"):
            candidates.append(("source_activation_capture_record", str(capture_value)))
        if compact_value not in (None, "", "unknown"):
            candidates.append(("compact_vector_rows", str(compact_value)))
        if not candidates:
            raise ValueError(f"unable to resolve {key} from direction packet, source capture record, or compact vectors")
        values = {value for _, value in candidates}
        if len(values) > 1:
            raise ValueError(f"{key} provenance mismatch across sources: {candidates}")
        resolved[key] = candidates[0][1]
    return resolved["target_module"], resolved["target_layer"], resolved["target_module_family"]


def group_rows(compact_rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in compact_rows:
        grouped.setdefault(str(row.get("probe_id")), {})[str(row.get("side"))] = row
    return grouped


def select_vector_fields(source: str) -> tuple[str, str]:
    if source == "prompt_last_token":
        return "prompt_last_token_vector", "prompt_last_token_input_vector"
    if source == "prompt_mean_pool":
        return "prompt_mean_pool_vector", "prompt_mean_pool_input_vector"
    raise ValueError("selected vector source must be prompt_last_token or prompt_mean_pool")


def build_delta_design(
    *,
    compact_rows: list[dict[str, Any]],
    direction_packet: dict[str, Any],
    source_capture_record: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    grouped = group_rows(compact_rows)
    selected_source = str(direction_packet.get("recommended_vector_source", "none"))
    target_module, target_layer, target_module_family = resolve_target_metadata(
        direction_packet,
        source_capture_record,
        compact_rows,
    )

    if direction_packet.get("direction_candidate_status") != "direction_candidate_reviewable":
        status = "delta_design_rejected"
        output_field = input_field = None
        rationale = "direction packet was not reviewable"
    else:
        try:
            output_field, input_field = select_vector_fields(selected_source)
            status = "delta_design_reviewable"
            rationale = "selected vector source produced a reviewable direction basis"
        except ValueError:
            output_field = input_field = None
            status = "delta_design_rejected"
            rationale = "selected vector source was invalid"

    file_scope_output_directions: list[list[float]] = []
    file_scope_input_basis: list[list[float]] = []
    regression_input_basis: list[float] | None = None
    malformed = False
    per_probe: list[dict[str, Any]] = []
    output_vector_length = 0
    input_vector_length = 0

    if output_field is not None and input_field is not None:
        for probe_id in FILE_SCOPE_PROBES + [REGRESSION_GUARD_PROBE]:
            pair = grouped.get(probe_id, {})
            failure = pair.get("failure")
            correction = pair.get("correction")
            if failure is None or correction is None:
                malformed = True
                continue
            try:
                failure_output = [float(v) for v in failure[output_field]]
                correction_output = [float(v) for v in correction[output_field]]
                failure_input = [float(v) for v in failure[input_field]]
            except (KeyError, TypeError, ValueError):
                malformed = True
                continue
            output_direction = vector_subtract(correction_output, failure_output)
            per_probe.append(
                {
                    "probe_id": probe_id,
                    "output_direction_norm": vector_norm(output_direction),
                    "failure_input_basis_norm": vector_norm(failure_input),
                }
            )
            if probe_id in FILE_SCOPE_PROBES:
                file_scope_output_directions.append(output_direction)
                file_scope_input_basis.append(failure_input)
            else:
                regression_input_basis = failure_input

        if file_scope_output_directions:
            output_vector_length = len(file_scope_output_directions[0])
        if file_scope_input_basis:
            input_vector_length = len(file_scope_input_basis[0])

    avg_output_direction = average_vectors(file_scope_output_directions)
    avg_input_basis = average_vectors(file_scope_input_basis)
    regression_input_alignment = (
        cosine_similarity(regression_input_basis, avg_input_basis)
        if regression_input_basis is not None and avg_input_basis is not None
        else None
    )

    if status != "delta_design_rejected":
        if malformed or len(file_scope_output_directions) != 3 or len(file_scope_input_basis) != 3:
            status = "delta_design_rejected"
            rationale = "required file-scope output or input vectors were missing or malformed"
        elif avg_output_direction is None or avg_input_basis is None or output_vector_length == 0 or input_vector_length == 0:
            status = "delta_design_rejected"
            rationale = "output or input vector dimensions were invalid"
        elif regression_input_alignment is not None and regression_input_alignment >= 0.95:
            status = "delta_design_unclear"
            rationale = "regression guard input basis was too aligned with the file-scope input basis"

    design = {
        "selected_vector_source": selected_source,
        "target_module": target_module,
        "target_layer": target_layer,
        "target_module_family": target_module_family,
        "per_probe": per_probe,
        "average_file_scope_output_direction_norm": vector_norm(avg_output_direction) if avg_output_direction else None,
        "average_file_scope_input_basis_norm": vector_norm(avg_input_basis) if avg_input_basis else None,
        "regression_input_alignment_cosine": regression_input_alignment,
        "output_vector_length": output_vector_length,
        "input_vector_length": input_vector_length,
        "proposed_delta_shape": [output_vector_length, input_vector_length] if output_vector_length and input_vector_length else None,
        "rank": 1,
        "formula": "delta_W = scale * normalize(output_direction) outer normalize(input_basis)",
        "candidate_scale_ladder": ["1e-4", "1e-3", "1e-2"],
        "writes_tensor_artifact": False,
        "selected_rationale": rationale,
        "delta_design_status": status,
    }
    packet = {
        "selected_vector_source": selected_source,
        "target_module": target_module,
        "target_layer": target_layer,
        "target_module_family": target_module_family,
        "output_vector_length": output_vector_length,
        "input_vector_length": input_vector_length,
        "proposed_delta_shape": design["proposed_delta_shape"],
        "delta_design_status": status,
        "regression_input_alignment_cosine": regression_input_alignment,
        "selected_rationale": rationale,
    }
    return packet, design


def render_risk_register() -> str:
    return "\n".join(
        [
            "# LARQL Delta Design Risk Register",
            "",
            "- risk of layer 0 being too early or lexical;",
            "- risk of broad scope-policy edits;",
            "- risk of regression entanglement;",
            "- risk of a rank-1 update being too blunt;",
            "- risk of BF16 rounding hiding small deltas;",
            "- risk of larger deltas causing broad behavior changes;",
            "",
            "Mitigations:",
            "",
            "- no delta artifact is written in this task;",
            "- any scale ladder choice must be separately authorized;",
            "- any patched model must be reauditioned before acceptance.",
        ]
    ).rstrip() + "\n"


def render_review_packet(*, packet: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Delta Design Review Packet",
            "",
            "- the direction packet established a reviewable output-space correction direction;",
            "- output-space direction alone is not enough for a weight delta;",
            "- module-input vectors are required to define a rank-1 design candidate;",
            f"- selected vector source: `{packet['selected_vector_source']}`;",
            f"- proposed delta shape: `{packet['proposed_delta_shape']}`;",
            f"- delta design status: `{packet['delta_design_status']}`;",
            "- no delta artifact is written in this task;",
            "",
            f"Next step: `{REQUIRED_NEXT_STEP}`",
        ]
    ).rstrip() + "\n"


def write_packet(
    *,
    run_id: str,
    out_root: Path,
    compact_vectors_path: Path,
    direction_packet_path: Path,
    direction_coherence_report_path: Path,
    source_activation_capture_record_path: Path,
    authorize_larql_delta_design_packet: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_delta_design_packet)
    compact_rows = load_jsonl(compact_vectors_path)
    direction_packet = load_json_object(direction_packet_path)
    _direction_coherence_report = load_json_object(direction_coherence_report_path)
    source_capture_record = load_json_object(source_activation_capture_record_path)
    validate_inputs(
        direction_packet=direction_packet,
        source_capture_record=source_capture_record,
        compact_rows=compact_rows,
    )

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    packet_bits, design = build_delta_design(
        compact_rows=compact_rows,
        direction_packet=direction_packet,
        source_capture_record=source_capture_record,
    )

    (out_dir / "rank1_delta_design.json").write_text(
        json.dumps(
            {
                **design,
                "note_bf16_rounding": "BF16 rounding previously made 1e-6 ineffective",
                "note_scale_authorization": "scale choice requires separate authorization",
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    (out_dir / "delta_design_risk_register.md").write_text(render_risk_register(), encoding="utf-8")
    (out_dir / "delta_design_review_packet.md").write_text(
        render_review_packet(packet=packet_bits),
        encoding="utf-8",
    )

    packet = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_activation_capture_record_path": str(source_activation_capture_record_path),
        "source_direction_packet_path": str(direction_packet_path),
        "source_direction_coherence_report_path": str(direction_coherence_report_path),
        "compact_vectors_path": str(compact_vectors_path),
        "delta_design_packet_authorized": True,
        **packet_bits,
        "model_inference_performed": False,
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
        "delta_artifact_recommended": False,
        "required_next_step": REQUIRED_NEXT_STEP,
    }
    (out_dir / "larql_delta_design_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--compact-vectors", required=True, type=Path)
    parser.add_argument("--direction-packet", required=True, type=Path)
    parser.add_argument("--direction-coherence-report", required=True, type=Path)
    parser.add_argument("--source-activation-capture-record", required=True, type=Path)
    parser.add_argument("--authorize-larql-delta-design-packet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_packet(
            run_id=args.run_id,
            out_root=args.out_root,
            compact_vectors_path=args.compact_vectors,
            direction_packet_path=args.direction_packet,
            direction_coherence_report_path=args.direction_coherence_report,
            source_activation_capture_record_path=args.source_activation_capture_record,
            authorize_larql_delta_design_packet=args.authorize_larql_delta_design_packet,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
