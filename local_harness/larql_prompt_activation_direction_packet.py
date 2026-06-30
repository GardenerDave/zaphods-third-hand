#!/usr/bin/env python3
"""Prepare a packet-only LARQL prompt activation direction candidate review artifact."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_prompt_activation_direction_packet.v0"
REQUIRED_NEXT_STEP = "supervised_direction_candidate_review"
FILE_SCOPE_PROBES = [
    "original_larql_behavior_replay",
    "adjacent_file_anti_overfit",
    "all_files_authorized_control",
]
REGRESSION_GUARD_PROBE = "unrelated_task_regression"


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL prompt activation direction packet requires explicit opt-in authorization")


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


def validate_source_artifacts(
    *,
    capture_record: dict[str, Any],
    activation_summary: dict[str, Any],
    compact_rows: list[dict[str, Any]],
) -> None:
    if capture_record.get("report_type") != "larql_activation_capture_probe.v0":
        raise ValueError("source activation capture report_type mismatch")
    if capture_record.get("compact_vectors_written") is not True:
        raise ValueError("source activation capture must have compact vectors written")
    if capture_record.get("capture_mode") != "prompt_forward":
        raise ValueError("source activation capture must use prompt_forward mode")
    if capture_record.get("larql_core_path") is not True:
        raise ValueError("source activation capture must keep larql_core_path true")
    if capture_record.get("adapter_baseline_path") is not False:
        raise ValueError("source activation capture must keep adapter_baseline_path false")
    if activation_summary.get("selected_candidate_direction_status") not in {
        "prompt_signal_detected",
        "prompt_signal_unclear",
        "prompt_capture_failed",
    }:
        raise ValueError("activation summary selected_candidate_direction_status mismatch")
    if not compact_rows:
        raise ValueError("compact vector rows are required")


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


def pairwise_cosines(vectors: list[list[float]]) -> list[float]:
    values: list[float] = []
    for idx, left in enumerate(vectors):
        for right in vectors[idx + 1 :]:
            cosine = cosine_similarity(left, right)
            if cosine is not None:
                values.append(cosine)
    return values


def evaluate_source_selection(
    *,
    file_scope_vectors: list[list[float]],
    regression_vector: list[float] | None,
) -> dict[str, Any]:
    avg_file_scope = average_vectors(file_scope_vectors)
    file_scope_pairwise = pairwise_cosines(file_scope_vectors)
    file_scope_mean_cosine = (
        sum(file_scope_pairwise) / len(file_scope_pairwise) if file_scope_pairwise else None
    )
    regression_vs_file_scope_cosine = (
        cosine_similarity(regression_vector, avg_file_scope)
        if regression_vector is not None and avg_file_scope is not None
        else None
    )
    coherence_margin = (
        file_scope_mean_cosine - regression_vs_file_scope_cosine
        if file_scope_mean_cosine is not None and regression_vs_file_scope_cosine is not None
        else None
    )
    eligible = (
        len(file_scope_vectors) == 3
        and avg_file_scope is not None
        and file_scope_mean_cosine is not None
        and file_scope_mean_cosine > 0.0
        and regression_vs_file_scope_cosine is not None
        and coherence_margin is not None
        and coherence_margin > 0.0
    )
    return {
        "file_scope_vectors_present": len(file_scope_vectors),
        "average_direction": avg_file_scope,
        "pairwise_cosines": file_scope_pairwise,
        "file_scope_mean_cosine": file_scope_mean_cosine,
        "regression_vs_file_scope_cosine": regression_vs_file_scope_cosine,
        "coherence_margin": coherence_margin,
        "eligible": eligible,
    }


def split_probe_rows(compact_rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in compact_rows:
        probe_id = str(row.get("probe_id"))
        side = str(row.get("side"))
        grouped.setdefault(probe_id, {})[side] = row
    return grouped


def build_direction_candidates(compact_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    grouped = split_probe_rows(compact_rows)
    per_probe: list[dict[str, Any]] = []
    file_scope_last_vectors: list[list[float]] = []
    file_scope_mean_vectors: list[list[float]] = []
    regression_last_vector: list[float] | None = None
    regression_mean_vector: list[float] | None = None
    malformed = False

    for probe_id, pair_rows in grouped.items():
        failure = pair_rows.get("failure")
        correction = pair_rows.get("correction")
        if failure is None or correction is None:
            malformed = True
            continue
        try:
            failure_last = [float(v) for v in failure["prompt_last_token_vector"]]
            correction_last = [float(v) for v in correction["prompt_last_token_vector"]]
            failure_mean = [float(v) for v in failure["prompt_mean_pool_vector"]]
            correction_mean = [float(v) for v in correction["prompt_mean_pool_vector"]]
            last_direction = vector_subtract(correction_last, failure_last)
            mean_direction = vector_subtract(correction_mean, failure_mean)
        except (KeyError, TypeError, ValueError):
            malformed = True
            continue

        entry = {
            "probe_id": probe_id,
            "vector_length": len(last_direction),
            "last_token_direction_norm": vector_norm(last_direction),
            "mean_pool_direction_norm": vector_norm(mean_direction),
        }
        per_probe.append(entry)

        if probe_id in FILE_SCOPE_PROBES:
            file_scope_last_vectors.append(last_direction)
            file_scope_mean_vectors.append(mean_direction)
        elif probe_id == REGRESSION_GUARD_PROBE:
            regression_last_vector = last_direction
            regression_mean_vector = mean_direction

    last_eval = evaluate_source_selection(
        file_scope_vectors=file_scope_last_vectors,
        regression_vector=regression_last_vector,
    )
    mean_eval = evaluate_source_selection(
        file_scope_vectors=file_scope_mean_vectors,
        regression_vector=regression_mean_vector,
    )

    status = "direction_candidate_rejected"
    recommended_vector_source = "none"
    rationale = "required direction vectors were missing or malformed"
    if not malformed and len(file_scope_last_vectors) == 3 and len(file_scope_mean_vectors) == 3:
        selection_scores = {
            "prompt_last_token": {
                "file_scope_mean_cosine": last_eval["file_scope_mean_cosine"],
                "regression_vs_file_scope_cosine": last_eval["regression_vs_file_scope_cosine"],
                "coherence_margin": last_eval["coherence_margin"],
                "eligible": last_eval["eligible"],
            },
            "prompt_mean_pool": {
                "file_scope_mean_cosine": mean_eval["file_scope_mean_cosine"],
                "regression_vs_file_scope_cosine": mean_eval["regression_vs_file_scope_cosine"],
                "coherence_margin": mean_eval["coherence_margin"],
                "eligible": mean_eval["eligible"],
            },
        }
        eligible_sources = [
            (source_name, score)
            for source_name, score in selection_scores.items()
            if score["eligible"]
        ]
        if eligible_sources:
            eligible_sources.sort(
                key=lambda item: (
                    float(item[1]["coherence_margin"]),
                    float(item[1]["file_scope_mean_cosine"]),
                ),
                reverse=True,
            )
            best_source, best_score = eligible_sources[0]
            status = "direction_candidate_reviewable"
            recommended_vector_source = best_source
            rationale = (
                f"selected {best_source} by max positive coherence margin "
                f"({best_score['coherence_margin']}) against regression entanglement"
            )
        else:
            status = "direction_candidate_unclear"
            rationale = "vectors exist but file-scope coherence was weak or regression alignment was too high"
    else:
        selection_scores = {
            "prompt_last_token": {
                "file_scope_mean_cosine": last_eval["file_scope_mean_cosine"],
                "regression_vs_file_scope_cosine": last_eval["regression_vs_file_scope_cosine"],
                "coherence_margin": last_eval["coherence_margin"],
                "eligible": last_eval["eligible"],
            },
            "prompt_mean_pool": {
                "file_scope_mean_cosine": mean_eval["file_scope_mean_cosine"],
                "regression_vs_file_scope_cosine": mean_eval["regression_vs_file_scope_cosine"],
                "coherence_margin": mean_eval["coherence_margin"],
                "eligible": mean_eval["eligible"],
            },
        }

    direction_candidates = {
        "per_probe": per_probe,
        "average_file_scope_last_token_direction_norm": (
            vector_norm(last_eval["average_direction"]) if last_eval["average_direction"] else None
        ),
        "average_file_scope_mean_pool_direction_norm": (
            vector_norm(mean_eval["average_direction"]) if mean_eval["average_direction"] else None
        ),
        "regression_guard_last_token_direction_norm": (
            vector_norm(regression_last_vector) if regression_last_vector is not None else None
        ),
        "regression_guard_mean_pool_direction_norm": (
            vector_norm(regression_mean_vector) if regression_mean_vector is not None else None
        ),
    }
    coherence_report = {
        "file_scope_last_token_pairwise_cosines": last_eval["pairwise_cosines"],
        "file_scope_mean_pool_pairwise_cosines": mean_eval["pairwise_cosines"],
        "file_scope_last_token_mean_cosine": last_eval["file_scope_mean_cosine"],
        "file_scope_mean_pool_mean_cosine": mean_eval["file_scope_mean_cosine"],
        "regression_vs_file_scope_last_token_cosine": last_eval["regression_vs_file_scope_cosine"],
        "regression_vs_file_scope_mean_pool_cosine": mean_eval["regression_vs_file_scope_cosine"],
        "last_token_coherence_margin": last_eval["coherence_margin"],
        "mean_pool_coherence_margin": mean_eval["coherence_margin"],
        "selection_rule": "max_positive_coherence_margin",
        "selection_scores": selection_scores,
        "selected_rationale": rationale,
        "direction_candidate_status": status,
        "recommended_vector_source": recommended_vector_source,
    }
    return direction_candidates, coherence_report


def resolve_target_metadata(
    capture_record: dict[str, Any],
    compact_rows: list[dict[str, Any]],
) -> tuple[str, str, str]:
    for key in ["target_module", "target_layer", "target_module_family"]:
        value = capture_record.get(key)
        if value not in (None, "", "unknown"):
            continue
        break
    else:
        return (
            str(capture_record["target_module"]),
            str(capture_record["target_layer"]),
            str(capture_record["target_module_family"]),
        )

    for row in compact_rows:
        module = row.get("target_module")
        layer = row.get("target_layer")
        family = row.get("target_module_family")
        if module not in (None, "", "unknown") and layer not in (None, "", "unknown") and family not in (None, "", "unknown"):
            return str(module), str(layer), str(family)
    raise ValueError("unable to resolve target metadata from source activation capture record or compact vectors")


def render_risk_register() -> str:
    return "\n".join(
        [
            "# LARQL Prompt Activation Direction Risk Register",
            "",
            "- risk of editing general refusal or scope behavior too broadly;",
            "- risk of overfitting to specific file names;",
            "- risk that the all-files-authorized control pushes opposite behavior from the hold-out probes;",
            "- risk that unrelated summarization is entangled with the same direction;",
            "- risk of layer 0 being too early or too lexical;",
            "- risk of vectors reflecting prompt wording rather than target policy;",
            "",
            "Mitigations:",
            "",
            "- review this packet before any delta artifact;",
            "- no delta writing occurs in this task;",
            "- require later reaudition before accepting any behavior change.",
        ]
    ).rstrip() + "\n"


def render_review_packet(
    *,
    direction_candidate_status: str,
    recommended_vector_source: str,
    coherence_report: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# LARQL Prompt Activation Direction Review Packet",
            "",
            "- prompt-forward activation capture produced compact evidence vectors;",
            "- compact vectors remain evidence, not a model modification;",
            f"- direction candidate status: `{direction_candidate_status}`;",
            f"- recommended vector source: `{recommended_vector_source}`;",
            "- no delta artifact is written in this task;",
            "- no promotion is authorized.",
            "",
            "Coherence observations:",
            "",
            f"- file-scope last-token mean cosine: `{coherence_report.get('file_scope_last_token_mean_cosine')}`;",
            f"- file-scope mean-pool mean cosine: `{coherence_report.get('file_scope_mean_pool_mean_cosine')}`;",
            f"- regression-vs-file last-token cosine: `{coherence_report.get('regression_vs_file_scope_last_token_cosine')}`;",
            f"- regression-vs-file mean-pool cosine: `{coherence_report.get('regression_vs_file_scope_mean_pool_cosine')}`;",
            "",
            f"Next step: `{REQUIRED_NEXT_STEP}`",
        ]
    ).rstrip() + "\n"


def write_packet(
    *,
    run_id: str,
    out_root: Path,
    compact_vectors_path: Path,
    activation_summary_path: Path,
    source_activation_capture_record_path: Path,
    authorize_larql_direction_candidate_packet: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_direction_candidate_packet)

    capture_record = load_json_object(source_activation_capture_record_path)
    activation_summary = load_json_object(activation_summary_path)
    compact_rows = load_jsonl(compact_vectors_path)
    validate_source_artifacts(
        capture_record=capture_record,
        activation_summary=activation_summary,
        compact_rows=compact_rows,
    )
    target_module, target_layer, target_module_family = resolve_target_metadata(
        capture_record,
        compact_rows,
    )

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    direction_candidates, coherence_report = build_direction_candidates(compact_rows)
    direction_status = coherence_report["direction_candidate_status"]
    recommended_vector_source = coherence_report["recommended_vector_source"]

    (out_dir / "direction_candidates.json").write_text(
        json.dumps(direction_candidates, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "direction_coherence_report.json").write_text(
        json.dumps(coherence_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "direction_risk_register.md").write_text(render_risk_register(), encoding="utf-8")
    (out_dir / "direction_review_packet.md").write_text(
        render_review_packet(
            direction_candidate_status=direction_status,
            recommended_vector_source=recommended_vector_source,
            coherence_report=coherence_report,
        ),
        encoding="utf-8",
    )

    packet = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_activation_capture_record_path": str(source_activation_capture_record_path),
        "source_activation_summary_path": str(activation_summary_path),
        "compact_vectors_path": str(compact_vectors_path),
        "target_module": target_module,
        "target_layer": target_layer,
        "target_module_family": target_module_family,
        "direction_packet_authorized": True,
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
        "direction_candidate_status": direction_status,
        "recommended_vector_source": recommended_vector_source,
        "delta_artifact_recommended": False,
        "required_next_step": REQUIRED_NEXT_STEP,
    }
    (out_dir / "larql_prompt_activation_direction_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--compact-vectors", required=True, type=Path)
    parser.add_argument("--activation-summary", required=True, type=Path)
    parser.add_argument("--source-activation-capture-record", required=True, type=Path)
    parser.add_argument("--authorize-larql-direction-candidate-packet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_packet(
            run_id=args.run_id,
            out_root=args.out_root,
            compact_vectors_path=args.compact_vectors,
            activation_summary_path=args.activation_summary,
            source_activation_capture_record_path=args.source_activation_capture_record,
            authorize_larql_direction_candidate_packet=args.authorize_larql_direction_candidate_packet,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
