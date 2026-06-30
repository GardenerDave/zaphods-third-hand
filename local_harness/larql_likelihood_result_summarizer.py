#!/usr/bin/env python3
"""Summarize multiple LARQL teacher-forced likelihood runs across scales."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPORT_TYPE = "larql_likelihood_scale_comparison.v0"
TARGET_PROBES = {
    "original_larql_behavior_replay",
    "adjacent_file_anti_overfit",
}
CONTROL_REGRESSION_PROBES = {
    "all_files_authorized_control",
    "unrelated_task_regression",
}


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL likelihood result summarization requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def parse_scale_label(path: Path) -> str:
    matches = re.findall(r"1e-[0-9]+|1e\+[0-9]+|[0-9]+e-[0-9]+|[0-9]+e\+[0-9]+", str(path))
    if matches:
        return matches[-1]
    raise ValueError(f"could not derive scale label from path: {path}")


def scale_sort_key(label: str) -> float:
    try:
        return float(label)
    except ValueError:
        return float(label.replace("_", ""))


def summarize_comparison(path: Path) -> dict[str, Any]:
    payload = load_json_object(path)
    probes = payload.get("probes")
    if not isinstance(probes, list):
        raise ValueError(f"{path}: probes must be a list")
    per_probe: dict[str, float] = {}
    target_values: list[float] = []
    control_values: list[float] = []
    for probe in probes:
        if not isinstance(probe, dict):
            raise ValueError(f"{path}: probe entry must be an object")
        probe_id = probe.get("probe_id")
        if not isinstance(probe_id, str):
            raise ValueError(f"{path}: probe_id missing")
        if "exception" in probe:
            raise ValueError(f"{path}: probe {probe_id} contains exception")
        margin_delta = probe.get("margin_delta")
        if not isinstance(margin_delta, (int, float)):
            raise ValueError(f"{path}: probe {probe_id} missing numeric margin_delta")
        margin_delta_f = float(margin_delta)
        per_probe[probe_id] = margin_delta_f
        if probe_id in TARGET_PROBES:
            target_values.append(margin_delta_f)
        if probe_id in CONTROL_REGRESSION_PROBES:
            control_values.append(margin_delta_f)
    if len(target_values) != len(TARGET_PROBES):
        raise ValueError(f"{path}: missing target probes")
    if len(control_values) != len(CONTROL_REGRESSION_PROBES):
        raise ValueError(f"{path}: missing control/regression probes")
    return {
        "scale_label": parse_scale_label(path),
        "source_comparison_path": str(path),
        "per_probe_margin_delta": per_probe,
        "target_probe_margin_delta_mean": sum(target_values) / len(target_values),
        "target_probe_margin_delta_min": min(target_values),
        "target_probe_margin_delta_max": max(target_values),
        "control_regression_margin_delta_mean": sum(control_values) / len(control_values),
        "control_regression_margin_delta_min": min(control_values),
        "control_regression_margin_delta_max": max(control_values),
    }


def is_monotonic_non_decreasing(values: list[float]) -> bool:
    return all(left <= right for left, right in zip(values, values[1:]))


def is_monotonic_non_increasing(values: list[float]) -> bool:
    return all(left >= right for left, right in zip(values, values[1:]))


def recommend_next_step(target_means: list[float], control_means: list[float], target_mono: bool, control_mono: bool) -> str:
    latest_target = target_means[-1]
    latest_control = control_means[-1]
    if control_mono and latest_control < 0.0:
        return "do_not_scale_blindly"
    if target_mono and latest_target > 0.0 and latest_control >= 0.0:
        return "reaudition_behavior_only_if_margin_flips"
    if all(value <= 0.0 for value in target_means):
        return "test_alternate_direction"
    return "test_alternate_layer"


def build_scale_comparison(comparison_paths: list[Path]) -> dict[str, Any]:
    runs = [summarize_comparison(path) for path in comparison_paths]
    runs.sort(key=lambda item: scale_sort_key(item["scale_label"]))
    target_means = [run["target_probe_margin_delta_mean"] for run in runs]
    control_means = [run["control_regression_margin_delta_mean"] for run in runs]
    target_monotonic = is_monotonic_non_decreasing(target_means)
    control_regression_monotonic = is_monotonic_non_increasing(control_means)
    return {
        "report_type": REPORT_TYPE,
        "model_inference_performed": False,
        "training_performed": False,
        "weight_edit_performed": False,
        "delta_artifact_written": False,
        "patched_model_materialized": False,
        "promotion_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "runs": runs,
        "target_probes_aggregate": {
            "means_by_scale": [
                {"scale": run["scale_label"], "margin_delta_mean": run["target_probe_margin_delta_mean"]}
                for run in runs
            ],
            "target_improvement_monotonic": target_monotonic,
        },
        "control_regression_probes_aggregate": {
            "means_by_scale": [
                {"scale": run["scale_label"], "margin_delta_mean": run["control_regression_margin_delta_mean"]}
                for run in runs
            ],
            "control_regression_monotonic": control_regression_monotonic,
        },
        "recommended_next_step": recommend_next_step(
            target_means,
            control_means,
            target_monotonic,
            control_regression_monotonic,
        ),
    }


def render_review_packet(scale_comparison: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LARQL Likelihood Scale Comparison Review Packet",
            "",
            "- this is a packet-only comparison across teacher-forced likelihood runs;",
            "- it does not run model inference, training, patching, or promotion;",
            "- the result is evidence, not authority.",
            "",
            f"- run count: `{len(scale_comparison['runs'])}`;",
            f"- target improvement monotonic: `{scale_comparison['target_probes_aggregate']['target_improvement_monotonic']}`;",
            f"- control regression monotonic: `{scale_comparison['control_regression_probes_aggregate']['control_regression_monotonic']}`;",
            f"- recommended next step: `{scale_comparison['recommended_next_step']}`;",
        ]
    ).rstrip() + "\n"


def write_likelihood_result_summary(
    *,
    run_id: str,
    out_root: Path,
    comparison_paths: list[Path],
    authorize_larql_likelihood_result_summarization: bool,
) -> dict[str, Any]:
    require_authorization(authorize_larql_likelihood_result_summarization)
    if len(comparison_paths) < 2:
        raise ValueError("at least two comparison paths are required")
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    scale_comparison = build_scale_comparison(comparison_paths)
    (out_dir / "scale_comparison.json").write_text(
        json.dumps(scale_comparison, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "scale_comparison_review_packet.md").write_text(
        render_review_packet(scale_comparison),
        encoding="utf-8",
    )
    return scale_comparison


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--comparison", dest="comparisons", action="append", required=True, type=Path)
    parser.add_argument("--authorize-larql-likelihood-result-summarization", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_likelihood_result_summary(
            run_id=args.run_id,
            out_root=args.out_root,
            comparison_paths=args.comparisons,
            authorize_larql_likelihood_result_summarization=args.authorize_larql_likelihood_result_summarization,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
