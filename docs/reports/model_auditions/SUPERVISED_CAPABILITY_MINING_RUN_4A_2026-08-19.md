# Supervised Capability Mining Run 4A

Status: review-only closeout. No capability-card, routing-policy, resource-weight, training, promotion, or queue action was performed.

## Frozen execution

- Execution commit: `15dd84cfa82d9c2cef47778111e811e11ecf7274`
- Preregistration: `docs/research/RUN_4A_PREREGISTRATION_2026-08-19.json`
- Preregistration file SHA256: `a9418fe1e45a05e46b4fd183a6345333893192305fbf767461f3b280b26d748b`
- Execution manifest's canonical preregistration digest: `41401c0ba09f388f29b4812908772f88fcf38e82e1ed8b18a0565c7cc36bb060`
- Fixture pack SHA256: `0c10d1d712368cd66bd18be48557454e9e242a2d19d7b9f223d190be43f83d20`
- Driver SHA256: `0fd09c204b840609da040d0de8256adcf55fc6f5f3d57ba04539ac8ddd99cdee`
- Harness SHA256: `a6125d4b9d32ca912da81fd0df316cd56eada60c825b02789b5496fd24590f88`
- Run directory: `.work/run4a_intervention_market_calibration/run_20260819T184835Z/`
- Execution manifest SHA256: `25f879eb5af2340f41c4504270ede365e2dd715bec48f7939945e509ca22c4ca`
- Aggregate SHA256: `bee66dac025f40c964b207442e6dd232a9f39a4d18448e568b2b6430b34f3016`

The execution was terminal and completed without ambiguous started calls.

## Baseline and selection

All 20 candidate baselines returned valid model responses and deterministic baseline failures. There were no baseline passes and no baseline infrastructure exclusions.

| Block | Eligible baselines | Included tasks | Reserve |
|---|---:|---|---|
| contradiction-handling | 5 | contradiction-001 through contradiction-004 | contradiction-005 |
| triage-routing | 5 | triage-001 through triage-004 | triage-005 |
| scope-authority-boundary | 5 | scope-001 through scope-004 | scope-005 |
| unsupported-certainty | 5 | uncertainty-001 through uncertainty-004 | uncertainty-005 |

Each block reached four eligible failures. Selection artifacts are preserved under the run directory. Candidate 005 was correctly reserve-only in every block.

## Comparative results

All 48 preregistered intervention arms completed with valid model responses. Infrastructure exclusions were zero for every arm.

| Block | Deterministic retry | Local teacher | External teacher |
|---|---|---|---|
| contradiction-handling | 2/4, 50%, supported_positive | 0/4, 0%, supported_negative | 1/4, 25%, supported_negative |
| triage-routing | 2/4, 50%, supported_positive | 2/4, 50%, supported_positive | 3/4, 75%, supported_positive |
| scope-authority-boundary | 1/4, 25%, supported_negative | 4/4, 100%, supported_positive | 4/4, 100%, supported_positive |
| unsupported-certainty | 3/4, 75%, supported_positive | 2/4, 50%, supported_positive | 3/4, 75%, supported_positive |

Supported-positive intervention sets:

- contradiction-handling: `{deterministic_patch_retry}`
- triage-routing: `{deterministic_patch_retry, local_teacher, external_teacher}`
- scope-authority-boundary: `{local_teacher, external_teacher}`
- unsupported-certainty: `{deterministic_patch_retry, local_teacher, external_teacher}`

Three of four blocks had at least two supported-positive interventions. Therefore:

`RUN_4A_EVIDENCE_FORMATION_MET=true`

This is evidence formation under the preregistered threshold, not an intervention-superiority claim.

## Resource accounting

Actual calls:

- Baseline worker calls: 20
- Post-intervention worker calls: 48
- Total worker calls: 68
- Local-teacher calls: 16
- External-teacher calls: 16
- Total model calls: 100
- Total teacher calls: 32
- Infrastructure exclusions: 0

Realized monotonic elapsed time:

| Role | Calls | Elapsed coverage | Total elapsed_ms |
|---|---:|---:|---:|
| worker, baseline plus retries | 68 | 68/68 | 392,838.340 |
| local teacher | 16 | 16/16 | 111,861.708 |
| external teacher | 16 | 16/16 | 402,721.410 |
| total | 100 | 100/100 | 907,421.458 |

Frozen-prior expected decision cost:

- Baseline worker: 20 × 5,276.567 ms = 105,531.340 ms
- Deterministic retry: 16 × 5,276.567 ms = 84,425.072 ms
- Local-teacher arms: 16 × (16,220.624 + 5,276.567) ms = 343,955.056 ms
- External-teacher arms: 16 × (28,704.012 + 5,276.567) ms = 543,689.264 ms
- Total expected cost: **1,077,600.732 ms**

The run used the full preregistered maximum of 100 calls and remained within the planned call/time budget. Expected cost and realized elapsed time are reported separately.

Token telemetry was complete for worker calls (68 calls, 34,374 total tokens) and local-teacher calls (16 calls, 22,510 total tokens). External-teacher token telemetry was unavailable and was not estimated.

## Review boundary

Run 4A produces comparative intervention evidence suitable for review. It has not been merged into `.work/capability_cards/capability_cards.json`, and it does not authorize an economic Run 4 router. Any incorporation requires a separate review and freeze.
