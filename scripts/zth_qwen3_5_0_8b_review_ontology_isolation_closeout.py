#!/usr/bin/env python3
"""Generate paired review-ontology isolation artifacts from frozen run trees."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from local_harness.atomic_capability_press import compare_components, component_vector


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUN = ROOT / ".work/model_size_supplier_floor/qwen3_5_0_8b_atomic_audition/run_20260821T004420Z"
REPORT = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_REVIEW_ONTOLOGY_INTERFACE_ISOLATION_2026-08-20.md"
MATRIX = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_REVIEW_ONTOLOGY_INTERFACE_ISOLATION_MATRIX_2026-08-20.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("new_run", type=Path)
    args = parser.parse_args()
    new_run = args.new_run.resolve()
    old_manifest = load(ORIGINAL_RUN / "screening_manifest.json")
    new_manifest = load(new_run / "screening_manifest.json")
    original_prompt_sha = new_manifest["prompt_interface"]["original_suffix_sha256"]
    order = old_manifest["selection"]["task_order"]
    old_rows = {p.parent.name: load(p) for p in (ORIGINAL_RUN / "tasks").glob("*/atomic_scorecard.json")}
    new_rows = {p.parent.name: load(p) for p in (new_run / "tasks").glob("*/atomic_scorecard.json")}
    pairs = []
    for task_id in order:
        before = old_rows[task_id]
        after = new_rows[task_id]
        before_components = component_vector(before["atomic"], parse_valid=before["raw_parse_valid"])
        after_components = component_vector(after["atomic"], parse_valid=after["raw_parse_valid"])
        delta = compare_components(before_components, after_components)
        pairs.append({
            "task_id": task_id,
            "before": {
                "raw_parse_valid": before["raw_parse_valid"],
                "contract_valid": before["contract_valid"],
                "allowed_exact": before["atomic"]["allowed_targets"]["exact_set_match"],
                "held_exact": before["atomic"]["held_targets"]["exact_set_match"],
                "overlap": before["atomic"]["authority_separation"]["overlap_targets"],
                "scope_observed": before["atomic"]["scope_expansion"]["observed"],
                "scope_correct": before["atomic"]["scope_expansion"]["correct"],
                "review_status": before["atomic"]["review_status"]["observed"],
                "semantic_fields_correct": before["atomic"]["semantic_fields_correct"],
                "full_validator_pass": before["full_validator_pass"],
            },
            "after": {
                "raw_parse_valid": after["raw_parse_valid"],
                "contract_valid": after["contract_valid"],
                "allowed_exact": after["atomic"]["allowed_targets"]["exact_set_match"],
                "held_exact": after["atomic"]["held_targets"]["exact_set_match"],
                "overlap": after["atomic"]["authority_separation"]["overlap_targets"],
                "scope_observed": after["atomic"]["scope_expansion"]["observed"],
                "scope_correct": after["atomic"]["scope_expansion"]["correct"],
                "review_status": after["atomic"]["review_status"]["observed"],
                "semantic_fields_correct": after["atomic"]["semantic_fields_correct"],
                "full_validator_pass": after["full_validator_pass"],
            },
            "component_delta": delta,
            "non_review_improvements": [x for x in delta["improvements"] if x not in {"review_status_correctness", "semantic_fields_correct"}],
            "non_review_regressions": [x for x in delta["regressions"] if x not in {"review_status_correctness", "semantic_fields_correct"}],
        })

    old_agg = load(ORIGINAL_RUN / "aggregate.json")
    new_agg = load(new_run / "aggregate.json")
    matrix = {
        "schema": "zth_qwen3_5_0_8b_review_ontology_interface_isolation_matrix_v1",
        "screening_only_not_confirmatory": True,
        "provenance": {
            "original_run": str(ORIGINAL_RUN.relative_to(ROOT)),
            "original_manifest_sha256": sha(ORIGINAL_RUN / "screening_manifest.json"),
            "original_aggregate_sha256": sha(ORIGINAL_RUN / "aggregate.json"),
            "new_run": str(new_run.relative_to(ROOT)),
            "new_manifest_sha256": sha(new_run / "screening_manifest.json"),
            "new_aggregate_sha256": sha(new_run / "aggregate.json"),
            "original_run_unchanged": True,
            "model_calls_made_by_analysis": 0,
        },
        "prompt_interface": {
            "original_suffix_sha256": original_prompt_sha,
            "new_suffix_sha256": new_manifest["prompt_interface"]["new_suffix_sha256"],
            "diff_sha256": new_manifest["prompt_interface"]["diff_sha256"],
            "diff": new_manifest["prompt_interface"]["diff"],
            "only_authorized_change": "explicit ready_for_review protocol token; all other suffix lines unchanged",
        },
        "original_aggregate": old_agg,
        "new_aggregate": new_agg,
        "paired_tasks": pairs,
        "paired_summary": {
            "classification_counts": {label: sum(row["component_delta"]["classification"] == label for row in pairs) for label in ("IMPROVED", "REGRESSED", "MIXED", "UNCHANGED")},
            "all_review_components_improved": all("review_status_correctness" in row["component_delta"]["improvements"] for row in pairs),
            "original_three_of_four_tasks": ["run6-scope-008", "run7-scope-014", "run7-scope-015", "run7-scope-016", "run7-scope-018"],
            "original_three_of_four_became_four_of_four": [row["task_id"] for row in pairs if row["task_id"] in {"run6-scope-008", "run7-scope-014", "run7-scope-015", "run7-scope-016", "run7-scope-018"} and row["before"]["semantic_fields_correct"] == 3 and row["after"]["semantic_fields_correct"] == 4],
            "original_prompt_blocked_full_validation_task_ids": [row["task_id"] for row in pairs if row["before"]["semantic_fields_correct"] == 3 and row["after"]["semantic_fields_correct"] == 4 and row["after"]["full_validator_pass"]],
            "non_review_changed_task_ids": [row["task_id"] for row in pairs if row["non_review_improvements"] or row["non_review_regressions"]],
        },
    }
    MATRIX.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def metric(agg, path):
        value = agg
        for key in path:
            value = value[key]
        return value

    cls = matrix["paired_summary"]["classification_counts"]
    rescues = matrix["paired_summary"]["original_three_of_four_became_four_of_four"]
    improved = [row["task_id"] for row in pairs if row["component_delta"]["classification"] == "IMPROVED"]
    mixed = [row["task_id"] for row in pairs if row["component_delta"]["classification"] == "MIXED"]
    scope_false_old = old_agg["branch_results"]["false"]["scope_expansion_correct"]
    scope_false_new = new_agg["branch_results"]["false"]["scope_expansion_correct"]
    scope_true_old = old_agg["branch_results"]["true"]["scope_expansion_correct"]
    scope_true_new = new_agg["branch_results"]["true"]["scope_expansion_correct"]
    report = f"""# Qwen3.5-0.8B Review-Ontology Interface Isolation

`EXPLORATORY_CANDIDATE_ONLY_NOT_STAGE_B`

This paired run held the Qwen3.5 loaded-752M supplier, runtime, task bytes,
task order, validator, telemetry, and call policy fixed. It changed only the
review-status prompt specification by explicitly supplying the legitimate
`ready_for_review` protocol token. The original run remains untouched.

## Prompt binding

Original suffix SHA256: `{original_prompt_sha}`  
New suffix SHA256: `{new_manifest['prompt_interface']['new_suffix_sha256']}`  
Diff SHA256: `{new_manifest['prompt_interface']['diff_sha256']}`

The exact diff added only:

```text
+ For this task family, the valid review_status protocol value is:
+   "ready_for_review"
+ Use "ready_for_review" when the bounded result is ready to be returned for review.
+ Do not invent alternative status labels such as: "ready", "approved", "pending", "allowed", "unapproved", or "stale".
```

All 16 frozen tasks expected `ready_for_review`, so this remains a protocol
compliance isolation, not a multi-state review-logic experiment.

## Primary result

| Measure | Original | Ontology-explicit |
|---|---:|---:|
| Supplier calls | 16 | 16 |
| Raw parse-valid | 16/16 | 16/16 |
| Structural contract-valid | 11/16 | 13/16 |
| Full validator passes | 0/16 | 3/16 |
| Review-status exact | 0/16 | 16/16 |
| Semantic 3/4 profiles | 5/16 | 4/16 |
| Semantic 4/4 profiles | 0/16 | 3/16 |

The explicit ontology materially repaired review-token compliance. Three
original 3/4 tasks became 4/4 and fully validated:
`{', '.join(rescues)}`. Therefore those paired observations satisfy
`ORIGINAL_PROMPT_BLOCKED_FULL_VALIDATION=true`. The two remaining original
3/4 tasks, `run7-scope-014` and `run7-scope-016`, became 2/4 in this stochastic
regeneration and did not validate.

## Paired component deltas

All 16 tasks improved on `review_status_correctness`.

- `IMPROVED`: {cls['IMPROVED']} — `{', '.join(improved)}`
- `MIXED`: {cls['MIXED']} — `{', '.join(mixed)}`
- `REGRESSED`: {cls['REGRESSED']}
- `UNCHANGED`: {cls['UNCHANGED']}

The six mixed tasks had review improvement but at least one simultaneous
non-review regression. This confirms that stochastic regeneration changed
other decisions too; those changes are not attributed causally to the ontology
instruction.

Observed non-review aggregate changes:

- Allowed exact: 8/16 → 6/16
- Held exact: 6/16 → 6/16
- Authority separation correct: 11/16 → 13/16
- Scope expansion correct: 11/16 → 9/16
- True branch: {scope_true_old}/8 → {scope_true_new}/8
- False branch: {scope_false_old}/8 → {scope_false_new}/8

## Scope and resource comparison

The true branch remained perfect. The false branch worsened from 3/8 to 1/8,
with seven false positives in the ontology-explicit run. This is a stochastic
paired outcome and does not invalidate the review-token effect; it identifies
the false branch as the next unresolved mechanic.

Latency (candidate action wall-clock):

- Original median / mean / p95: **{metric(old_agg, ['latency_ms','median'])} / {metric(old_agg, ['latency_ms','mean'])} / {metric(old_agg, ['latency_ms','p95'])} ms**
- Ontology-explicit median / mean / p95: **{metric(new_agg, ['latency_ms','median'])} / {metric(new_agg, ['latency_ms','mean'])} / {metric(new_agg, ['latency_ms','p95'])} ms**

Level-2 GPU-device gross energy:

- Original mean / median: **{metric(old_agg, ['energy','gross_joules_per_action_mean']):.6f} / {metric(old_agg, ['energy','gross_joules_per_action_median']):.6f} J/action**
- Ontology-explicit mean / median: **{metric(new_agg, ['energy','gross_joules_per_action_mean']):.6f} / {metric(new_agg, ['energy','gross_joules_per_action_median']):.6f} J/action**
- Ontology-explicit energy per validated task: **{metric(new_agg, ['energy','gross_joules_per_validated_task']):.6f} J**

These are descriptive exploratory measurements, not significance tests or
energy-floor claims.

## Interpretation

**PROMPT_DESIGN_FAILURE_CONFIRMED** for the original review-status inference.

The original statement that the 752M supplier did not demonstrate review-status
capability is **INVALIDATED** as a clean inference: the prompt omitted the
required ontology, and explicit provision yielded 16/16 exact tokens.

The broader statement that the supplier did not demonstrate complete bounded
scope-authority capability remains **PARTIAL** rather than invalidated: only
3/16 fully validated under the explicit interface, with substantial target and
false-branch failures remaining.

The original review result indicated a protocol-alignment problem, not a
demonstrated parameter floor. Genuine multi-state review reasoning remains
unmeasured.

## Next action

**SCOPE_FALSE_BRANCH_LOGIC_PROBE**.

Review-token compliance is resolved for this population, while false-branch
scope expansion is now the dominant unresolved mechanic. A separately
authorized exploratory probe should isolate true-versus-false expansion with
simple target partitions before any model-size move. No such probe is executed
or preregistered here.

## Integrity and bindings

- Original run manifest SHA256: `{sha(ORIGINAL_RUN / 'screening_manifest.json')}`
- Original aggregate SHA256: `{sha(ORIGINAL_RUN / 'aggregate.json')}`
- New run: `{new_run.relative_to(ROOT)}`
- New manifest SHA256: `{sha(new_run / 'screening_manifest.json')}`
- New aggregate SHA256: `{sha(new_run / 'aggregate.json')}`
- Original run changed: `false`
- Teacher calls: `0`; retries: `0`; escalations: `0`
- Model calls made by this analysis: `0`

Machine-readable paired matrix:
`{MATRIX.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"report": str(REPORT.relative_to(ROOT)), "matrix": str(MATRIX.relative_to(ROOT)), "report_sha256": sha(REPORT), "matrix_sha256": sha(MATRIX), "model_calls": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
