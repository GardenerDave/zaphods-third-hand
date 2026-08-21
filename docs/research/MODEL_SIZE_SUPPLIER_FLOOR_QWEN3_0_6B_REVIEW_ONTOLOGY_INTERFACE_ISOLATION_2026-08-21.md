# Qwen3-0.6B Review-Ontology Interface Isolation

`PROTOCOL_COMPLIANCE_ISOLATION`  
`EXPLORATORY_CANDIDATE_ONLY_NOT_STAGE_B`

This additive run held the Qwen3-0.6B supplier, artifact, runtime, GTX 1650,
telemetry, 12 tasks, order, fixtures, validator, and no-retry/no-escalation
policy fixed. It changed only the review-status protocol instruction. Neither
preserved 0.6B run was modified.

## Prompt correction

Original explicit-interface suffix SHA256: `8386cb934c15b3a07b6a668075961c505a2c5ecd2d57980a5509c885c67ff4bc`  
Corrected suffix SHA256: `75dc7be7a5e782b3858276d28fd90ba9a7620a951a4b3e1d308b904d6d12b7cc`  
Diff SHA256: `42c089dbed6563071950fc653ef8a4a4b6d2e561bc3837ebfff56da04a9882df`

The only addition was the explicit `ready_for_review` protocol token and a
prohibition on alternative labels. All 12 fixtures expect that same literal.
This experiment therefore measures protocol-token compliance more directly
than multi-state review-state reasoning.

## Primary result

| Measure | Original explicit-interface, normalized diagnostic view | Corrected raw run |
|---|---:|---:|
| Parse-valid | 12/12 exposed after one fence removal | 8/12 |
| Structural contract-valid | 10/12 | 6/12 |
| Review-status exact | 0/12 | 8/12 |
| Full validator-valid | 0/12 | 4/12 |
| Semantic 3/4 | 5/12 | 1/12 |
| Semantic 4/4 | 0/12 | 4/12 |

The corrected run produced 8/12 raw exact review tokens and 4/12 full
validated tasks. Four responses remained non-JSON and therefore had no
observable review field; raw validation remains authoritative.

The five preserved original normalized 3/4 tasks were:
`run7-scope-002, run7-scope-006, run7-scope-008, run7-scope-011, run7-scope-012`.

Four became 4/4 and fully validated in the corrected paired observations:
`run7-scope-006, run7-scope-008, run7-scope-011, run7-scope-012`. The fifth, `run7-scope-002`, did not; its
corrected response was non-JSON. These four paired observations satisfy
`ORIGINAL_PROMPT_BLOCKED_FULL_VALIDATION=true` without changing the original
run.

## Corrected atomic profile

- Allowed-target exact: 4/12
- Allowed-target micro TP/FP/FN: 8/6/6; precision/recall/F1: 0.571429/0.571429/0.571429
- Held-target exact: 5/12
- Held-target micro TP/FP/FN: 10/4/14; precision/recall/F1: 0.714286/0.416667/0.526316
- Authority separation observed and correct: 6/12
- Positive scope-expansion branch: 8/12
- False branch: not exercised; all 12 fixtures require expansion
- Semantic profile: 0/4=4, 1/4=0, 2/4=3, 3/4=1, 4/4=4

## Paired task changes

Compared against the preserved normalized explicit-interface objects, the
explicit component classifier found:

- IMPROVED: 8 — `run7-scope-003, run7-scope-004, run7-scope-005, run7-scope-006, run7-scope-008, run7-scope-009, run7-scope-011, run7-scope-012`
- REGRESSED: 4 — `run7-scope-001, run7-scope-002, run7-scope-007, run7-scope-010`
- MIXED: 0
- UNCHANGED: 0

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

Corrected 596M candidate action latency was **2148.464 ms median**, **2197.724 ms mean**, and **2442.516 ms p95**. Mean gross Level-2 GPU-device energy was **67.761667 J/action**; energy per validated task was **203.285 J**. These are GTX 1650 device-only exploratory measurements, not whole-system or confirmatory energy claims.

## Next experiment

**SCOPE_FALSE_BRANCH_LOGIC_PROBE**. Review-token compliance is now directly
tested, while this 0.6B population still has no negative scope-expansion
branch and target/authority errors remain. No such probe is executed here.

## Integrity

- Original run: `.work/model_size_supplier_floor/qwen3_0_6b_interface_disambiguation/run_20260820T181000Z`
- Corrected run: `.work/model_size_supplier_floor/qwen3_0_6b_review_ontology_interface_isolation/run_20260821T022334Z`
- Original run unchanged: `true`
- Historical raw/validator evidence changed: `false`
- Supplier calls: `12`; teacher calls: `0`; retries: `0`; escalations: `0`
- Analysis model calls: `0`

Machine-readable matrix: `docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_REVIEW_ONTOLOGY_INTERFACE_ISOLATION_MATRIX_2026-08-21.json`
