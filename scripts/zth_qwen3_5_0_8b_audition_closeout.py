#!/usr/bin/env python3
"""Generate review-only Qwen3.5-0.8B audition artifacts from terminal evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_ATOMIC_AUDITION_2026-08-20.md"
MATRIX = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_ATOMIC_AUDITION_MATRIX_2026-08-20.json"
RUNTIME = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_RUNTIME_FREEZE_2026-08-20.json"
TASK_MANIFEST = ROOT / "docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_AUDITION_TASK_SET_2026-08-20.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def md(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("|", "\\|")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    manifest = load(run / "screening_manifest.json")
    aggregate = load(run / "aggregate.json")
    runtime = load(RUNTIME)
    task_manifest = load(TASK_MANIFEST)
    rows = [load(path) for path in sorted((run / "tasks").glob("*/atomic_scorecard.json"))]
    rows.sort(key=lambda row: manifest["selection"]["task_order"].index(row["task_id"]))
    task_paths = {}
    for row in rows:
        task_dir = run / "tasks" / row["task_id"]
        task_paths[row["task_id"]] = {
            "response": str(task_dir.relative_to(ROOT) / "response.json"),
            "response_sha256": sha(task_dir / "response.json"),
            "validation": str(task_dir.relative_to(ROOT) / "validation.json"),
            "validation_sha256": sha(task_dir / "validation.json"),
            "scorecard": str(task_dir.relative_to(ROOT) / "atomic_scorecard.json"),
            "scorecard_sha256": sha(task_dir / "atomic_scorecard.json"),
        }
    matrix = {
        "schema": "zth_qwen3_5_0_8b_atomic_audition_matrix_v1",
        "screening_only_not_confirmatory": True,
        "provenance": {
            "run_directory": str(run.relative_to(ROOT)),
            "execution_manifest_sha256": sha(run / "screening_manifest.json"),
            "aggregate_sha256": sha(run / "aggregate.json"),
            "runtime_freeze": str(RUNTIME.relative_to(ROOT)),
            "runtime_freeze_sha256": sha(RUNTIME),
            "task_manifest": str(TASK_MANIFEST.relative_to(ROOT)),
            "task_manifest_sha256": sha(TASK_MANIFEST),
            "scorecard_schema_sha256": sha(ROOT / "docs/research/ATOMIC_SUPPLIER_SCORECARD_SCHEMA_V1.json"),
            "raw_responses_preserved": True,
            "validator_artifacts_preserved": True,
            "historical_runs_modified": False,
            "model_calls_made": 16,
            "teacher_calls_made": 0,
            "retry_count": 0,
            "escalation_count": 0,
        },
        "candidate": runtime["candidate"],
        "runtime": runtime["runtime"],
        "hardware": runtime["hardware"],
        "aggregate": aggregate,
        "tasks": [
            {
                "task_id": row["task_id"],
                "reference_facts": row["reference_facts"],
                "scorecard": row,
                "artifact_paths": task_paths[row["task_id"]],
            }
            for row in rows
        ],
        "comparison_context": {
            "qwen3_0_6b_explicit_interface_raw_parse_valid": "6/12",
            "qwen3_0_6b_explicit_interface_normalized_contract_usable": "10/12",
            "qwen3_0_6b_explicit_interface_normalized_review_exact": "0/12",
            "qwen3_0_6b_explicit_interface_normalized_three_of_four": "5/12",
            "qwen3_1_7b_historical_profile": "structured historical paths generally demonstrated exact review ontology; not a task-matched size-only control",
        },
    }
    MATRIX.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    false_rows = [r for r in rows if not r["reference_facts"]["requires_scope_expansion_flag"]]
    true_rows = [r for r in rows if r["reference_facts"]["requires_scope_expansion_flag"]]
    confusion = {}
    for row in rows:
        observed = row["atomic"]["review_status"]["observed"]
        key = f"ready_for_review -> {observed}"
        confusion[key] = confusion.get(key, 0) + 1
    table = [
        "| Task | Branch | Parse | Contract | Allowed exact | Held exact | Scope observed/correct | Review observed | Sem fields | Full |",
        "|---|---:|---:|---:|---:|---:|---|---|---:|---:|",
    ]
    for row in rows:
        atomic = row["atomic"]
        table.append(
            "| " + " | ".join([
                md(row["task_id"]),
                "true" if row["reference_facts"]["requires_scope_expansion_flag"] else "false",
                md(row["raw_parse_valid"]), md(row["contract_valid"]),
                md(atomic["allowed_targets"]["exact_set_match"]), md(atomic["held_targets"]["exact_set_match"]),
                f"{md(atomic['scope_expansion']['observed'])}/{md(atomic['scope_expansion']['correct'])}",
                md(atomic["review_status"]["observed"]), md(atomic["semantic_fields_correct"]), md(row["full_validator_pass"]),
            ]) + " |"
        )
    profile = aggregate["semantic_fields_correct_distribution"]
    report = f"""# Qwen3.5-0.8B Atomic Supplier Audition

`SCREENING_ONLY_NOT_CONFIRMATORY`

This exploratory audition tested one candidate supplier on the frozen 16-task
scope-authority-boundary set. It did not call a teacher, retry, escalate,
modify historical evidence, update capability cards, or change production
routing.

## Frozen bindings

- Candidate: `{runtime['candidate']['model_identity']}` / `{runtime['candidate']['filename']}`
- Operative loaded supplier parameters: **{runtime['candidate']['operative_supplier_parameter_count']}**
- Upstream total parameter metadata: **{runtime['candidate']['upstream_total_parameter_count']}** (provenance, not the operative GGUF count)
- Artifact SHA256: `{runtime['candidate']['sha256']}`; size: `{runtime['candidate']['size_bytes']}` bytes
- Quantization: `{runtime['candidate']['quantization']}`
- Runtime: llama.cpp `{runtime['runtime']['llama_cpp_version']}` / `{runtime['runtime']['build_revision']}`, context `{runtime['runtime']['context']}`, thinking `{runtime['runtime']['reasoning']}`
- Hardware: `{runtime['hardware']['gpu_class']}`, UUID `{runtime['hardware']['gpu_uuid']}`
- Telemetry: Level 2, GPU-device-only, remote read-only HTTP, public alias `JARVIS_LOCAL`, sampling interval `0.25 s`
- Run directory: `{run.relative_to(ROOT)}`
- Execution manifest SHA256: `{sha(run / 'screening_manifest.json')}`
- Aggregate SHA256: `{sha(run / 'aggregate.json')}`

The Qwen3.5 architecture/generation differs from Qwen3-0.6B and Qwen3-1.7B;
these results provide upward-bracket information, not pure parameter-only
causal evidence.

## Execution result

All 16 responses were transport-valid and raw-parse-valid. None was fully
validator-valid.

| Measure | Result |
|---|---:|
| Tasks | 16 |
| Transport-valid | {aggregate['transport_valid']}/16 |
| Raw parse-valid | {aggregate['raw_parse_valid']}/16 |
| Structural contract-valid | {aggregate['contract_valid']}/16 |
| Validator structural all-checks-pass | {aggregate.get('validator_contract_valid', 'not separately retained')}/16 |
| Reference-fact-valid | {aggregate['reference_fact_valid']}/16 |
| Full validator passes | {aggregate['full_validator_passes']}/16 |
| Supplier calls | 16 |
| Teacher calls | 0 |
| Retries / escalations | 0 / 0 |

The raw interface therefore worked for this explicit typed JSON prompt, while
semantic and authority validation remained unsuccessful at the full-task
level.

## Atomic profile

| Dimension | Result |
|---|---:|
| Allowed-target exact set | {aggregate['allowed_targets']['exact']}/16 |
| Allowed-target mean precision / recall | {aggregate['allowed_targets']['precision_mean']:.3f} / {aggregate['allowed_targets']['recall_mean']:.3f} |
| Held-target exact set | {aggregate['held_targets']['exact']}/16 |
| Held-target mean precision / recall | {aggregate['held_targets']['precision_mean']:.3f} / {aggregate['held_targets']['recall_mean']:.3f} |
| Observed no-overlap separation | {aggregate['authority_separation']['observed_and_correct']}/16 |
| Any allowed/held overlap | {aggregate['authority_separation']['overlap']}/16 |
| Scope expansion correct | {aggregate['scope_expansion']['correct']}/16 |
| Scope expansion false positive | {aggregate['scope_expansion']['false_positive']}/16 |
| Scope expansion false negative | {aggregate['scope_expansion']['false_negative']}/16 |
| Review-status exact ontology | {aggregate['review_status']['exact']}/16 |

The branch-conditioned scope result was **{aggregate['branch_results']['false']['scope_expansion_correct']}/8** on the false branch and **{aggregate['branch_results']['true']['scope_expansion_correct']}/8** on the true branch. The five false positives occurred on false-branch tasks; there were no false negatives on true-branch tasks.

Semantic-field profile distribution (exact allowed set, exact held set,
scope-expansion boolean, exact review status):

| Profile | Count |
|---:|---:|
| 0/4 | {profile['0']} |
| 1/4 | {profile['1']} |
| 2/4 | {profile['2']} |
| 3/4 | {profile['3']} |
| 4/4 | {profile['4']} |

There were **{len(aggregate['three_of_four_near_misses'])}** 3/4 near misses:
`{', '.join(aggregate['three_of_four_near_misses'])}`. Every one was blocked
by `review_status`, not by a target or scope-expansion field. Exact review
ontology was absent in all 16 responses; observed labels were preserved as
confusion pairs: `{json.dumps(confusion, sort_keys=True)}`. No status aliases
were normalized.

Per-task atomic results:

{chr(10).join(table)}

## Resource measurements

Canonical latency was candidate action wall-clock time. Median / mean / p95
were **{aggregate['latency_ms']['median']} / {aggregate['latency_ms']['mean']} /
{aggregate['latency_ms']['p95']} ms**. Level-2 GPU-device telemetry recorded
mean gross energy **{aggregate['energy']['gross_joules_per_action_mean']:.6f} J/action**
and median **{aggregate['energy']['gross_joules_per_action_median']:.6f} J/action**.
Energy per validated task is unavailable because there were zero full
validated successes. These are not whole-system energy values and no energy
floor is claimed.

The 30-second idle baseline was **{aggregate['idle_power']['mean_power_watts']:.6f} W**
mean, with **{aggregate['idle_power']['gross_energy_joules']:.6f} J** gross
sampled energy. Process-level remote exclusivity was not independently
observable through telemetry endpoint v1; the operator runtime record stated
the candidate was the only model resident and the 1.7B reference was unloaded.

## Descriptive comparison

The Qwen3-0.6B explicit-interface profile had raw parse-valid `6/12`,
normalized contract-usable `10/12`, normalized exact review status `0/12`,
and normalized 3/4 profiles `5/12`. The present Qwen3.5 loaded supplier had
raw parse-valid `16/16`, but exact review status `0/16`, target partitioning
errors, and no full passes. The interface problem improved here, but the
semantic profile did not demonstrate complete stewardship.

Historical 1.7B paths generally demonstrated the exact `ready_for_review`
ontology on structured outputs, but those runs are not task-matched size-only
controls and the Qwen3.5 architecture is different.

## Interpretation

Practical characterization: **FRAGMENTED_PARTIAL_CAPABILITY**.

The candidate demonstrates machine-readable output and nonzero atomic target
and scope mechanics, especially on the positive scope-expansion branch, but
it systematically emits non-ontology review labels, has five authority
overlap cases, and fails the complete bounded scope-authority contract on all
16 tasks. Complete scope-authority stewardship is not demonstrated.

This is not evidence that the model lacks all bounded reasoning. It is evidence
that the tested supplier/interface/runtime combination did not provide a
complete steward for this responsibility.

## Next-size decision

**ISOLATE_ATOMIC_FAILURE_BEFORE_SIZE_MOVE.** The highest-information next
action is a model-free analysis/design that isolates review-status ontology
selection and the five false-branch scope-expansion/authority-partition errors
before choosing another model. If a future audition is authorized, it must
retain the same atomic scorecard and separately freeze any new task set; this
screen is exploratory and does not create Stage B evidence.

## Integrity boundaries

- Raw responses and terminal validator artifacts were preserved unchanged.
- Historical Run 1–8 evidence was not modified or merged.
- No teacher, external, retry, or escalation calls occurred.
- No production routing or capability card was changed.
- `model_calls=16`; this report itself is model-free.

This report is review-only and does not confer production authority.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"report": str(REPORT.relative_to(ROOT)), "matrix": str(MATRIX.relative_to(ROOT)), "report_sha256": sha(REPORT), "matrix_sha256": sha(MATRIX)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
