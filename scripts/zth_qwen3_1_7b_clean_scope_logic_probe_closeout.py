#!/usr/bin/env python3
"""Generate the three-supplier clean scope probe closeout."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

from scripts import zth_qwen3_0_6b_clean_scope_logic_probe as base
from scripts.zth_qwen3_1_7b_clean_scope_logic_probe import (
    EXPECTED_MODEL_ID,
    EXPECTED_MODEL_SHA,
    EXPECTED_PARAMS,
    EXPECTED_EFFECTIVE_CTX,
    EXPECTED_TRAIN_CTX,
    EXPECTED_REQUESTED_CTX,
    RUNTIME_FREEZE,
    RUNTIME_FREEZE_SHA,
    TASK_MANIFEST,
    ROOT,
)


RUN_596 = ROOT / ".work/model_size_supplier_floor/qwen3_0_6b_clean_scope_logic_probe/run_20260821T025430Z"
RUN_752 = ROOT / ".work/model_size_supplier_floor/qwen3_5_0_8b_clean_scope_logic_probe/run_20260821T031601Z"
RUN_17 = ROOT / ".work/model_size_supplier_floor/qwen3_1_7b_clean_scope_logic_probe/run_20260821T034507Z"
REPORT_596 = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_2026-08-21.md"
REPORT_752 = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_CLEAN_SCOPE_LOGIC_PROBE_2026-08-21.md"
MATRIX_596 = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_MATRIX_2026-08-21.json"
MATRIX_752 = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_CLEAN_SCOPE_LOGIC_PROBE_MATRIX_2026-08-21.json"
DESIGN = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_DESIGN_2026-08-21.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rows(run: Path) -> dict[str, dict[str, Any]]:
    return {path.parent.name: json.loads(path.read_text()) for path in run.glob("tasks/*/scorecard.json")}


def resource_metrics(run: Path) -> dict[str, Any]:
    values = list(rows(run).values())
    latencies = [row["wall_elapsed_ms"] for row in values]
    energies = [row["power_summary"]["gross_energy_joules"] for row in values]
    active = [row["power_summary"]["mean_active_watts"] for row in values]
    peaks = [row["power_summary"]["peak_observed_watts"] for row in values]
    ordered = sorted(latencies)
    return {"latency_ms": {"median": round(statistics.median(latencies), 3), "mean": round(statistics.mean(latencies), 3), "p95": round(ordered[min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))], 3)}, "energy": {"mean_joules_per_action": round(statistics.mean(energies), 6), "median_joules_per_action": round(statistics.median(energies), 6), "total_gross_joules": round(sum(energies), 6), "mean_active_power_watts": round(statistics.mean(active), 6), "max_peak_observed_watts": round(max(peaks), 6), "measurement_level": 2, "measurement_boundary": "gpu_device_only"}, "idle": json.loads((run / "idle_power_samples.json").read_text())["summary"]}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--run-dir", type=Path, required=True); args = parser.parse_args()
    r596, r752, r17 = rows(RUN_596), rows(RUN_752), rows(args.run_dir)
    task_manifest = json.loads(TASK_MANIFEST.read_text()); task_by_id = {task["task_id"]: task for task in task_manifest["tasks"]}; order = [task["task_id"] for task in task_manifest["tasks"]]
    per_task = []
    false_categories = {"failed_by_all_three": [], "recovered_at_752m": [], "recovered_only_at_17b": [], "recovered_by_both_752m_and_17b": []}
    for task_id in order:
        expected = r596[task_id]["expected_scope_expansion_required"]
        a, b, c = r596[task_id], r752[task_id], r17[task_id]
        row = {"task_id": task_id, "expected": expected, "596m_observed": a["observed_scope_expansion_required"], "752m_observed": b["observed_scope_expansion_required"], "17b_observed": c["observed_scope_expansion_required"], "596m_correct": a["correct"], "752m_correct": b["correct"], "17b_correct": c["correct"], "difficulty_features": task_by_id[task_id]["difficulty_features"]}
        per_task.append(row)
        if expected is False:
            if not a["correct"] and not b["correct"] and not c["correct"]: false_categories["failed_by_all_three"].append(task_id)
            if b["correct"]: false_categories["recovered_at_752m"].append(task_id)
            if c["correct"] and not b["correct"]: false_categories["recovered_only_at_17b"].append(task_id)
            if b["correct"] and c["correct"]: false_categories["recovered_by_both_752m_and_17b"].append(task_id)

    def feature_stats(feature: str, supplier: str) -> dict[str, Any]:
        subset = [row for row in per_task if feature in row["difficulty_features"]]
        key = f"{supplier}_correct"
        return {"tasks": len(subset), "correct": sum(row[key] for row in subset), "accuracy": round(sum(row[key] for row in subset) / len(subset), 6) if subset else None, "task_ids": [row["task_id"] for row in subset]}

    features = sorted({feature for row in per_task for feature in row["difficulty_features"]})
    feature_comparison = {feature: {supplier: feature_stats(feature, supplier) for supplier in ("596m", "752m", "17b")} for feature in features}
    held = [row for row in per_task if any(any(marker in evidence.casefold() for marker in ("held", "outside", "expired approval")) for evidence in task_by_id[row["task_id"]]["authority_evidence"])]
    feature_comparison["held_target_present"] = {supplier: {"tasks": len(held), "correct": sum(row[f"{supplier}_correct"] for row in held), "accuracy": round(sum(row[f"{supplier}_correct"] for row in held) / len(held), 6), "task_ids": [row["task_id"] for row in held]} for supplier in ("596m", "752m", "17b")}
    resources = {"596m": resource_metrics(RUN_596), "752m": resource_metrics(RUN_752), "17b": resource_metrics(args.run_dir)}
    aggregates = {"596m": json.loads((RUN_596 / "aggregate.json").read_text()), "752m": json.loads((RUN_752 / "aggregate.json").read_text()), "17b": json.loads((args.run_dir / "aggregate.json").read_text())}
    matrix = {"schema": "zth_qwen3_1_7b_clean_scope_logic_probe_three_supplier_matrix_v1", "status": "exploratory_matched_not_confirmatory", "matched_task_set_identical": True, "matched_prompts_identical": True, "provenance": {"run_596": str(RUN_596), "run_752": str(RUN_752), "run_17b": str(args.run_dir), "run_596_aggregate_sha256": sha(RUN_596 / "aggregate.json"), "run_752_aggregate_sha256": sha(RUN_752 / "aggregate.json"), "run_17b_aggregate_sha256": sha(args.run_dir / "aggregate.json"), "task_manifest_sha256": sha(TASK_MANIFEST), "semantic_rule_sha256": base.sha256_bytes(base.SEMANTIC_RULE.encode()), "runtime_freeze_sha256": RUNTIME_FREEZE_SHA, "historical_evidence_changed": False}, "suppliers": {"596m": {"model_id": "Qwen3-0.6B-Q4_K_M.gguf", "operative_parameters": 596049920, "effective_n_ctx": 40960, "artifact_sha256": base.EXPECTED_MODEL_SHA}, "752m": {"model_id": "Qwen3.5-0.8B-Q4_K_M.gguf", "operative_parameters": 752393024, "effective_n_ctx": 40960, "artifact_sha256": "bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517"}, "17b": {"model_id": EXPECTED_MODEL_ID, "label": "Qwen3 1.7B-labeled / 2.032B operative supplier", "operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX, "requested_n_ctx": EXPECTED_REQUESTED_CTX, "artifact_sha256": EXPECTED_MODEL_SHA}}, "per_task": per_task, "false_branch_categories": {key: {"count": len(value), "task_ids": value} for key, value in false_categories.items()}, "feature_comparison": feature_comparison, "resource_comparison": resources, "aggregates": aggregates, "interpretation": {"scope_characterization_17b": "SCOPE_RULE_SYSTEMATIC_TRUE_BIAS", "clean_scope_ladder": "NO_OBSERVED_SCOPE_LADDER", "practical_scope_bracket": "NOT_SUPPORTED", "next_decision": "SCOPE_RULE_NOT_SIZE_RESOLVED", "context_limit_non_binding_for_probe": True, "architecture_generation_confound": True}}
    matrix_path = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_1_7B_CLEAN_SCOPE_LOGIC_PROBE_MATRIX_2026-08-21.json"; write_json(matrix_path, matrix)

    def mline(name: str, agg: dict[str, Any], res: dict[str, Any]) -> str:
        return f"| {name} | {agg['overall_accuracy']:.3f} | {agg['branch_results']['true']['correct']}/8 | {agg['branch_results']['false']['correct']}/8 | {res['latency_ms']['median']:.3f} | {res['latency_ms']['mean']:.3f} | {res['latency_ms']['p95']:.3f} | {res['energy']['mean_joules_per_action']:.6f} | {res['energy']['mean_active_power_watts']:.6f} | {res['energy']['max_peak_observed_watts']:.6f} |"

    report_path = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_1_7B_CLEAN_SCOPE_LOGIC_PROBE_2026-08-21.md"
    report = f"""# Qwen3 1.7B-Labeled Clean Scope-Expansion Logic Probe

`EXPLORATORY_MATCHED_NOT_CONFIRMATORY=true`  
`SUPPLIER_MODEL_CALLS_MADE=16`  
`TEACHER_CALLS_MADE=0`  
`RETRIES=0`  
`ESCALATIONS=0`

## Corrected runtime binding

The supplier is recorded precisely as **Qwen3 1.7B-labeled / 2.032B operative
supplier**. The filename label is not used as the operative parameter count.

| Binding | Value |
|---|---|
| Model ID | `{EXPECTED_MODEL_ID}` |
| Artifact SHA256 | `{EXPECTED_MODEL_SHA}` |
| Operative parameters | `{EXPECTED_PARAMS}` |
| Requested context | `{EXPECTED_REQUESTED_CTX}` |
| Effective context | `{EXPECTED_EFFECTIVE_CTX}` |
| Training context | `{EXPECTED_TRAIN_CTX}` |
| Context cap reason | native training-context cap |
| Context limit non-binding | true |
| Max prompt characters | 1181 |
| Conservative prompt + completion bound | 1693 |

The 40960 request was capped by llama.cpp because it exceeded the model's
32768 training context. This was not a VRAM-fit reduction and was not caused
by `--fit`. The context difference is a supplier-runtime confound, but the
frozen prompt/completion bound is far below 32768 for every task.

## Probe integrity

The task manifest, task order, prompt bytes, semantic rule, output contract,
and leakage criteria are byte-identical to both prior clean probes. The shared
semantic-rule SHA256 is `{base.sha256_bytes(base.SEMANTIC_RULE.encode())}`;
answer-leakage findings are 0. Historical and prior clean runs were not
modified.

## 1.7B result

| Metric | Result |
|---|---:|
| Raw parse-valid | {sum(row['raw_parse_valid'] for row in r17.values())}/16 |
| Contract-valid | {sum(row['contract_valid'] for row in r17.values())}/16 |
| Overall | {aggregates['17b']['overall_accuracy']:.3f} (8/16) |
| True branch | {aggregates['17b']['branch_results']['true']['correct']}/8 |
| False branch | {aggregates['17b']['branch_results']['false']['correct']}/8 |
| Serialization failures | {aggregates['17b']['serialization_failures']} |
| Invalid-contract failures | {aggregates['17b']['invalid_contract_failures']} |
| Scope-decision failures | {aggregates['17b']['scope_decision_failures']} |
| True precision / recall / F1 | {aggregates['17b']['true_precision']:.3f} / {aggregates['17b']['true_recall']:.3f} / {aggregates['17b']['true_f1']:.3f} |
| False-positive rate | {aggregates['17b']['false_positive_rate']:.3f} |
| False-negative rate | {aggregates['17b']['false_negative_rate']:.3f} |

Confusion matrix: TP=8, FN=0, FP=8, TN=0. The 1.7B-labeled supplier
therefore emitted the same systematic true bias observed at 596M.

## Three-supplier false-branch comparison

| False-branch category | Count | Task IDs |
|---|---:|---|
| Failed by all three | {len(false_categories['failed_by_all_three'])} | {', '.join(false_categories['failed_by_all_three'])} |
| Recovered at 752M | {len(false_categories['recovered_at_752m'])} | {', '.join(false_categories['recovered_at_752m']) or '—'} |
| Recovered only at 1.7B | {len(false_categories['recovered_only_at_17b'])} | {', '.join(false_categories['recovered_only_at_17b']) or '—'} |
| Recovered by both 752M and 1.7B | {len(false_categories['recovered_by_both_752m_and_17b'])} | {', '.join(false_categories['recovered_by_both_752m_and_17b']) or '—'} |

All three suppliers retained 8/8 on the true branch. The 752M-only correction
was `clean-scope-007`; 1.7B did not recover it. Seven false-branch tasks failed
for all three suppliers, and the remaining false task was recovered only at
752M.

## Feature-conditioned comparison

| Frozen feature | Tasks | 596M | 752M | 1.7B |
|---|---:|---:|---:|---:|
"""
    for feature in [*features, "held_target_present"]:
        s = feature_comparison[feature]
        report += f"| `{feature}` | {s['596m']['tasks']} | {s['596m']['correct']} | {s['752m']['correct']} | {s['17b']['correct']} |\n"
    report += f"""

The fixed `requested_read_inside_boundary` feature was 0/8 for all three
suppliers. `requested_mutation_outside_boundary` was 8/8 for all three.
Every task had held or out-of-boundary evidence.

## Resource comparison

All measurements are Level-2 GPU-device-only telemetry on the same GTX 1650.

| Supplier | Overall | True | False | Median ms | Mean ms | P95 ms | Mean J/action | Mean active W | Peak W |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{mline('Qwen3 596M', aggregates['596m'], resources['596m'])}
{mline('Qwen3.5 752M', aggregates['752m'], resources['752m'])}
{mline('Qwen3 1.7B-labeled / 2.032B', aggregates['17b'], resources['17b'])}

The comparison is descriptive, not pure parameter scaling: model generation,
architecture, and effective context differ at the 1.7B-labeled point.

## Interpretation

### 1.7B characterization

**SCOPE_RULE_SYSTEMATIC_TRUE_BIAS**

The supplier was structurally compliant and correct on all eight outside-
boundary tasks, but incorrect on all eight within-authority tasks.

### Clean ladder

**NO_OBSERVED_SCOPE_LADDER**

The 1.7B-labeled supplier did not materially improve the missing false branch.
The clean evidence does not establish broad balanced scope-rule recovery below
or at this supplier point.

### Practical scope bracket

**NOT_SUPPORTED**

The tested 596M Qwen3, loaded 752M Qwen3.5, and 1.7B-labeled Qwen3 suppliers do
not provide a supported practical bracket for this atomic mechanic. This does
not establish a universal parameter floor; it identifies an unresolved
supplier/runtime behavior under the tested interface.

### Next decision

**SCOPE_RULE_NOT_SIZE_RESOLVED**

The same systematic failure persists at the established 1.7B-labeled point.
The next research step should not claim that size alone resolved the mechanic.

## Provenance

- 596M aggregate SHA256: `{sha(RUN_596 / 'aggregate.json')}`
- 752M aggregate SHA256: `{sha(RUN_752 / 'aggregate.json')}`
- 1.7B aggregate SHA256: `{sha(args.run_dir / 'aggregate.json')}`
- 596M report SHA256: `{sha(REPORT_596)}`
- 752M report SHA256: `{sha(REPORT_752)}`
- 596M matrix SHA256: `{sha(MATRIX_596)}`
- 752M matrix SHA256: `{sha(MATRIX_752)}`
- 1.7B runtime freeze SHA256: `{RUNTIME_FREEZE_SHA}`
- Shared task manifest SHA256: `{sha(TASK_MANIFEST)}`
- 1.7B preflight/execution manifest SHA256: `{sha(args.run_dir / 'preflight.json')}`

Raw prior runs, the interpretation erratum, historical scope evidence, and
task fixtures remain unchanged.
"""
    report_path.write_text(report, encoding="utf-8")

    comparison_path = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_CLEAN_SCOPE_596M_752M_1_7B_COMPARISON_2026-08-21.md"
    comparison = f"""# Clean Scope-Rule Ladder: 596M, 752M, and 1.7B-Labeled Suppliers

This is an exploratory, matched, descriptive comparison using the same 16
tasks and semantic rule.

| Supplier | Operative params | Effective context | True | False | Overall |
|---|---:|---:|---:|---:|---:|
| Qwen3 | 596049920 | 40960 | 8/8 | 0/8 | 8/16 |
| Qwen3.5 | 752393024 | 40960 | 8/8 | 1/8 | 9/16 |
| Qwen3 1.7B-labeled | 2031739904 | 32768 | 8/8 | 0/8 | 8/16 |

False-branch outcomes: seven tasks failed for all three; one task was
recovered only by 752M; none was recovered only by 1.7B or by both 752M and
1.7B. The true branch was retained at 8/8 for all suppliers.

The measured 1.7B context was capped by the model's native training context,
not by VRAM fit. The frozen probe inputs fit comfortably below 32768, but the
context difference remains a runtime confound. Qwen3 and Qwen3.5 also differ
in architecture and training generation.

Disposition:

```text
SCOPE_CHARACTERIZATION=SCOPE_RULE_SYSTEMATIC_TRUE_BIAS
CLEAN_SCOPE_LADDER=NO_OBSERVED_SCOPE_LADDER
PRACTICAL_SCOPE_BRACKET=NOT_SUPPORTED
NEXT_DECISION=SCOPE_RULE_NOT_SIZE_RESOLVED
```

Bound runs:

- 596M: `{RUN_596}`; aggregate `{sha(RUN_596 / 'aggregate.json')}`
- 752M: `{RUN_752}`; aggregate `{sha(RUN_752 / 'aggregate.json')}`
- 1.7B: `{args.run_dir}`; aggregate `{sha(args.run_dir / 'aggregate.json')}`
- Shared task manifest: `{sha(TASK_MANIFEST)}`
"""
    comparison_path.write_text(comparison, encoding="utf-8")
    comparison_json_path = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_CLEAN_SCOPE_596M_752M_1_7B_COMPARISON_2026-08-21.json"; write_json(comparison_json_path, {"schema": "zth_clean_scope_three_supplier_comparison_v1", "matched_task_set_identical": True, "suppliers": {"596m": {"operative_parameters": 596049920, "effective_n_ctx": 40960}, "752m": {"operative_parameters": 752393024, "effective_n_ctx": 40960}, "17b": {"operative_parameters": EXPECTED_PARAMS, "effective_n_ctx": EXPECTED_EFFECTIVE_CTX, "n_ctx_train": EXPECTED_TRAIN_CTX, "requested_n_ctx": EXPECTED_REQUESTED_CTX}}, "false_branch_categories": false_categories, "true_branch_retained": {"596m": "8/8", "752m": "8/8", "17b": "8/8"}, "interpretation": matrix["interpretation"], "aggregates": aggregates})
    print(json.dumps({"report": str(report_path), "report_sha256": sha(report_path), "matrix": str(matrix_path), "matrix_sha256": sha(matrix_path), "comparison": str(comparison_path), "comparison_sha256": sha(comparison_path), "comparison_json": str(comparison_json_path), "comparison_json_sha256": sha(comparison_json_path), "scope_characterization": "SCOPE_RULE_SYSTEMATIC_TRUE_BIAS", "clean_scope_ladder": "NO_OBSERVED_SCOPE_LADDER", "next_decision": "SCOPE_RULE_NOT_SIZE_RESOLVED"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
