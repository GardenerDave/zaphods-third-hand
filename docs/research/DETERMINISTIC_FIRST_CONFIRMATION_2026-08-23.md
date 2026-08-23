# Corrected deterministic-first confirmation closeout

This fresh confirmation follows the control-plane audit at `7b1071a` and uses
independent runtime authority records. It does not modify the preserved
12-task run or its raw responses.

## Results

| metric | result |
|---|---:|
| routing decisions correct | 8/8 |
| model calls avoided | 2 |
| fallback calls planned/made | 2/2 |
| fallback operations normalized | 1/2 |
| complete capability coverage | 4/8 |
| incomplete coverage correctly detected | 4/4 |
| actual read-only observations | 3 |
| validated observations | 3 |
| routing success | 6/8 |
| task-terminal success | 3/8 |
| ready for review | 5/8 |
| runtime evaluator influence | 0 |
| model output granted authority | 0 |

The two deterministic presence cases reached terminal success after validated
observations. One semantic fallback reached terminal success after model
normalization, authority validation, and observation. The other fallback
failed closed before tool execution. Amend and dispatch resolved and were
routing-successful, but had no qualified actuator and therefore ended
`ready_for_review` with `NO_QUALIFIED_EXECUTION_SUPPLIER`. Ambiguous and
unsupported requests also failed closed.

## Interpretation

The corrected slice demonstrates:

- `INDEPENDENT_RUNTIME_AUTHORITY_PROVENANCE_DEMONSTRATED=true`;
- `ROUTING_SUCCESS_TASK_SUCCESS_SEPARATION_DEMONSTRATED=true`;
- `COMPLETE_EXECUTION_CAPABILITY_COVERAGE_ENFORCED=true`;
- `DETERMINISTIC_FIRST_CAPABILITY_ROUTING_DEMONSTRATED=true`;
- `MODEL_CALL_AVOIDANCE_FROM_CAPABILITY_DECOMPOSITION_DEMONSTRATED=true`;
- `SEMANTIC_MODEL_FALLBACK_DEMONSTRATED=true` in the bounded partial sense;
- `DYNAMIC_INTELLIGENCE_SURFACE_MINIMIZATION_DEMONSTRATED=true` in the
  bounded routing sense.

The result is not general execution capability or production routing. No
actuator was added, no authority was broadened, and no qualification changed.

## Resource and provenance accounting

There were 2 model calls, 3 read-only tool calls, 0 teacher/30B/external calls,
0 retries, and 0 duplicate calls. Model latency mean/median/p95 was
3573.767/3573.767/3671.361 ms. Gross GPU-device energy total/mean/median was
179.528/89.764/89.764 J. These are descriptive measurements only.

The complete per-task routing-versus-terminal matrix, response hashes, runtime
authority provenance, and driver hashes are in
[the confirmation matrix](DETERMINISTIC_FIRST_CONFIRMATION_MATRIX_2026-08-23.json).

`NEXT_DECISION=DIAGNOSE_SEMANTIC_FALLBACK_INTERFACE`.
