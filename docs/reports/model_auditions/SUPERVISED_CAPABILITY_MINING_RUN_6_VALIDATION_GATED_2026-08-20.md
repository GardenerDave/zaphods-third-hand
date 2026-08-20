# Run 6 validation-gated economic escalation closeout

## Status

Run 6 completed as the frozen validation-gated sequential economic-routing
experiment. It produced 24 comparable policy tasks: 12 triage tasks using one
physically shared external action per task, and 12 scope tasks using isolated
external-control and local-first treatment paths.

The treatment preserved final validated portfolio solve rate and reduced
realized policy-level post-baseline elapsed time. Both preregistered success
criteria were met on this fresh mixed workload. This is review-only evidence;
it does not modify production routing, capability cards, prior Run 4/4A/4B/5
evidence, resource priors, or intervention status.

## Frozen provenance

- Execution commit: `4eb07b9427c2c3a3d808e6f314e772ee15cfcd5d`
- Execution directory: `.work/run6_sequential_economic_routing/run_20260820T030541Z/`
- Execution manifest: `.work/run6_sequential_economic_routing/run_20260820T030541Z/execution_manifest.json`
- Execution manifest SHA256: `f35d39d6ba7135c840a47da208c25a76dab8796b6ae7c9069185e8438ade86c4`
- Aggregate: `.work/run6_sequential_economic_routing/run_20260820T030541Z/aggregate.json`
- Aggregate SHA256: `29f8f38862af6558d23ce6e8d71935bfe5776b889613fc22bee9b73af3773bda`
- Triage selection: `.work/run6_sequential_economic_routing/run_20260820T030541Z/selections/triage.json`
- Triage selection SHA256: `bbd4c04006611088aab37ad65b898068cf65fcad551bcbd6b5be86ceea8e9b2f`
- Scope selection: `.work/run6_sequential_economic_routing/run_20260820T030541Z/selections/scope.json`
- Scope selection SHA256: `73b08b5b1c6807fcfa83a4462d3c3a40fee802ac780c3939b979c622f96d5628`
- Policy source SHA256: `7f28fa843c09a886f71138c71f11ce0e672786b23a9c9ff63127edbf48547e58`
- Policy freeze file SHA256: `8038870ad8e489e88e1cc3e67e86fe5284e4f9c719327b8bdb30ca1da3fc5337`
- Policy canonical digest: `20967f513a1939cd6a8afdf498c211b053e7bd381c6b9cf703ca1a706ffe5c7a`
- Driver SHA256: `01683c0f4b4eb29669258e4313fc261a85edbc36bab68210db9a31c2c418dc1c`
- Preregistration SHA256: `71f64a40565f4ccf634d65a633dbd4de5810ce294151220f2401b5272fd401e9`
- Triage fixture-pack canonical SHA256: `7f939b42581e78cfb56a2706b00d5e5ee711453e3467a52c2d64f937076fcaf7`
- Scope fixture-pack canonical SHA256: `dfe395c8cf3651069c8b9710fa71a129dbf262a4925ff3be1404134a8765e250`
- Triage manifest SHA256: `a06c56370240bd767062fd6692237bd42646c5fd4bdda532d2b90f58b0f4d344`
- Scope manifest SHA256: `128a44501536cb730eb6491555e20f66d5612e5f5843baf5c81d69a194203343`
- Triage novelty audit SHA256: `3f1c577f2ce9f4f73697a4df8bb6dbf90dd4c62f5072c9cce23c776bef0fadfd`
- Scope novelty audit SHA256: `ab2f7709606e1ceba496572e8248d529da8fe9d1f44ef28fe811974b97466926`
- Resource manifest SHA256: `8f7820a6a3e5734e071452f643374d8c6c769d4d149bcec3f2f82b88ee6530c2`
- Resource manifest canonical digest: `33ad2521dc5acc0be5a67b3ef77c167e882cf6ce53140dc60acc8f89c9ad76ab`
- Run 5 interpretation freeze SHA256: `a17591b29870f874a5f493107acf5c9b9982c1d2feae78c606200638a825cf22`
- Run 5 closeout report SHA256: `bfd41515bba5db7d9cf0ff60e7340a3c98b2f0c297320d544d5847037cf44cc9`
- Run 4A comparative evidence SHA256: `c48a97000fbf85b7ea3919a8269009d3200d3c2369924c456ec9dcc8736baf7b`
- Run 4B closeout report SHA256: `ddb09bd03fc62cdfaa71acbdc5e18fcb301be9a4f644496bb7292ce7d672df19`
- Pair-order seed: `20260825`

The execution manifest records `experiment_completed`, no active call, and no
infrastructure dispositions. Runtime identities matched the preregistration:
worker `Qwen_Qwen3-1.7B-Q4_K_M.gguf`, local teacher
`Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`, and external teacher
`codex-cli-0.146.0`.

## Frozen policies and selection

Control was `external_everywhere`: external teacher for triage-routing and
scope-authority-boundary. Treatment was
`validation_gated_economic_escalation`: the shared external action for triage,
and local teacher first for scope, with exactly one external escalation only
after a valid local model response failed deterministic validation.

There was no deterministic patch, fallback, third teacher, adaptive threshold,
or infrastructure-triggered escalation.

Each family had 15 candidates. The first 12 eligible baseline failures in
frozen order were selected; all 15 candidates in each family were eligible.
The following are all 30 terminal baseline dispositions:

| Family | Candidates | Disposition |
|---|---|---|
| Triage | `run6-triage-001` through `run6-triage-015` | `baseline_failed_eligible` |
| Scope | `run6-scope-001` through `run6-scope-015` | `baseline_failed_eligible` |

Selected tasks were `run6-triage-001` through `run6-triage-012` and
`run6-scope-001` through `run6-scope-012`. Reserves were candidates 013–015
within each family. No replacement or adaptive selection occurred.

## Comparative results

### Triage-routing: shared external action

| Measure | Result |
|---|---:|
| Comparable tasks | 12 |
| Common external validated solves | 11/12 |
| Common external elapsed | 419,645.131 ms |
| Control outcome | 11/12 |
| Treatment outcome | 11/12 |
| Paired outcomes | 11 `both_solve`; 1 `neither` |

The common action was physically executed once per selected task and its result
and realized policy cost were bound identically to both policy scorecards.

### Scope-authority-boundary: direct control versus sequential treatment

| Measure | Control external-direct | Treatment local-first |
|---|---:|---:|
| Comparable tasks | 12 | 12 |
| Final validated solves | 12/12 | 12/12 |
| Local-first passes | — | 12 |
| Local-first failures | — | 0 |
| External escalations | — | 0 |
| Realized post-baseline elapsed | 503,581.936 ms | 139,263.468 ms |

Scope paired outcomes were 12 `both_solve`, 0 `control_only`, 0
`treatment_only`, and 0 `neither`. The treatment had no escalation rescues,
escalation failures, or unresolved-after-escalation cases because every local
first stage passed deterministic validation.

### Portfolio result

| Measure | Control | Treatment |
|---|---:|---:|
| Comparable policy tasks | 24 | 24 |
| Final validated solves | 23/24 | 23/24 |
| Solve rate | 95.833% | 95.833% |
| Realized post-baseline policy elapsed | 923,227.067 ms | 558,908.599 ms |

- Quality preserved: **true**
- Realized resource reduced: **true**
- Economic routing success: **true**
- Absolute realized policy-level savings: **364,318.468 ms**
- Relative realized policy-level savings: **39.461%** versus control

The single portfolio miss was the shared triage `neither` outcome and therefore
affected both policies equally. No scope quality difference was observed.

## Escalation economics

- Scope local-first passes: 12/12
- Scope local-first failures: 0/12
- External escalations: 0/12 (0.000% escalation rate)
- Escalation rescues: 0
- Escalation failures: 0
- Treatment unresolved after escalation: 0
- External-first scope calls avoided by the treatment policy: 12
- Realized treatment scope elapsed: 139,263.468 ms
- Realized control scope elapsed: 503,581.936 ms

No recovery-failure cost was observed because no treatment escalation occurred.
The result therefore evaluates the observed all-local-pass branch and does not
estimate a universal failure value or escalation recovery price.

## Physical execution resource history

Physical accounting counts every durable model-call attempt, with shared triage
actions counted once:

| Role | Attempts | Valid response captures | Infrastructure failures | Realized elapsed |
|---|---:|---:|---:|---:|
| Worker | 66 | 66 | 0 | 215,826.970 ms |
| External teacher | 24 | 24 | 0 | 809,289.278 ms |
| Local teacher | 12 | 12 | 0 | 82,697.042 ms |
| **Total** | **102** | **102** | **0** | **1,107,813.290 ms** |

Trajectory reconciliation found 66 files with 66 `call_started` and 66
`response_captured` worker events, 24/24 external-teacher events, and 12/12
local-teacher events. No ambiguous started call or infrastructure artifact was
present.

## Expected versus realized cost

The frozen maximum planning budget was 126 calls and 1,639,564.146 ms,
including up to 12 treatment escalations. The observed execution used 102
calls and zero escalations. Under the frozen priors, the corresponding
zero-escalation physical expectation was 1,231,797.198 ms; realized physical
time was 1,107,813.290 ms. These are descriptive comparisons and do not
recalibrate the priors.

Frozen expected post-baseline policy costs were:

- Control: 815,533.896 ms
- Treatment with zero escalations: 665,733.240 ms
- Expected treatment savings for this observed branch: 149,800.656 ms

Realized policy-level costs were 923,227.067 ms for control and 558,908.599 ms
for treatment, yielding 364,318.468 ms (39.461%) realized savings. Expected
decision cost, realized policy cost, and physical experiment cost remain
separate quantities.

## Interpretation and limitations

On this fresh mixed triage/scope workload, deterministic validation-gated
conditional escalation preserved final validated portfolio performance while
reducing realized policy-level inference time relative to
external-teacher-everywhere. This is a result for the preregistered workload,
not a universal economic-routing claim.

The observed treatment branch had zero local failures and therefore did not
exercise external recovery. The experiment does not establish local universal
substitutability, universal escalation effectiveness, or a value-of-success
constant. It does not evaluate contradiction-handling or unsupported-certainty,
and it does not retire `external_teacher`.

No evidence was merged into capability cards or production routing. No
training, promotion, queueing, retirement, or autonomous downstream action was
performed.
