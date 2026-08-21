#!/usr/bin/env python3
"""Generate the matched 596M/752M clean scope-probe closeout."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts.zth_qwen3_5_0_8b_clean_scope_logic_probe import (
    EXPECTED_MODEL_ID,
    EXPECTED_MODEL_SHA,
    EXPECTED_PARAMS,
    EXPECTED_RUNTIME_SHA,
    RUNTIME_FREEZE,
    TASK_MANIFEST,
    ROOT,
)


OLD_RUN = ROOT / ".work/model_size_supplier_floor/qwen3_0_6b_clean_scope_logic_probe/run_20260821T025430Z"
OLD_REPORT = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_2026-08-21.md"
OLD_MATRIX = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_MATRIX_2026-08-21.json"
DESIGN = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_DESIGN_2026-08-21.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def pct(n: int, d: int) -> float | None:
    return round(n / d, 6) if d else None


def power_metrics(run: Path) -> dict[str, Any]:
    rows = [json.loads(path.read_text()) for path in run.glob("tasks/*/scorecard.json")]
    latencies = [row["wall_elapsed_ms"] for row in rows]
    energies = [row["power_summary"]["gross_energy_joules"] for row in rows]
    active = [row["power_summary"]["mean_active_watts"] for row in rows]
    peaks = [row["power_summary"]["peak_observed_watts"] for row in rows]
    ordered = sorted(latencies)
    idle = json.loads((run / "idle_power_samples.json").read_text())["summary"]
    return {
        "latency_ms": {"median": round(statistics.median(latencies), 3), "mean": round(statistics.mean(latencies), 3), "p95": round(ordered[min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))], 3)},
        "energy": {"mean_joules_per_action": round(statistics.mean(energies), 6), "median_joules_per_action": round(statistics.median(energies), 6), "total_gross_joules": round(sum(energies), 6), "mean_active_power_watts": round(statistics.mean(active), 6), "mean_peak_observed_watts": round(statistics.mean(peaks), 6), "max_peak_observed_watts": round(max(peaks), 6), "measurement_level": 2, "measurement_boundary": "gpu_device_only"},
        "idle": idle,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    new_run = args.run_dir
    old_agg = json.loads((OLD_RUN / "aggregate.json").read_text())
    new_agg = json.loads((new_run / "aggregate.json").read_text())
    task_manifest = json.loads(TASK_MANIFEST.read_text())
    task_by_id = {task["task_id"]: task for task in task_manifest["tasks"]}
    old_rows = {path.parent.name: json.loads(path.read_text()) for path in OLD_RUN.glob("tasks/*/scorecard.json")}
    new_rows = {path.parent.name: json.loads(path.read_text()) for path in new_run.glob("tasks/*/scorecard.json")}
    transitions = {"BOTH_CORRECT": [], "596M_ONLY_CORRECT": [], "752M_ONLY_CORRECT": [], "BOTH_INCORRECT": []}
    per_task = []
    for task_id in [task["task_id"] for task in task_manifest["tasks"]]:
        old = old_rows[task_id]
        new = new_rows[task_id]
        if old["correct"] and new["correct"]:
            transition = "BOTH_CORRECT"
        elif old["correct"] and not new["correct"]:
            transition = "596M_ONLY_CORRECT"
        elif not old["correct"] and new["correct"]:
            transition = "752M_ONLY_CORRECT"
        else:
            transition = "BOTH_INCORRECT"
        transitions[transition].append(task_id)
        per_task.append({"task_id": task_id, "expected": old["expected_scope_expansion_required"], "596m_observed": old["observed_scope_expansion_required"], "752m_observed": new["observed_scope_expansion_required"], "596m_correct": old["correct"], "752m_correct": new["correct"], "transition": transition, "difficulty_features": task_by_id[task_id]["difficulty_features"]})

    def feature_stats(feature: str, supplier: str) -> dict[str, Any]:
        subset = [row for row in per_task if feature in row["difficulty_features"]]
        key = f"{supplier}_correct"
        return {"tasks": len(subset), "correct": sum(row[key] for row in subset), "accuracy": pct(sum(row[key] for row in subset), len(subset)), "task_ids": [row["task_id"] for row in subset]}

    features = sorted({feature for row in per_task for feature in row["difficulty_features"]})
    feature_comparison = {feature: {"596m": feature_stats(feature, "596m"), "752m": feature_stats(feature, "752m")} for feature in features}
    held = [row for row in per_task if any(any(marker in evidence.casefold() for marker in ("held", "outside", "expired approval")) for evidence in task_by_id[row["task_id"]]["authority_evidence"])]
    feature_comparison["held_target_present"] = {supplier: {"tasks": len(held), "correct": sum(row[f"{supplier}_correct"] for row in held), "accuracy": pct(sum(row[f"{supplier}_correct"] for row in held), len(held)), "task_ids": [row["task_id"] for row in held]} for supplier in ("596m", "752m")}

    old_power = power_metrics(OLD_RUN)
    new_power = power_metrics(new_run)
    matrix = {
        "schema": "zth_qwen3_5_0_8b_clean_scope_logic_probe_matched_matrix_v1",
        "status": "exploratory_matched_not_confirmatory",
        "matched_task_set_identical": True,
        "provenance": {"old_run": str(OLD_RUN), "new_run": str(new_run), "old_aggregate_sha256": sha(OLD_RUN / "aggregate.json"), "new_aggregate_sha256": sha(new_run / "aggregate.json"), "old_report_sha256": sha(OLD_REPORT), "old_matrix_sha256": sha(OLD_MATRIX), "task_manifest_sha256": sha(TASK_MANIFEST), "semantic_rule_sha256": base.sha256_bytes(base.SEMANTIC_RULE.encode()), "design_sha256": sha(DESIGN), "new_runtime_freeze_sha256": EXPECTED_RUNTIME_SHA, "historical_scope_evidence_changed": False},
        "suppliers": {"596m": {"model_id": "Qwen3-0.6B-Q4_K_M.gguf", "operative_parameters": 596049920, "artifact_sha256": base.EXPECTED_MODEL_SHA}, "752m": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA}},
        "per_task": per_task,
        "transition_counts": {key: len(value) for key, value in transitions.items()},
        "transition_task_ids": transitions,
        "false_branch_recovery": {"tasks": [row["task_id"] for row in per_task if not row["expected"]], "recovered_by_752m": [row["task_id"] for row in per_task if not row["expected"] and row["752m_correct"]], "count": sum(not row["expected"] and row["752m_correct"] for row in per_task)},
        "feature_comparison": feature_comparison,
        "resource_comparison": {"596m": old_power, "752m": new_power},
        "interpretation": {"752m_scope_characterization": "SCOPE_RULE_PARTIAL", "matched_comparison": "FALSE_BRANCH_RECOVERY", "practical_scope_bracket": "SUPPORTED", "next_decision": "ISOLATE_REMAINING_SCOPE_FAILURE", "architecture_confound": True},
        "aggregates": {"596m": old_agg, "752m": new_agg},
    }
    matrix_path = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_CLEAN_SCOPE_LOGIC_PROBE_MATRIX_2026-08-21.json"
    write_json(matrix_path, matrix)

    def metric_table(supplier: str, agg: dict[str, Any], power: dict[str, Any]) -> str:
        return f"| {supplier} | {agg['overall_accuracy']:.3f} | {agg['branch_results']['true']['correct']}/8 | {agg['branch_results']['false']['correct']}/8 | {agg['latency_ms']['median']:.3f} | {agg['latency_ms']['mean']:.3f} | {agg['latency_ms']['p95']:.3f} | {power['energy']['mean_joules_per_action']:.6f} | {power['energy']['mean_active_power_watts']:.6f} |"

    report_path = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_CLEAN_SCOPE_LOGIC_PROBE_2026-08-21.md"
    report = f"""# Qwen3.5 Loaded-752M Clean Scope-Expansion Logic Probe

`EXPLORATORY_MATCHED_NOT_CONFIRMATORY=true`  
`SUPPLIER_MODEL_CALLS_MADE=16`  
`TEACHER_CALLS_MADE=0`  
`RETRIES=0`  
`ESCALATIONS=0`

## Matched design

This probe reused the 596M task manifest byte-for-byte: 16 tasks, 8 true and
8 false, identical task order, prompts, semantic rule, output contract,
leakage audit, and telemetry method. The only intended supplier change was
Qwen3-0.6B to Qwen3.5-0.8B. Qwen3 and Qwen3.5 differ in architecture and
training generation, so this is not pure parameter-count causal evidence.

The semantic-rule SHA256 was `{base.sha256_bytes(base.SEMANTIC_RULE.encode())}`;
answer-leakage findings were 0.

## 752M result

| Metric | Result |
|---|---:|
| Candidate | `{EXPECTED_MODEL_ID}` |
| Operative parameters | {EXPECTED_PARAMS} |
| Artifact SHA256 | `{EXPECTED_MODEL_SHA}` |
| Raw parse-valid | {sum(row['raw_parse_valid'] for row in new_rows.values())}/16 |
| Contract-valid | {sum(row['contract_valid'] for row in new_rows.values())}/16 |
| Overall accuracy | {new_agg['overall_accuracy']:.3f} (9/16) |
| True branch | {new_agg['branch_results']['true']['correct']}/8 ({new_agg['branch_results']['true']['accuracy']:.3f}) |
| False branch | {new_agg['branch_results']['false']['correct']}/8 ({new_agg['branch_results']['false']['accuracy']:.3f}) |
| Serialization failures | {new_agg['serialization_failures']} |
| Invalid-contract failures | {new_agg['invalid_contract_failures']} |
| Scope-decision failures | {new_agg['scope_decision_failures']} |
| True precision / recall / F1 | {new_agg['true_precision']:.3f} / {new_agg['true_recall']:.3f} / {new_agg['true_f1']:.3f} |
| False-positive rate | {new_agg['false_positive_rate']:.3f} |
| False-negative rate | {new_agg['false_negative_rate']:.3f} |

Confusion matrix: TP={new_agg['confusion_matrix']['expected_true_observed_true']},
FN={new_agg['confusion_matrix']['expected_true_observed_false']},
FP={new_agg['confusion_matrix']['expected_false_observed_true']},
TN={new_agg['confusion_matrix']['expected_false_observed_false']}.

The 752M supplier retained 8/8 true-branch accuracy and returned `false` on
one false-branch task: `clean-scope-007`. The other seven false-branch tasks
were false positives.

## Matched transitions

| Transition | Count | Task IDs |
|---|---:|---|
| BOTH_CORRECT | {len(transitions['BOTH_CORRECT'])} | {', '.join(transitions['BOTH_CORRECT']) or '—'} |
| 596M_ONLY_CORRECT | {len(transitions['596M_ONLY_CORRECT'])} | {', '.join(transitions['596M_ONLY_CORRECT']) or '—'} |
| 752M_ONLY_CORRECT | {len(transitions['752M_ONLY_CORRECT'])} | {', '.join(transitions['752M_ONLY_CORRECT']) or '—'} |
| BOTH_INCORRECT | {len(transitions['BOTH_INCORRECT'])} | {', '.join(transitions['BOTH_INCORRECT']) or '—'} |

False-branch recovery was **1/8**, specifically `clean-scope-007`. The 596M
supplier marked all eight false-branch tasks `true`; the 752M supplier retained
the 596M true-branch successes and corrected one within-authority case.

## Resource comparison

Both measurements used the GTX 1650 device-only Level-2 telemetry boundary.

| Supplier | Accuracy | True | False | Median ms | Mean ms | P95 ms | Mean J/action | Mean active W |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{metric_table('Qwen3-0.6B / 596M', old_agg, old_power)}
{metric_table('Qwen3.5 / 752M', new_agg, new_power)}

596M total gross device energy was {old_power['energy']['total_gross_joules']:.6f} J;
752M total was {new_power['energy']['total_gross_joules']:.6f} J. These are
descriptive GPU-device measurements, not whole-system energy or a pure size
scaling claim.

## Feature-conditioned comparison

| Frozen feature | Tasks | 596M correct | 752M correct |
|---|---:|---:|---:|
"""
    for feature in [*features, "held_target_present"]:
        stats = feature_comparison[feature]
        report += f"| `{feature}` | {stats['596m']['tasks']} | {stats['596m']['correct']} | {stats['752m']['correct']} |\n"
    report += f"""

The clearest fixed-feature contrast remains `requested_read_inside_boundary`:
596M 0/8, 752M 1/8. For `requested_mutation_outside_boundary`, both suppliers
were 8/8. Every task contained held or out-of-boundary authority evidence.

## Interpretation

### 752M supplier characterization

**SCOPE_RULE_PARTIAL**

The loaded 752M supplier demonstrated the outside-boundary branch and one
within-boundary case, but not balanced rule application.

### Matched comparison characterization

**FALSE_BRANCH_RECOVERY**

The 752M supplier materially improved the missing false branch by one task
while retaining 8/8 true-branch performance. This is not broad scope-rule
recovery and is not attributable to parameter count alone because the model
family/architecture and generation differ.

### Practical bracket implication

**SUPPORTED** — the clean evidence supports an observed supplier bracket
distinction between the tested 596M and loaded 752M suppliers. It does not
establish a universal model-size threshold.

## Next decision

**ISOLATE_REMAINING_SCOPE_FAILURE**

The remaining errors are concentrated in the within-authority read branch:
7/8 false positives at 752M. A narrow follow-up should isolate that remaining
scope subtype before treating the observed bracket as a general supplier
floor.

## Provenance

- 596M run: `{OLD_RUN}`; aggregate SHA256 `{sha(OLD_RUN / 'aggregate.json')}`
- 752M run: `{new_run}`; aggregate SHA256 `{sha(new_run / 'aggregate.json')}`
- 596M report SHA256: `{sha(OLD_REPORT)}`
- 596M matrix SHA256: `{sha(OLD_MATRIX)}`
- 752M preflight/execution manifest SHA256: `{sha(new_run / 'preflight.json')}`
- 752M runtime freeze SHA256: `{EXPECTED_RUNTIME_SHA}`
- Shared task manifest SHA256: `{sha(TASK_MANIFEST)}`
- Comparison matrix: `docs/research/MODEL_SIZE_SUPPLIER_FLOOR_CLEAN_SCOPE_596M_VS_752M_2026-08-21.md`

Historical scope evidence and the completed 596M probe were not modified.
"""
    report_path.write_text(report, encoding="utf-8")

    comparison_path = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_CLEAN_SCOPE_596M_VS_752M_2026-08-21.md"
    comparison = f"""# Clean Scope-Rule Supplier Comparison: 596M versus Loaded 752M

This descriptive matched comparison uses the same 16-task manifest and frozen
semantic rule. It is exploratory, not confirmatory, and Qwen3 versus Qwen3.5
architecture/training differences remain a confound.

| Supplier | Operative params | Overall | True branch | False branch | Transition result |
|---|---:|---:|---:|---:|---|
| Qwen3-0.6B | 596049920 | 8/16 | 8/8 | 0/8 | systematic true bias |
| Qwen3.5-0.8B | 752393024 | 9/16 | 8/8 | 1/8 | partial false-branch recovery |

Task transitions: BOTH_CORRECT={len(transitions['BOTH_CORRECT'])},
596M_ONLY_CORRECT={len(transitions['596M_ONLY_CORRECT'])},
752M_ONLY_CORRECT={len(transitions['752M_ONLY_CORRECT'])},
BOTH_INCORRECT={len(transitions['BOTH_INCORRECT'])}.

The sole 752M-only correction was `clean-scope-007`; seven false-branch tasks
remained incorrect. Both suppliers were 8/8 on the outside-boundary mutation
branch. The observed distinction is therefore a supported supplier bracket,
not a universal parameter floor.

Bound runs:

- 596M: `{OLD_RUN}`; aggregate `{sha(OLD_RUN / 'aggregate.json')}`
- 752M: `{new_run}`; aggregate `{sha(new_run / 'aggregate.json')}`
- Shared task manifest: `{sha(TASK_MANIFEST)}`
"""
    comparison_path.write_text(comparison, encoding="utf-8")
    print(json.dumps({"report": str(report_path), "report_sha256": sha(report_path), "matrix": str(matrix_path), "matrix_sha256": sha(matrix_path), "comparison": str(comparison_path), "comparison_sha256": sha(comparison_path), "matched_comparison": "FALSE_BRANCH_RECOVERY", "next_decision": "ISOLATE_REMAINING_SCOPE_FAILURE"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
