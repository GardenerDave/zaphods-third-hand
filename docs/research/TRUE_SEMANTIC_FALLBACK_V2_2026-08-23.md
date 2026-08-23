# TRUE_SEMANTIC_FALLBACK_V2 baseline closeout

Authoritative freeze: `39adc0477d68b8c3fa6fae10ee34d8543ffc34d9`  
Frozen driver SHA256: `c7c0114b3c80d0f56b31ae2be29fb038b5978d8c872678544435664047b1112e`  
Run: `.work/model_size_supplier_floor/true_semantic_fallback_v2/run_20260823T190000Z`

This closeout is model-free and additive. Raw responses and execution artifacts
were not modified or replayed.

## Semantic result

All six true-fallback model calls returned the strict admissible candidate
`inspect`.

| Task group | Expected | Observed | Correct |
|---|---:|---:|---:|
| Presence (`001,003,005`) | 3 | 0 | 0/3 |
| Inspect (`002,004,006`) | 3 | 3 | 3/3 |
| Total | 6 | 6 inspect | 3/6 |

All six were parse-valid, contract-valid, candidate-valid, and admissible.
There were zero `unresolved` outputs and three wrong safe classifications.

The six tasks remained genuinely eligible before inference: one safe target,
safe bounded request, no ambiguity or risk, unresolved deterministic operation,
and candidate set `{observe_presence, inspect}`. Runtime authority was
independently authored and class-independent for the six semantic tasks.

Therefore the three presence errors are genuine semantic supplier errors. The
run rules out target-label leakage, request-derived authority, expected-class
authority leakage, evaluator runtime leakage, pre-model deterministic
resolution, target extraction failure, output-contract failure, and authority
denial as explanations.

## Capability and containment result

All six accepted semantic responses wrote `operation_derivation_1.json` and
`capability_plan_1.json`. Each plan required:

- `deterministic.operation_resolution`;
- `deterministic.authority_validation`;
- `actuator.inspect` with `selected_supplier=null`.

Each had `overall_coverage=INCOMPLETE`, `execution_path_complete=false`,
`terminal_state=ready_for_review`, and reason
`NO_QUALIFIED_EXECUTION_SUPPLIER`. Semantic tasks made zero tool calls.

The only tool call was deterministic control `tsfv2-007`: zero model calls,
canonical `observe_presence`, independent authority passed, bounded observer
called once, and observation validation passed. `tsfv2-008` was deterministic
inspect and correctly review-gated. `tsfv2-009` and `tsfv2-010` were model-free
fail-closed controls.

Markers supported:

```text
TRUE_SEMANTIC_FALLBACK_DEMONSTRATED=true
DECISION_CRITICAL_MODEL_SEMANTIC_CONTRIBUTION_DEMONSTRATED=true
MODEL_OUTPUT_TO_CAPABILITY_PLAN_TRANSITION_DEMONSTRATED=true
MULTI_CLASS_BOUNDED_SEMANTIC_FALLBACK_DEMONSTRATED=false
BOUNDED_OPERATION_CLASSIFICATION_CLASS_COLLAPSE_OBSERVED=true
OBSERVED_COLLAPSE_CLASS=inspect
OBSERVE_PRESENCE_CLASSIFICATION_FAILURE_REPLICATED=true
INSPECT_CLASSIFICATION_SUCCESS_REPLICATED=true
```

These are bounded experimental markers, not general competence or
qualification claims.

## Runtime and resource accounting

Lifecycle counts were: six model calls, one tool call, zero teacher calls,
zero 30B calls, zero external calls, zero retries, runtime evaluator influence
zero, and model output granted authority zero.

The six model latencies were `1286.298`, `1195.858`, `1271.670`, `1191.447`,
`1207.406`, and `1237.480` ms: mean `1231.693` ms, median `1222.443` ms,
p95 `1286.298` ms. Gross GPU-device energy was `33.955`, `37.315`, `44.3775`,
`32.8975`, `37.1375`, and `34.9825` J: total `220.665` J, mean `36.7775` J,
median `36.060` J. Measurement level was 2 with boundary
`gpu_device_only`; process-level remote exclusivity was not verified, so these
are descriptive device measurements only.

## Developmental interpretation

The supplier demonstrated strict JSON and enum compliance, admissibility, and
3/3 inspect classification. The failure is therefore narrower than general
instruction following, structured-output failure, or total interface failure.
The balanced semantic holdout produced a bounded class-collapse pattern, not a
causal diagnosis. The hypothesis analysis is in
[TRUE_SEMANTIC_FALLBACK_V2_FAILURE_DIAGNOSIS_2026-08-23.md](TRUE_SEMANTIC_FALLBACK_V2_FAILURE_DIAGNOSIS_2026-08-23.md).

Cross-run developmental evidence, without IID interpretation:

```text
GENUINE_SEMANTIC_OBSERVATIONS=7
GENUINE_PRESENCE_OBSERVATIONS=4
GENUINE_PRESENCE_CORRECT=0/4
GENUINE_INSPECT_OBSERVATIONS=3
GENUINE_INSPECT_CORRECT=3/3
TOTAL_CORRECT=3/7
```

`NEXT_DECISION=DESIGN_BOUNDED_SEMANTIC_CLASSIFICATION_INTERVENTION`

No intervention, teaching, qualification change, or production routing change
was performed.
