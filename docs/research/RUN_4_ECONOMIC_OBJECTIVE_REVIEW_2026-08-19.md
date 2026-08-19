# Run 4 Economic Objective Review

This is a model-free review of the frozen Run 4A comparative intervention
evidence. It does not alter Run 3 evidence, Run 4 resource weights, or any
router. Run 4A remains calibration evidence and is not production routing
authority.

## Established

Run 4A completed 20 terminal baselines and 48 isolated intervention arms with
zero infrastructure exclusions. The reviewed comparative freeze is:

`docs/research/RUN_4A_COMPARATIVE_EVIDENCE_FREEZE_2026-08-19.json`

Its canonical freeze digest is
`a23a7daa0c8681e8f57beed768c1cf3b3daafc360d139f48a147e8c4493dd0c3`.

The verified evidence is:

| Block | Deterministic retry | Local teacher | External teacher |
|---|---:|---:|---:|
| contradiction-handling | 2/4, supported-positive | 0/4, supported-negative | 1/4, supported-negative |
| triage-routing | 2/4, supported-positive | 2/4, supported-positive | 3/4, supported-positive |
| scope-authority-boundary | 1/4, supported-negative | 4/4, supported-positive | 4/4, supported-positive |
| unsupported-certainty | 3/4, supported-positive | 2/4, supported-positive | 3/4, supported-positive |

The evidence-formation criterion was met in three of four blocks. These are
small empirical rates, not precise population probabilities or superiority
claims.

The frozen expected immediate action costs, including the resulting worker
retry, are:

- deterministic patch retry: 5,276.567 ms;
- local teacher: 21,497.191 ms;
- external teacher: 33,980.579 ms.

The Run 3 capability bundle, Run 3 routing policy, and approved Run 4 resource
manifest were verified unchanged.

## Derived frontier

Using supported-positive evidence only, and defining dominance as no worse
rescue rate and no greater expected cost with at least one strict inequality,
the non-dominated frontier is:

- contradiction-handling: deterministic patch retry;
- triage-routing: deterministic patch retry and external teacher;
- scope-authority-boundary: local teacher;
- unsupported-certainty: deterministic patch retry.

The supported-positive actions dominated within a block are:

- triage-routing: local teacher, dominated by deterministic retry;
- scope-authority-boundary: external teacher, dominated by local teacher;
- unsupported-certainty: local and external teacher, dominated by deterministic retry.

Negative or unsupported interventions are not called “dominated” by this
frontier calculation; they remain negative/insufficient evidence.

## Triage tradeoff

The two triage frontier alternatives are:

- deterministic retry: rescue rate 0.50 at 5,276.567 ms;
- external teacher: rescue rate 0.75 at 33,980.579 ms.

The external alternative adds 28,704.012 ms and 0.25 empirical rescue
probability, or 1,148.16048 ms per additional percentage point of observed
rescue rate. This descriptive ratio should not be interpreted as a calibrated
population value with four observations per action.

## Candidate objectives

| Objective | Definition | Run 4A choices | Arbitrary parameter | Assessment |
|---|---|---|---|---|
| A. Cheapest supported-positive | Choose the lowest-cost supported-positive action | deterministic; deterministic; local; deterministic | No | Conservative cost tie-break; preserves support and negative evidence |
| B. Highest rescue, cheapest tie-break | Maximize empirical rescue rate, then minimize cost | deterministic; external; local; deterministic | No | Capability-first comparator; exposes the triage cost/quality tradeoff |
| C. Rescue rate / cost | Maximize empirical rescue per millisecond | deterministic; deterministic; local; deterministic | No explicit scalar, but treats sparse rates as cardinal | More cost-sensitive, but unstable with small samples |
| D. Cost / rescue rate | Minimize cost per observed rescue | deterministic; deterministic; local; deterministic | No explicit scalar, but divides by sparse rates | Same small-sample instability; undefined at zero |
| E. Expected terminal cost | Action cost plus failure probability times downstream cost | Not evaluable | Requires a frozen downstream failure cost and sequential conditional probabilities | No defensible downstream cost exists in the current evidence |
| F. Explicit budget/frontier | Select actions under a frozen resource budget | Not evaluated | Requires an independently grounded budget | Useful only after a budget is externally specified |

The existing Run 3 router’s capability-only behavior should not be treated as a
clean cost-control comparator if it receives a different evidence bundle. A
clean future comparison holds the Run 4A comparative evidence identical and
compares B (capability-first) with A (cheapest supported-positive). This makes
the triage choice behaviorally different without giving treatment newer
capability evidence.

## Proposed objective

The smallest defensible cost-aware rule is:

> At the selected frozen evidence resolution, choose the cheapest action among
> supported-positive interventions. Preserve supported-negative evidence and
> abstain/fail closed when no supported-positive action exists.

This rule has no tuned magic constant, cannot upgrade insufficient evidence,
and can differ from the capability-first comparator on the frozen triage
choice. Quality remains a hard constraint: a future treatment must retain at
least the control’s deterministically validated solve rate.

## Proposed Run 4 comparison

Use identical fresh tasks, validators, model identities, evidence, thresholds,
and authority boundaries:

- **Control:** capability-first selection: highest empirical rescue rate, with
  expected cost only as a deterministic tie-break;
- **Treatment:** cheapest supported-positive selection.

The primary quality constraint is treatment final validated solve rate at least
control. The preferred primary resource outcome is realized total model-call
elapsed time. Expected cost from the frozen priors, call counts, and per-role
elapsed time remain separately reported secondary measures.

This design asks whether quantitative resource information reduces realized
resource use when capability evidence is held constant. A comparison against
the historical Run 3 router can be reported descriptively, but is less clean
causally because its evidence base differs.

## Not yet done

- no economic router has been implemented;
- no Run 4 fixtures or preregistration exist;
- no Run 4 execution has occurred;
- Run 4A has not been merged into capability cards or the Run 3 routing policy;
- no monetary, energy, hardware-independent, or universal cost claim is made.

Another broad intervention-calibration experiment is not required to specify
the candidate objective: Run 4A already supplies competing supported-positive
actions in triage and scope. A fresh Run 4 behavioral experiment is required
to test the objective, with policy and evidence frozen before task selection.

`RUN_4A_EVIDENCE_FROZEN=true`

`RUN_4_ECONOMIC_OBJECTIVE_SPECIFIABLE=true`

`RUN_4_ROUTER_IMPLEMENTATION_READY=false`

`ECONOMIC_RUN_4_READY=false`
