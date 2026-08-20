# Run 5 mixed-portfolio economic routing closeout

## Status

Run 5 completed as the frozen mixed triage/scope experiment. It produced 24
comparable policy tasks: 12 triage tasks using one physically shared external
action per task, and 12 scope tasks using isolated external-control and
local-treatment arms.

The treatment policy reduced realized policy-level post-baseline elapsed time,
but did not preserve validated portfolio solve rate. Therefore the frozen
economic-routing success criterion was not met.

This is review-only evidence. It does not modify production routing, capability
cards, Run 4/4A/4B evidence, or resource priors.

## Frozen provenance

- Execution commit: `5497bbc281df8e9758cdc76b24d33e7752e3eef7`
- Execution directory: `.work/run5_mixed_economic_routing/run_20260819T013828Z/`
- Execution manifest: `.work/run5_mixed_economic_routing/run_20260819T013828Z/execution_manifest.json`
- Execution manifest SHA256: `69ebfbb54e9d86f29ff899621858ec64cb0de1eea1f104a89e7db537a2c0f39f`
- Aggregate: `.work/run5_mixed_economic_routing/run_20260819T013828Z/aggregate.json`
- Aggregate SHA256: `9f5b9c01e62fcdd5d1c039e5380c1d55d17ea3abfacd2f5c6f8c30adad3a51dc`
- Policy source SHA256: `8a35889f84e9d0642357c6c2beb996252d525d6c5aa78ae82b1428c49a34cd96`
- Policy freeze SHA256: `c0402861a93599372d5b20f3659b81eb99333983922454849876733a7527c877`
- Policy canonical digest: `b4079d01b9569fcabbdd8b1517a81bdecdb3f5b4b02aa2f7dec668510974d055`
- Driver SHA256: `8c35f344d4ceff822ae83fee0e66bba4a49f9fab3f911b15bbdc54eeb4746725`
- Preregistration SHA256: `cbb6b6250db3489189b43afad36b17ac8ae42dfb928c62ab184766fd269102cd`
- Triage fixture manifest SHA256: `e44f7868c316f17f2cddd00736899e3f7e622af0cae4f3c449a5875eb11c906c`
- Triage fixture-pack canonical SHA256: `85aabb3803a82665b647c370bc0ae9783c62c891e0187f2f19688316f01949ce`
- Scope fixture manifest SHA256: `273bf634c9eac4e6ddeb2d30d09cb0fd31dd49c670115c48274f1eb9a943418c`
- Scope fixture-pack canonical SHA256: `cee93ab449b6aa0ebc838f9ba9077d9a30de218a171307408f718aab5e763379`
- Pair-order seed: `20260824`

The execution manifest records status `experiment_completed`, with no active
call and no infrastructure dispositions.

## Frozen policy and design

Control `external_everywhere` selected `external_teacher` for both families.
Treatment `evidence_qualified_economic` selected `external_teacher` for
triage-routing and `local_teacher` for scope-authority-boundary.

The triage external action was physically executed once and its result was
bound identically to both policy scorecards. Scope used two isolated arms from
the same baseline. The policies therefore differed only on scope.

Each family had 15 candidates. Selection took the first 12 eligible baseline
failures in frozen order; all 15 candidates in each family were eligible.

### Baseline dispositions

All 30 candidates had disposition `baseline_failed_eligible`, with a valid
model response and deterministic baseline validation failure.

- Triage selected: `run5-triage-001` through `run5-triage-012`
- Triage reserves: `run5-triage-013`, `run5-triage-014`, `run5-triage-015`
- Scope selected: `run5-scope-001` through `run5-scope-012`
- Scope reserves: `run5-scope-013`, `run5-scope-014`, `run5-scope-015`

Both family selections were complete; no replacement or adaptive selection
occurred.

## Comparative results

### Triage-routing: common external action

| Measure | Result |
|---|---:|
| Comparable tasks | 12 |
| Common external validated solves | 10/12 |
| Common external elapsed | 429,703.030 ms |
| Control outcome | 10/12 |
| Treatment outcome | 10/12 |
| Paired outcomes | 10 both_solve; 2 neither |

The common action was counted once in physical execution history, while its
observed result and policy-level cost were assigned identically to both policy
scorecards.

### Scope-authority-boundary: differing action

| Measure | Control external | Treatment local |
|---|---:|---:|
| Comparable tasks | 12 | 12 |
| Validated solves | 12/12 | 11/12 |
| Realized post-baseline elapsed | 428,129.430 ms | 137,073.828 ms |

Paired scope outcomes were 11 `both_solve`, 1 `control_only`, 0
`treatment_only`, and 0 `neither`.

### Portfolio result

| Measure | Control | Treatment |
|---|---:|---:|
| Comparable policy tasks | 24 | 24 |
| Validated solves | 22/24 | 21/24 |
| Solve rate | 91.667% | 87.500% |
| Realized post-baseline policy elapsed | 857,832.460 ms | 566,776.858 ms |

- Quality preserved: **false**
- Realized resource reduced: **true**
- Economic routing success: **false**
- Absolute realized policy-level savings: **291,055.602 ms**
- Relative realized policy-level savings: **33.929%** versus control

The quality difference is one validated solve, specifically the one
scope-authority-boundary `control_only` pair. Triage contributed the same
outcome to both policies.

## Physical execution resource history

Physical experiment accounting counts actual durable calls, with the shared
triage action counted once:

| Role | Attempts | Valid response captures | Realized elapsed |
|---|---:|---:|---:|
| Worker | 66 | 66 | 199,948.232 ms |
| External teacher | 24 | 24 | 749,096.234 ms |
| Local teacher | 12 | 12 | 82,890.803 ms |
| **Total** | **102** | **102** | **1,031,935.269 ms** |

There were zero infrastructure failures and zero excluded tasks. The valid
response counts above are reconciled directly from all 66 durable trajectory
files: every `call_started` has a corresponding `response_captured` with
`transport_valid=true` and `transport_classification=model_response`. This
trajectory-level reconciliation corrects the generated aggregate's incomplete
worker-only `valid_responses_by_role` field without changing that raw artifact.

The frozen planning expectation was 1,231,797.198 ms. The realized physical
total was 199,861.929 ms lower; this comparison is descriptive and does not
recalibrate the resource priors.

## Expected versus realized policy cost

Frozen expected post-baseline policy costs were:

- Control: 815,533.896 ms
- Treatment: 665,733.240 ms
- Planned treatment savings: 149,800.656 ms (approximately 18.368%)

Realized policy-level costs were 857,832.460 ms for control and 566,776.858 ms
for treatment, yielding 291,055.602 ms (33.929%) realized savings. Expected
decision cost, realized policy cost, and physical experiment cost remain
separate quantities; the shared triage action is not double-counted in the
physical total.

## Interpretation and limitations

On this fresh mixed triage/scope workload, the evidence-qualified economic
policy used less realized policy-level inference time but failed the frozen
quality-preservation criterion. The result does not support economic-routing
success for this experiment.

The result is limited to the preregistered triage-routing and
scope-authority-boundary distribution. It does not establish that all task
families have economic substitutes, that local always replaces external, that
the cheapest supported-positive action is sufficient, or that
`external_teacher` can be retired. It does not evaluate
contradiction-handling or unsupported-certainty in Run 5.

No evidence was merged into capability cards or production routing, and no
training, promotion, queueing, or autonomous action was performed.
