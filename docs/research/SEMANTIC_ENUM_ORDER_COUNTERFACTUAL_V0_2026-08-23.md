# Semantic Enum Order Counterfactual V0 Closeout

The frozen experiment at commit `f14023e7484584b975cbac93989daa0f01767e7b`
used driver SHA256
`6dc7e4cddc52e9ac9ea5070d449f5346c09e5387278caed4acc74d274113f495` and was
executed from
`.work/model_size_supplier_floor/semantic_enum_order_counterfactual_v0/run_20260823T204600Z`.

The operator produced exactly 12 responses: one A and one B for each of six
tasks, with the preregistered A/B, B/A, A/B, B/A, A/B, B/A order. All 12
responses were `inspect` and all were parse-valid, contract-valid,
candidate-valid, and admissible. There were 12 model calls, zero tool calls,
zero retries, zero teacher/30B/external calls, zero runtime evaluator
influence, and zero model-granted authority.

Arm A scored semantic correctness 3/6: presence 0/3 and inspect 3/3. Arm B
scored identically: presence 0/3 and inspect 3/3. The paired transition table
was `inspect -> inspect = 6`; all other transitions, including unresolved,
were zero. Therefore `ENUM_ORDER_CHANGED_OUTPUT_COUNT=0/6`.

The first-enum association did not replicate causally: Arm A placed `inspect`
first, while Arm B placed `observe_presence` first, yet both produced
`inspect` 6/6. The bounded result is:

```text
ENUM_ORDER_EFFECT_SUPPORTED=false
FIRST_ENUM_SELECTION_PATTERN_SUPPORTED=false
ENUM_ORDER_HYPOTHESIS_MATERIALLY_WEAKENED=true
BOUNDED_OPERATION_CLASSIFICATION_CLASS_COLLAPSE_REPLICATED=true
OBSERVED_COLLAPSE_CLASS=inspect
COLLAPSE_INVARIANT_TO_ENUM_ORDER=true
```

All accepted classifications wrote `operation_derivation_1.json` and
`capability_plan_1.json`; the inspect actuator remained uncovered, with
`overall_coverage=INCOMPLETE`, `execution_path_complete=false`, and
`NO_QUALIFIED_EXECUTION_SUPPLIER`. No tool was invoked. Correct inspect
classifications and incorrect presence-to-inspect classifications therefore
remain distinct semantic outcomes despite identical safe containment.

Telemetry is descriptive only. Measurement level was 2 with boundary
`gpu_device_only`; process-level remote exclusivity was not established. Arm A
latency mean/median/p95 was 905.370/882.287/1238.113 ms, and Arm B was
905.771/921.110/1249.856 ms. Overall latency was
905.570/898.952/1238.113 ms. Energy totals were 162.6925 J for A, 173.04 J
for B, and 335.7325 J overall.

The predecessor unexecuted freeze remains preserved. The full per-call raw
artifact hashes and paired scores are in the [closeout matrix](SEMANTIC_ENUM_ORDER_COUNTERFACTUAL_V0_MATRIX_2026-08-23.json).

Next decision:

`NEXT_DECISION=OPERATOR_EXECUTE_SEMANTIC_LABEL_COUNTERFACTUAL`
