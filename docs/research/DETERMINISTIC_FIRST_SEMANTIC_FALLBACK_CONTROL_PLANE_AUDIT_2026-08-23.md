# Deterministic-first control-plane audit

This additive audit preserves the closeout at `1d68d67` and does not modify or
rescore its raw model responses, tool observations, frozen task matrix, or
historical scores.

## Provenance defect

The historical driver’s `runtime_task(task)` constructed the runtime authority
record from `expected_requested_target` and `expected_authority_operations`.
Those values were not read from runtime artifacts after preparation, so direct
runtime expected-field reads were zero, but the authority values were already
derived from evaluator knowledge before preparation.

Recorded disposition:

- `RUNTIME_EXPECTED_FIELD_DIRECT_READS=0`;
- `EVALUATOR_DERIVED_RUNTIME_AUTHORITY=true`;
- `ORACLE_FREE_RUNTIME_AUTHORITY_DEMONSTRATED=false`;
- `AUTHORITY_VALUE_CORRECTNESS_NOT_DISPUTED=true`.

The fresh confirmation driver separates `runtime_cases.json` and
`evaluator_cases.json`; runtime authority is authored independently and is
never synthesized from evaluator fields.

## Completion semantics

The preserved six deterministic-sufficient requests included `inspect`,
`amend`, `index`, and `dispatch`. The historical runtime resolved those
operations and marked them terminally successful without an actuator executing
the requested operation. The only actual operations performed were the four
read-only repository observations.

Therefore:

- `FROZEN_EVALUATOR_TERMINAL_MATCH=10/12` remains historical;
- historical routing success is reported separately;
- actual operation execution was limited to validated observations;
- `END_TO_END_TASK_COMPLETION_DEMONSTRATED=false`;
- `NON_OBSERVATION_OPERATIONS_TERMINATED_WITHOUT_ACTUATION=true`;
- `SUCCESS_CONTRACT_CONFUSED_ROUTING_SUCCESS_WITH_TASK_SUCCESS=true`.

The repaired confirmation distinguishes `ROUTING_SUCCESS` from
`TASK_TERMINAL_SUCCESS`. A resolved operation without a qualified actuator is
an incomplete plan and ends `ready_for_review` with
`NO_QUALIFIED_EXECUTION_SUPPLIER`.

## Preserved fallback evidence

The four preserved fallback responses remain unchanged: four calls, two
canonical operations resolved, and two unresolved/fail-closed. No semantic
diagnosis or replay is performed by this audit.

The detailed provenance graph and per-task routing-versus-execution matrix are
in [the audit matrix](DETERMINISTIC_FIRST_SEMANTIC_FALLBACK_CONTROL_PLANE_AUDIT_MATRIX_2026-08-23.json).
