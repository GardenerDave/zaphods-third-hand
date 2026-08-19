# Supervised Capability Mining Run 4B: Scope Intervention Replication

Status: completed; review-only calibration evidence. This report does not
modify production routing, capability cards, Run 4/Run 4A evidence, or the
status of any intervention.

## Frozen provenance

- Execution commit: `b32ff64d0adef21f355baa41c7e9371946e63a18`
- Preregistration: `docs/research/RUN_4B_SCOPE_INTERVENTION_REPLICATION_PREREGISTRATION_2026-08-19.json`
- Preregistration SHA256: `59f02a1e23c9cbe7e91bfb9c464675ccbb7bbb54b779091ea11cef8846ce5771`
- Driver: `scripts/zth_run4b_scope_replication.py`
- Driver SHA256: `d2154079ea78a9a2f64d615c28feb5f7ecfc42babc63d81e73fd8ec14a2574c0`
- Fixture pack SHA256: `b2f6d5aa1c007dc2ccbbaccf724bb75f9c89b5b3096b96dbc31ab2c8ad7a17e9`
- Execution directory: `.work/run4b_scope_replication/run_20260819T231103Z/`
- Execution manifest SHA256: `1cf719dff9fe401f9b881c3bb4a111f769578f7fd5a75d311f5eb9375f294ce1`
- Selection artifact SHA256: `95260d8e0afe28c4cee6cc43f47f42869ca7ab54838d29098d9a8ada1a37e19b`
- Aggregate artifact SHA256: `f49c38c91f5d3c136927cd05697e88721aa7ba965f31c0be004b6910b830b5ea`

The run used the preregistered scope-authority-boundary target at
`failure_class` resolution, with external teacher control and local teacher
treatment. Each selected baseline failure received exactly one teacher call
and one worker retry, with no patch, fallback, escalation, or cross-arm data.

## Baseline selection

All 15 candidates produced valid model responses and deterministic baseline
failures. Therefore the first 12 frozen candidates were selected and the final
three remained reserve-only.

Selected tasks:

`run4b-scope-001` through `run4b-scope-012`

Reserve tasks:

`run4b-scope-013`, `run4b-scope-014`, `run4b-scope-015`

Baseline dispositions for all candidates were
`baseline_failed_eligible`; there were no baseline passes or infrastructure
failures.

## Comparative result

| Arm | Validated solves | Comparable pairs | Solve rate | Post-baseline elapsed |
|---|---:|---:|---:|---:|
| external_teacher control | 12 | 12 | 1.00 | 434,458.484 ms |
| local_teacher treatment | 12 | 12 | 1.00 | 142,306.701 ms |

Paired outcomes:

- both solve: 12
- external-only: 0
- local-only: 0
- neither: 0

There were 12 comparable pairs and zero infrastructure-excluded pairs. Both
interventions preserved validated capability on this fresh scope sample. The
local arm used 292,151.783 ms less post-baseline elapsed time, a descriptive
reduction of 67.245% relative to external control.

This replicates the Run 4A pure-efficiency observation on this sample:
local_teacher matched external_teacher’s validated solve rate at lower
realized resource use. It does not establish universal superiority, eliminate
possible external-teacher niches, or retire external_teacher.

## Resource accounting

Scientific comparable-pair resource comparison:

- external control: 434,458.484 ms
- local treatment: 142,306.701 ms
- absolute difference: 292,151.783 ms
- relative reduction: 67.245%

Execution resource history, including all durable attempts:

| Resource role | Attempts | Valid model responses | Infrastructure failures | Elapsed telemetry coverage |
|---|---:|---:|---:|---:|
| worker | 39 | 39 | 0 | 39/39 |
| local_teacher | 12 | 12 | 0 | 12/12 |
| external_teacher | 12 | 12 | 0 | 12/12 |
| total | 63 | 63 | 0 | 63/63 |

The 39 worker attempts comprise 15 baselines and 24 post-intervention
retries. The realized total across all calls was 606,534.819 ms. The frozen
planning expectation was 744,881.745 ms; these are distinct quantities and the
resource priors were not recalibrated.

The generated aggregate records the complete attempt counts and timings. Its
role-validity subfield is supplemented here from the durable
`response_captured` transitions, where worker transport validity is recorded
on the transition rather than as a duplicate raw-response field. No raw
artifact was changed.

## Interpretation boundary

The pre-run research classification
`scope-authority-boundary / external_teacher = dominated_needs_replication`
is now supported by this targeted replication as a repeated sample-level
efficiency pattern. It is not a retirement decision. Further evidence could
still identify harder scope cases or complementary external-teacher behavior.

Run 4B remains review-only calibration evidence and is not merged into
`.work/capability_cards/capability_cards.json`.

