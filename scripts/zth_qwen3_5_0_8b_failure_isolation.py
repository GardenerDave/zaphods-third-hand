#!/usr/bin/env python3
"""Model-free forensic isolation for the frozen Qwen3.5 atomic audition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPORT = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_ATOMIC_AUDITION_2026-08-20.md"
SOURCE_MATRIX = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_ATOMIC_AUDITION_MATRIX_2026-08-20.json"
OUTPUT_JSON = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_ATOMIC_FAILURE_ISOLATION_2026-08-20.json"
OUTPUT_REPORT = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_ATOMIC_FAILURE_ISOLATION_2026-08-20.md"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify_review(observed: str, semantic_fields: int) -> str:
    # Conservative classification: only labels with a preserved review
    # boundary and an otherwise exact semantic object are called ontology-only.
    if observed == "pending" and semantic_fields == 3:
        return "ONTOLOGY_ONLY_CANDIDATE"
    if observed == "unapproved" and semantic_fields == 3:
        return "ONTOLOGY_ONLY_CANDIDATE"
    if observed == "approved":
        return "SEMANTIC_STATE_MISMATCH"
    return "AMBIGUOUS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    manifest = load(run / "screening_manifest.json")
    task_order = manifest["selection"]["task_order"]
    rows = []
    for task_id in task_order:
        task_dir = run / "tasks" / task_id
        task = load(task_dir / "fixture.snapshot.json")
        scorecard = load(task_dir / "atomic_scorecard.json")
        atomic = scorecard["atomic"]
        response_path = task_dir / "response.json"
        validation_path = task_dir / "validation.json"
        observed_status = atomic["review_status"]["observed"]
        review_class = classify_review(observed_status, atomic["semantic_fields_correct"])
        rows.append({
            "task_id": task_id,
            "expected": task["validator"]["reference_facts"],
            "observed": {
                "allowed_targets": atomic["allowed_targets"]["observed_literal_set"],
                "held_targets": atomic["held_targets"]["observed_literal_set"],
                "scope_expansion_required": atomic["scope_expansion"]["observed"],
                "review_status": observed_status,
            },
            "atomic": {
                "allowed_exact": atomic["allowed_targets"]["exact_set_match"],
                "held_exact": atomic["held_targets"]["exact_set_match"],
                "allowed_precision": atomic["allowed_targets"]["precision"],
                "allowed_recall": atomic["allowed_targets"]["recall"],
                "held_precision": atomic["held_targets"]["precision"],
                "held_recall": atomic["held_targets"]["recall"],
                "overlap": atomic["authority_separation"]["overlap_targets"],
                "scope_correct": atomic["scope_expansion"]["correct"],
                "semantic_fields_correct": atomic["semantic_fields_correct"],
                "semantic_field_vector": atomic["semantic_field_vector"],
            },
            "review_status_class": review_class,
            "fixture": {
                "difficulty_features": task.get("difficulty_features", []),
                "source_document": task.get("provenance", {}).get("source_document"),
                "source_anchor": task.get("provenance", {}).get("source_anchor"),
                "prompt": task["prompt"],
            },
            "artifact_hashes": {
                "response_sha256": sha(response_path),
                "validation_sha256": sha(validation_path),
                "scorecard_sha256": sha(task_dir / "atomic_scorecard.json"),
            },
        })

    expected_statuses = sorted({row["expected"]["review_status"] for row in rows})
    observed_statuses = sorted({row["observed"]["review_status"] for row in rows})
    confusion = {}
    for row in rows:
        key = f"{row['expected']['review_status']} -> {row['observed']['review_status']}"
        confusion.setdefault(key, []).append(row["task_id"])

    false_branch = [row for row in rows if row["expected"]["requires_scope_expansion_flag"] is False]
    true_branch = [row for row in rows if row["expected"]["requires_scope_expansion_flag"] is True]
    false_positive_rows = [row for row in false_branch if row["observed"]["scope_expansion_required"] is True]
    overlap_rows = [row for row in rows if row["atomic"]["overlap"]]
    allowed_mismatch = [row for row in rows if not row["atomic"]["allowed_exact"]]
    held_mismatch = [row for row in rows if not row["atomic"]["held_exact"]]
    low_profiles = [row for row in rows if row["atomic"]["semantic_fields_correct"] <= 1]
    near_misses = [row for row in rows if row["atomic"]["semantic_fields_correct"] == 3]

    analysis = {
        "schema": "zth_qwen3_5_0_8b_atomic_failure_isolation_v1",
        "model_calls_made": 0,
        "provenance": {
            "run_directory": str(run.relative_to(ROOT)),
            "execution_manifest_sha256": sha(run / "screening_manifest.json"),
            "aggregate_sha256": sha(run / "aggregate.json"),
            "source_audition_report": str(SOURCE_REPORT.relative_to(ROOT)),
            "source_audition_report_sha256": sha(SOURCE_REPORT),
            "source_audition_matrix": str(SOURCE_MATRIX.relative_to(ROOT)),
            "source_audition_matrix_sha256": sha(SOURCE_MATRIX),
            "raw_artifacts_unchanged": True,
            "validator_artifacts_unchanged": True,
            "frozen_audition_changed": False,
        },
        "review_status_audit": {
            "expected_distinct_values": expected_statuses,
            "expected_distinct_count": len(expected_statuses),
            "observed_values": observed_statuses,
            "confusion": {key: {"count": len(ids), "task_ids": ids} for key, ids in sorted(confusion.items())},
            "prompt_supplied_explicit_ontology": False,
            "prompt_required_type": "string",
            "exact_protocol_token": "ready_for_review",
            "measurement_validity": "THIS SAMPLE MEASURES PROTOCOL-TOKEN COMPLIANCE MORE DIRECTLY THAN MULTI-STATE REVIEW JUDGMENT",
            "legitimate_scope_fixture_statuses_found_in_repository": ["ready_for_review"],
            "legitimate_other_task_family_status_found_in_repository": ["review_required"],
        },
        "review_status_semantic_proximity": {
            "ONTOLOGY_ONLY_CANDIDATE": [row["task_id"] for row in rows if row["review_status_class"] == "ONTOLOGY_ONLY_CANDIDATE"],
            "SEMANTIC_STATE_MISMATCH": [row["task_id"] for row in rows if row["review_status_class"] == "SEMANTIC_STATE_MISMATCH"],
            "AMBIGUOUS": [row["task_id"] for row in rows if row["review_status_class"] == "AMBIGUOUS"],
            "counts": {
                "ONTOLOGY_ONLY_CANDIDATE": sum(row["review_status_class"] == "ONTOLOGY_ONLY_CANDIDATE" for row in rows),
                "SEMANTIC_STATE_MISMATCH": sum(row["review_status_class"] == "SEMANTIC_STATE_MISMATCH" for row in rows),
                "AMBIGUOUS": sum(row["review_status_class"] == "AMBIGUOUS" for row in rows),
            },
            "method_note": "Conservative: only otherwise 3/4 outputs with a non-approval review boundary are ontology-only candidates; no synonym normalization was applied.",
        },
        "near_misses_3_of_4": [
            {
                "task_id": row["task_id"],
                "allowed_targets_exact": row["atomic"]["allowed_exact"],
                "held_targets_exact": row["atomic"]["held_exact"],
                "scope_expansion_correct": row["atomic"]["scope_correct"],
                "expected_review_status": row["expected"]["review_status"],
                "observed_review_status": row["observed"]["review_status"],
                "classification": row["review_status_class"],
            }
            for row in near_misses
        ],
        "five_false_positive_false_branch": [
            {
                "task_id": row["task_id"],
                "expected_allowed_targets": row["expected"]["required_allowed_targets"],
                "expected_held_targets": row["expected"]["required_held_targets"],
                "observed_allowed_targets": row["observed"]["allowed_targets"],
                "observed_held_targets": row["observed"]["held_targets"],
                "authority_overlap": row["atomic"]["overlap"],
                "allowed_targets_exact": row["atomic"]["allowed_exact"],
                "held_targets_exact": row["atomic"]["held_exact"],
                "review_status": row["observed"]["review_status"],
                "fixture_features": row["fixture"]["difficulty_features"],
                "source_document": row["fixture"]["source_document"],
                "source_anchor": row["fixture"]["source_anchor"],
                "prompt": row["fixture"]["prompt"],
            }
            for row in false_positive_rows
        ],
        "branch_comparison": {
            "false": {
                "tasks": len(false_branch),
                "scope_correct": sum(row["atomic"]["scope_correct"] is True for row in false_branch),
                "allowed_exact": sum(row["atomic"]["allowed_exact"] for row in false_branch),
                "held_exact": sum(row["atomic"]["held_exact"] for row in false_branch),
                "no_overlap": sum(not row["atomic"]["overlap"] for row in false_branch),
                "semantic_profile_distribution": {str(i): sum(row["atomic"]["semantic_fields_correct"] == i for row in false_branch) for i in range(5)},
            },
            "true": {
                "tasks": len(true_branch),
                "scope_correct": sum(row["atomic"]["scope_correct"] is True for row in true_branch),
                "allowed_exact": sum(row["atomic"]["allowed_exact"] for row in true_branch),
                "held_exact": sum(row["atomic"]["held_exact"] for row in true_branch),
                "no_overlap": sum(not row["atomic"]["overlap"] for row in true_branch),
                "semantic_profile_distribution": {str(i): sum(row["atomic"]["semantic_fields_correct"] == i for row in true_branch) for i in range(5)},
            },
        },
        "intersections": {
            "false_positive_expansion": [row["task_id"] for row in false_positive_rows],
            "overlap": [row["task_id"] for row in overlap_rows],
            "allowed_target_mismatch": [row["task_id"] for row in allowed_mismatch],
            "held_target_mismatch": [row["task_id"] for row in held_mismatch],
            "semantic_profile_0_or_1": [row["task_id"] for row in low_profiles],
            "false_positive_and_overlap": [row["task_id"] for row in false_positive_rows if row in overlap_rows],
            "false_positive_and_allowed_mismatch": [row["task_id"] for row in false_positive_rows if row in allowed_mismatch],
            "false_positive_and_held_mismatch": [row["task_id"] for row in false_positive_rows if row in held_mismatch],
            "false_positive_and_low_profile": [row["task_id"] for row in false_positive_rows if row in low_profiles],
            "overlap_and_allowed_mismatch": [row["task_id"] for row in overlap_rows if row in allowed_mismatch],
            "overlap_and_held_mismatch": [row["task_id"] for row in overlap_rows if row in held_mismatch],
        },
        "hypotheses": {
            "REVIEW_STATUS_ONTOLOGY_ALIGNMENT_FAILURE": {"state": "SUPPORTED", "basis": "0/16 exact protocol tokens, one expected scope-family token, five observed non-protocol labels, and no explicit ontology in the prompt."},
            "REVIEW_STATE_REASONING_FAILURE": {"state": "INSUFFICIENT_EVIDENCE", "basis": "Three of five 3/4 cases are plausible ontology-only candidates and the sample has no genuine multi-state review-status choice."},
            "SCOPE_EXPANSION_POSITIVE_RESPONSE_BIAS": {"state": "SUPPORTED", "basis": "8/8 true-branch decisions were correct while 5/8 false-branch decisions were false positives; target errors co-occur in 4/5 false positives, so the pattern is descriptive rather than causal."},
        },
        "next_experiment": {
            "recommendation": "REVIEW_ONTOLOGY_INTERFACE_ISOLATION",
            "reason": "The highest-information unresolved variable is the absent explicit review-status ontology; hold model, runtime, tasks, validator, and all other prompt content fixed in a separately authorized exploratory paired screen.",
            "execution": "not executed",
        },
        "tasks": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    confusion_lines = []
    for key, value in analysis["review_status_audit"]["confusion"].items():
        confusion_lines.append(f"| `{key}` | {value['count']} | {', '.join(value['task_ids'])} |")
    near_lines = []
    for row in analysis["near_misses_3_of_4"]:
        near_lines.append(f"| {row['task_id']} | {row['observed_review_status']} | {row['classification']} | {row['allowed_targets_exact']} | {row['held_targets_exact']} | {row['scope_expansion_correct']} |")
    false_lines = []
    for row in analysis["five_false_positive_false_branch"]:
        false_lines.append(f"| {row['task_id']} | {row['expected_allowed_targets']} | {row['expected_held_targets']} | {row['observed_allowed_targets']} | {row['observed_held_targets']} | {row['authority_overlap'] or '—'} | {row['allowed_targets_exact']} / {row['held_targets_exact']} | {row['review_status']} |")
    inter = analysis["intersections"]
    report = f"""# Qwen3.5-0.8B Atomic Failure Isolation

`MODEL_FREE_FORENSIC_ANALYSIS_ONLY`

This report does not alter the frozen audition result, raw responses, terminal
validator artifacts, aggregate, or original audition report. It separates
protocol-token alignment from semantic evidence using preserved outputs only.

## Frozen result preserved

- Raw parse-valid: **16/16**
- Atomic structural contract-valid: **11/16**
- Full validator-valid: **0/16**
- Allowed exact: **8/16**; held exact: **6/16**
- Authority separation observed/correct: **11/16**
- Scope expansion: true branch **8/8**, false branch **3/8**
- Review-status exact: **0/16**
- Semantic profiles: 0/4 **3**, 1/4 **6**, 2/4 **2**, 3/4 **5**, 4/4 **0**

Bindings: run `{run.relative_to(ROOT)}`, execution manifest SHA256
`{sha(run / 'screening_manifest.json')}`, source audition report SHA256
`{sha(SOURCE_REPORT)}`, and source matrix SHA256 `{sha(SOURCE_MATRIX)}`.

## Review-status ontology audit

All 16 scope fixtures expect the same exact literal: `ready_for_review`.
The audition prompt required only `review_status` to be a JSON string and did
not provide an allowed ontology. Therefore this population measures protocol
token compliance more directly than multi-state review judgment.

| Expected → observed | Count | Task IDs |
|---|---:|---|
{chr(10).join(confusion_lines)}

Observed labels were not normalized. The repository contains
`ready_for_review` for the scope-authority family; `review_required` occurs in
other task-family fixtures but was not an expected value in this audition.

## Conservative semantic-proximity view

| Classification | Count | Task IDs |
|---|---:|---|
| ONTOLOGY_ONLY_CANDIDATE | {analysis['review_status_semantic_proximity']['counts']['ONTOLOGY_ONLY_CANDIDATE']} | {', '.join(analysis['review_status_semantic_proximity']['ONTOLOGY_ONLY_CANDIDATE'])} |
| SEMANTIC_STATE_MISMATCH | {analysis['review_status_semantic_proximity']['counts']['SEMANTIC_STATE_MISMATCH']} | {', '.join(analysis['review_status_semantic_proximity']['SEMANTIC_STATE_MISMATCH'])} |
| AMBIGUOUS | {analysis['review_status_semantic_proximity']['counts']['AMBIGUOUS']} | {', '.join(analysis['review_status_semantic_proximity']['AMBIGUOUS'])} |

The ontology-only label is used only where the rest of the object is 3/4 and
the emitted state preserves a non-approval/review boundary. `approved` is a
semantic-state mismatch on tasks whose held/unauthorized facts contradict
approval. The remaining cases are ambiguous because the single-state fixture
population cannot distinguish lexical ontology failure from review-state
reasoning.

## Five 3/4 near misses

| Task | Observed status | Classification | Allowed exact | Held exact | Scope exact |
|---|---|---|---:|---:|---:|
{chr(10).join(near_lines)}

Three of five are plausible interface/ontology-only cases; two remain
ambiguous. None is converted into a validator pass, and no
`ready_for_review` substitution was applied.

## False-branch scope-expansion forensic

The five false positives were `{', '.join(inter['false_positive_expansion'])}`.

| Task | Expected allowed | Expected held | Observed allowed | Observed held | Overlap | Target exactness | Status |
|---|---|---|---|---|---|---|---|
{chr(10).join(false_lines)}

The observable pattern is mixed rather than a pure boolean-only defect:

- `run6-scope-006` had both target sets exact but still produced a false-positive expansion flag.
- `run6-scope-001` preserved allowed targets but missed the held target identity.
- `run6-scope-002` and `run6-scope-007` combined target/authority overlap with false-positive expansion.
- `run6-scope-005` omitted both target sets and produced a false-positive expansion.

Thus only one of five false positives is an isolated expansion decision; four
co-occur with target or authority errors.

## Branch and overlap comparison

| Branch | Tasks | Expansion correct | Allowed exact | Held exact | No overlap | Semantic profile distribution |
|---|---:|---:|---:|---:|---:|---|
| false | 8 | 3 | 3 | 2 | 6 | 0/4={analysis['branch_comparison']['false']['semantic_profile_distribution']['0']}, 1/4={analysis['branch_comparison']['false']['semantic_profile_distribution']['1']}, 2/4={analysis['branch_comparison']['false']['semantic_profile_distribution']['2']}, 3/4={analysis['branch_comparison']['false']['semantic_profile_distribution']['3']} |
| true | 8 | 8 | 5 | 4 | 5 | 0/4={analysis['branch_comparison']['true']['semantic_profile_distribution']['0']}, 1/4={analysis['branch_comparison']['true']['semantic_profile_distribution']['1']}, 2/4={analysis['branch_comparison']['true']['semantic_profile_distribution']['2']}, 3/4={analysis['branch_comparison']['true']['semantic_profile_distribution']['3']} |

Intersections:

- False-positive expansion ∩ overlap: `{', '.join(inter['false_positive_and_overlap']) or 'none'}`
- False-positive expansion ∩ allowed mismatch: `{', '.join(inter['false_positive_and_allowed_mismatch']) or 'none'}`
- False-positive expansion ∩ held mismatch: `{', '.join(inter['false_positive_and_held_mismatch']) or 'none'}`
- False-positive expansion ∩ 0/4 or 1/4: `{', '.join(inter['false_positive_and_low_profile']) or 'none'}`
- All overlap tasks: `{', '.join(inter['overlap'])}`

The true-branch success and false-branch false-positive pattern supports a
positive-response bias descriptively, but the target-error intersections mean
it is not isolated as a standalone expansion mechanism.

## Hypothesis states

- **REVIEW_STATUS_ONTOLOGY_ALIGNMENT_FAILURE — SUPPORTED.** Exact protocol compliance was 0/16, the prompt supplied no ontology, and five non-protocol labels were emitted.
- **REVIEW_STATE_REASONING_FAILURE — INSUFFICIENT_EVIDENCE.** Three of five near misses are plausible ontology-only cases, and no task required choosing among multiple legitimate review states.
- **SCOPE_EXPANSION_POSITIVE_RESPONSE_BIAS — SUPPORTED.** The descriptive split was 8/8 true versus 3/8 false, with five false positives; this is not a model-size-floor claim or causal explanation.

## Recommended next experiment

**REVIEW_ONTOLOGY_INTERFACE_ISOLATION**.

Use the same model/runtime/tasks and change only the review-status interface by
supplying the exact legitimate ZTH ontology. Keep raw validation authoritative
and treat the result as exploratory. This is the highest-information next
step because it directly tests the strongest confound before moving model
size. It is not executed or preregistered here.

## Integrity

- Raw responses unchanged: `true`
- Terminal validator artifacts unchanged: `true`
- Frozen audition changed: `false`
- Model calls in this analysis: `0`

Machine-readable detail is in
`{OUTPUT_JSON.relative_to(ROOT)}`.
"""
    OUTPUT_REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"report": str(OUTPUT_REPORT.relative_to(ROOT)), "json": str(OUTPUT_JSON.relative_to(ROOT)), "model_calls": 0, "report_sha256": sha(OUTPUT_REPORT), "json_sha256": sha(OUTPUT_JSON)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
