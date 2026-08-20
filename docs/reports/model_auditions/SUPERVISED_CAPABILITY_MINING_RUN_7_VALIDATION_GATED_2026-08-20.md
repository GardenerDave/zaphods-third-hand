# Supervised Capability Mining Run 7: Validation-Gated Escalation

Status: completed; review required; no capability-evidence merge.

Run 7 successfully exercised the previously unobserved validation-gated
escalation branch on 20 selected fresh, difficulty-enriched
`scope-authority-boundary` failures. Local-first failed deterministic
validation on 3/20 tasks. All three failures triggered exactly one
preregistered external recovery attempt; one recovered and two remained
unresolved.

The primary result was:

| Policy | Final validated solves | Realized post-baseline policy elapsed |
|---|---:|---:|
| Control, external-direct | 20/20 (1.000) | 798,455.839 ms |
| Treatment, local-first + conditional escalation | 18/20 (0.900) | 330,432.860 ms |
| Difference | -2 solves | -468,022.979 ms (-58.616%) |

Thus `quality_preserved=false`, `resource_reduced=true`, and
`economic_routing_success=false`. Run 7 demonstrated substantial economic
savings but failed the frozen quality-preservation criterion.

## Local supplier, validation gate, and recovery path

The sequential policy decomposes into three experimentally distinct
mechanisms.

### Local supplier

Local-first passed deterministic validation on 17/20 tasks and failed on 3/20.
The observed initial local success rate was 85%.

### Validation gate

All three observed deterministic local failures caused exactly one escalation.
The control-flow gate therefore behaved according to the frozen policy on all
three observed failure cases. This is evidence about these observations, not
a population-level estimate of validator sensitivity.

### External recovery

There were 3 escalation attempts, 1 rescue, and 2 unresolved tasks. The
observed recovery fraction was 1/3. Three observations are not a
population-level recovery-rate estimate.

## Direct external success versus escalation-path failure

The external-direct control solved 20/20, including all three tasks on which
local-first failed: `run7-scope-001`, `run7-scope-006`, and
`run7-scope-019`. The treatment-side external escalation solved only
`run7-scope-006`; it failed on `run7-scope-001` and `run7-scope-019`.

The external teacher identity was the same frozen supplier, but the
intervention paths differed. Control used:

```text
original baseline/task -> external teacher -> worker retry -> validation
```

Treatment recovery used:

```text
original baseline/task + local-failure evidence
    -> external escalation -> worker retry -> validation
```

The two `control_only` outcomes therefore cannot be explained simply as the
external teacher lacking capability on those tasks: matched direct control
paths solved both. The discrepancy makes treatment recovery path construction,
intervention context, or retry interaction the next diagnostic target. This
report does not claim which factor caused the discrepancy.

### Escalation-task comparison

Values below are mechanically extracted from the paired scorecards and stage
summaries. Treatment sequential elapsed is local-first elapsed plus escalation
elapsed.

| Task | Control external validation | Local-first validation | Escalated | Escalation validation | Final treatment | Paired outcome | Local ms | Escalation ms | Treatment sequential ms | Matched control ms |
|---|---|---|---|---|---|---|---:|---:|---:|---:|
| `run7-scope-001` | passed | failed | yes | failed | failed | control_only | 12,429.491 | 39,908.104 | 52,337.595 | 30,019.182 |
| `run7-scope-006` | passed | failed | yes | passed | passed | both_solve | 13,519.074 | 16,192.341 | 29,711.415 | 38,018.105 |
| `run7-scope-019` | passed | failed | yes | failed | failed | control_only | 11,896.758 | 58,401.492 | 70,298.250 | 34,656.247 |

## Gate effectiveness versus recovery effectiveness

Observed gate behavior was complete on the observed failures:

```text
3 local deterministic failures -> 3 escalations triggered
```

Observed recovery behavior was incomplete:

```text
3 escalations -> 1 rescue, 2 unresolved
```

The quality failure occurred after the gate had triggered the intended
recovery action. The artifacts do not support describing this as a failure to
detect the local misses.

## Escalation economics

The observed escalation rate was 3/20 = 15%. Under frozen priors, treatment
remains strictly cheaper through 7/20 = 35%; at 8/20 = 40% it is no longer
cheaper. Run 7 was therefore well inside the frozen economic envelope.

Run 7 did not fail because too many tasks escalated. It failed because two
escalated tasks were not recovered. This is why the resource criterion passed
while the combined economic-routing criterion failed.

| Treatment stage | Count |
|---|---:|
| Local-first passes | 17 |
| Local-first validation failures | 3 |
| Escalations | 3 |
| Escalation rescues | 1 |
| Escalation failures | 2 |
| Final treatment solves | 18 |

The observed paired outcomes were:

| Paired outcome | Count |
|---|---:|
| Both solve | 18 |
| Control only | 2 |
| Treatment only | 0 |
| Neither | 0 |

All intervention and escalation transport classifications were
`model_response`; infrastructure exclusions were zero.

## Selection and baseline dispositions

All 24 frozen candidates were processed in order. Every baseline was a valid
model response with a deterministic validation failure and was eligible under
the preregistered `failure_class` / `scope-authority-boundary` rule.

Selected, in frozen order:

`run7-scope-001` through `run7-scope-020`.

Reserve-only candidates:

`run7-scope-021`, `run7-scope-022`, `run7-scope-023`, `run7-scope-024`.

The selection artifact records `selection_uses_intervention_outputs=false`.

## Run 6 to Run 7

Run 6 had 12/12 scope local-first solves, zero escalations, 12/12 final scope
treatment solves, preserved portfolio quality, and 39.461% resource
reduction. Its escalation branch was unobserved.

Run 7 produced naturally observed local failures without intervention-based
fixture selection. It supplied the missing escalation observations: 17/20
local-first passes, 3 failures, 3 escalations, 1 rescue, and 2 unresolved
tasks. The branch trigger worked on this sample, but recovery was
insufficient to preserve quality.

## What Run 7 resolved

Run 6 left open whether naturally occurring local failures would trigger the
sequential recovery branch. Run 7 answers yes: three naturally observed local
validation failures triggered it.

Run 6 also left open whether escalation would reliably restore quality lost by
local-first. Run 7 answers no on this sample: one of three escalated failures
was recovered, while matched external-direct control solved all three.

The next unresolved diagnostic question is why the same frozen external
teacher solved `run7-scope-001` and `run7-scope-019` directly but failed to
recover them in treatment escalation. The next analysis should inspect the
paired artifacts before any policy change, including:

- teacher prompt construction;
- baseline evidence presented;
- local-failure diagnostics added;
- authority context;
- teacher and worker outputs;
- deterministic validation diagnostics;
- token, context, and resource metadata where available.

This report does not design or preregister a subsequent experiment.

## Descriptive cumulative scope chain

The following are separate experiments, verified from their frozen aggregate
artifacts:

| Experiment | Local/local-first | External/external-direct |
|---|---:|---:|
| Run 4A | 4/4 | 4/4 |
| Run 4B | 12/12 | 12/12 |
| Run 5 | 11/12 | 12/12 |
| Run 6 | 12/12 | 12/12 |
| Run 7 | 17/20 | 20/20 |
| Descriptive total | 56/60 | 60/60 |

**DESCRIPTIVE CUMULATIVE ARITHMETIC ONLY.** This is not one pooled
experiment, a formal equivalence analysis, a population reliability estimate,
retirement justification, or production-routing authorization. Run 7's
sequential final treatment result is reported separately as 18/20 after
escalation; it is not mixed into the initial-local numerator.

## Claim boundaries

Run 7 supports:

- naturally observed local failures on a difficulty-enriched fresh sample;
- deterministic triggering of the frozen escalation branch for those failures;
- one observed successful recovery and two observed unsuccessful recoveries;
- substantial realized resource savings;
- failure of the complete sequential policy to preserve quality on this
  sample.

Run 7 does not establish:

- universal escalation ineffectiveness;
- universal external-teacher weakness;
- validator failure;
- a universal 15% local failure rate or 1/3 escalation rescue rate;
- that local-first should be abandoned;
- that `external_teacher` should be retired;
- that the M-parameter model should be inserted;
- production-routing authority.

## Planning economics and physical accounting

Frozen action costs were 21,497.191 ms for local-first and 33,980.579 ms for
external-first. For 20 tasks:

```text
control = 20 × 33,980.579 = 679,611.580 ms
treatment = 20 × 21,497.191 + E × 33,980.579
```

The treatment is strictly cheaper through `E=7` (35%); at `E=8` (40%) it is
not cheaper under the frozen priors. The observed `E=3` was below that
threshold. Realized policy elapsed, rather than priors, determined the
primary resource result.

Physical execution history preserved every attempted call:

| Role | Attempts | Realized elapsed |
|---|---:|---:|
| Worker | 67 | 347,913.233 ms |
| Local teacher | 20 | 133,186.027 ms |
| External teacher | 23 | 767,171.320 ms |
| Total | 110 | 1,248,270.580 ms |

The 110 calls comprise 24 baselines, 20 external control actions, 20 local
first-stage actions, 3 treatment escalations, and their worker retries. No
call was triggered by infrastructure failure.

## Authority boundary

This report is a durable review artifact only. Run 7 evidence has not been
merged into capability cards or production routing, and no intervention has
been retired, promoted, trained, queued, or otherwise operationalized. The
M-parameter model remains outside this work.

## Frozen provenance

| Binding | Value |
|---|---|
| Execution commit | `08298d87147f67ad9ad2624c376adb8790cf1f75` |
| Pair-order seed | `20260826` |
| Run 7 driver | `scripts/zth_run7_scope_escalation.py` |
| Driver SHA256 | `f1bdac815109a2dce473529ae14ddc24d60b048b74f3268e25fa6f9d9b1ad547` |
| Preregistration | `docs/research/RUN_7_VALIDATION_GATED_ESCALATION_PREREGISTRATION_2026-08-20.json` |
| Preregistration SHA256 | `1c45ce7be83194d4adfb5cf1af6b04d90495712b6779956bc6f7691ac4055de6` |
| Policy source SHA256 | `015c0ee04724a6480e20b7730e9fcfd2663622c473dda937cf76f3e9f8ad2220` |
| Policy freeze file SHA256 | `1315ac04a5dc7171cc3d0c528a375da52a37b96cf9bf82a1a4ffd2fbea2e4cb1` |
| Policy canonical digest | `8e84c1c625eec039e68ea70fadb5ca551300fb1d04ac5604ceff36c82b0c1974` |
| Fixture pack SHA256 | `7b0f94b5301bba35a10165030b37313a8b5734f01c7a934d9e5ea9c25b800740` |
| Fixture manifest SHA256 | `f708ce62a524085446e0b42e633dbcf738be816d00564785d573230d1352117c` |
| Novelty audit SHA256 | `bbc548e52c69b88fc24b2d83dee3b3690b453e2e55ca947e67daea5b8ed240f2` |
| Difficulty criteria SHA256 | `5d8ffee88086f4d2cacd26549f153ee5d44b587e5c5d9d412228dfdd7ebbf770` |
| Resource manifest SHA256 | `8f7820a6a3e5734e071452f643374d8c6c769d4d149bcec3f2f82b88ee6530c2` |
| Resource canonical digest | `33ad2521dc5acc0be5a67b3ef77c167e882cf6ce53140dc60acc8f89c9ad76ab` |
| Execution directory | `.work/run7_scope_escalation/run_20260820T045113Z/` |
| Execution manifest SHA256 | `ad8c9bee121efd0a1e683c393a7a4ba74cccefaa77f82e7350d3be71c224bd0f` |
| Selection artifact SHA256 | `edaa7e4f308cc22752e1732f53362807a9fe15c5db024c51dbb0a78464c3c48d` |
| Aggregate artifact SHA256 | `c64d7ff2a5031f5151f3af44437b5142824af00e8fcb391e97376d5f9a07f3eb` |

Runtime identities were the frozen worker
`Qwen_Qwen3-1.7B-Q4_K_M.gguf`, local teacher
`Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`, and external teacher
`codex-cli-0.146.0`. The recorded timeouts were worker/local 900 seconds and
external 120 seconds. The raw execution directory remains under `.work` and
was not modified by this documentation change.
