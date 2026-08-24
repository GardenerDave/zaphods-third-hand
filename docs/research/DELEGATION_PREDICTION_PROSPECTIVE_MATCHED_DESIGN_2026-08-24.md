# Prospective Matched Delegation-Prediction Test

Status: design/preregistration only. No target execution or outcome evidence
exists.

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

Both receive the same frozen request, output schema, target authority context,
and deterministic evaluator. Supplier identity is the only execution-arm
difference. Neither supplier can grant authority, change the evaluator, or
self-qualify.

The matched design executes both supplier arms for each task. This makes the
outcome for either frozen predictor's selected supplier observable without
letting either predictor inspect the target result. It is an experimental
paired-delegation design, not production routing.

## C. Generalized predictor

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
3. delegate when the selected score is at least the existing 0.50
   supported-positive floor;
4. otherwise abstain;
5. ties or missing scores abstain.

Therefore this predictor selects external and predicts
`DELEGATION_EXPECTED_TO_SUCCEED=true` for the in-scope target stratum and
also selects external for the out-of-profile expansion stratum.

This is intentionally a broad comparison score. It does not inspect the target
scope subcase.

## D. Degeneralized predictor

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

Evidence cutoff: the Run 4A execution evidence and frozen resource prior,
before this prospective target cohort is generated or executed.

Profile fields:

- supplier/version;
- capability family `scope-authority-boundary`;
- exact target interface version;
- review-only authority context;
- supported scope subcase;
- validated opportunity count and rescue rate;
- expected action cost;
- known failure/transfer boundary;
- evidence freshness and source hashes.

Prediction rule, frozen before target execution:

1. require exact family and compatible authority context;
2. require the same non-expanding read-only scope interface version;
3. require a supported-positive historical profile with at least three
   opportunities and rescue rate at least 0.50;
4. among supported suppliers, select the lower frozen expected action cost;
5. abstain on unsupported scope subcases, interface/context mismatch,
   insufficient evidence, or ties.

For the in-profile non-expanding stratum, both suppliers qualify at 4/4 and the
lower-cost local supplier is selected. For the expansion-required stratum, the
profile has no pre-target positive evidence for this subcase and therefore
abstains. It does not infer that expansion is unsafe; it reports
`INSUFFICIENT_BOUNDED_EVIDENCE`.

This is transparent deterministic selection, not fitted weighting.

## E. Exact prediction target

Primary target:

`DELEGATION_EXPECTED_TO_SUCCEED`

For a supplier arm, success means that the supplier returns the required
bounded scope object and the independent deterministic evaluator validates:

- exact allowed targets;
- exact held targets;
- no unauthorized overlap;
- correct `scope_expansion_required`;
- exact `ready_for_review` status;
- valid structured output.

A predictor's selected supplier is scored against that supplier's matched arm
outcome. An abstention is scored as no delegation. The matched non-selected
supplier outcome is retained only for the preregistered false-negative/
counterfactual analysis; it does not alter the prediction.

Secondary targets:

- `FALSE_POSITIVE_DELEGATION`;
- `FALSE_NEGATIVE_WITHHOLD`;
- `SUPPLIER_ARM_VALIDATED_SOLVE`;
- realized resource cost, descriptive only.

Resource cost is never allowed to substitute for capability success.

## F. Fresh matched cohort

Minimum viable cohort: 16 tasks, each run once for both suppliers.

- 8 `profile_supported_nonexpanding` tasks;
- 8 `profile_out_of_coverage_expansion_required` tasks;
- one safe bounded target packet per task;
- fresh neutral repository-relative target names;
- no exact reuse of Run 1/2/4A/4B/5/6/7/8 fixtures or wording;
- same frozen prompt/schema/authority protocol across supplier arms.

Planned task IDs are `dpt-scope-001` through `dpt-scope-016`. The evaluator
case manifest records the fresh requests and expected scoring facts; those
expected facts are scoring-only and must never enter runtime/model inputs.

The target strata are intentionally balanced:

| Stratum | Tasks | Bounded condition | Generalized prediction | Degeneralized prediction |
|---|---:|---|---|---|
| profile-supported non-expanding | 001–008 | exact allowed/held read-only scope, no expansion | delegate external | delegate local |
| profile-out-of-coverage expansion | 009–016 | expansion flag required by target authority | delegate external | abstain |

This yields eight supplier-choice disagreements and eight
generalized-only-delegation disagreements before outcomes exist. There is no
manufactured degeneralized-only delegation cell because the frozen historical
profile does not support one; the design records that absence rather than
inventing evidence.

Optional stronger cohort: 24 tasks, 12 per stratum, using the same frozen
predictors and evaluator. It is not required for the minimum design.

## G. Independent evaluator

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

## H. Leakage and freshness controls

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
- both supplier arms receive byte-identical model-visible task inputs;
- all authority validation occurs before any action beyond the bounded supplier
  call.

The target fixture novelty audit must compare normalized requests, target names,
and fixture IDs against the preserved historical fixture manifests. A match
fails the freeze.

## I. Expected execution budget

Minimum cohort:

- 16 fresh tasks;
- 2 supplier arms per task;
- 32 model calls total;
- 0 tool calls required;
- 0 teacher calls beyond the two declared supplier arms;
- 0 retries unless separately frozen before execution;
- 0 external inference outside the declared external supplier arm.

The execution driver must stop on any response/artifact mismatch and preserve
partial evidence. No response repair or replay is permitted.

## J. Primary descriptive metrics

For each predictor:

- delegated opportunities;
- abstentions;
- correct predictions;
- false-positive delegations;
- false-negative withholds;
- validated delegated solves;
- coverage;
- selected supplier distribution.

For each supplier arm:

- validated solves / 16;
- parse/contract/evaluator validity;
- authority-boundary failures;
- latency and resource telemetry.

The main comparison is not a scalar accuracy claim. It is the paired structure
of:

`generalized_prediction`,
`degeneralized_prediction`,
`actual_validated_outcome`.

## K. Interpretation markers

Define before execution:

- `DEGENERALIZED_PREDICTION_OUTPERFORMS_GENERALIZED`: degeneralized has
  more correct primary predictions and no increase in false-positive
  delegations, with at least one disagreement cell;
- `GENERALIZED_PREDICTION_OUTPERFORMS_DEGENERALIZED`: generalized has more
  correct primary predictions under the same rule;
- `PREDICTORS_TIED`: equal correct predictions and equal false-positive
  delegations;
- `DEGENERALIZED_REDUCES_FALSE_POSITIVE_DELEGATION`: fewer false-positive
  delegations, regardless of overall tie;
- `DEGENERALIZED_RECOVERS_VALID_BOUNDED_DELEGATION`: at least one
  degeneralized-selected supplier arm validates and the generalized predictor
  either abstains or selects a supplier whose matched arm fails;
- `NO_MEANINGFUL_PREDICTOR_DISAGREEMENT`: fewer than two disagreement cells
  after frozen prediction;
- `COHORT_INSUFFICIENT_FOR_COMPARISON`: fewer than four valid disagreement
  opportunities or any unresolved evaluator/authority integrity failure.

No marker qualifies a supplier or changes routing.

## L. Major threats to validity

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

## M. Does this test delegation prediction?

Yes, if executed as frozen. It does not retest semantic label sensitivity:
the interface is held constant across suppliers. It compares two pre-outcome
supplier-selection rules on fresh bounded delegation opportunities, with
independent paired outcomes and explicit abstention. The broad score and
responsibility-specific profile disagree before target execution, which is the
necessary condition for a meaningful comparison.

A positive result would support only:

> In this prospective bounded scope cohort, the responsibility/interface
> evidence profile predicted delegated-arm validation outcomes better than the
> selected generalized historical aggregate.

It would not establish a general benchmark theory, universal benchmark
insufficiency, or production qualification.

## Design status

`DESIGN_READY_TO_FREEZE`

The design is concrete enough for a later freeze, but this pass does not freeze
or execute it.
