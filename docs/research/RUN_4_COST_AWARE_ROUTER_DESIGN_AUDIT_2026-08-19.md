# Run 4 Cost-Aware Router Design Audit

This is a model-free design audit. It does not create Run 4 fixtures, implement
the Run 4 router, execute interventions, or use Run 3C capability outcomes.
The capability boundary is the existing Run 1 + Run 2 evidence bundle used by
the frozen Run 3 advisory router.

## Established inputs

- Run 3 capability bundle: 44 trajectories, 97 cards, 32 exact signatures,
  bundle SHA256 `383274a27c89345b3a8bcede75123420973a7a3e53318224e6460c0d05b47fc1`.
- Existing evidence hierarchy: exact signature, semantic signature, failure
  class, task family, then abstention.
- Support threshold: at least 3 comparable task opportunities and rescue rate
  at least 0.50 for supported-positive evidence.
- Approved elapsed-time priors: worker `5276.567` ms, local teacher
  `16220.624` ms, external teacher `28704.012` ms.
- Immediate action cost includes the intervention call and its resulting worker
  retry: deterministic `5276.567` ms, local `21497.191` ms, external
  `33980.579` ms.

The approved resource manifest is used only for these frozen time priors. No
Run 3C pass/fail, routing, paired, or family-performance outcomes are used in
this audit.

## Measured choice-set coverage

The four evidence resolutions contain 96 distinct evidence keys:

| Resolution | Keys | 0 supported-positive actions | 1 | 2 | 3+ |
|---|---:|---:|---:|---:|---:|
| exact signature | 32 | 32 | 0 | 0 | 0 |
| semantic signature | 31 | 31 | 0 | 0 | 0 |
| failure class | 25 | 24 | 1 | 0 | 0 |
| task family | 8 | 2 | 5 | 1 | 0 |
| **Total** | **96** | **89** | **6** | **1** | **0** |

Thus only 1/96 evidence keys (1.04%) currently has competing supported-positive
actions whose cost could change a choice. Seven keys have at least one
supported-positive action; six have only one, so cost cannot choose among
supported alternatives there. The remaining 89 keys must abstain or preserve
negative/insufficient evidence rather than invent a cheap action.

The one multi-action key is the `unsupported-certainty` task-family key:
deterministic retry is supported at 2/3 and external teacher at 3/3. The
cheaper deterministic action has the lower observed rescue rate. The current
Run 3 advisory recommendation already selects the cheaper supported-positive
action. Across all seven keys with a supported-positive action, the current
recommendation is already the cheapest supported-positive action; there are no
current recommendations with a cheaper supported-positive alternative.

The detailed per-key/per-intervention enumeration, including observed and
supported-negative evidence, is review-only at
`.work/capability_cards/run4_cost_aware_choice_sets.json`; its summary is at
`.work/capability_cards/run4_cost_aware_summary.json`.

## Minimum defensible proposed rule

The smallest defensible future rule is:

> At the selected evidence resolution, choose the cheapest intervention among
> supported-positive actions. If none exists, preserve the existing
> fail-closed abstention/fixed-ladder behavior. Never convert observed,
> insufficient, or supported-negative evidence into authority.

This preserves the existing hierarchy, threshold, negative-evidence semantics,
and advisory boundary. Cost is a tie-break/choice among already supported
positive actions; it does not make an unsupported action eligible. A future
experiment must retain deterministic validation and require treatment quality
to be at least the control quality.

Alternative rules were not selected:

- success per elapsed-time unit and cost divided by empirical success rate add
  an unvalidated quality/cost tradeoff to a very sparse evidence set;
- both can prefer a higher-cost action because of small-sample rate changes,
  which would make quality preservation harder to interpret;
- Run 3 evidence provides only one genuine competing choice, so it cannot
  support selecting a more complex optimization rule.

## Proposed isolated Run 4 comparison

Use identical fresh tasks, validators, worker/teacher identities, capability
evidence, thresholds, and authority boundaries in both arms.

- **Control:** existing capability-only Run 3 routing semantics.
- **Treatment:** the same capability evidence and hierarchy, with only the
  proposed cheapest-supported-positive decision rule added.

The preferred primary resource outcome is realized total model-call elapsed
milliseconds. Expected decision cost from the approved priors is a planning
metric only. Worker calls, deterministic retries, local-teacher calls,
external-teacher calls, total teacher calls, and elapsed time by role remain
secondary metrics. Final deterministically validated solve rate remains the
quality constraint.

## Not yet done / risks

The Run 4 router, fixtures, preregistration, and behavioral execution do not
exist yet. Cost-aware decision coverage is currently very low, so a fresh task
set may contain few or no cases where cost can change the supported choice.
The one competing key also shows lower empirical success for the cheaper
action. This is an explicit quality-risk case, not evidence that the expensive
action should be chosen automatically. The proposed control/treatment design
is needed before making any cost-aware performance claim.

No model calls were made.
