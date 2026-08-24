# Semantic Enum Order Counterfactual V0

Status: frozen design; no inference has run.

The predecessor freeze `26c8a9342877dc2e8bec9a30e3fc0d39ff70fbd4` is preserved
as an unexecuted superseded pre-inference freeze. Its generated order was
A-then-B for all six pairs despite the intended alternating declaration. No
model call or response existed, so scientific model evidence was not
contaminated. This successor changes only the execution-order construction and
uses a fresh prepared run.

This bounded interface experiment tests one hypothesis from the oracle-clean
TRUE_SEMANTIC_FALLBACK_V2 baseline: whether the observed all-`inspect` output
pattern is associated with the order of the two safe enum alternatives in the
structured response schema. V2 used the effective order
`inspect, observe_presence, unresolved`; its six outputs matched the first
member. This is an association, not a causal conclusion.

The paired arms use the same six fresh, neutral-target, genuinely unresolved
semantic requests, the same prompt text, class definitions, model settings,
independent authority, target, preflight, and semantic information gap.

Arm A is the V2-effective order:

```json
["inspect", "observe_presence", "unresolved"]
```

Arm B reverses only the two safe alternatives:

```json
["observe_presence", "inspect", "unresolved"]
```

The order is represented explicitly; no set or sorting operation constructs
either schema. `unresolved` remains last. Each task runs once in each arm in a
counterbalanced A/B, B/A order. The experiment plans 12 model calls and no
tool calls, because it isolates semantic classification from downstream
actuation. Accepted outputs may produce deterministic validation and plan
artifacts, but no tool is invoked by this driver.

Runtime authority is independently authored and identical across the six
semantic tasks: both `observe_presence` and `inspect` are allowed for the
exact neutral target. It cannot reveal the expected class or repair a wrong
safe classification. Evaluator expectations are in a separate manifest.

The primary paired observation is whether each task's output changes between
arms. Results must be reported per arm and as transitions, without treating a
small paired sample as a universal causal estimate.

The preregistered successor order is A/B, B/A, A/B, B/A, A/B, B/A. The
prepared artifact contains an exact counterbalance audit and a predecessor /
successor identity audit for all model-visible inputs.

Preserved V2 markers:

- `SEMANTIC_CLASSIFICATION_CORRECT=3/6`
- `PRESENCE_CORRECT=0/3`
- `INSPECT_CORRECT=3/3`
- `V2_FIRST_ENUM_MEMBER=inspect`
- `V2_OUTPUT_MATCHED_FIRST_ENUM_MEMBER=6/6`
- `ENUM_ORDER_CAUSAL_EFFECT_NOT_YET_DEMONSTRATED=true`

No qualification, production interface, prompt definition, deterministic
grammar, authority, supplier, or training state changes in this experiment.
The next decision after operator execution is
`OPERATOR_EXECUTE_SEMANTIC_ENUM_ORDER_COUNTERFACTUAL`.
