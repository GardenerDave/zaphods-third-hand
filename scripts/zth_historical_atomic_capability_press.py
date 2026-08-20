#!/usr/bin/env python3
"""Apply the reusable atomic press to preserved scope-authority evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from local_harness.atomic_capability_press import (
    compare_components,
    component_vector,
    exact_status_confusion,
    score_scope_object,
)

ROOT = Path(__file__).resolve().parents[1]
QWEN_ATOMIC_MATRIX = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_ATOMIC_CAPABILITY_MATRIX_2026-08-20.json"

RUNS = {
    "run4b": {
        "root": ROOT / ".work/run4b_scope_replication/run_20260819T231103Z",
        "fixture_dir": ROOT / "local_harness/fixtures/capability_loop/reviewed_run4b_scope",
        "selection": ROOT / ".work/run4b_scope_replication/run_20260819T231103Z/selection.json",
        "layout": "run4b",
        "prefix": "run4b-scope-",
        "role": "Qwen3-1.7B worker with external/local teacher arms",
        "report": ROOT / "docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_4B_SCOPE_2026-08-19.md",
    },
    "run5": {
        "root": ROOT / ".work/run5_mixed_economic_routing/run_20260819T013828Z",
        "fixture_dir": ROOT / "local_harness/fixtures/capability_loop/reviewed_run5_scope",
        "selection": ROOT / ".work/run5_mixed_economic_routing/run_20260819T013828Z/selections/scope.json",
        "layout": "run5",
        "prefix": "run5-scope-",
        "role": "Qwen3-1.7B worker with external/local teacher arms",
        "report": ROOT / "docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_5_MIXED_2026-08-20.md",
    },
    "run6": {
        "root": ROOT / ".work/run6_sequential_economic_routing/run_20260820T030541Z",
        "fixture_dir": ROOT / "local_harness/fixtures/capability_loop/reviewed_run6_scope",
        "selection": ROOT / ".work/run6_sequential_economic_routing/run_20260820T030541Z/selections/scope.json",
        "layout": "run6",
        "prefix": "run6-scope-",
        "role": "Qwen3-1.7B worker with local-first and external control; no observed escalation",
        "report": ROOT / "docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_6_VALIDATION_GATED_2026-08-20.md",
    },
    "run7": {
        "root": ROOT / ".work/run7_scope_escalation/run_20260820T045113Z",
        "fixture_dir": ROOT / "local_harness/fixtures/capability_loop/run7_scope",
        "selection": ROOT / ".work/run7_scope_escalation/run_20260820T045113Z/selections/scope.json",
        "layout": "run7",
        "prefix": "run7-scope-",
        "role": "Qwen3-1.7B worker with historical local/escalation arms before the later guidance-integration repair",
        "report": ROOT / "docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_7_VALIDATION_GATED_2026-08-20.md",
    },
    "run8": {
        "root": ROOT / ".work/run8_scope_escalation/run_20260820T150846Z",
        "fixture_dir": ROOT / "local_harness/fixtures/capability_loop/run8_scope",
        "selection": ROOT / ".work/run8_scope_escalation/run_20260820T150846Z/selections/scope.json",
        "layout": "run8",
        "prefix": "run8-scope-",
        "role": "Qwen3-1.7B worker with repaired escalation implementation",
        "report": ROOT / "docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_8_VALIDATION_GATED_2026-08-20.md",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def selected_ids(config: dict[str, Any]) -> list[str]:
    selection = load(config["selection"])
    return list(selection.get("included_task_ids", []))


def fixture_for(config: dict[str, Any], task_id: str) -> dict[str, Any]:
    suffix = task_id.split("-scope-", 1)[1]
    return load(config["fixture_dir"] / f"scope-{suffix}.json")


def task_root(config: dict[str, Any], task_id: str) -> Path:
    root = config["root"]
    if config["layout"] == "run4b":
        return root / "tasks" / task_id / "arms"
    if config["layout"] == "run5":
        return root / "tasks" / "scope" / task_id / "arms"
    return root / "tasks" / "scope" / task_id


def stage_dir(config: dict[str, Any], task_id: str, stage: str) -> Path:
    root = task_root(config, task_id)
    if stage == "control_external":
        return root / "control"
    if stage == "local_first":
        return root / ("treatment" if config["layout"] in {"run4b", "run5"} else "local_first")
    if stage == "escalation":
        return root / "escalation"
    raise ValueError(stage)


def raw_and_validation(config: dict[str, Any], task_id: str, stage: str) -> tuple[Path, Path]:
    directory = stage_dir(config, task_id, stage)
    return directory / "worker-retry.raw.json", directory / "worker-retry.validation.json"


def parse_stage(config: dict[str, Any], task_id: str, stage: str, reference: dict[str, Any]) -> dict[str, Any] | None:
    raw_path, validation_path = raw_and_validation(config, task_id, stage)
    if not raw_path.exists() or not validation_path.exists():
        return None
    raw_record = load(raw_path)
    content = raw_record.get("content", "")
    try:
        obj = json.loads(content)
        parse_valid = True
    except (TypeError, json.JSONDecodeError):
        obj = None
        parse_valid = False
    score = score_scope_object(obj, reference) if parse_valid else score_scope_object(None, reference)
    validation = load(validation_path)
    metadata = raw_record.get("metadata", {})
    return {
        "stage": stage,
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_sha256": sha256(raw_path),
        "validation_path": str(validation_path.relative_to(ROOT)),
        "validation_sha256": sha256(validation_path),
        "raw_parse_valid": parse_valid,
        "bare_json_object": parse_valid and not content.strip().startswith("```") if isinstance(content, str) else False,
        "transport_valid": raw_record.get("transport_valid"),
        "transport_classification": raw_record.get("transport_classification"),
        "model_identity": metadata.get("model") or metadata.get("resolved_model"),
        "score": score,
        "saved_validation_status": validation.get("validation_status"),
        "saved_failed_checks": [
            check.get("check_id")
            for check in validation.get("structural_checks", []) + validation.get("semantic_checks", [])
            if check.get("status") == "failed"
        ],
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [row["score"] for row in rows]
    def micro(key: str) -> dict[str, Any]:
        tp = sum(s[key]["true_positives"] for s in scores)
        fp = sum(s[key]["false_positives"] for s in scores)
        fn = sum(s[key]["false_negatives"] for s in scores)
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
        return {"true_positives": tp, "false_positives": fp, "false_negatives": fn, "precision": precision, "recall": recall, "f1": f1}
    return {
        "task_count": len(rows),
        "raw_parse_valid": sum(row["raw_parse_valid"] for row in rows),
        "bare_json_object": sum(row["bare_json_object"] for row in rows),
        "field_types_all_correct": sum(all(s["field_types_correct"].values()) for s in scores),
        "contract_valid": sum(s["structural_contract_valid"] for s in scores),
        "fully_validator_valid": sum(row["saved_validation_status"] == "passed" for row in rows),
        "allowed_exact": sum(s["allowed_targets"]["exact_set_match"] for s in scores),
        "held_exact": sum(s["held_targets"]["exact_set_match"] for s in scores),
        "allowed_micro": micro("allowed_targets"),
        "held_micro": micro("held_targets"),
        "authority_separation_observed_and_correct": sum(s["authority_separation"]["no_allowed_held_overlap"] is True for s in scores),
        "authority_separation_not_observable": sum(s["authority_separation"]["no_allowed_held_overlap"] is None for s in scores),
        "scope_expansion_correct": sum(s["scope_expansion"]["correct"] is True for s in scores),
        "scope_expansion_false_positive": sum(s["scope_expansion"]["false_positive"] for s in scores),
        "scope_expansion_false_negative": sum(s["scope_expansion"]["false_negative"] for s in scores),
        "scope_expansion_not_observable": sum(s["scope_expansion"]["correct"] is None for s in scores),
        "review_status_exact": sum(s["review_status"]["exact_match"] is True for s in scores),
        "review_status_confusion": exact_status_confusion(scores),
        "semantic_fields_distribution": dict(sorted(Counter(s["semantic_fields_correct"] for s in scores).items())),
        "near_miss_3_of_4": sum(s["semantic_fields_correct"] == 3 for s in scores),
        "near_miss_2_of_4": sum(s["semantic_fields_correct"] == 2 for s in scores),
        "error_cluster_tags": dict(Counter(tag for s in scores for tag in s["error_cluster_tags"])),
    }


def capability_class(aggregate_row: dict[str, Any], key: str) -> str:
    n = aggregate_row["task_count"]
    if key == "machine_readable_output": count = aggregate_row["raw_parse_valid"]
    elif key == "field_typing": count = aggregate_row["field_types_all_correct"]
    elif key == "allowed_target_identification": count = aggregate_row["allowed_exact"]
    elif key == "held_target_identification": count = aggregate_row["held_exact"]
    elif key == "authority_separation": count = aggregate_row["authority_separation_observed_and_correct"]
    elif key == "scope_expansion": count = aggregate_row["scope_expansion_correct"]
    elif key == "review_status": count = aggregate_row["review_status_exact"]
    elif key == "full_task": count = aggregate_row["fully_validator_valid"]
    else: return "INSUFFICIENT_EVIDENCE"
    if count == n: return "DEMONSTRATED"
    if count: return "PARTIAL"
    return "NOT_DEMONSTRATED"


def run_press(name: str, config: dict[str, Any]) -> dict[str, Any]:
    ids = selected_ids(config)
    rows: dict[str, dict[str, Any]] = {}
    for task_id in ids:
        fixture = fixture_for(config, task_id)
        reference = fixture["validator"]["reference_facts"]
        stages = {}
        for stage in ("control_external", "local_first", "escalation"):
            parsed = parse_stage(config, task_id, stage, reference)
            if parsed is not None:
                stages[stage] = parsed
        repairs = None
        if "local_first" in stages and "escalation" in stages:
            repairs = compare_components(
                component_vector(stages["local_first"]["score"], parse_valid=stages["local_first"]["raw_parse_valid"]),
                component_vector(stages["escalation"]["score"], parse_valid=stages["escalation"]["raw_parse_valid"]),
            )
        rows[task_id] = {
            "reference": {
                "source_path": str((config["fixture_dir"] / f"scope-{task_id.split('-scope-', 1)[1]}.json").relative_to(ROOT)),
                "source_sha256": sha256(config["fixture_dir"] / f"scope-{task_id.split('-scope-', 1)[1]}.json"),
                "reference_facts": reference,
                "difficulty_features": fixture.get("calibration", {}).get("difficulty_features", []),
            },
            "stages": stages,
            "repair_delta_local_to_escalation": repairs,
        }
    stage_aggs = {}
    for stage in ("control_external", "local_first", "escalation"):
        stage_rows = [task["stages"][stage] for task in rows.values() if stage in task["stages"]]
        if stage_rows:
            stage_aggs[stage] = aggregate(stage_rows)
    capability = {stage: {key: capability_class(agg, key) for key in ("machine_readable_output", "field_typing", "allowed_target_identification", "held_target_identification", "authority_separation", "scope_expansion", "review_status", "full_task")} for stage, agg in stage_aggs.items()}
    feature_conditioning: dict[str, dict[str, list[int]]] = {}
    for task in rows.values():
        features = task["reference"]["difficulty_features"]
        for stage, stage_row in task["stages"].items():
            feature_conditioning.setdefault(stage, {})
            for feature in features:
                feature_conditioning[stage].setdefault(feature, []).append(stage_row["score"]["semantic_fields_correct"])
    feature_summary = {
        stage: {
            feature: {
                "task_observations": len(values),
                "semantic_fields_correct_total": sum(values),
                "semantic_fields_correct_mean": sum(values) / len(values),
                "distribution": dict(sorted(Counter(values).items())),
            }
            for feature, values in sorted(features.items())
        }
        for stage, features in sorted(feature_conditioning.items())
    }
    repair_deltas = {task_id: task["repair_delta_local_to_escalation"] for task_id, task in rows.items() if task["repair_delta_local_to_escalation"]}
    return {
        "run": name,
        "root": str(config["root"].relative_to(ROOT)),
        "role_and_runtime": config["role"],
        "selected_task_ids": ids,
        "task_count": len(ids),
        "stages": rows,
        "stage_aggregates": stage_aggs,
        "capability_map": capability,
        "feature_conditioning": feature_summary,
        "repair_deltas": repair_deltas,
        "tree_sha256_manifest": tree_hashes(config["root"]),
        "aggregate_sha256": sha256(config["root"] / "aggregate.json"),
        "report_path": str(config["report"].relative_to(ROOT)),
        "report_sha256": sha256(config["report"]),
    }


def main() -> None:
    output = ROOT / "docs/research/HISTORICAL_ATOMIC_CAPABILITY_MATRIX_2026-08-20.json"
    result = {
        "schema": "zth_historical_atomic_capability_matrix_v1",
        "model_calls_made": 0,
        "historical_artifacts_changed": False,
        "task_family_scope": "scope-authority-boundary only; no cross-family synthesis",
        "runs": {name: run_press(name, config) for name, config in RUNS.items()},
    }
    existing_qwen = load(QWEN_ATOMIC_MATRIX)
    result["existing_qwen3_0_6b_press"] = {
        "classification": "PARTIAL_ATOMIC_PRESS_COMPATIBLE",
        "reason": "Imported from the preserved 0.6B atomic press rather than rescored; it contains reference facts, per-task scores, and immutable run-tree manifests, but its two exploratory interface views are not the same lifecycle as Runs 4B-8.",
        "source_path": str(QWEN_ATOMIC_MATRIX.relative_to(ROOT)),
        "source_sha256": sha256(QWEN_ATOMIC_MATRIX),
        "aggregates": existing_qwen.get("aggregates"),
        "capability_map": existing_qwen.get("capability_map"),
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    compatibility = {
        "schema": "zth_historical_atomic_capability_compatibility_v1",
        "model_calls_made": 0,
        "historical_artifacts_changed": False,
        "runs": {
            name: {
                "classification": "FULL_ATOMIC_PRESS_COMPATIBLE",
                "reason": "Selected scope tasks have preserved raw worker outputs, deterministic validation artifacts, fixture reference facts, and durable provenance; stage availability is recorded in the matrix.",
                "run_root": str(config["root"].relative_to(ROOT)),
                "aggregate_sha256": sha256(config["root"] / "aggregate.json"),
                "report_path": str(config["report"].relative_to(ROOT)),
                "report_sha256": sha256(config["report"]),
                "fixture_dir": str(config["fixture_dir"].relative_to(ROOT)),
                "fixture_manifest_sha256": sha256(config["fixture_dir"] / "manifest.json"),
                "selected_count": len(selected_ids(config)),
                "stages_observed": sorted({stage for task in result["runs"][name]["stages"].values() for stage in task["stages"]}),
                "escalation_branch_observed": bool(result["runs"][name]["repair_deltas"]),
            }
            for name, config in RUNS.items()
        },
        "existing_qwen3_0_6b_press": result["existing_qwen3_0_6b_press"],
    }
    (ROOT / "docs/research/HISTORICAL_ATOMIC_CAPABILITY_COMPATIBILITY_2026-08-20.json").write_text(json.dumps(compatibility, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "historical_atomic_matrix_written", "runs": len(RUNS), "model_calls": 0}))


if __name__ == "__main__":
    main()
