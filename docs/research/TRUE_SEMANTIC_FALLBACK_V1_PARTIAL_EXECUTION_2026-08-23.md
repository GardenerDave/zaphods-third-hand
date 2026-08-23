# True semantic fallback V1 partial execution closeout

This is an additive closeout of the operator execution directory
`.work/model_size_supplier_floor/true_semantic_fallback_v1/run_20260823T160000Z_operator1`.
The frozen V1 design commit was `25b6051b910acece9dcc192533e86f0bf8db4cdb`; the
repository closeout before operator execution was
`3da279086a1864244f26bc09c9e527eb4f92fbce`.

The prior unexecuted V0 and blocked V1 evidence remain unchanged. The operator
verified the frozen execution driver byte-for-byte:

`03697a2dc201b5d1281a1b5a01d6fcb6101b1df772d283d85083b907853ea559`

## Preserved partial result

Exactly one response exists, for `tsfv1-001`; five frozen semantic tasks were
not executed. The preserved hashes are:

- `response.json`: `c163eb949e077b0c28a5b6395af4ad1b1e6abd91aaf51cd3ac0001cdbd9768ed`
- `candidate_validation.json`: `fea442f3b28d086f7ec92bc17c19d1040b9b0ce9a9a855fb4ab902d153ee8422`
- `call_started.json`: `1a6500b16b11407142fc6beb64aea6077f1785c440323c9d20b0bfbff00de556`
- `power_samples.json`: `16f5b604ab5865b7f2775f37a32449ed64366d086211cf6b81d8cfd009881420`
- `operation_derivation_1.json`: `e3c78fb4937ea993f0cd07647eca843ac7add4677d4245dec4fcdf253b8a53ff`

The model returned `{"operation_class_candidate": "inspect"}`. Parsing,
schema validation, enum validity, and candidate admissibility all passed. The
frozen evaluator expects `observe_presence` for `tsfv1-001`, so the semantic
classification is `false`. This is the first preserved failure in which the
model owned a genuinely unresolved, decision-critical operation-class fact.

Counts are: observed semantic classifications `1`, correct `0/1`, remaining
frozen opportunities not executed `5`, model calls `1`, tool calls `0`,
runtime results `0`, and tool observations `0`. This is not a `0/6` result.

Markers supported by this partial evidence:

```text
TRUE_SEMANTIC_FALLBACK_EXECUTION_BEGUN=true
GENUINE_SEMANTIC_FALLBACK_RESPONSE_CAPTURED=true
DECISION_CRITICAL_MODEL_SEMANTIC_RESPONSIBILITY_EXERCISED=true
FIRST_GENUINE_SEMANTIC_OPERATION_CLASSIFICATION_FAILURE_PRESERVED=true
TSFV1_001_EXPECTED_CLASS=observe_presence
TSFV1_001_OBSERVED_CLASS=inspect
TSFV1_001_PARSE_VALID=true
TSFV1_001_CONTRACT_VALID=true
TSFV1_001_CANDIDATE_VALID=true
TSFV1_001_CANDIDATE_ADMISSIBLE=true
TSFV1_001_SEMANTIC_CLASSIFICATION_CORRECT=false
MODEL_CALLS_MADE=1
TOOL_CALLS_MADE=0
TRUE_SEMANTIC_FALLBACK_DEMONSTRATED=false
MODEL_OUTPUT_TO_CAPABILITY_PLAN_TRANSITION_DEMONSTRATED=false
```

## Scientific validity

The task had one safe target, neutral target naming, unresolved deterministic
operation derivation, both safe candidate classes in runtime authority, no
evaluator fields in runtime, and evaluator-corruption invariance. The observed
semantic error is not explained by target-label leakage, runtime authority
class leakage, evaluator runtime leakage, deterministic pre-resolution, target
extraction failure, output-contract failure, authority denial, or tool failure.

The operator compatibility wrapper was infrastructure-only in its stated role:
it supplied `telemetry_base_url` and `telemetry_preflight` from the existing
0.6B telemetry module because the frozen 1.7B module lacked those helpers. The
wrapper artifact itself was not available in the repository run directory, so
`OPERATOR_COMPATIBILITY_WRAPPER_HASH_UNAVAILABLE=true`. No evidence indicates
that it changed the request, prompt, schema, model, parser, eligibility,
authority, or evaluator.

## Post-model planning defect

After the valid candidate was written to `operation_derivation_1.json`, the
frozen `plan()` implementation counted suppliers with expressions equivalent
to `x["selected_supplier"] and ...`. The `actuator.inspect` record has
`selected_supplier=null`; Python therefore yielded `None` into `sum()` and
raised `TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'`.

This is recorded as:

```text
POST_MODEL_PLANNING_DEFECT_DEMONSTRATED=true
POST_MODEL_PLANNING_DEFECT_CLASS=OPTIONAL_SUPPLIER_BOOLEAN_SUM_NONE
SEMANTIC_RESPONSE_PRESERVED_BEFORE_PLANNING_FAILURE=true
PLANNING_FAILURE_CAUSED_MODEL_ERROR=false
```

The future-only repair uses explicit `selected_supplier is not None` booleans
for MODEL, TOOL, and DETERMINISTIC_CODE counts. The frozen driver and all
operator response artifacts were not modified.

## Boundary and successor

No remaining V1 task is executed and no response is replayed. A fresh successor
design is prepared in
[TRUE_SEMANTIC_FALLBACK_V2_DESIGN_2026-08-23.md](TRUE_SEMANTIC_FALLBACK_V2_DESIGN_2026-08-23.md).
It retains neutral targets, shared class-independent authority, separate
evaluator data, two real candidate classes, enum-only output, one deterministic
target, genuine unresolved operation semantics, interleaved classes, and no
teacher or retries. It must use a fresh holdout and the repaired planner.

`NEXT_DECISION=RUN_FRESH_TRUE_SEMANTIC_FALLBACK_BASELINE_WITH_REPAIRED_HARNESS`

No model/tool calls, teaching intervention, qualification change, or production
routing change occurred in this closeout.
