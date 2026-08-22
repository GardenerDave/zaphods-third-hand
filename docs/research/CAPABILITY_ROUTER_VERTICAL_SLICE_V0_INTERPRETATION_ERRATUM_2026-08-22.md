# Additive Router V0 interpretation erratum

This note preserves the completed Router V0 run and corrects terminology for
the next slice. V0 remains successful evidence:

- deterministic/no-model branch: 2/2;
- bounded Qwen3 1.7B branch: 4/4;
- fail-closed unsupported branch: 2/2;
- terminal task correctness: 8/8;
- supplier-class choice: 8/8;
- unnecessary model calls: 0.

The following were implementation boundaries of V0, not failures of that
result:

```text
CAPABILITY_PLAN_DERIVED_FROM_PACKET=false
MULTI_SUPPLIER_PER_CAPABILITY_SUPPORTED=false
ALL_REQUIRED_CAPABILITIES_COVERAGE_ENFORCED=false
MODEL_RUNTIME_LAZY=false
TOOL_SUPPLIER_BRANCH_DEMONSTRATED=false
```

V0's prepared manifest used `expected_deterministic_calls=0`, while its
terminal lifecycle recorded `deterministic_calls=2`. The prepared field was a
planned-call placeholder and was not a count of deterministic execution
steps; the terminal lifecycle is the authoritative observed count. Router V1
uses unambiguous `planned_model_calls`, `planned_tool_calls`, and
`planned_deterministic_steps` fields.

No V0 raw run, scorecard, route trace, or matrix was modified.
