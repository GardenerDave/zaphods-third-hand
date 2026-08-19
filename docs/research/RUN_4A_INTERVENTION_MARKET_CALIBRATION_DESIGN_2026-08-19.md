# Run 4A Intervention-Market Calibration Design

This is a model-free design artifact. It does not create fixtures, call
models, modify the Run 3 capability bundle, change the approved resource
weights, or implement the economic Run 4 router.

The executable freeze below supersedes the earlier exploratory 18-task sizing
sketch: it uses four target blocks, 20 candidates, and a target of 16 included
tasks (the first four valid baseline failures per block), with one reserve per
block.

## Established

The frozen Run 1 + Run 2 capability evidence contains 96 evidence keys:

- 89 have zero supported-positive interventions;
- 6 have exactly one supported-positive intervention;
- 1 has two supported-positive interventions.

The existing capability-only recommendation already selects the cheapest
supported-positive action for every supported key. Consequently, adding the
cheapest-supported-positive rule today would make zero policy changes. The
approved elapsed-time priors remain:

| Role | Expected elapsed time |
|---|---:|
| worker | 5,276.567 ms |
| local teacher | 16,220.624 ms |
| external teacher | 28,704.012 ms |

These are expected elapsed-time priors only. They are not prices, energy
weights, or universal compute costs.

## Proposed research question

For the same fresh, valid worker-failure opportunities, how do these isolated
interventions compare in deterministic rescue probability and realized
resource cost?

1. `deterministic_patch_retry`
2. `local_teacher`
3. `external_teacher`

Run 4A is intervention calibration, not routing optimization. Interventions
are not selected adaptively and no result is automatically merged into the
production capability bundle.

## Proposed paired design

The executable calibration uses 20 genuinely fresh candidates: five per
target block. The first four valid baseline failures in each block become the
included comparative tasks; the fifth remains a preregistered reserve and is
never substituted adaptively.

| Target block | Candidates |
|---|---:|
| contradiction-handling | 3 |
| destructive-action-restraint | 3 |
| evidence-grounding | 3 |
| queue-authority-boundary | 3 |
| scope-authority-boundary | 3 |
| unsupported-certainty | 3 |
| **Total** | **20** |

Each target block uses one preregistered normalized failure-signature target
and five independently authored scenarios, while preserving the actual
per-task validator signature. The first four valid failures provide the target
16 three-way comparative tasks. This gives every intervention four comparable
opportunities per block when all candidates are eligible, while the existing
`n >= 3` support threshold remains unchanged. This is not a formal power
calculation.

The fixtures must be authored after this design and before preregistration,
from repository-grounded material not used in reviewed_v1, reviewed_v2,
reviewed_v3, reviewed_v3b, or reviewed_v3c. They must carry stable IDs,
source document/anchor, novelty classification, output contracts, bounded
reference facts, and deterministic validator provenance. Task selection must
not use expected intervention outcomes. No pilot outputs, teacher outputs, or
Run 3C outcomes may be used.

Each task receives one canonical baseline worker attempt. A valid baseline
failure defines that task's intervention opportunity. A baseline pass is
recorded and removes the task from all three intervention denominators; it is
not replaced adaptively. The same immutable baseline failure artifacts and
diagnostics are referenced by all three independent arms.

## Frozen arm semantics

For each valid baseline failure, run exactly one independent arm for each
intervention:

- **Deterministic patch arm:** apply the already frozen deterministic patch and
  make one worker retry. No teacher fallback.
- **Local-teacher arm:** make one local-teacher call and one resulting worker
  retry. No deterministic or external fallback.
- **External-teacher arm:** make one external-teacher call and one resulting
  worker retry. No deterministic or local fallback.

The smallest harness addition needed is an experiment-only isolated-arm entry
point that consumes the immutable baseline artifact and selected intervention
source, performs exactly that one intervention and one worker retry, and
fails closed on transport ambiguity. It must not change the normal supervised
loop or grant routing authority.

An arm's teacher or worker output must never be passed to another arm. Every
arm gets the original task context, its own bounded intervention packet, and
the same baseline diagnostics. Each arm has independent prompt/request
provenance and transport classification.

## Measurements

The primary per-task/per-intervention observation is:

`deterministically_validated_rescue = true | false`

Only transport-valid model responses enter this denominator. Infrastructure
failures remain durable exclusions with no capability verdict.

Record for each arm:

- intervention and worker call counts;
- valid opportunities, valid model calls, rescues, failures, and rescue rate;
- realized monotonic elapsed milliseconds by role and total;
- expected action cost from the approved priors, kept separate from realized
  elapsed time;
- token telemetry where available, null where unavailable;
- model/service identity, prompt/request provenance, and infrastructure status.

## Evidence formation and review boundary

For every evidence key and intervention, produce opportunities, valid calls,
rescues, rescue rate, realized-cost distribution, expected action cost, source
provenance, and status using the existing thresholds:

- **supported-positive:** at least 3 valid comparable opportunities and rescue
  rate at least 0.50;
- **supported-negative:** at least 3 valid comparable opportunities and rescue
  rate below 0.50;
- **observed:** 1–2 valid opportunities;
- **insufficient:** zero valid opportunities.

Three-way pairing makes a genuine competing supported-positive key possible
when at least two interventions each meet the supported-positive rule on the
same key. One supported intervention is not a market; two or more are the
minimum for a future cost choice. Run 4A evidence remains review-only until a
separate bundle update and policy freeze explicitly approve it.

## Run 4A success criteria

Run 4A does not require one intervention to beat another. It succeeds as a
calibration if:

1. all preregistered tasks are attempted without adaptive replacement;
2. every attempted arm has a terminal transport-valid or infrastructure
   disposition;
3. paired evidence is complete wherever the baseline was a valid failure;
4. at least two evidence keys have two or more supported-positive
   interventions; and
5. at least one reviewed key exposes a genuine cost/quality tradeoff: two
   supported-positive interventions with different expected action costs and
   different observed rescue rates.

Condition 4 forms a reusable intervention market. Condition 5 identifies a
state where a future reviewed cost-aware rule could plausibly differ from
capability-only routing. It does not itself authorize a route, select an
optimization formula, or establish causal superiority. If conditions 4–5 are
not met, the evidence remains useful calibration but Economic Run 4 is not
ready.

## Planning budget

At the maximum preregistered case where all 16 included baseline attempts are
valid failures, the three-way design requires:

| Resource | Calls |
|---|---:|
| baseline worker | 16 |
| deterministic retry worker | 16 |
| local-teacher calls | 16 |
| local-teacher retry worker | 16 |
| external-teacher calls | 16 |
| external-teacher retry worker | 16 |
| **total model calls** | **96** |

That is 48 intervention calls, 64 worker calls, and an expected elapsed-time
budget of:

`64×5276.567 + 16×16220.624 + 16×28704.012 = 1,056,494.464 ms`

approximately 17.61 minutes of serial model-call time under the frozen priors.
Baseline passes and infrastructure exclusions reduce completed intervention
calls; they must not be replaced adaptively. This is a planning estimate,
not a guaranteed wall-clock duration.

## Not yet done

- reviewed_v4a fixtures have not been authored;
- no Run 4A preregistration exists;
- no isolated-arm harness has been implemented or frozen;
- no model calls or teacher calls have occurred;
- no Run 4A evidence has been added to capability cards;
- no economic Run 4 router exists.

Economic Run 4 remains false until Run 4A produces reviewed comparative
evidence and a later policy freeze records a routing rule that can actually
differ from the capability-only control.

`RUN_4A_DESIGN_READY=true`  
`ECONOMIC_RUN_4_READY=false`

No model calls were made.
