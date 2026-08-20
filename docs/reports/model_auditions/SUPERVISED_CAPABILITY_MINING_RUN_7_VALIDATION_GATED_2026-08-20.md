# Supervised Capability Mining Run 7: Validation-Gated Escalation

Status: completed; review required; no capability-evidence merge.

Run 7 evaluated the frozen validation-gated escalation policy on 20 selected
fresh, difficulty-enriched `scope-authority-boundary` failures. The control
used external-first execution. The treatment used local-first execution and
escalated to the external teacher only after a valid local response failed
deterministic validation.

The treatment was cheaper but did not preserve final validated performance:

| Policy | Final validated solves | Realized post-baseline policy elapsed |
|---|---:|---:|
| Control, external-direct | 20/20 (1.000) | 798,455.839 ms |
| Treatment, local-first + conditional escalation | 18/20 (0.900) | 330,432.860 ms |
| Difference | -2 solves | -468,022.979 ms (-58.616%) |

Accordingly, `quality_preserved=false`, `resource_reduced=true`, and
`economic_routing_success=false`.

## Escalation-branch result

The branch was empirically exercised. Of 20 local-first attempts, 17 passed
validation and 3 failed. All 3 failures triggered exactly one external
escalation. One escalation rescued the task; two remained unresolved after
escalation.

| Treatment stage | Count |
|---|---:|
| Local-first passes | 17 |
| Local-first validation failures | 3 |
| Escalations | 3 |
| Escalation rescues | 1 |
| Escalation failures | 2 |
| Final treatment solves | 18 |

The escalation rate was 3/20 = 15.000%, below the frozen 35% economic
break-even rate (7/20). That favorable cost position did not compensate for
the two final quality losses. The observed paired outcomes were:

| Paired outcome | Count |
|---|---:|
| Both solve | 18 |
| Control only | 2 |
| Treatment only | 0 |
| Neither | 0 |

The three escalation tasks were `run7-scope-001`, `run7-scope-006`, and
`run7-scope-019`. `run7-scope-006` was rescued; the other two remained
unresolved. All intervention and escalation transport classifications were
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

## Interpretation

Run 7 demonstrates that the validation gate can identify naturally observed
local failures and invoke the preregistered external recovery path. In this
sample, recovery succeeded once and failed twice. The complete sequential
policy therefore did not meet its quality-preservation criterion, despite a
large realized resource reduction.

This is not evidence that validation-gated escalation is universally
ineffective; it is the observed result on this difficulty-enriched sample.
The result does not authorize production routing, capability-card changes,
retirement, promotion, training, queueing, or addition of the M-parameter
model. It remains review-only.

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
was not modified by this closeout report.

## Authority boundary

This report is a durable review artifact only. Run 7 evidence has not been
merged into capability cards or production routing, and no intervention has
been retired, promoted, trained, queued, or otherwise operationalized.
