# Qwen3.5-0.8B Review-Ontology Interface Isolation

`EXPLORATORY_CANDIDATE_ONLY_NOT_STAGE_B`

This paired run held the Qwen3.5 loaded-752M supplier, runtime, task bytes,
task order, validator, telemetry, and call policy fixed. It changed only the
review-status prompt specification by explicitly supplying the legitimate
`ready_for_review` protocol token. The original run remains untouched.

## Prompt binding

Original suffix SHA256: `3a1003f506379b1fd21eae3103cc683bf86a12f5667bdcc07a76828a58b0b9c8`  
New suffix SHA256: `bd6c3d2aa7513fc913c48ba153b7c18d840b493f76db7c30780e084e4a64dbc7`  
Diff SHA256: `8a4fae590e4428feb6167884d28f446266efd18c1b5aeded77c9d7d16b53aa1d`

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
`run6-scope-008, run7-scope-015, run7-scope-018`. Therefore those paired observations satisfy
`ORIGINAL_PROMPT_BLOCKED_FULL_VALIDATION=true`. The two remaining original
3/4 tasks, `run7-scope-014` and `run7-scope-016`, became 2/4 in this stochastic
regeneration and did not validate.

## Paired component deltas

All 16 tasks improved on `review_status_correctness`.

- `IMPROVED`: 10 — `run6-scope-001, run6-scope-002, run6-scope-005, run6-scope-007, run6-scope-008, run7-scope-013, run7-scope-015, run7-scope-017, run7-scope-018, run7-scope-020`
- `MIXED`: 6 — `run6-scope-003, run6-scope-004, run6-scope-006, run7-scope-014, run7-scope-016, run7-scope-019`
- `REGRESSED`: 0
- `UNCHANGED`: 0

The six mixed tasks had review improvement but at least one simultaneous
non-review regression. This confirms that stochastic regeneration changed
other decisions too; those changes are not attributed causally to the ontology
instruction.

Observed non-review aggregate changes:

- Allowed exact: 8/16 → 6/16
- Held exact: 6/16 → 6/16
- Authority separation correct: 11/16 → 13/16
- Scope expansion correct: 11/16 → 9/16
- True branch: 8/8 → 8/8
- False branch: 3/8 → 1/8

## Scope and resource comparison

The true branch remained perfect. The false branch worsened from 3/8 to 1/8,
with seven false positives in the ontology-explicit run. This is a stochastic
paired outcome and does not invalidate the review-token effect; it identifies
the false branch as the next unresolved mechanic.

Latency (candidate action wall-clock):

- Original median / mean / p95: **962.803 / 922.622 / 1076.251 ms**
- Ontology-explicit median / mean / p95: **1082.869 / 1078.176 / 1234.398 ms**

Level-2 GPU-device gross energy:

- Original mean / median: **55.621563 / 57.260000 J/action**
- Ontology-explicit mean / median: **59.299375 / 61.687500 J/action**
- Ontology-explicit energy per validated task: **316.263333 J**

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

- Original run manifest SHA256: `96770484dc302de63619f58ff88397937b01b654b4f376d54eda53b74c4d1808`
- Original aggregate SHA256: `27a6757bfc7d3c356182d7a3d8995d32bc1967c35fa0eb7ef05e097d8ba5e330`
- New run: `.work/model_size_supplier_floor/qwen3_5_0_8b_review_ontology_isolation/run_20260821T011936Z`
- New manifest SHA256: `268908bd4306830c1c6f7b5b94ef0d5a27d7cc447533f427a9e08690867a2879`
- New aggregate SHA256: `adc2b43aaea0c3026375352a3bc4a417991996d58869cf91bf5efcaea4853150`
- Original run changed: `false`
- Teacher calls: `0`; retries: `0`; escalations: `0`
- Model calls made by this analysis: `0`

Machine-readable paired matrix:
`docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_REVIEW_ONTOLOGY_INTERFACE_ISOLATION_MATRIX_2026-08-20.json`
