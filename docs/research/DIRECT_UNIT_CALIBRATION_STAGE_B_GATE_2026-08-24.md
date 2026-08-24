# Direct-Unit Calibration Stage B Gate

Date: 2026-08-24

## Decision

`CLEAN_GRANULARITY_REPLICATION_READY`

This is a model-free readiness decision only. Stage B has not been executed,
no Stage B target manifest or evaluator cases were created, and no supplier
was called.

## Authoritative Stage A state

The accepted semantic measurement is bound to:

- semantic audit commit `fb21f019e08e9f7d312fa37439396e0ee509641b`;
- Stage A result commit `6b1ec1ec3649276c3f846507cd3bb71e558ee14c`;
- Stage A raw run `.work/model_size_supplier_floor/direct_unit_calibration_2026-08-24/run_20260824T185745Z`;
- semantic classification `STAGE_A_SEMANTIC_FAILURE_RESULT_SUPPORTED`;
- `VALIDATOR_GAP_SUPPORTED=false`.

The committed atomic evidence contains 64 direct observations: 32 historical
Scope V0 observations and 32 new Stage A observations. The Stage A semantic
audit verified the new raw response hashes and the result commit remains an
ancestor. No compound teacher/worker rescue observation is included in the
new-family rates.

| Supplier | Scope | Triage | Unsupported certainty | Micro | Family macro |
|---|---:|---:|---:|---:|---:|
| local | 5/16 | 0/8 | 0/8 | 5/32 (15.625%) | 10.4167% |
| external | 16/16 | 0/8 | 0/8 | 16/32 (50.000%) | 33.3333% |

## Policy-form provenance

Both policy forms predate the Stage A outcomes.

`RUN4A_INTERVENTION_AGGREGATE_ALL_FAMILIES_V1` defines the broad form as an
aggregate supplier score, selecting the supplier with the higher existing
score and delegating when a score exists. It does not apply the historical
0.50 block threshold to the broad aggregate.

`SCOPE_INTERFACE_PROFILE_RUN4A_V1` and the frozen Run 4 policy establish the
bounded form: require the matched responsibility/interface and
supported-positive evidence, select among supported suppliers by the frozen
cost rule, and abstain/fail closed when no supported-positive evidence exists.
The form is reusable for the aligned direct Stage A evidence at each family;
this is a resolution change, not a new post-outcome decision rule.

## Broad aggregation adjudication

The proposed broad comparator uses `MICRO_AGGREGATE_DIRECT`. This follows the
historical broad aggregate's opportunity-weighted “all families” semantics:
each comparable direct opportunity contributes equally. The Stage A
`FAMILY_MACRO_AGGREGATE_DIRECT` view remains required descriptive evidence and
is not discarded.

The decision is not sensitive to this choice:

- micro: external `16/32` > local `5/32`;
- family macro: external `33.3333%` > local `10.4167%`.

Therefore `BROAD_POLICY_NOT_IDENTIFIABLE_WITHOUT_POST_OUTCOME_CHOICE=false`.

## Bounded evidence-state adjudication

The existing Run 3/Run 4 semantics define:

- supported-positive: at least 3 comparable opportunities and rate at least
  0.50;
- supported-negative: at least 3 comparable opportunities and rate below
  0.50;
- observed/insufficient: lower support;
- no supported-positive candidate: abstain/fail closed.

This rule is implemented in the preserved capability-card hierarchy and is
used by the frozen economic policy. It is not fitted to Stage A outcomes.

Applied descriptively to the aligned direct Stage A units:

| Family | Supplier | Direct evidence state | Bounded action basis |
|---|---|---|---|
| scope-authority-boundary | local | `SUPPORTED_NEGATIVE` (5/16) | not selectable |
| scope-authority-boundary | external | `SUPPORTED_POSITIVE` (16/16) | selectable |
| triage-routing | local | `SUPPORTED_NEGATIVE` (0/8) | not selectable |
| triage-routing | external | `SUPPORTED_NEGATIVE` (0/8) | not selectable |
| unsupported-certainty | local | `SUPPORTED_NEGATIVE` (0/8) | not selectable |
| unsupported-certainty | external | `SUPPORTED_NEGATIVE` (0/8) | not selectable |

The bounded policy does not equate absence of evidence with incapability. It
uses the preexisting “no supported-positive evidence → abstain” action. The
0/8 observations are recorded as observed negative data and map to the
existing supported-negative polarity because the frozen minimum support is
three; this is not a new threshold chosen to create disagreement.

## Natural pre-target policy decisions

| Family | Generalized decision | Bounded decision | Disagreement | Provenance |
|---|---|---|---|---|
| scope-authority-boundary | delegate external | delegate external | `NONE` | broad micro aggregate; aligned direct supported-positive evidence and frozen cost rule |
| triage-routing | delegate external | abstain | `DELEGATE_VS_ABSTAIN` | broad micro aggregate; both matched direct units supported-negative and no supported-positive candidate abstains |
| unsupported-certainty | delegate external | abstain | `DELEGATE_VS_ABSTAIN` | same preexisting evidence-state/action rule |

Thus `NATURAL_PRE_TARGET_POLICY_DISAGREEMENT_EXISTS=true`. The disagreement
does not depend on a favorable expected supplier, a post-outcome threshold, or
an aggregation choice.

The clean Stage B estimand is:

> On fresh direct capability-family tasks where a broad cross-family aggregate
> recommends external delegation but matched responsibility/interface evidence
> has no supported-positive supplier, which representation makes better
> delegate-versus-abstain decisions?

This is a delegation-decision comparison, not a generic supplier benchmark.

## Fresh holdout and interface audit

`FRESH_STAGE_B_HOLDOUT_SPACE_AVAILABLE=true` as a design-feasibility finding.
The repository preserves deterministic triage and unsupported-certainty fixture
patterns, manifests, novelty audits, multiple source-anchor families, and
independent evaluator mechanisms. Existing case IDs/text must not be reused;
the future freeze must author a new model-free freshness pack from unused
source anchors and verify non-duplication. No target cases were created here.

`SUPPLIER_INTERFACE_IDENTITIES_USABLE_FOR_STAGE_B=true` under the already
accepted best-observation condition:

- local service/runtime: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf via
  JARVIS_LOCAL;
- external service: codex-cli-0.146.0 via the preserved service mechanism;
- observed Stage A provider-native model: gpt-5.6-luna, recorded as
  provenance only and not asserted as future native-model continuity.

The experiment-authored V2 interface can be reused as a compatible direct
interface. Native envelopes remain supplier-specific and must be re-observed
at a later freeze.

## Proposed Stage B budget

The economical proposal is 16 fresh tasks:

- 8 fresh triage-routing cases;
- 8 fresh unsupported-certainty cases;
- both supplier arms for every task;
- 16 local calls and 16 external calls, 32 supplier calls total.

This budget is proposed, not frozen. It focuses on the two naturally
disagreeing families and excludes scope cases that currently produce no policy
disagreement. No target may be selected for anticipated supplier weakness.

## Scoring boundary

Retain the already frozen lexicographic order:

1. fewer false-positive delegations;
2. more successful delegations;
3. fewer unnecessary abstentions;
4. cost only when capability outcomes are equivalent.

Both matched supplier arms remain experimental counterfactuals. For a future
delegate-versus-abstain case, neither validating means justified abstention;
either eligible matched arm validating means unnecessary abstention. “Eligible
matched arm” must be defined before target execution as the supplier/interface
arm admitted by the frozen experiment controls, not as the predictor’s own
positive-evidence decision; otherwise abstention could never be judged
unnecessary.

## Gate characterization

All required readiness conditions pass:

- `STAGE_A_MEASUREMENT_VALID=true`;
- direct competence units aligned and atomic evidence reconstructable;
- broad policy form and aggregation independently identifiable;
- bounded policy form and actionability rule independently identifiable;
- natural pre-target disagreement exists in two families;
- no manufactured threshold or target outcome is required;
- fresh holdout generation space remains available;
- supplier/interface identities remain usable under best-observation limits;
- scoring can be frozen before Stage B outcomes;
- readiness is independent of the eventual winner.

No Stage B target outcomes, supplier calls, policy changes, qualification, or
production-routing changes occurred in this gate analysis.

`STAGE_B_READINESS_INDEPENDENT_OF_EXPECTED_WINNER=true`

`NEXT_DECISION=FREEZE_CLEAN_GRANULARITY_REPLICATION_STAGE_B`
