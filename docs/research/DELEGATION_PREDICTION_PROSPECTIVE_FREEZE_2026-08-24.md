# Prospective Delegation-Prediction Experiment Freeze

Status: frozen, unexecuted. This artifact freezes the hardened design from
`39f2a07b15324b01c62f14e447fc94169675ddf2`; it does not execute suppliers or
create a runtime directory.

## Frozen protocol

The primary estimand is delegation-decision quality for the fixed
`scope-authority-boundary` cohort. The cohort contains 16 cases in manifest
order:

- 8 supplier-selection disagreements;
- 8 delegate-versus-abstain disagreements;
- 8 binary expected-success disagreements.

The cases are deliberately disagreement-enriched and are not an incidence-
representative routing sample.

The two frozen policies are:

- `RUN4A_INTERVENTION_AGGREGATE_ALL_FAMILIES_V1`: delegate to the higher
  existing broad aggregate score; ties or missing scores abstain. The
  historical Run 4A 0.50 threshold remains scoped to historical
  `supported_positive` evidence and is not applied to the broad aggregate.
- `SCOPE_INTERFACE_PROFILE_RUN4A_V1`: require compatible bounded evidence and
  select the lower expected-cost supported supplier; unsupported, mismatched,
  or tied cases abstain.

Decision comparison is lexicographic: false-positive avoidance, successful
delegation, abstention quality, then cost only when capability outcomes are
equivalent. The evaluator is scoring-only and unavailable to runtime
prediction.

## Supplier and interface lineage

Historical and prospective identities are exact for the preserved fields:

- local: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` via `JARVIS_LOCAL`;
- external: `codex-cli-0.146.0` via the Codex service class.

The prospective experiment-authored contract is a compatible successor to
`run4a_scope_json_contract_v1`, not exact prompt/interface reuse. The
experiment-authored payload is matched across arms; supplier-native envelopes
are supplier-specific and must not be described as byte-identical. Execution
requires no tools, repository access, evaluator access, authority changes, or
self-qualification.

## Pre-execution audit

The audit passed before freeze artifact creation:

- no prospective runtime directory;
- no prospective response or result artifacts;
- no supplier inference, teacher call, tool call, or external inference;
- no outcome-dependent artifact;
- no evaluator-only fields in runtime predictor inputs;
- no dropped or altered prospective cases;
- no historical artifact mutation.

All source hashes, case identities, predictor policies, evaluator separation,
controls, and machine-readable contamination results are in
[`DELEGATION_PREDICTION_PROSPECTIVE_FREEZE_2026-08-24.json`](DELEGATION_PREDICTION_PROSPECTIVE_FREEZE_2026-08-24.json).

`PROSPECTIVE_DELEGATION_PREDICTION_COHORT_FROZEN=true`

`DELEGATION_DECISION_ESTIMAND_FROZEN=true`

`DISAGREEMENT_ENRICHED_SAMPLING_FROZEN=true`

`EVALUATOR_RUNTIME_SEPARATION_FROZEN=true`

`SUPPLIER_IDENTITY_AND_INTERFACE_LINEAGE_FROZEN=true`

`PROSPECTIVE_EXECUTION_POLICY_FROZEN=true`

`PRE_FREEZE_PROSPECTIVE_INFERENCE_DETECTED=false`

`PROSPECTIVE_RUNTIME_ARTIFACTS_CREATED=false`

`PRIMARY_CHARACTERIZATION=PROSPECTIVE_DELEGATION_PREDICTION_EXPERIMENT_FROZEN_UNEXECUTED`
