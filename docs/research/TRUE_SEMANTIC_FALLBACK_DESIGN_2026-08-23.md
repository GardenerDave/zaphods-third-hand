# First genuinely necessary semantic fallback

This is a fresh bounded experiment following the model-free necessity audit at
`6176921`. It preserves prior runs and introduces a new experimental capability:
`semantic.bounded_operation_classification`.

## Scientific question

Can the 1.7B supplier classify a genuinely unresolved operation class when code
has already established one safe target, no risk, no ambiguity, and at least two
bounded operation classes remain plausible?

The six true-fallback tasks use fresh paraphrases outside the frozen
deterministic operation grammar. Three express presence observation and three
express inspection. Two deterministic controls and two fail-closed controls
prove that model routing is conditional.

## Responsibility split

Deterministic code owns target extraction, risk and ambiguity checks, eligibility,
authority, capability coverage, tool selection, and terminal validation. The
model emits exactly one enum field:

```json
{"operation_class_candidate":"observe_presence|inspect|unresolved"}
```

It does not emit a target, supplier, tool, authority, success, or terminal state.
The model result is admissible only if it is a valid enum member and one of the
preflight candidate classes.

## Frozen eligibility

Model routing requires all of:

- exactly one safely extracted target;
- safe bounded request with no risky/unsupported operation;
- no multi-operation or multi-target ambiguity;
- unresolved deterministic operation derivation;
- both `observe_presence` and `inspect` remaining plausible.

Polite wrappers are not used to create eligibility. Existing deterministic
operation rules are not changed after inference.

## Execution and interpretation

Presence classifications may use the existing exact-target read-only observer.
Inspect classifications are authority-valid but must fail closed with
`NO_QUALIFIED_EXECUTION_SUPPLIER`; no inspect actuator is added. Routing
correctness, execution-path completeness, and terminal success are scored
separately.

Runtime and evaluator manifests are physically separate. Runtime code does not
read expected values. Qualification remains `false` and the registry entry is
`EXPERIMENTAL_CANDIDATE`.
