# Deterministic-first confirmation authority and coverage audit

This is a model-free additive audit of the completed corrected confirmation. It
does not replay calls or alter the historical run at
`.work/model_size_supplier_floor/deterministic_first_confirmation/run_20260823T130000Z/`.

## Preserved result

The historical markers remain unchanged:

- `INDEPENDENT_RUNTIME_AUTHORITY_PROVENANCE_DEMONSTRATED=true`
- `ROUTING_SUCCESS_TASK_SUCCESS_SEPARATION_DEMONSTRATED=true`
- `DETERMINISTIC_FIRST_CAPABILITY_ROUTING_DEMONSTRATED=true`
- `MODEL_CALL_AVOIDANCE_FROM_CAPABILITY_DECOMPOSITION_DEMONSTRATED=true`
- `SEMANTIC_MODEL_FALLBACK_DEMONSTRATED=true` in the bounded partial sense
- `DYNAMIC_INTELLIGENCE_SURFACE_MINIMIZATION_DEMONSTRATED=true` in the bounded routing sense

The preserved confirmation evidence remains: routing 8/8, two deterministic
presence observations terminally successful, two fallback calls with one
normalized, three validated observations, two no-actuator cases correctly
review-gated, and two ambiguous/unsupported cases fail-closed.

## Authority ordering audit

The historical path checked exact target membership before observation, but
checked canonical operation membership only in the later success-contract
state. Therefore:

- `TARGET_AUTHORITY_PRE_EXECUTION_ENFORCEMENT_DEMONSTRATED=true`
- `OPERATION_AUTHORITY_PRE_EXECUTION_ENFORCEMENT_DEMONSTRATED=false`
- `OPERATION_AUTHORITY_CURRENTLY_PARTICIPATES_IN_TERMINAL_VALIDATION=true`

All three historical observations had legitimate `observe_presence` authority;
this is an untested-denial-path ordering defect, not evidence of an
unauthorized historical call.

The repaired runtime path now uses an explicit deterministic
`validate_execution_authority()` gate for both operation and target before the
read-only observer. The success-contract evaluator remains a separate
post-execution terminal check.

Authority provenance is therefore:

```text
runtime request/packet
  -> canonical operation + requested target
  -> ENVIRONMENT_AUTHORITY_RECORD
  -> pre-actuation operation/target gate
  -> bounded observer
```

Evaluator expectations remain a closeout-only input:

```text
runtime cases + packets + environment authority -> runtime plan/execution
evaluator cases + preserved runtime results       -> scoring only
```

No evaluator field is on the runtime dependency path.

## Coverage audit

`capability_plan_0` is stage-local. For semantic fallback tasks it covers the
initial MODEL step, not necessarily the eventual TOOL path. The repaired
closeout projection uses the latest available plan:

- `PLAN0_COVERAGE_IS_STAGE_LOCAL=true`
- `PLAN0_COVERAGE_USED_AS_FINAL_EXECUTION_COVERAGE_METRIC=true` in the historical closeout
- `FINAL_EXECUTION_COVERAGE_ACCOUNTING_DEMONSTRATED=false` for the historical artifact
- `FINAL_EXECUTION_COVERAGE_ACCOUNTING_IMPLEMENTED=true` in the repaired code

The broader historical marker is preserved for provenance, but its scope is
narrowed additively:

- `NO_ACTUATOR_INCOMPLETE_COVERAGE_ENFORCED=true`
- `COMPLETE_EXECUTION_CAPABILITY_COVERAGE_MARKER_SCOPE=NO_ACTUATOR_FAIL_CLOSED_ONLY`

The per-task projection is in the accompanying [audit matrix](DETERMINISTIC_FIRST_CONFIRMATION_AUTHORITY_ORDERING_AUDIT_MATRIX_2026-08-23.json).

## State terminology

The repaired control plane distinguishes:

- `ROUTING_DECISION_CORRECT`: the bounded route or fail-closed decision was correct;
- `EXECUTION_PATH_COMPLETE`: the latest plan has all required execution suppliers;
- `TASK_TERMINAL_SUCCESS`: the requested observation/effect was produced and validated.

These are intentionally not interchangeable. In particular, the unresolved
fallback has stage-0 MODEL coverage but incomplete final execution coverage,
and amend/dispatch have correct routing decisions but no qualified actuator.

## Audit controls

Model-free tests cover authorized and denied operation/target paths, no observer
invocation on denial, evaluator corruption invariance, missing-actuator
coverage, unresolved fallback coverage, and ambiguous/unsupported fail-closed
behavior. No model, teacher, tool, external, retry, production, or qualification
action occurred during this audit.

`NEXT_DECISION=DIAGNOSE_SEMANTIC_FALLBACK_INTERFACE` remains unchanged and is
not executed here.
