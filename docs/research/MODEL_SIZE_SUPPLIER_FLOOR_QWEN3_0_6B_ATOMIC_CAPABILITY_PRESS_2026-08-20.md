# Qwen3-0.6B Atomic Capability Press

## Scope and provenance

This is a model-free analysis of two completed exploratory screens. It does
not call a model, rerun either screen, alter raw responses or validators, or
create confirmatory evidence. The frozen Stage A disposition remains
`NOT_PROMISING_AT_THIS_SIZE`.

The analysis treats the two screens as paired observations of the same twelve
tasks:

- Stage A: `.work/model_size_supplier_floor/qwen3_0_6b_stage_a/run_20260820T171851Z/`
- Explicit-interface screen: `.work/model_size_supplier_floor/qwen3_0_6b_interface_disambiguation/run_20260820T181000Z/`
- Stage A report SHA256: `51543cc07aa89922e86c554b669b8da689d151ace7f181f5f39cac3eb6eda14b`
- Stage A forensic report SHA256: `c3b95e43a9e9c5d68ca2f54f8920f02886bd8f0930561618ca1bf60bb57e361b`
- Interface-screen report SHA256: `303496298d725ba95b74952e2d7844f4997249a6eafe920b397dc09777bdd1bd`
- Atomic matrix: `docs/research/MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_0_6B_ATOMIC_CAPABILITY_MATRIX_2026-08-20.json`

The matrix contains the per-task reference facts, scores, paired comparison,
feature conditioning, and SHA256 manifests for every file in both preserved
run trees. Those manifests are the durable immutability record for this
analysis. `model_calls_made=0`, `raw_artifacts_changed=false`, and
`validator_artifacts_changed=false`.

## Reference fact matrix

Scoring was anchored first to the frozen fixture validator reference facts:

- `allowed_targets`
- `held_targets`
- `scope_expansion_required`
- `review_status`

The twelve task-specific facts and their fixture source paths/SHA256 values
are recorded in the matrix. Difficulty features were copied only from the
fixture metadata; no new feature labels were invented. All twelve fixtures
require the positive `scope_expansion_required=true` branch, so expansion
results do not test the negative branch.

For Stage A, only the already-justified in-memory operation was used: removal
of one outer markdown fence. For the interface screen, raw results remain
primary and the same wrapper-only exposure is reported secondarily. No field
value, type, target, or authority decision was repaired.

## Full-task results are not atomic results

Both screens have zero fully validated responses. That is important for the
supplier role, but it does not imply zero atomic capability. The following
sections measure the component decisions independently.

### Serialization and structural contract

| Measure | Stage A raw | Stage A fence-exposed | Interface raw | Interface fence-exposed |
|---|---:|---:|---:|---:|
| Bare/parse-valid JSON | 0/12 | 12/12 | 6/12 | 12/12 |
| Correct field types | 0/12 | 3/12 | 6/12 | 12/12 |
| Structurally contract-usable | 0/12 | 3/12 | 4/12 | 10/12 |
| Fully validator-valid | 0/12 | 0/12 | 0/12 | 0/12 |

The explicit interface therefore fixed a real interface/representation
component: raw bare JSON rose from 0/12 to 6/12, and every fence-exposed
interface response had the required field types. It did not fix the semantic
reference checks.

### Target identification

Metrics below are micro-averaged across target literals. They are diagnostic,
not a population estimate.

| Run/view | Allowed exact | Allowed precision / recall / F1 | Held exact | Held precision / recall / F1 |
|---|---:|---:|---:|---:|
| Stage A fence-exposed | 6/12 | 0.471 / 0.571 / 0.516 | 2/12 | 0.400 / 0.250 / 0.308 |
| Interface raw | 3/12 | 0.600 / 0.429 / 0.500 | 4/12 | 0.818 / 0.375 / 0.514 |
| Interface fence-exposed | 6/12 | 0.526 / 0.714 / 0.606 | 6/12 | 0.591 / 0.542 / 0.565 |

In the fence-exposed views, both target sets were exact on 2/12 Stage A
responses and 5/12 interface responses. Target identity sometimes survived a
representation error: a singleton string can identify the right target while
still failing the required list type. The original response remains invalid
in that case.

### Authority separation, expansion, and review status

| Measure | Stage A raw | Stage A fence-exposed | Interface raw | Interface fence-exposed |
|---|---:|---:|---:|---:|
| No allowed/held overlap | 12/12* | 10/12 | 10/12 | 10/12 |
| Scope expansion correct | 0/12 | 2/12 | 6/12 | 12/12 |
| Scope expansion type-correct and correct | 0/12 | 1/12 | 6/12 | 12/12 |
| Review status exact | 0/12 | 0/12 | 0/12 | 0/12 |

`*` Raw Stage A has no parsed object; this is a vacuous non-overlap count, not
evidence of correct separation. Review status was expected to be
`ready_for_review` for these fixtures. The observed normalized statuses never
matched it: Stage A produced `allowed`, `approved`, `hold`, `pending`,
`proposal`, `read-only`, and `ready`; the interface screen produced `allowed`,
`approved`, `hold`, `ready`, and `required`.

### Atomic semantic-field distribution

The four field points are exact allowed-target set, exact held-target set,
correct expansion boolean, and exact review status. Type errors are not silently
converted into semantic passes.

| Correct fields | Stage A raw | Stage A fence-exposed | Interface raw | Interface fence-exposed |
|---:|---:|---:|---:|---:|
| 0/4 | 12 | 6 | 6 | 0 |
| 1/4 | 0 | 3 | 2 | 5 |
| 2/4 | 0 | 2 | 1 | 2 |
| 3/4 | 0 | 1 | 3 | 5 |
| 4/4 | 0 | 0 | 0 | 0 |

There was one Stage A and five explicit-interface 3/4 near-miss observations,
but none had the fourth review-status field correct. The interface produced
five 3/4 profiles after wrapper exposure; this is partial atomic evidence, not
a validated supplier result.

Other full combinations are retained in the matrix. Fence-exposed exact
targets plus correct expansion occurred on 2/12 Stage A and 5/12 interface
observations; exact targets plus exact review status, all four semantic fields,
and fully validator-valid were each 0/12 in both views.

## Type errors versus semantic errors

Stage A had only 3/12 fence-exposed responses with all required field types;
the interface screen had 12/12 after wrapper exposure. Examples of diagnostic
representation failures include singleton strings in target fields and string
forms of the expansion flag. Where a literal singleton string named an
expected target, the matrix records `target_identity_semantically_usable=true`
while `type_correct=false`; it is not counted as contract-valid. No broad
natural-language interpretation or field invention was used.

## Paired interface effect

The explicit interface improved 11 tasks and left one unchanged; no task was
classified as regressed. The unchanged task was `run7-scope-012`, which already
had a 3/4 fence-exposed semantic profile and remained 3/4. Improvements were
component-specific:

- scope-expansion judgment changed on tasks 001, 002, 003, 004, 005, 006,
  007, 008, 009, and 010;
- held-target judgment also improved on 002, 005, 006, and 011;
- serialization/type behavior improved broadly, from 3/12 to 12/12 correct
  types in the fence-exposed view;
- review status did not improve to an exact match on any task.

The interface change therefore fixed serialization and the expansion decision
more than it fixed complete authority reasoning. It did not rescue any full
validation result.

## Repeated error clusters

Counts below refer to the fence-exposed diagnostic views unless stated
otherwise; task IDs are in the matrix at per-response granularity.

| Cluster | Stage A | Interface |
|---|---:|---:|
| Review-status mismatch | 12/12 | 12/12 |
| Allowed-target set mismatch | 6/12 | 6/12 |
| Held-target set mismatch | 10/12 | 6/12 |
| Allowed/held overlap | 2/12 | 2/12 |
| Scope-expansion mismatch or uninterpretable | 10/12 (3 mismatch, 7 uninterpretable) | 0/12 |
| Type/representation error | 9/12 | 0/12 |

Stage A allowed-target mismatches were tasks 001, 003, 004, 005, 007, and
009; held-target mismatches were 001, 002, 003, 004, 005, 006, 007, 009,
010, and 011. Interface allowed-target mismatches were 001, 003, 004, 005,
007, and 009; held-target mismatches were 001, 003, 004, 007, 009, and 010.
Overlap occurred on 003 and 009 in both normalized views. Review-status
mismatch occurred on every task in every parsed/fence-exposed semantic view.

## Task-feature conditioning

These are descriptive overlapping counts across only twelve tasks, not tests
of feature effects. The value is mean `semantic_fields_correct` per feature.

| Fixture feature | n | Stage A mean | Interface mean |
|---|---:|---:|---:|
| conflicting authority across artifacts | 4 | 0.75 | 2.25 |
| cross-artifact target consistency | 5 | 1.20 | 2.00 |
| implicit/explicit approval distinction | 6 | 1.00 | 2.17 |
| multiple simultaneous allowed/held boundaries | 6 | 0.50 | 1.50 |
| nested responsibility/authority | 7 | 0.86 | 2.14 |
| partial or stale authority | 4 | 0.75 | 2.00 |
| preserve allowed targets and hold others | 8 | 0.88 | 2.13 |
| scope change requiring separate authorization | 8 | 0.75 | 1.88 |

The interface screen improved descriptive atomic counts across every listed
feature, but the sample is too small and overlapping to identify a causal
feature boundary.

## Atomic capability map

| Atomic responsibility | Evidence classification | Boundary |
|---|---|---|
| Produce machine-readable JSON | `PARTIAL` | `INTERFACE_DEPENDENT` |
| Respect required field types | `PARTIAL` | `INTERFACE_DEPENDENT` |
| Identify allowed targets | `PARTIAL` | — |
| Identify held targets | `PARTIAL` | — |
| Separate allowed from held | `PARTIAL` | — |
| Detect scope expansion | `DEMONSTRATED` | positive-required branch only |
| Select review status | `NOT_DEMONSTRATED` | — |
| Complete bounded scope-authority decision | `NOT_DEMONSTRATED` | — |

“Demonstrated” for expansion is deliberately narrow: every interface
fence-exposed response matched the positive flag in this sample, but no task
tested a false branch. It is not evidence of universal expansion judgment.

## Practical interpretation

### What survives at approximately 596M?

The candidate can emit an existing JSON object behind a removable wrapper on
all twelve Stage A tasks, and the explicit typed interface raises direct bare
JSON compliance to 6/12 and required types to 12/12 after wrapper exposure.
Target identities and allowed/held set decisions are partially present. The
positive scope-expansion decision is consistently present under the explicit
interface in this sample.

### Main blockers

The strongest systematic blocker is review-status selection: 0/24 normalized
observations matched the required status. Target-set errors and two recurring
allowed/held overlaps remain. Thus the failure is not one isolated formatting
defect, even though formatting was a real Stage A confound.

### Breadth and narrower stewardship

The evidence is best characterized as
`FRAGMENTED_PARTIAL_CAPABILITY`: interface-sensitive serialization and some
target/expansion mechanics are present, while complete authority decisions and
review status are not demonstrated. A narrower supplier role is **not
supported** by this evidence: no bounded sub-role was independently specified
and validated, and the persistent review-status failure prevents assigning
stewardship from these observations.

This does not change `NOT_PROMISING_AT_THIS_SIZE` for the full supplier role,
and it does not establish that the model is broadly incapable of reasoning.

## Recommended next research actions

1. Bracket upward in model size using the same atomic matrix and explicit
   typed interface, because complete stewardship and review-status selection
   remain at 0/12.
2. If useful after that comparison, run a separately authorized logic-probe
   screen isolating review-status and allowed/held boundary decisions to test
   whether a genuinely narrower role exists. Do not assign that role from
   screening output alone.

No next model was selected in this analysis.

## Reproducibility and immutability

The reproducible scorer is
`scripts/zth_qwen3_0_6b_atomic_capability_press.py` and its model-free tests
are in `tests/test_qwen3_0_6b_atomic_capability_press.py`. The machine-readable
matrix is the authoritative detailed score artifact; it includes all 24
per-task/per-view records, reference-fact hashes, paired classifications,
feature conditioning, capability map, and complete run-tree SHA256 manifests.

The preserved Stage A and interface-screen run trees, raw responses,
terminal validators, and aggregates were read only and remain unchanged.
