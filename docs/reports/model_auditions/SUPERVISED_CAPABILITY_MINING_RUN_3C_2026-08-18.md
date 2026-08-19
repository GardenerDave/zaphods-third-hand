# Supervised Capability Mining Run 3C

Run 3C was executed from the frozen preregistration and detached durable
launcher. The 24 tasks were evaluated in both arms with transport-valid model
responses; no adaptive changes were made.

## Headline results

| Metric | Control: fixed ladder | Treatment: frozen advisory routing |
|---|---:|---:|
| Validated passes | 14/24 (58.3%) | 15/24 (62.5%) |
| Unresolved | 10 | 9 |
| Worker calls | 83 | 73 |
| Deterministic retry calls | 24 | 16 |
| Local-teacher tasks / calls | 13 / 24 | 9 / 17 |
| External-teacher tasks / calls | 11 / 11 | 16 / 16 |
| Expensive teacher calls | 35 | 33 |
| Infrastructure failures | 0 | 0 |

Treatment expensive-teacher usage fell from 35 to 33 calls, a 5.7% reduction.
Treatment final validated passes were one higher than control.

The preregistered criteria are therefore:

- `routing_cost_reduction_observed`: MET
- `routing_quality_preserved`: MET
- `routing_success`: MET
- `strong_routing_result`: NOT MET (the reduction was below 25%)

This is evidence from one paired 24-task experiment, not statistical certainty
or proof of an optimal policy.

## Frozen execution and provenance

- Preregistration: `docs/research/RUN_3C_PREREGISTRATION_2026-08-18.json`
- Seed: `20260820`
- Task/arm ordering: the preregistered order was used unchanged.
- Output evidence: `.work/capability_batch_reviewed_v3c/run3c_execution_2026-08-20/`
- Execution status: completed; detached session terminated; launcher exit status was 0.
- All 48 arms had terminal durable state.
- Only transport-classified model responses entered capability metrics.
- The required non-metric worker preflight returned `model_response` for the configured worker.

## Treatment routing

Treatment routing dispositions:

- `recommend`: 20
- `avoid`: 0
- `abstain`: 4

Evidence resolutions:

- `task_family`: 20
- `none`: 4
- `exact_signature`, `semantic_signature`, `failure_class`: 0

Actions taken:

- deterministic patch retry: 12
- external teacher path: 8
- fixed ladder after abstention: 4

The treatment produced four treatment-only solves, three control-only solves,
11 solves in both arms, and six unresolved tasks in both arms. At the paired
task level, treatment was cheaper with an equal-or-better result on four tasks,
cheaper with a worse result on zero tasks, and more expensive on five tasks;
the remaining paired cases had equal intervention cost.

## Family results

| Family | Control passes | Treatment passes | Control expensive calls | Treatment expensive calls |
|---|---:|---:|---:|---:|
| contradiction-handling | 2/4 | 1/4 | 6 | 9 |
| destructive-action-restraint | 4/4 | 2/4 | 1 | 4 |
| evidence-grounding | 2/4 | 2/4 | 6 | 6 |
| queue-authority-boundary | 1/4 | 2/4 | 12 | 9 |
| scope-authority-boundary | 1/4 | 4/4 | 10 | 7 |
| unsupported-certainty | 4/4 | 4/4 | 0 | 1 |

The aggregate reduction coexists with family variation: treatment improved
scope and queue outcomes, while control did better on contradiction and
destructive-restraint in this sample.

## Interpretation and limits

Frozen evidence-guided routing reduced expensive model intervention by 2 calls
(5.7%) without reducing deterministic final solve rate. The result meets the
preregistered routing-success criterion but not the stronger 25% reduction
criterion. Routing recommendations were all at task-family resolution, so
this run does not establish exact-signature routing quality. The experiment
does not demonstrate autonomous stewardship, weight learning, permanent model
capability change, arbitrary out-of-distribution generalization, or universal
patch applicability.

All model outputs, validations, request provenance, routing decisions, and
paired trajectories remain in the ignored Run 3C evidence directory. No
patches were promoted, no training was performed, and no queue or acceptance
authority was granted.
