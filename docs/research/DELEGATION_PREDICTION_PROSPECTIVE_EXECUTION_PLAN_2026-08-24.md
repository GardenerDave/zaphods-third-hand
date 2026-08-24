# Prospective Delegation-Prediction Execution Plan

Experiment: `DELEGATION_PREDICTION_TEST_SCOPE_V0`

This is a prepared plan only. It must not be executed from this design commit.

## Frozen sequence

1. Freeze the predictor JSON and evaluator-case JSON.
2. Generate a fresh runtime fixture pack from the 16 evaluator case IDs without
   copying expected evaluator fields into runtime inputs.
3. Run the model-free novelty, authority, evaluator-influence, and predictor
   snapshot checks.
4. For every task, prepare one byte-identical request/schema/authority packet
   for the local and external supplier arms.
5. Compute both frozen predictions before any supplier call.
6. Execute the local and external arms exactly once per task.
7. Validate each response with the independent deterministic evaluator.
8. Record raw responses and telemetry without repair or retry.
9. Score each predictor against the matched supplier-arm outcome.
10. Stop before any qualification, production routing, or policy promotion.

## Planned artifacts

- predictor manifest:
  `docs/research/DELEGATION_PREDICTION_PROSPECTIVE_PREDICTORS_2026-08-24.json`;
- evaluator manifest:
  `docs/research/DELEGATION_PREDICTION_PROSPECTIVE_EVALUATOR_CASES_2026-08-24.json`;
- fresh runtime fixture pack and run directory: created only at a later freeze;
- per-task prediction snapshots;
- per-arm raw response, validation, authority, and telemetry artifacts;
- closeout matrix with generalized prediction, degeneralized prediction, both
  matched arm outcomes, and primary/secondary metrics.

## Budget

Minimum cohort: 16 tasks × 2 supplier arms = 32 model calls.

- model calls: 32;
- tool calls: 0;
- retries: 0;
- teacher calls outside the two declared supplier arms: 0;
- outcome evidence before execution: 0.

An optional 24-task cohort would require 48 model calls. No execution directory is
created in this design pass.

## Pre-execution assertions

- `MODEL_CALLS_MADE=0`;
- `TOOL_CALLS_MADE=0`;
- `RESPONSE_FILES=0`;
- predictor/evaluator hashes match the frozen manifest;
- target fixture novelty audit passes;
- evaluator expected fields are absent from runtime inputs;
- runtime authority is independent of predictor and evaluator;
- both arm inputs are identical except supplier identity;
- prediction snapshots predate every response;
- `runtime_evaluator_influence=0`;
- no target outcome has entered either predictor.

## Stop conditions

Stop and preserve partial evidence if any response exists before prediction
snapshots, if a response artifact is missing, if runtime/evaluator separation
fails, or if a supplier call needs retry or repair. Do not replay or alter the
frozen predictors.

## Outcome interpretation

Use only the pre-registered descriptive markers in the predictor manifest.
Do not infer statistical significance from this minimum cohort. A positive result
would support only this bounded scope/interface/supplier configuration.
