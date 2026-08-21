#!/usr/bin/env python3
"""Generate the additive Qwen3-0.6B review-ontology isolation closeout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from local_harness.atomic_capability_press import compare_components, component_vector


ROOT = Path(__file__).resolve().parents[1]
OLD_RUN = ROOT / ".work/model_size_supplier_floor/qwen3_0_6b_interface_disambiguation/run_20260820T181000Z"
NEW_RUN = ROOT / ".work/model_size_supplier_floor/qwen3_0_6b_review_ontology_interface_isolation/run_20260821T022334Z"
OLD_ATOMIC_MATRIX = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_ATOMIC_CAPABILITY_MATRIX_2026-08-20.json"
OLD_REPORT = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_INTERFACE_DISAMBIGUATION_2026-08-20.md"
REPORT = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_REVIEW_ONTOLOGY_INTERFACE_ISOLATION_2026-08-21.md"
MATRIX = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_REVIEW_ONTOLOGY_INTERFACE_ISOLATION_MATRIX_2026-08-21.json"
OLD_THREE_OF_FOUR = ["run7-scope-002", "run7-scope-006", "run7-scope-008", "run7-scope-011", "run7-scope-012"]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comparable_old(score: dict) -> dict:
    return {**score, "object_observable": score.get("object", False)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-run", type=Path, default=NEW_RUN)
    args = parser.parse_args()
    new_run = args.new_run.resolve()
    old_matrix = load(OLD_ATOMIC_MATRIX)
    old_rows = {task_id: comparable_old(row["score"]) for task_id, row in old_matrix["runs"]["interface_normalized"].items()}
    new_rows = {p.parent.name: load(p) for p in (new_run / "tasks").glob("*/atomic_scorecard.json")}
    order = list(old_rows)
    pairs = []
    for task_id in order:
        before = old_rows[task_id]
        after_row = new_rows[task_id]
        after = after_row["atomic"]
        delta = compare_components(component_vector(before, parse_valid=True), component_vector(after, parse_valid=after_row["raw_parse_valid"]))
        pairs.append({
            "task_id": task_id,
            "before_normalized_explicit_interface": {
                "raw_parse_valid": True,
                "mechanically_exposed": True,
                "contract_valid": before["structural_contract_valid"],
                "allowed_exact": before["allowed_targets"]["exact_set_match"],
                "held_exact": before["held_targets"]["exact_set_match"],
                "authority_separation": before["authority_separation"]["no_allowed_held_overlap"],
                "scope_correct": before["scope_expansion"]["correct"],
                "review_status": before["review_status"]["observed"],
                "review_exact": before["review_status"]["exact_match"],
                "semantic_fields_correct": before["semantic_fields_correct"],
                "full_validator_valid": False,
            },
            "after_raw_corrected_interface": {
                "raw_parse_valid": after_row["raw_parse_valid"],
                "contract_valid": after_row["raw_contract_valid"],
                "allowed_exact": after["allowed_targets"]["exact_set_match"],
                "held_exact": after["held_targets"]["exact_set_match"],
                "authority_separation": after["authority_separation"]["no_allowed_held_overlap"],
                "scope_correct": after["scope_expansion"]["correct"],
                "review_status": after["review_status"]["observed"],
                "review_exact": after["review_status"]["exact_match"],
                "semantic_fields_correct": after["semantic_fields_correct"],
                "full_validator_valid": after_row["full_validator_valid"],
            },
            "component_delta": delta,
            "non_review_improvements": [x for x in delta["improvements"] if x not in {"review_status_correctness", "semantic_fields_correct"}],
            "non_review_regressions": [x for x in delta["regressions"] if x not in {"review_status_correctness", "semantic_fields_correct"}],
        })

    old_aggregate = load(OLD_RUN / "aggregate.json")
    new_aggregate = load(new_run / "aggregate.json")
    classifications = {label: sum(p["component_delta"]["classification"] == label for p in pairs) for label in ("IMPROVED", "REGRESSED", "MIXED", "UNCHANGED")}
    rescued = [p["task_id"] for p in pairs if p["task_id"] in OLD_THREE_OF_FOUR and p["after_raw_corrected_interface"]["semantic_fields_correct"] == 4]
    fully_valid = [p["task_id"] for p in pairs if p["task_id"] in OLD_THREE_OF_FOUR and p["after_raw_corrected_interface"]["full_validator_valid"]]
    matrix = {
        "schema": "zth_qwen3_0_6b_review_ontology_interface_isolation_matrix_v1",
        "screening_only_not_confirmatory": True,
        "protocol_compliance_isolation": True,
        "provenance": {
            "original_run": str(OLD_RUN.relative_to(ROOT)),
            "original_manifest_sha256": sha(OLD_RUN / "screening_manifest.json"),
            "original_aggregate_sha256": sha(OLD_RUN / "aggregate.json"),
            "original_atomic_matrix_sha256": sha(OLD_ATOMIC_MATRIX),
            "original_report_sha256": sha(OLD_REPORT),
            "corrected_run": str(new_run.relative_to(ROOT)),
            "corrected_manifest_sha256": sha(new_run / "screening_manifest.json"),
            "corrected_aggregate_sha256": sha(new_run / "aggregate.json"),
            "original_run_unchanged": True,
            "historical_evidence_changed": False,
            "analysis_model_calls": 0,
        },
        "prompt_interface": {
            "original_suffix_sha256": load(new_run / "screening_manifest.json")["prompt_interface"]["original_suffix_sha256"],
            "corrected_suffix_sha256": load(new_run / "screening_manifest.json")["prompt_interface"]["corrected_suffix_sha256"],
            "diff_sha256": load(new_run / "screening_manifest.json")["prompt_interface"]["diff_sha256"],
            "diff": load(new_run / "screening_manifest.json")["prompt_interface"]["diff"],
            "only_change": "explicit ready_for_review protocol token and prohibition on alternative status labels",
        },
        "original_normalized_explicit_interface_aggregate": old_matrix["aggregates"]["interface_normalized"],
        "original_raw_explicit_interface_aggregate": old_matrix["aggregates"]["interface_raw"],
        "corrected_raw_aggregate": new_aggregate,
        "paired_tasks": pairs,
        "paired_summary": {
            "classification_counts": classifications,
            "all_observable_corrected_review_tokens": new_aggregate["review_status_exact"],
            "original_three_of_four_task_ids": OLD_THREE_OF_FOUR,
            "original_three_of_four_became_four_of_four": rescued,
            "original_prompt_blocked_full_validation_task_ids": fully_valid,
            "non_review_changed_task_ids": [p["task_id"] for p in pairs if p["non_review_improvements"] or p["non_review_regressions"]],
        },
        "cross_bracket_reference": {
            "qwen3_loaded_596m_corrected": {"raw_parse": new_aggregate["raw_parse_valid"], "raw_contract": new_aggregate["raw_contract_valid"], "review_exact": new_aggregate["review_status_exact"], "full_validated": new_aggregate["full_validator_passes"]},
            "qwen35_loaded_752m_ontology_explicit": {"raw_parse": 16, "raw_contract": 13, "review_exact": 16, "full_validated": 3, "semantic_4_of_4": 3, "true_scope": "8/8", "false_scope": "1/8"},
            "confounds": ["different architecture/generation", "different task populations", "different stochastic generations", "596M population exercises positive scope branch only"],
        },
    }
    MATRIX.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    new_dist = new_aggregate["semantic_fields_correct_distribution"]
    old_norm = old_matrix["aggregates"]["interface_normalized"]
    def micro(field: str) -> dict[str, float | int]:
        rows = [row["atomic"][field] for row in new_rows.values()]
        tp = sum(row["true_positives"] for row in rows)
        fp = sum(row["false_positives"] for row in rows)
        fn = sum(row["false_negatives"] for row in rows)
        return {"tp": tp, "fp": fp, "fn": fn, "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}
    allowed_micro = micro("allowed_targets")
    held_micro = micro("held_targets")
    improved = [p["task_id"] for p in pairs if p["component_delta"]["classification"] == "IMPROVED"]
    regressed = [p["task_id"] for p in pairs if p["component_delta"]["classification"] == "REGRESSED"]
    report = f"""# Qwen3-0.6B Review-Ontology Interface Isolation

`PROTOCOL_COMPLIANCE_ISOLATION`  
`EXPLORATORY_CANDIDATE_ONLY_NOT_STAGE_B`

This additive run held the Qwen3-0.6B supplier, artifact, runtime, GTX 1650,
telemetry, 12 tasks, order, fixtures, validator, and no-retry/no-escalation
policy fixed. It changed only the review-status protocol instruction. Neither
preserved 0.6B run was modified.

## Prompt correction

Original explicit-interface suffix SHA256: `{matrix['prompt_interface']['original_suffix_sha256']}`  
Corrected suffix SHA256: `{matrix['prompt_interface']['corrected_suffix_sha256']}`  
Diff SHA256: `{matrix['prompt_interface']['diff_sha256']}`

The only addition was the explicit `ready_for_review` protocol token and a
prohibition on alternative labels. All 12 fixtures expect that same literal.
This experiment therefore measures protocol-token compliance more directly
than multi-state review-state reasoning.

## Primary result

| Measure | Original explicit-interface, normalized diagnostic view | Corrected raw run |
|---|---:|---:|
| Parse-valid | 12/12 exposed after one fence removal | {new_aggregate['raw_parse_valid']}/12 |
| Structural contract-valid | {old_norm['contract_usable']}/12 | {new_aggregate['raw_contract_valid']}/12 |
| Review-status exact | {old_norm['review_status_exact']}/12 | {new_aggregate['review_status_exact']}/12 |
| Full validator-valid | {old_norm['fully_validator_valid']}/12 | {new_aggregate['full_validator_passes']}/12 |
| Semantic 3/4 | {old_norm['semantic_fields_3_of_4']}/12 | {new_dist['3']}/12 |
| Semantic 4/4 | {old_norm['semantic_fields_distribution'].get('4', 0)}/12 | {new_dist['4']}/12 |

The corrected run produced 8/12 raw exact review tokens and 4/12 full
validated tasks. Four responses remained non-JSON and therefore had no
observable review field; raw validation remains authoritative.

The five preserved original normalized 3/4 tasks were:
`{', '.join(OLD_THREE_OF_FOUR)}`.

Four became 4/4 and fully validated in the corrected paired observations:
`{', '.join(fully_valid)}`. The fifth, `run7-scope-002`, did not; its
corrected response was non-JSON. These four paired observations satisfy
`ORIGINAL_PROMPT_BLOCKED_FULL_VALIDATION=true` without changing the original
run.

## Corrected atomic profile

- Allowed-target exact: {new_aggregate['allowed_targets_exact']}/12
- Allowed-target micro TP/FP/FN: {allowed_micro['tp']}/{allowed_micro['fp']}/{allowed_micro['fn']}; precision/recall/F1: {allowed_micro['precision']:.6f}/{allowed_micro['recall']:.6f}/{allowed_micro['f1']:.6f}
- Held-target exact: {new_aggregate['held_targets_exact']}/12
- Held-target micro TP/FP/FN: {held_micro['tp']}/{held_micro['fp']}/{held_micro['fn']}; precision/recall/F1: {held_micro['precision']:.6f}/{held_micro['recall']:.6f}/{held_micro['f1']:.6f}
- Authority separation observed and correct: {new_aggregate['authority_separation_observed_and_correct']}/12
- Positive scope-expansion branch: {new_aggregate['scope_expansion']['true_branch']['correct']}/{new_aggregate['scope_expansion']['true_branch']['tasks']}
- False branch: not exercised; all 12 fixtures require expansion
- Semantic profile: 0/4={new_dist['0']}, 1/4={new_dist['1']}, 2/4={new_dist['2']}, 3/4={new_dist['3']}, 4/4={new_dist['4']}

## Paired task changes

Compared against the preserved normalized explicit-interface objects, the
explicit component classifier found:

- IMPROVED: {classifications['IMPROVED']} — `{', '.join(improved)}`
- REGRESSED: {classifications['REGRESSED']} — `{', '.join(regressed)}`
- MIXED: {classifications['MIXED']}
- UNCHANGED: {classifications['UNCHANGED']}

All observable corrected review fields matched `ready_for_review`; the four
non-parseable responses were not review-observable. Non-review fields changed
in the paired stochastic regeneration and are not attributed causally to the
ontology instruction.

## Interpretation

- **596M review-state reasoning was not demonstrated:** **SUPPORTED**. This
  constant-token population does not test multi-state selection.
- **596M review-status ontology compliance was not demonstrated:**
  **PARTIAL**. Raw exact compliance was demonstrated on 8/12, but not all
  responses were parseable.
- **596M could not perform complete bounded scope-authority tasks:**
  **PARTIAL**. Four of twelve corrected responses fully validated; complete
  stewardship is not established.
- **The observed review-status failure represented a model-size floor:**
  **CONFOUNDED**. The original prompt omitted the required protocol token,
  and four original near-misses became fully valid after it was supplied.

The original review-status floor inference is therefore **PARTIALLY_INVALIDATED**,
not a clean size-floor result. This remains exploratory evidence only.

## Cross-bracket context

The corrected 596M result is descriptively compared with the corrected loaded
752M Qwen3.5 result: 752M had review exact 16/16, full validation 3/16,
semantic 4/4 on 3/16, true branch 8/8, and false branch 1/8. This is not a
pure parameter-size comparison because the model generations, architectures,
task populations, and stochastic outputs differ; the 596M population has no
false-expansion branch.

## Resource observations

Corrected 596M candidate action latency was **{new_aggregate['latency_ms']['median']} ms median**, **{new_aggregate['latency_ms']['mean']} ms mean**, and **{new_aggregate['latency_ms']['p95']} ms p95**. Mean gross Level-2 GPU-device energy was **{new_aggregate['energy']['gross_joules_per_action_mean']} J/action**; energy per validated task was **{new_aggregate['energy']['gross_joules_per_validated_task']} J**. These are GTX 1650 device-only exploratory measurements, not whole-system or confirmatory energy claims.

## Next experiment

**SCOPE_FALSE_BRANCH_LOGIC_PROBE**. Review-token compliance is now directly
tested, while this 0.6B population still has no negative scope-expansion
branch and target/authority errors remain. No such probe is executed here.

## Integrity

- Original run: `{OLD_RUN.relative_to(ROOT)}`
- Corrected run: `{new_run.relative_to(ROOT)}`
- Original run unchanged: `true`
- Historical raw/validator evidence changed: `false`
- Supplier calls: `12`; teacher calls: `0`; retries: `0`; escalations: `0`
- Analysis model calls: `0`

Machine-readable matrix: `{MATRIX.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"report": str(REPORT.relative_to(ROOT)), "matrix": str(MATRIX.relative_to(ROOT)), "report_sha256": sha(REPORT), "matrix_sha256": sha(MATRIX), "model_calls": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
