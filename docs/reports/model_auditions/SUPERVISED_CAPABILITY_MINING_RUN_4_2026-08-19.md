# Targeted Economic Routing Run 4

Status: completed and ready for review. This was the preregistered targeted
triage-routing comparison; it does not establish universal economic routing or
retire any intervention.

## Frozen bindings

- Execution commit: `f8e8a95f12ebe4a7418334a7f8f66ec3172a90e8`
- Preregistration SHA256:
  `d862ff155a1b80a636c644075797ca7c08ed4347478c14a58d795853cc408d47`
- Policy source SHA256:
  `ef5a0ddba3b058baba006cde9d7791f15e21ece7b40d86d947a4af7fc371c72f`
- Policy freeze digest:
  `5b0b2d4bc29d66070e13e2bf3f31b6463b97517849d9550821f5323b8896dd17`
- Paired driver SHA256:
  `82699f24d13a3d6929dc89a858f6f3376b012a850b325fadddd2cb9293b164af`
- Fixture-pack SHA256:
  `7dcef17c93a5eab5605621951be3084b2a4929ddcedf74fb9c39f47b8d377fef`
- Run 4A comparative-evidence freeze:
  `a23a7daa0c8681e8f57beed768c1cf3b3daafc360d139f48a147e8c4493dd0c3`
- Approved resource-weight manifest digest:
  `33ad2521dc5acc0be5a67b3ef77c167e882cf6ce53140dc60acc8f89c9ad76ab`
- Deterministic patch SHA256:
  `7cfb4453919ad945f0d149ec8af8763653b3734a54b86f23303b84a60dfdacf6`
- External-teacher timeout: 120 seconds

## Execution

Run directory:
`.work/run4_economic_routing/run_20260819T220012Z/`

The 15 baselines were valid model responses and deterministic validation
failures. The first 12 eligible candidates were selected; candidates 013–015
were reserves. All 12 pairs and 24 intervention arms reached terminal state.
There were zero infrastructure exclusions and no ambiguous started calls.

Selected tasks:

`001`, `002`, `003`, `004`, `005`, `006`, `007`, `008`, `009`, `010`, `011`,
and `012` under the `run4-economic-triage-` prefix.

## Primary result

| Measure | Control: capability-first | Treatment: cheapest supported-positive |
|---|---:|---:|
| Comparable pairs | 12 | 12 |
| Validated solves | 10/12 (83.33%) | 1/12 (8.33%) |
| Post-baseline elapsed time | 459,601.748 ms | 66,982.433 ms |

Paired outcomes were:

- both solve: 1
- control only: 9
- treatment only: 0
- neither: 2

The treatment used 392,619.315 ms less post-baseline time, an 85.426% reduction,
but did not preserve validated quality.

- `quality_preserved`: false
- `resource_reduced`: true
- `economic_routing_success`: false

## Resource accounting

- Baseline worker calls: 15
- Control worker retries: 12
- Treatment worker retries: 12
- Total worker calls: 39
- External-teacher calls: 12
- Local-teacher calls: 0
- Total model calls: 51
- Infrastructure exclusions: 0

Frozen-prior planning total: 550,234.257 ms. Realized total elapsed time across
valid worker and external-teacher calls: 549,201.462 ms. The expected and
realized quantities are reported separately. Worker token telemetry was
present; external-teacher token fields remained unavailable/null.

## Prior invalid execution

`.work/run4_economic_routing/run_20260819T215707Z/` remains permanently
excluded from scientific evidence. Its 15 baseline attempts all failed with
transport errors before reaching the worker, yielding zero capability
observations, zero policy comparisons, and zero intervention evidence. Those
attempts are not combined with this valid run's denominators or call counts.

## Interpretation and authority boundary

On this fresh targeted triage distribution, the cheapest supported-positive
policy reduced realized post-baseline inference time but failed the
quality-preservation criterion. This is descriptive evidence from 12 paired
tasks, not a population-level superiority claim. The result remains
review-only and is not merged into capability cards or production routing.

The existing research classification
`scope-authority-boundary / external_teacher = dominated_needs_replication`
is unchanged; Run 4 does not retire that or any other intervention.

## Durable artifacts

- Execution manifest:
  `.work/run4_economic_routing/run_20260819T220012Z/execution_manifest.json`
  SHA256: `65058ed01a90733946b01e9175acf67c5aa036ee23be568d075613298963dbdd`
- Selection artifact:
  `.work/run4_economic_routing/run_20260819T220012Z/selection.json`
  SHA256: `9f4fd8a0d1f9a6b0d3cc97a783403eb8dbda1e81a6f2f73ede1c3403694f48bc`
- Aggregate:
  `.work/run4_economic_routing/run_20260819T220012Z/aggregate.json`
  SHA256: `759db41231d76e94231b4ca0bace96cb17dd435742d3701594cd3b69017d9580`

Authority: `review_required_no_evidence_merge`.
