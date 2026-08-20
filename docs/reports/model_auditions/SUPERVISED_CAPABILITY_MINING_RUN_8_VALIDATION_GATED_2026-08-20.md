# Supervised Capability Mining Run 8: Validation-Gated Escalation

Status: completed review-only experiment; no production-routing or capability-card authority.

## Executive result

Run 8 exercised the repaired validation-gated escalation branch on a fresh,
difficulty-enriched scope-authority-boundary workload.

- Control external-direct: 20/20 validated solves.
- Treatment local-first final result: 20/20 validated solves.
- Local-first initial passes: 18/20.
- Local-first validation failures: 2/20.
- Repaired external escalations: 2.
- Escalation rescues: 2/2.
- Paired outcomes: both_solve=20, control_only=0, treatment_only=0, neither=0.

Thus quality was preserved on all 20 comparable pairs. The repaired escalation
branch was empirically exercised and recovered both observed local-first
failures.

The realized control policy elapsed was 863,918.174 ms. The preregistered
sequential treatment elapsed, audited from the durable local and escalation
stage artifacts, was 338,286.365 ms. Savings were 525,631.809 ms, or
60.843%. Therefore `quality_preserved=true`, `resource_reduced=true`, and
`economic_routing_success=true` for this sample.

## Research question and policy

Run 8 asked whether, after the Run 7 escalation-guidance integration repair,
validation-gated local-first escalation preserves final validated quality
relative to external-direct control while reducing realized inference use on
fresh difficulty-enriched scope failures.

Control used external_teacher, one worker retry, deterministic validation, and
stop. Treatment used local_teacher, one worker retry, and deterministic
validation; only a valid local model response followed by deterministic
validation failure triggered one external_teacher escalation with the repaired
diagnostic/review-only contract and one additional worker retry.

There was no patch, fallback, third teacher, adaptive threshold, or
infrastructure-triggered escalation.

## Selection and freshness

The frozen pack contained 24 candidates. All 24 produced valid model-response
baseline failures satisfying the frozen failure_class and
scope-authority-boundary eligibility rules. The first 20 were selected; the
remaining four were reserves. Selection used no intervention outputs.

Selected tasks:

`run8-scope-001` through `run8-scope-020`.

Reserve tasks:

`run8-scope-021`, `run8-scope-022`, `run8-scope-023`, `run8-scope-024`.

The novelty audit recorded 24 new-source candidates, with zero task-ID
collisions, exact prompt duplicates, normalized prompt duplicates, or
high-similarity pairs. No model outputs were consulted during fixture
construction or selection.

## Mechanism outcomes

| Stage | Result |
|---|---:|
| Local-first passes | 18/20 |
| Local-first failures | 2/20 |
| Escalations triggered | 2/2 local failures |
| Escalation rescues | 2/2 |
| Escalation failures | 0/2 |
| Final treatment solves | 20/20 |

The escalation tasks were `run8-scope-016` and `run8-scope-018`; both had
valid local responses that failed deterministic validation, then passed after
the repaired external recovery path. No infrastructure exclusions occurred.

## Comparative result

| Policy | Validated solves | Realized post-baseline elapsed |
|---|---:|---:|
| External-direct control | 20/20 | 863,918.174 ms |
| Local-first with repaired escalation | 20/20 final | 338,286.365 ms |
| Difference | 0 solves | 525,631.809 ms savings (60.843%) |

Paired outcome counts were: both_solve=20, control_only=0,
treatment_only=0, neither=0.

The observed escalation rate was 2/20 = 10%, below the frozen 35% break-even
rate. Under the frozen priors, the expected treatment cost at two escalations
was 497,904.978 ms versus expected control cost of 679,611.580 ms.

## Sequential accounting note

The frozen raw `aggregate.json` records
`treatment_post_baseline_elapsed_ms=313,690.136 ms`, because the inherited
scorecard field sums the final stage and does not add the already durable local
stage for escalated tasks. The two escalated local stages contributed
13,176.262 ms and 11,419.967 ms. This review report therefore uses the
preregistered sequential policy definition:

`313,690.136 + 13,176.262 + 11,419.967 = 338,286.365 ms`.

The raw aggregate and all raw artifacts remain unchanged. The component-level
audit is used only for this review-only policy-cost calculation.

## Physical execution accounting

Actual physical attempts were:

- worker: 66;
- local_teacher: 20;
- external_teacher: 22;
- total model-call attempts: 108.

The maximum frozen structure was 144 calls. The actual physical elapsed total
was 1,321,265.219 ms, comprising 372,729.858 ms worker time, 135,530.470 ms
local-teacher time, and 813,004.891 ms external-teacher time. All 108 attempts
reached terminal artifacts and there were zero recorded infrastructure
failures.

Physical experiment cost is distinct from policy-level cost: both control and
treatment paths were run for scientific comparison, while the treatment policy
cost includes only its local-first stages and the two actual escalations.

## Interpretation and boundaries

Run 8 supports, on this fresh sample:

- repaired validation-gated escalation was exercised;
- both naturally observed local-first failures triggered escalation;
- both observed escalations rescued the task;
- final treatment quality matched external-direct control;
- treatment policy elapsed was materially lower.

This does not establish universal escalation reliability, universal
local/external equivalence, a universal rescue rate, retirement of
external_teacher, production-routing authority, or validation of the
M-parameter model. Run 7 remains historically bound to its unrepaired driver
and retains its original result: control 20/20, treatment 18/20,
quality_preserved=false, resource_reduced=true.

## Durable provenance

- Execution commit: `b3262446492ea5d061d76a782c54e81971d9a225`.
- Run directory: `.work/run8_scope_escalation/run_20260820T150846Z/`.
- Execution manifest: `.work/run8_scope_escalation/run_20260820T150846Z/execution_manifest.json`.
- Execution manifest SHA256: `312463d5825f3928d37449b63542d2bd55adf71cb5567ec9647c5fa3f21d3610`.
- Selection: `.work/run8_scope_escalation/run_20260820T150846Z/selections/scope.json`.
- Selection SHA256: `635cd923760b010d81cf95e980030b1ca0413dca272cbb370f48dbe5214a7b44`.
- Aggregate: `.work/run8_scope_escalation/run_20260820T150846Z/aggregate.json`.
- Aggregate SHA256: `225f1afaba0aa05212eb241481002ac1d6515575a139b894c3b5d5f466c7538d`.
- Run 8 preregistration SHA256: `0e9869657906f4c0df309ab665a09ebaa8924986c80b3514f84c9cfa590f9912`.
- Run 8 driver SHA256: `b849379340714e00ed47c3c2cd7b4d6eea2d9317385f0630cf1979e3d5ba6281`.
- Run 8 fixture-pack SHA256: `2a860d497ecc2fa314867e1058fa1191b04e1f0cc9fc1ae508039c047a53fed9`.
- Run 8 policy-freeze SHA256: `4333ab25ab960203e700b028a9d146b4d8910ed3fc9c3d6a9e72d15a39d5a071`.
- Run 7 repair-freeze SHA256: `1258bcea172c300259e3230aaf028a0b75161616ad1129f492d6c2b2214e49e5`.

This is a review-only closeout. Run 8 evidence is not merged into capability
cards and does not alter production routing.
