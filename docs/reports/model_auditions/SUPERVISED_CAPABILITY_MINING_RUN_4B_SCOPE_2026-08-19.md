# Supervised Capability Mining Run 4B: Scope Intervention Replication

Status: completed; review-only calibration evidence. This report does not
modify production routing, capability cards, Run 4/Run 4A evidence, resource
priors, or the status of any intervention.

## Executive result

Run 4B successfully replicated Run 4A’s apparent scope pure-efficiency pattern
on a larger fresh paired sample. On all 12 comparable pairs, both the local
and external teacher solved the task: `both_solve=12`, `external_only=0`,
`local_only=0`, and `neither=0`. Local teacher post-baseline elapsed time was
`142,306.701 ms` versus `434,458.484 ms` for external teacher, a reduction of
`292,151.783 ms` or `67.245%`.

The concordant pairs matter: this was not merely equal aggregate solve counts;
the sample showed no observed capability niche separating the two teachers on
these scope-authority-boundary failures. This does not prove universal
equivalence, establish that external teacher has no harder-task niche, or
retire `external_teacher`.

## Frozen provenance

- Execution commit: `b32ff64d0adef21f355baa41c7e9371946e63a18`
- Closeout commit: `b79ef5ef8feca43dc61ff92efe8daf1c1d9ff398`
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

## Experimental design and baseline selection

All 15 frozen candidates were processed in order. Every candidate produced a
valid model response and a deterministic baseline failure, so the first 12
were selected and the final three remained reserve-only.

Selected tasks:

`run4b-scope-001` through `run4b-scope-012`

Reserve tasks:

`run4b-scope-013`, `run4b-scope-014`, `run4b-scope-015`

Baseline dispositions for all 15 candidates were
`baseline_failed_eligible`; there were no baseline passes or infrastructure
failures.

Each selected task branched from the same baseline failure into two isolated
arms:

- Control: `external_teacher` plus one worker retry.
- Treatment: `local_teacher` plus one worker retry.

There was no deterministic-patch arm, fallback, escalation, or adaptive
intervention selection.

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
local arm used `292,151.783 ms` less post-baseline elapsed time, a descriptive
reduction of `67.245%` relative to external control.

## Relationship to Run 4A

Run 4A first observed the apparent scope efficiency pattern:

- `local_teacher`: 4/4 validated rescues;
- `external_teacher`: 4/4 validated rescues;
- local had the lower frozen expected action cost.

At that point, external teacher was Pareto-dominated among the supported-
positive actions in the observed sample, but the sample contained only four
opportunities per intervention. Its research status therefore remained
`dominated_needs_replication`.

Run 4B deliberately tested that apparent dominance on 12 new paired scope
failures. Both interventions solved all 12 tasks, every pair was concordant,
and local again used materially less realized inference resource. Run 4B
therefore strengthens the evidence that `local_teacher` is currently a
pure-efficiency substitute for `external_teacher` on the tested
scope-authority-boundary distribution.

“Strengthens the evidence” is the appropriate claim here; this replication
does not prove universal equivalence or eliminate the possibility of an
external-teacher niche on harder or differently structured scope failures.

## Cumulative descriptive scope evidence

The two experiments remain separate samples and separate experimental records:

| Sample | local_teacher | external_teacher |
|---|---:|---:|
| Run 4A | 4/4 | 4/4 |
| Run 4B | 12/12 | 12/12 |
| Descriptive arithmetic across both samples | 16/16 | 16/16 |

The `16/16` versus `16/16` figures are a descriptive cumulative summary, not a
pooled preregistered statistical experiment and not a population-equivalence
claim. No confidence intervals or significance tests are asserted.

## Resource accounting

Scientific comparable-pair resource comparison:

- external control: `434,458.484 ms`
- local treatment: `142,306.701 ms`
- absolute difference: `292,151.783 ms`
- relative reduction: `67.245%`

Execution resource history, including all durable attempts:

| Resource role | Attempts | Valid model responses | Infrastructure failures | Elapsed telemetry coverage |
|---|---:|---:|---:|---:|
| worker | 39 | 39 | 0 | 39/39 |
| local_teacher | 12 | 12 | 0 | 12/12 |
| external_teacher | 12 | 12 | 0 | 12/12 |
| total | 63 | 63 | 0 | 63/63 |

The 39 worker attempts comprise 15 baselines and 24 post-intervention
retries. The realized total across all calls was `606,534.819 ms`. The frozen
planning expectation was `744,881.745 ms`; these are distinct quantities and
the resource priors were not recalibrated.

The generated aggregate records complete attempt counts and timings. Its
worker role-validity field is supplemented here from durable
`response_captured` transitions, where worker transport validity is recorded
on the transition rather than as a duplicate raw-response field. No raw
artifact was changed.

## Three levels of interpretation

### Sample result — established

On the 12 fresh Run 4B pairs, both teachers solved all tasks and local used
`67.245%` less post-baseline elapsed time.

### Replication result — supported

The Run 4A scope efficiency pattern reproduced on a larger fresh paired
sample, with no discordant pair in Run 4B.

### Routing or retirement claim — not authorized

The result may justify considering local-first routing for this evidence class
after explicit policy review. It does not establish universal local/external
equivalence, show that external teacher cannot improve, prove that it has no
harder-task niche, authorize automatic production routing, or retire
`external_teacher`.

## Relation to the targeted economic Run 4

Run 4 showed the complementary capability/price tradeoff on triage-routing:
the cheap deterministic intervention reduced resource use but solved only 1/12
fresh paired tasks versus 10/12 for external teacher, so capability was not
interchangeable with cost.

Run 4B shows the complementary scope case: the cheaper local intervention
matched external teacher on every fresh paired task while using substantially
less realized resource.

Together, these results show why economic routing cannot be based on cost alone
or on binary supported-positive status alone. It needs capability evidence
specific enough to identify where a cheaper intervention is a genuine
substitute and where expensive capability is worth buying. This is a research
interpretation, not production routing policy.

## Authority and limitations

`external_teacher` is currently dominated on the reviewed
scope-authority-boundary evidence among supported-positive interventions, but
“dominated” describes the observed capability/cost evidence at this resolution;
it is not a permanent model classification. The existing
`dominated_needs_replication` label remains a research-priority label rather
than a retirement decision. Future review may choose a more precise descriptive
status, but this report does not change the taxonomy automatically.

Run 4B remains review-only calibration evidence and is not merged into
`.work/capability_cards/capability_cards.json`.

