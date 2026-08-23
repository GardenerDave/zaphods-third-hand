# Action-expression normalization experiment closeout

This fresh 12-call experiment tested the boundary:

```text
action_expression -> deterministic.operation_normalization -> canonical_operation
```

Historical evidence was not rescored. The model emitted only
`action_expression` and `object_expression`; it did not receive canonical
mappings or authority decisions.

## Model-free historical projection

The frozen baseline outputs from the teaching holdout projected to 8/8 correct
canonical operations under the new rules. The patched teaching outputs projected
to 4/8 because the patch collapsed every action to `check`, including direct
operation controls. This is additive architectural evidence only.

## Fresh result

| Metric | Result |
|---|---:|
| Parse-valid | 12/12 |
| Contract-valid | 12/12 |
| Action-expression structurally usable | 12/12 |
| Object-expression exact | 9/12 |
| Normalized | 4/12 |
| Unresolved | 6/12 |
| Ambiguous | 2/12 |
| Canonical operation correct (applicable normalized tasks) | 4/8 |
| Overall normalization decision correct, including fail-closed cases | 8/12 |
| Safe target binding | 4/12 |
| Secondary surface-expression exact | 6/12 |
| Ambiguous requests failed closed | 2/2 |
| Unsupported requests failed closed | 2/2 |
| Authority broadening events | 0 |
| Model output granted authority | 0 |

By regime:

- presence observation: canonical operation 1/4, object exact 2/4;
- direct controls: canonical operation 3/4; `index` was unresolved and its
  object expression was also incorrect;
- ambiguous: 2/2 returned `AMBIGUOUS` and failed closed;
- unsupported: 2/2 returned `UNRESOLVED` and failed closed.

The successful controls were inspect, amend, and dispatch. The supplier did
not reliably emit a usable action expression for the presence requests. Raw
examples included action expressions containing the target or a generic phrase,
such as `docs/normalization-presence-alpha.txt` and `Check if ... is present`,
which the exact normalizer correctly refused to guess about.

## Resource report

The 12 Qwen3 1.7B calls used 816.6275 J total gross GPU-device energy,
68.0523 J/call mean, and 69.065 J/call median. Latency was 2360.987 ms mean,
2348.43 ms median, and 2576.552 ms p95. There were no teacher, tool, retry,
external, or 30B calls.

## Characterization

`ACTION_EXPRESSION_INTERFACE_DEMONSTRATED=true` means the renamed structured
interface was contract-valid and structurally populated; it does not mean the
semantic atom was solved.

`DETERMINISTIC_OPERATION_NORMALIZATION_DEMONSTRATED=false`

`ACTION_FIELD_ROLE_OVERLOAD_RESOLVED_IN_EXPERIMENTAL_INTERFACE=false`

`INTELLIGENCE_SURFACE_REDUCED=false`

`PRIMARY_CHARACTERIZATION=ACTION_EXPRESSION_NORMALIZATION_BOUNDARY_PARTIAL`

`NEXT_DECISION=DIAGNOSE_ACTION_EXPRESSION_SUPPLIER_FLOOR`

The deterministic boundary itself behaved conservatively: it normalized only
frozen exact expressions, separated direct operations from presence, and failed
closed on unknown or multi-operation text. The remaining defect is primarily
insufficient supplier extraction of the new expression field, not unsafe
normalizer behavior. No automatic qualification or production-interface change
was made.
