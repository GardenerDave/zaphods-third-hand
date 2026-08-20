# Historical Atomic Capability Press

## Scope and safety boundary

This is a model-free analysis of preserved scope-authority-boundary evidence.
No model was called, no experiment was rerun, and no historical response,
validator, aggregate, or disposition was modified. The results are diagnostic
vectors, not capability-card evidence and not production-routing authority.

The reusable scorer is `local_harness/atomic_capability_press.py`. The
historical reader is `scripts/zth_historical_atomic_capability_press.py`.
The detailed per-task matrix, including source hashes and complete run-tree
manifests, is:

`docs/research/HISTORICAL_ATOMIC_CAPABILITY_MATRIX_2026-08-20.json`

Only the scope-authority-boundary family was pressed. Triage and unrelated task
families were not forced into this adapter.

## Compatibility inventory

| Run | Population | Compatibility | Reason |
|---|---:|---|---|
| Run 4B | 12 pairs | `FULL_ATOMIC_PRESS_COMPATIBLE` | Raw worker terminal outputs, validators, reference fixtures, and provenance present. |
| Run 5 | 12 pairs | `FULL_ATOMIC_PRESS_COMPATIBLE` | Same durable evidence shape and stable `reviewed_run5_scope` facts. |
| Run 6 | 12 pairs | `FULL_ATOMIC_PRESS_COMPATIBLE` | Control/local stages fully present; escalation branch correctly recorded as unobserved. |
| Run 7 | 20 pairs, 3 escalation stages | `FULL_ATOMIC_PRESS_COMPATIBLE` | Control, local-first, and observed escalation outputs have preserved validators and references. |
| Run 8 | 20 pairs, 2 escalation stages | `FULL_ATOMIC_PRESS_COMPATIBLE` | Same evidence shape with the repaired escalation implementation bound in its own run. |

The existing Qwen3-0.6B press is retained as a separate
`PARTIAL_ATOMIC_PRESS_COMPATIBLE` imported profile. Its matrix already contains
per-task scores and immutable run-tree manifests, but its two exploratory
interface views are not the same lifecycle as Runs 4B–8. It was not silently
recomputed here.

The compatibility JSON records exact aggregate/report/fixture hashes. The
historical matrix records a SHA256 for every file in each run tree. These are
read-only immutability manifests.

## What was scored

For Runs 4B and 5, the scored terminal output for each arm is the preserved
`worker-retry.raw.json`, because that is the response received by the
deterministic four-field validator. For Runs 6–8, the same terminal worker
output is scored independently for `control_external`, `local_first`, and,
where present, `escalation`. Teacher artifacts, prompts, telemetry, and arm
bindings remain provenance; they are not treated as four-field scope answers
when their diagnostic schema differs.

All reference facts come from the run-specific frozen fixture directory. No
targets, booleans, or status labels were inferred from prose. A missing parsed
object produces `NOT_OBSERVABLE` for separation and expansion, not a vacuous
success.

## Longitudinal atomic results

The table reports exact field counts over each terminal stage. Full validator
passes remain separate from atomic counts.

| Run / stage | n | parse | types | allowed exact | held exact | separation observed/correct | expansion correct | review exact | full validator |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4B control external | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 |
| 4B local first | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 |
| 5 control external | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 |
| 5 local first | 12 | 12 | 12 | 11 | 11 | 12 | 11 | 11 | 11 |
| 6 control external | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 |
| 6 local first | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 | 12 |
| 7 control external | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 20 |
| 7 local first | 20 | 20 | 18 | 18 | 18 | 20 | 19 | 20 | 17 |
| 7 escalation | 3 | 2 | 1 | 1 | 1 | 2 | 2 | 2 | 1 |
| 8 control external | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 20 |
| 8 local first | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 18 | 18 |
| 8 escalation | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |

These profiles preserve supplier/runtime provenance. They are not a size-only
ranking: Runs 4B–8 use the established 1.7B worker with different teacher,
fixture, and lifecycle conditions; the 0.6B profile is reported separately.

### Near-miss press

Across the compatible terminal stage observations:

- 3/4 failures: 3 — one Run 7 local-first task and two Run 8 local-first
  tasks (`run7-scope-006`, `run8-scope-016`, and `run8-scope-018`);
- 2/4 failures: 3 — two Run 7 local-first tasks and one Run 7 escalation;
  specifically `run7-scope-001`, `run7-scope-019`, and the escalation stage of
  `run7-scope-019`;
- 0/4 failures: one Run 5 local-first non-object JSON response and one Run 7
  escalation parse failure;
- the dominant missing field in every 3/4 near-miss was
  `scope_expansion_required` (a false negative);
- all three 3/4 near-misses retained exact allowed targets, held targets, and
  review status.

Thus a full-task failure sometimes hides a nearly complete answer with one
missing governance decision. The matrix retains every 0/4–4/4 profile rather
than pooling them into pass/fail.

## Review-status decomposition

The larger-supplier terminal paths selected the exact ontology label
`ready_for_review` whenever a structured answer was present, apart from the
one unparsed Run 5 local-first output and the one unparsed Run 7 escalation
output. Exact counts were:

- Run 4B: 24/24 terminal arm outputs exact;
- Run 5: control 12/12, local 11/12;
- Run 6: control/local 12/12 each;
- Run 7: control 20/20, local 20/20, escalation 2/3 observable;
- Run 8: control/local/escalation 20/20, 20/20, and 2/2.

The imported 0.6B interface screen had 0/12 exact review status in both raw
and wrapper-exposed semantic views, with labels such as `approved`, `allowed`,
`hold`, `ready`, and `required`. These are preserved as exact confusion labels;
`ready` is not normalized to `ready_for_review`.

This is evidence for a review-status atomic floor signal at approximately
0.6B, while the 1.7B historical paths generally possess the ontology label.
It is not a population-level model-size claim.

## Escalation and repair deltas

There were five observed local-to-escalation transitions: three in Run 7 and
two in Run 8. The observed terminal worker-output deltas were:

| Transition | Classification | Observable delta |
|---|---|---|
| Run 7 `run7-scope-001` | `REGRESSED` | Parsed local output with 2/4 semantic fields became an unparsed escalation output with 0/4. |
| Run 7 `run7-scope-006` | `IMPROVED` | `scope_expansion_required` changed from false to correct true; 3/4 became 4/4. |
| Run 7 `run7-scope-019` | `UNCHANGED` | Both stages remained 2/4; no atomic component improved. |
| Run 8 `run8-scope-016` | `IMPROVED` | Corrected scope-expansion decision; 3/4 became 4/4. |
| Run 8 `run8-scope-018` | `IMPROVED` | Corrected scope-expansion decision; 3/4 became 4/4. |

The most common positive repair delta was therefore a single
`scope_expansion_correctness` component, observed 3/5 times. Three of five
escalation-stage outputs were fully atomic-valid; one was unchanged and one
regressed. These are before/after observations, not proof that the teacher
alone caused the change.

The stronger intervention did not merely repair one universal defect: it
sometimes supplied a narrow missing governance decision, sometimes produced
no observable repair, and once lost structure. In Run 8, both observed
escalations reached 4/4 and rescued the final task; in Run 7, only one of three
did.

## Feature conditioning

The fixture metadata already defines difficulty features for the Run 7 and
Run 8 samples. The matrix reports descriptive per-feature distributions for
each stage. No retrospective labels were added. Because features overlap and
the samples are small, these results identify candidate boundaries only; they
do not estimate feature effects.

The repeated visible boundary in the raw stage profiles is the positive
scope-expansion decision: it was the missing fourth field in all observed 3/4
near-misses. Target-set and review-status mechanics were otherwise preserved
in those near-misses.

## Longitudinal capability map

The detailed map is in the matrix. A compact reading is:

| Supplier/stage | Structured output | Target identification | Separation | Expansion | Review status | Full task |
|---|---|---|---|---|---|---|
| 1.7B control, Runs 4B–8 | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED |
| 1.7B local, Run 4B | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED |
| 1.7B local, Run 5 | PARTIAL | PARTIAL | DEMONSTRATED | PARTIAL | PARTIAL | PARTIAL |
| 1.7B local, Run 6 | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED |
| 1.7B local, Run 7 | DEMONSTRATED | PARTIAL | DEMONSTRATED | PARTIAL | DEMONSTRATED | PARTIAL |
| 1.7B local, Run 8 | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | PARTIAL | DEMONSTRATED | PARTIAL |
| 1.7B escalation, Run 7 | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| 1.7B escalation, Run 8 | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED |
| 0.6B imported interface-exposed profile | PARTIAL / interface-dependent | PARTIAL | PARTIAL | DEMONSTRATED on positive branch only | NOT_DEMONSTRATED | NOT_DEMONSTRATED |

“DEMONSTRATED” here means all observed rows for that named stage, not
universal reliability. Different rows have different fixtures and runtime
conditions.

## Stewardship interpretation

### Mechanics that appear cheap/local

In the established 1.7B worker evidence, target partitioning and review-status
selection are often already correct before escalation. Of 76 local-first
terminal observations across Runs 4B–8, 75 had observed correct allowed/held
separation; 73/76 had exact allowed and held target sets, and 75/76 had exact
review status.
The repeated local failure was not a general inability to serialize or name
targets.

### Mechanics repeatedly supplied by stronger intervention

The clearest observed repair target is the scope-expansion boolean: all three
3/4 near-misses missed it, and all three successful escalation deltas repaired
it. This is a narrow observed pattern, not a causal or universal rule.

### Narrower stewardship candidates

The evidence supports no new production stewardship assignment. At most, the
following are candidates for separately validated narrower roles: target-list
partitioning and positive scope-expansion detection under the explicit
contract. They are not authorized roles because the analysis does not provide
independent task-family confirmation for those sub-responsibilities.

## Standard future supplier scorecard

Future sub-billion auditions should emit, per supplier/stage:

- model, quantization, runtime, hardware, and provenance identity;
- task family and frozen reference-fact source hashes;
- attempts, transport-valid, parse-valid, contract-valid, and full-validator
  outcomes;
- semantic-fields-correct distribution from 0/4 through 4/4;
- allowed/held target TP, FP, FN, precision, recall, F1, and exactness;
- authority overlap, omission, invention, and authorized-held diagnostics;
- scope-expansion correct/false-positive/false-negative/not-observable;
- exact review-status ontology and expected→observed confusion counts;
- repair delta for each escalation, without causal attribution;
- latency, token counts, energy, measurement level/boundary, and escalation
  requirement;
- durable evidence paths and SHA256 hashes.

This is a vector scorecard, not a single intelligence score and not a
capability-card update.

## Next sub-billion audition implication

No next model was selected. The next audition should be compared against this
atomic baseline using the same explicit typed output contract and should emit
the full scorecard above. In particular, it must distinguish interface
compliance, target precision/recall, scope-expansion decisions, review-status
ontology, and repair deltas before any full-task or economic interpretation.
