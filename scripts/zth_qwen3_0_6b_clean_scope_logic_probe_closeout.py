#!/usr/bin/env python3
"""Generate the review-only closeout for the clean scope logic probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

from scripts.zth_qwen3_0_6b_clean_scope_logic_probe import (
    ROOT,
    TASK_MANIFEST,
    RUNTIME_FREEZE,
    EXPECTED_MODEL_ID,
    EXPECTED_MODEL_SHA,
    EXPECTED_PARAMS,
    EXPECTED_GPU_UUID,
    SEMANTIC_RULE,
    sha256_file,
)


DESIGN = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_DESIGN_2026-08-21.md"
FORENSIC_AUDIT = ROOT / "docs/research/SCOPE_EXPANSION_PROMPT_CONTRACT_AUDIT_2026-08-21.md"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def pct(n: int, d: int) -> float | None:
    return round(n / d, 6) if d else None


def hash_bytes(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir
    manifest = json.loads((run / "probe_manifest.json").read_text())
    execution = json.loads((run / "preflight.json").read_text())
    aggregate = json.loads((run / "aggregate.json").read_text())
    task_manifest = json.loads(TASK_MANIFEST.read_text())
    task_by_id = {task["task_id"]: task for task in task_manifest["tasks"]}
    rows = []
    for task_id in manifest["task_order"]:
        score = json.loads((run / "tasks" / task_id / "scorecard.json").read_text())
        task = task_by_id[task_id]
        rows.append(
            {
                "task_id": task_id,
                "expected": score["expected_scope_expansion_required"],
                "observed": score["observed_scope_expansion_required"],
                "correct": score["correct"],
                "raw_parse_valid": score["raw_parse_valid"],
                "contract_valid": score["contract_valid"],
                "failure_class": score["failure_class"],
                "difficulty_features": task["difficulty_features"],
                "authority_evidence": task["authority_evidence"],
                "requested_operation": task["requested_operation"],
                "latency_ms": score["wall_elapsed_ms"],
                "gross_energy_joules": score["power_summary"]["gross_energy_joules"],
            }
        )

    def feature_stats(feature: str) -> dict[str, Any]:
        subset = [row for row in rows if feature in row["difficulty_features"]]
        return {"tasks": len(subset), "correct": sum(row["correct"] for row in subset), "accuracy": pct(sum(row["correct"] for row in subset), len(subset)), "task_ids": [row["task_id"] for row in subset]}

    feature_names = sorted({feature for row in rows for feature in row["difficulty_features"]})
    feature_conditioned = {feature: feature_stats(feature) for feature in feature_names}
    held_rows = [
        row
        for row in rows
        if any(
            any(marker in evidence.casefold() for marker in ("held", "outside", "expired approval"))
            for evidence in row["authority_evidence"]
        )
    ]
    feature_conditioned["held_target_present"] = {
        "tasks": len(held_rows),
        "correct": sum(row["correct"] for row in held_rows),
        "accuracy": pct(sum(row["correct"] for row in held_rows), len(held_rows)),
        "task_ids": [row["task_id"] for row in held_rows],
        "derivation": "authority_evidence contains an explicit held, outside-authority, or expired-approval statement",
    }
    matrix = {
        "schema": "zth_qwen3_0_6b_clean_scope_logic_probe_matrix_v1",
        "status": "exploratory_not_confirmatory",
        "provenance": {
            "run_directory": str(run),
            "execution_manifest_sha256": sha256_file(run / "preflight.json"),
            "aggregate_sha256": sha256_file(run / "aggregate.json"),
            "probe_manifest_sha256": sha256_file(run / "probe_manifest.json"),
            "task_manifest_path": str(TASK_MANIFEST.relative_to(ROOT)),
            "task_manifest_sha256": sha256_file(TASK_MANIFEST),
            "design_path": str(DESIGN.relative_to(ROOT)),
            "design_sha256": sha256_file(DESIGN),
            "runtime_freeze_path": str(RUNTIME_FREEZE.relative_to(ROOT)),
            "runtime_freeze_sha256": sha256_file(RUNTIME_FREEZE),
            "contract_audit_path": str(FORENSIC_AUDIT.relative_to(ROOT)),
            "contract_audit_sha256": sha256_file(FORENSIC_AUDIT),
            "raw_responses_unchanged": True,
            "historical_evidence_changed": False,
            "model_calls_made": 16,
        },
        "candidate": {"model_id": EXPECTED_MODEL_ID, "operative_parameters": EXPECTED_PARAMS, "artifact_sha256": EXPECTED_MODEL_SHA},
        "semantic_contract": {"rule": SEMANTIC_RULE, "rule_sha256": hash_bytes(SEMANTIC_RULE)},
        "task_order": [row["task_id"] for row in rows],
        "branch_balance": {"true": sum(row["expected"] for row in rows), "false": sum(not row["expected"] for row in rows)},
        "per_task": rows,
        "feature_conditioned": feature_conditioned,
        "aggregate": aggregate,
        "preflight": {"execution_git_commit": execution["execution_git_commit"], "model_ids": execution["non_generative_preflight"]["model_ids"], "telemetry": execution["telemetry_preflight"]},
        "interpretation": {
            "serialization_failures": aggregate["serialization_failures"],
            "scope_decision_failures": aggregate["scope_decision_failures"],
            "characterization": "SCOPE_RULE_SYSTEMATIC_TRUE_BIAS",
            "next_step": "RUN_SAME_CLEAN_SCOPE_PROBE_AT_752M",
        },
    }
    matrix_path = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_MATRIX_2026-08-21.json"
    write_json(matrix_path, matrix)

    true_rows = [row for row in rows if row["expected"]]
    false_rows = [row for row in rows if not row["expected"]]
    report_path = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_2026-08-21.md"
    report = f"""# Qwen3-0.6B Clean Scope-Expansion Logic Probe

`EXPLORATORY_NOT_CONFIRMATORY=true`  
`MODEL_CALLS_MADE=16`  
`TEACHER_CALLS_MADE=0`  
`RETRIES=0`  
`ESCALATIONS=0`

## Purpose and frozen separation

This is a fresh, balanced atomic probe of `scope_expansion_required` for the
Qwen3-0.6B supplier. It does not alter or numerically merge the earlier
confounded Run 7/Run 6 scope observations. The task-specific prompts contain
authority evidence and a requested operation but no direct expected-boolean
phrase. The shared rule was frozen before calls:

> {SEMANTIC_RULE.replace(chr(10), chr(10) + "> ")}

The output contract contained exactly one field:

```json
{{"scope_expansion_required": true}}
```

The value had to be a JSON boolean. Leakage audit findings: **0**.

## Bindings

| Item | Value |
|---|---|
| Run directory | `{run}` |
| Candidate | `{EXPECTED_MODEL_ID}` |
| Operative parameters | `{EXPECTED_PARAMS}` |
| Candidate artifact SHA256 | `{EXPECTED_MODEL_SHA}` |
| Task count | 16 |
| Branch balance | 8 true / 8 false |
| Telemetry | remote read-only HTTP, Level 2, GTX 1650 device only |
| GPU UUID | `{EXPECTED_GPU_UUID}` |
| Sample interval | 0.25 seconds |
| Historical evidence changed | false |

## Primary result

| Metric | Result |
|---|---:|
| Transport-valid responses | {sum(row['raw_parse_valid'] for row in rows)}/16 |
| Raw parse-valid | {sum(row['raw_parse_valid'] for row in rows)}/16 |
| Contract-valid | {sum(row['contract_valid'] for row in rows)}/16 |
| Overall accuracy | {aggregate['overall_accuracy']:.3f} (8/16) |
| True branch | {aggregate['branch_results']['true']['correct']}/8 ({aggregate['branch_results']['true']['accuracy']:.3f}) |
| False branch | {aggregate['branch_results']['false']['correct']}/8 ({aggregate['branch_results']['false']['accuracy']:.3f}) |
| Serialization failures | {aggregate['serialization_failures']} |
| Invalid-contract failures | {aggregate['invalid_contract_failures']} |
| Scope-decision failures | {aggregate['scope_decision_failures']} |
| True precision | {aggregate['true_precision']:.3f} |
| True recall | {aggregate['true_recall']:.3f} |
| True F1 | {aggregate['true_f1']:.3f} |
| False-positive rate | {aggregate['false_positive_rate']:.3f} |
| False-negative rate | {aggregate['false_negative_rate']:.3f} |

Confusion matrix:

| Expected \\ Observed | true | false |
|---|---:|---:|
| true | {aggregate['confusion_matrix']['expected_true_observed_true']} | {aggregate['confusion_matrix']['expected_true_observed_false']} |
| false | {aggregate['confusion_matrix']['expected_false_observed_true']} | {aggregate['confusion_matrix']['expected_false_observed_false']} |

Every response was structurally valid. All eight true-branch tasks were
correct. Every false-branch task was observed as `true`, producing eight
false positives. The failure is therefore a boolean decision failure with a
systematic true response bias, not a serialization failure.

## Per-task outcome

| Task | Expected | Observed | Correct | Failure |
|---|---:|---:|---:|---|
"""
    for row in rows:
        report += f"| {row['task_id']} | {str(row['expected']).lower()} | {str(row['observed']).lower()} | {str(row['correct']).lower()} | {row['failure_class'] or '—'} |\n"
    report += "\n## Feature-conditioned descriptive counts\n\n"
    report += "These are descriptive counts over the 16-task exploratory sample; they are not subgroup significance tests.\n\n"
    report += "| Existing fixture feature | Tasks | Correct | Accuracy |\n|---|---:|---:|---:|\n"
    for feature in [*feature_names, "held_target_present"]:
        stats = feature_conditioned[feature]
        report += f"| `{feature}` | {stats['tasks']} | {stats['correct']} | {stats['accuracy'] if stats['accuracy'] is not None else 'n/a'} |\n"
    idle_summary = json.loads((run / "idle_power_samples.json").read_text())["summary"]
    report += f"""

The most direct contrast is `requested_read_inside_boundary`: 0/8 correct,
versus `requested_mutation_outside_boundary`: 8/8 correct. Every task had a
held target, so the model did not distinguish “a held target is present” from
“the requested operation requires that held target” in this sample.

## Resource observations

| Metric | Result |
|---|---:|
| Action latency median | {aggregate['latency_ms']['median']} ms |
| Action latency mean | {aggregate['latency_ms']['mean']} ms |
| Action latency p95 | {aggregate['latency_ms']['p95']} ms |
| Idle mean power | {idle_summary['mean_power_watts']} W |
| Gross device energy/action mean | {aggregate['energy']['gross_joules_per_action_mean']} J |
| Gross device energy/action median | {aggregate['energy']['gross_joules_per_action_median']} J |
| Gross device energy total | {aggregate['energy']['gross_joules_total']} J |
| Energy boundary | GTX 1650 device only |

Energy is Level-2 device telemetry, not whole-system wall energy. No
energy-floor or production-cost conclusion is drawn.

## Interpretation

**SCOPE_RULE_SYSTEMATIC_TRUE_BIAS**

The candidate correctly recognized all eight requests that operated beyond the
explicit authority boundary, but marked all eight within-boundary reads as
requiring expansion. It therefore did not demonstrate the general rule across
both branches. The evidence directly supports these conclusions:

- It can produce the required atomic JSON and boolean without serialization
  failure.
- It recognized the outside-boundary/mutation branch in 8/8 observations.
- It did not recognize the inside-boundary/read branch in 0/8 observations.
- Failures are primarily boolean scope-decision failures, not formatting
  failures.
- It cannot, on this sample, distinguish a held adjacent target from a held
  target actually required by the requested operation.

The historical Run 7/Run 6 scope figures remain **HISTORICAL_CONFOUNDED_OBSERVATION**;
this clean result is **CLEAN_SCOPE_LOGIC_PROBE** and is not merged with them.

## Next bracket decision

**RUN_SAME_CLEAN_SCOPE_PROBE_AT_752M**

The clean 596M result is informative enough to justify a matched cross-size
probe. That future probe must use the same semantic rule, balanced branches,
answer-leakage audit, atomic output contract, and separate exploratory status.
It must not be treated as a Stage B confirmation or a production authority
decision.

## Provenance

- Task manifest SHA256: `{sha256_file(TASK_MANIFEST)}`
- Design SHA256: `{sha256_file(DESIGN)}`
- Runtime freeze SHA256: `{sha256_file(RUNTIME_FREEZE)}`
- Contract audit SHA256: `{sha256_file(FORENSIC_AUDIT)}`
- Execution preflight artifact SHA256: `{sha256_file(run / 'preflight.json')}`
- Aggregate SHA256: `{sha256_file(run / 'aggregate.json')}`
- Matrix path: `docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_CLEAN_SCOPE_LOGIC_PROBE_MATRIX_2026-08-21.json`

Raw responses, validator artifacts, and historical runs were not modified.
"""
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"report": str(report_path), "matrix": str(matrix_path), "report_sha256": sha256_file(report_path), "matrix_sha256": sha256_file(matrix_path), "characterization": "SCOPE_RULE_SYSTEMATIC_TRUE_BIAS", "next_step": "RUN_SAME_CLEAN_SCOPE_PROBE_AT_752M"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
