# Prospective Matched Delegation-Prediction Test

Status: hardened design/preregistration only. No target execution or outcome
evidence exists.

Authoritative design basis: `e4d5b48efed683f1265a7fb3799abe8c4b598f5f`.

Experiment identifier:

`DELEGATION_PREDICTION_TEST_SCOPE_V0`

## A. Selected capability family

Selected family: `scope-authority-boundary`.

This is the strongest first candidate because it has:

- an existing deterministic evaluator with exact allowed-target, held-target,
  scope-expansion, and review-status checks;
- a common supervised JSON interface for the two candidate suppliers;
- fresh fixture derivation through the existing scope-fixture methodology;
- a bounded delegation meaning: return the exact permitted and held targets
  without granting scope;
- prior matched supplier evidence with both local and external actions;
- a meaningful broad-score versus bounded-profile disagreement;
- a clear fail-closed state for unsupported scope subcases.

Rejected or deferred candidates:

- `triage-routing`: prior evidence favors external at the family level, so it
  offers less natural disagreement for the first comparison.
- bounded semantic operation classification: scientifically valuable, but its
  recent sequence is dominated by interface-label calibration and would test
  interface sensitivity again rather than delegation prediction.
- other families: available evidence is either less matched, less independently
  validated, or has weaker fresh-holdout support.

## B. Supplier set

Two existing suppliers are evaluated on every fresh target task:

| Supplier | Identity | Role |
|---|---|---|
| local | `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`, `JARVIS_LOCAL` | bounded scope-response supplier |
| external | `codex-cli-0.146.0` | bounded scope-response supplier |

Historical identity is verified from the Run 4A preregistration and resource
freeze: local is `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` via `JARVIS_LOCAL`,
and external is `codex-cli-0.146.0` via the Codex service class. The
prospective arms use those same identities, so the supplier transfer is
`EXACT` for the preserved identity/version fields.

The experiment-authored payload is held constant across arms: request, output
schema, target authority facts, and bounded contract. The supplier-native
envelope is not byte-identical: native system/client/runtime metadata belongs
to each supplier/interface configuration. This is therefore not a claim of
identical full model-visible bytes. The future freeze must record those native
interfaces, disable/omit tools and evaluator access, and require zero tool
calls. Neither supplier can grant authority, change the evaluator, or
self-qualify.

The matched design executes both supplier arms for each task. This makes the
outcome for either frozen predictor's selected supplier observable without
letting either predictor inspect the target result. It is an experimental
paired-delegation design, not production routing.

## C. Primary estimand and decision representation

The primary estimand is delegation-decision quality, not ordinary binary label
accuracy. Each frozen policy emits the tuple:

`selected_supplier = local | external | null`

`delegation_decision = delegate | abstain`
`expected_success = true | false/unsupported`

The design contains two distinct disagreement types:

- `SUPPLIER_SELECTION_DISAGREEMENT_COUNT=8`: both policies delegate, but one
  selects local and the other external;
- `DELEGATE_VS_ABSTAIN_DISAGREEMENT_COUNT=8`: the broad policy delegates
  external while the bounded policy abstains;
- `BINARY_EXPECTED_SUCCESS_DISAGREEMENT_COUNT=8`: the corresponding expected
  success values are true versus false/unsupported.

These are not interchangeable primary opportunities. Supplier selection is
scored against matched arm validation; abstention is scored against the
counterfactual matched arms.

## D. Generalized predictor

`GENERALIZED_PREDICTOR_ID=RUN4A_INTERVENTION_AGGREGATE_ALL_FAMILIES_V1`

Source artifacts:

- `.work/run4a_intervention_market_calibration/run_20260819T184835Z/aggregate.json`
  SHA256 `bee66dac025f40c964b207442e6dd232a9f39a4d18448e568b2b6430b34f3016`;
- `docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_4A_2026-08-19.md`
  SHA256 `361faf4580c94455d61826ee5b293d8dcdb7cf3fa256c877b97965c014e7b512`;
- execution commit `15dd84cfa82d9c2cef47778111e811e11ecf7274`.

The generalized score is the existing Run 4A aggregate across four capability
families, not a new score computed from the target cohort:

- local: 8 validated rescues / 16 opportunities = 0.5000;
- external: 11 validated rescues / 16 opportunities = 0.6875.

Prediction rule, frozen before target execution:

1. restrict candidates to local and external;
2. select the higher broad aggregate score;
3. delegate when the selected score exists;
4. ties or missing scores abstain.

The Run 4A `0.50` support threshold is retained as provenance for the
historical block-level `supported_positive` status, but it is not applied to
the all-family aggregate. The aggregate policy uses the higher existing score;
no new threshold is introduced.

Therefore this predictor selects external and predicts
`DELEGATION_EXPECTED_TO_SUCCEED=true` for the in-scope target stratum and
also selects external for the out-of-profile expansion stratum.

This is intentionally a broad comparison score. It does not inspect the target
scope subcase.

## E. Degeneralized predictor

`DEGENERALIZED_PREDICTOR_ID=SCOPE_INTERFACE_PROFILE_RUN4A_V1`

Historical sources:

- Run 4A scope-specific evidence: both local and external validated 4/4 on
  the frozen non-expanding scope slice;
- `docs/research/RUN_4A_PREREGISTRATION_2026-08-19.json`
  SHA256 `a9418fe1e45a05e46b4fd183a6345333893192305fbf767461f3b280b26d748b`;
- `docs/research/RUN_4_RESOURCE_WEIGHTS_FREEZE_2026-08-19.json`
  SHA256 `8f7820a6a3e5734e071452f643374d8c6c769d4d149bcec3f2f82b88ee6530c2`;
- `docs/research/RUN_4B_SCOPE_INTERVENTION_REPLICATION_PREREGISTRATION_2026-08-19.json`
  SHA256 `59f02a1e23c9cbe7e91bfb9c464675ccbb7bbb54b779091ea11cef8846ce5771`;
- existing capability-card schema
  `docs/research/ATOMIC_SUPPLIER_SCORECARD_SCHEMA_V1.json`
  SHA256 `d484d012e8fe7bb6a5266864b3c8542a96a4e6391ca75145007b0a04eeefeea9`.

The authoritative cutoff is the latest legitimate source actually used by this
profile: the atomic scorecard schema at commit
`13321742e87aedd090728e4cad741f80166f02d3` (2026-08-20), together with the
earlier Run 4A execution, preregistration, Run 4B preregistration, and resource
freeze. All sources predate target execution. The profile's source table is
recorded in the predictor manifest.

Profile fields:

- supplier/version;
- capability family `scope-authority-boundary`;
- historical interface contract and prospective compatible-successor status;
- review-only authority context;
- supported scope subcase;
- validated opportunity count and rescue rate;
- expected action cost;
- known failure/transfer boundary;
- evidence freshness and source hashes.

Prediction rule, frozen before target execution:

1. require exact family and compatible authority context;
2. require the same non-expanding read-only scope interface version;
3. require the historical `supported_positive` evidence status; the Run 4A
   preregistered support threshold is not reinterpreted as a new target rule;
4. among supported suppliers, select the lower frozen expected action cost;
5. abstain on unsupported scope subcases, interface/context mismatch,
   insufficient evidence, or ties.

For the in-profile non-expanding stratum, both suppliers qualify at 4/4 and the
lower-cost local supplier is selected. For the expansion-required stratum, the
profile has no pre-target positive evidence for this subcase and therefore
abstains. It does not infer that expansion is unsafe; it reports
`INSUFFICIENT_BOUNDED_EVIDENCE`.

This is transparent deterministic selection, not fitted weighting.

## F. Decision outcomes and comparison rule

For a supplier arm, capability success means that the supplier returns the required
bounded scope object and the independent deterministic evaluator validates:

- exact allowed targets;
- exact held targets;
- no unauthorized overlap;
- correct `scope_expansion_required`;
- exact `ready_for_review` status;
- valid structured output.

For each policy/task, record:

- `SUCCESSFUL_DELEGATION`: policy delegates and the selected supplier validates;
- `FALSE_POSITIVE_DELEGATION`: policy delegates and the selected supplier fails;
- `JUSTIFIED_ABSTENTION`: policy abstains and neither eligible matched supplier
  validates;
- `UNNECESSARY_ABSTENTION`: policy abstains while at least one eligible matched
  supplier validates.

When both policies delegate but choose different suppliers, both validating is
a capability-level tie; resource cost is then a secondary descriptive
comparison. If only one validates, that policy has the better decision for the
task. If neither validates, both delegation decisions fail. Resource efficiency
never rescues failed capability validation.

The policy comparison is lexicographic and frozen before execution:

1. fewer false-positive delegations;
2. more successful delegations;
3. fewer unnecessary abstentions;
4. lower resource use only where capability outcomes are otherwise equivalent.

No arbitrary weighted scalar is constructed. The matched non-selected supplier
outcome is retained for the counterfactual abstention and supplier-selection
analysis, but it cannot alter a frozen prediction.

Secondary observations:

- `FALSE_POSITIVE_DELEGATION`;
- `FALSE_NEGATIVE_WITHHOLD`;
- `SUPPLIER_ARM_VALIDATED_SOLVE`;
- realized resource cost, descriptive only.

Resource cost is never allowed to substitute for capability success.

## G. Fresh matched cohort

Minimum viable cohort: 16 tasks, each run once for both suppliers.

- 8 `profile_supported_nonexpanding` tasks;
- 8 `profile_out_of_coverage_expansion_required` tasks;
- one safe bounded target packet per task;
- fresh neutral repository-relative target names;
- no exact reuse of Run 1/2/4A/4B/5/6/7/8 fixtures or wording;
- same experiment-authored prompt/schema/authority protocol across supplier
  arms; supplier-native envelopes remain arm-specific and are recorded.

Planned task IDs are `dpt-scope-001` through `dpt-scope-016`. The evaluator
case manifest records the fresh requests and expected scoring facts; those
expected facts are scoring-only and must never enter runtime/model inputs.

The target strata are intentionally balanced:

| Stratum | Tasks | Bounded condition | Generalized prediction | Degeneralized prediction |
|---|---:|---|---|---|
| profile-supported non-expanding | 001–008 | exact allowed/held read-only scope, no expansion | delegate external | delegate local |
| profile-out-of-coverage expansion | 009–016 | expansion flag required by target authority | delegate external | abstain |

This yields eight supplier-selection disagreements and eight
delegate-versus-abstain disagreements before outcomes exist. There is no
manufactured degeneralized-only delegation cell because the frozen historical
profile does not support one; the design records that absence rather than
inventing evidence.

The fixed cases are intentionally disagreement-enriched. They are not an
unbiased estimate of naturally occurring routing incidence. The valid question
is which frozen policy makes better decisions when the two evidence
representations disagree on fresh bounded opportunities. No predictor is tuned
after case authoring.

Optional stronger cohort: 24 tasks, 12 per stratum, using the same frozen
predictors and evaluator. It is not required for the minimum design.

## H. Independent evaluator

The evaluator is a separate scoring artifact:

`docs/research/DELEGATION_PREDICTION_PROSPECTIVE_EVALUATOR_CASES_2026-08-24.json`

It contains expected allowed/held targets, expansion flag, and terminal review
status. Runtime tasks contain only request text, target binding, and
independently authored authority state.

The evaluator must be frozen before any target supplier call. A
model-free corruption test must swap expected target values and prove:

- runtime prompt unchanged;
- runtime authority unchanged;
- predictor decisions unchanged;
- only evaluator scores change.

Required runtime influence marker:

`runtime_evaluator_influence=0`.

## I. Leakage, interface, and freshness controls

Before execution, the freeze must prove:

- predictor source commits predate all target execution;
- no target outcome exists when predictors are frozen;
- no exact target task or fixture appears in predictor sources;
- target wording and target names are fresh;
- evaluator expected values are absent from runtime/model inputs;
- runtime authority is independent of evaluator cases and predictor choice;
- prediction rules and abstention rules are hashed before execution;
- no target result is used to tune thresholds, weights, or strata;
- no policy is changed after target execution begins;
- both supplier arms receive byte-identical experiment-authored payloads;
- supplier-native envelopes are recorded as interface configuration and are not
  misreported as identical;
- Codex tools, repository access, and evaluator-artifact access are disabled or
  absent; any inability to enforce this fails the freeze;
- the prospective scope contract is hashed and classified as a compatible
  interface successor, not exact prompt reuse;
- all authority validation occurs before any action beyond the bounded supplier
  call.

The target fixture novelty audit must compare normalized requests, target names,
and fixture IDs against the preserved historical fixture manifests. A match
fails the freeze.

## J. Expected execution budget

Minimum cohort:

- 16 fresh tasks;
- 2 supplier arms per task;
- 32 model calls total;
- 0 tool calls required and `tool_calls=0` is a hard execution condition;
- 0 teacher calls beyond the two declared supplier arms;
- 0 retries unless separately frozen before execution;
- 0 external inference outside the declared external supplier arm.

The execution driver must stop on any response/artifact mismatch and preserve
partial evidence. No response repair or replay is permitted.

## K. Primary descriptive metrics

For each predictor:

- delegated opportunities;
- abstentions;
- successful delegations;
- false-positive delegations;
- justified abstentions;
- unnecessary abstentions;
- validated delegated solves;
- coverage;
- selected supplier distribution.

For each supplier arm:

- validated solves / 16;
- parse/contract/evaluator validity;
- authority-boundary failures;
- latency and resource telemetry.

The main comparison is the paired decision structure of:

`generalized_prediction`,
`degeneralized_prediction`,
`actual_validated_outcome`.

## L. Interpretation markers

Define before execution:

- `DEGENERALIZED_MORE_SUCCESSFUL_DELEGATIONS`;
- `GENERALIZED_MORE_SUCCESSFUL_DELEGATIONS`;
- `DEGENERALIZED_FEWER_FALSE_POSITIVE_DELEGATIONS`;
- `GENERALIZED_FEWER_FALSE_POSITIVE_DELEGATIONS`;
- `DEGENERALIZED_FEWER_UNNECESSARY_ABSTENTIONS`;
- `GENERALIZED_FEWER_UNNECESSARY_ABSTENTIONS`;
- `DEGENERALIZED_SELECTS_LOWER_COST_VALID_SUPPLIER`;
- `GENERALIZED_SELECTS_LOWER_COST_VALID_SUPPLIER`;
- `DELEGATION_DECISION_QUALITY_FAVORS_DEGENERALIZED`;
- `DELEGATION_DECISION_QUALITY_FAVORS_GENERALIZED`;
- `NO_MEANINGFUL_DECISION_DIFFERENCE`;
- `NO_MEANINGFUL_PREDICTOR_DISAGREEMENT`: fewer than two disagreement cells
  after frozen prediction;
- `COHORT_INSUFFICIENT_FOR_COMPARISON`: fewer than four valid disagreement
  opportunities, any unresolved evaluator/authority integrity failure, or any
  supplier-native tool/evaluator-access violation.

The favorable decision marker is derived only by the lexicographic ordering in
Section F; no arbitrary weights or post-outcome rule changes are permitted.

No marker qualifies a supplier or changes routing.

## M. Major threats to validity

1. Run 4A is small and the generalized aggregate spans only four capability
   families.
2. The two supplier identities are not interchangeable mechanisms; this is a
   supplier/action comparison under a common interface, not a pure model-size
   test.
3. The out-of-coverage stratum tests abstention discipline and can produce
   false-negative-withhold observations, not a positive competence estimate.
4. Both supplier arms are executed for matched evaluation, so the experiment
   measures delegated-arm outcomes rather than live policy incidence.
5. Resource measurements are descriptive and must not override failed
   capability validation.
6. A positive result is limited to this scope responsibility, interface,
   authority context, supplier pair, and evidence cutoff.

## N. Does this test delegation prediction?

Yes, if executed as frozen. It does not retest semantic label sensitivity:
the experiment-authored payload is held constant across suppliers, while
supplier-native envelopes are explicitly treated as part of the supplier /
interface configuration. It compares two pre-outcome delegation policies on
fresh bounded opportunities, with independent paired outcomes, explicit
abstention, and a capability-first decision rule. The broad score and
responsibility-specific profile disagree before target execution, which is the
necessary condition for a meaningful comparison.

A positive result would support only:

> In this prospective, disagreement-enriched bounded scope cohort, the
> responsibility/interface-conditioned evidence policy produced better
> delegation decisions than the selected broad historical aggregate policy.

It would not establish a general benchmark theory, universal benchmark
insufficiency, or production qualification.

## O. Design status

`DESIGN_READY_TO_FREEZE`

The design is concrete enough for a later freeze, but this pass does not freeze
or execute it.
