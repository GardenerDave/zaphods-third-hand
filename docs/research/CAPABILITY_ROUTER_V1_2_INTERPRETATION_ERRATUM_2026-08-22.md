# Router V1.1 planning-grounding interpretation erratum

The preserved V1.1 result remains valid for its stated boundary:

- `ORACLE_FREE_RUNTIME_VALIDATION_DEMONSTRATED=true`;
- runtime evaluator-field reads were zero;
- separate evaluator closeout produced 8/8 task correctness;
- complete coverage executed 6/6 and incomplete coverage failed closed 2/2.

The V1.1 `planner_facts.json` artifact, however, copied world-fact fields such
as `semantic_request_shape`, `requires_target_binding`,
`requires_reference_entity`, `requires_tool_observation`, and
`tool_capability_id`. `derive_required_capabilities()` consumed those fields
directly. They are planner annotations, not independent environmental truth.

The corrected interpretation is additive:

```text
CANONICAL_FACT_GROUNDED_CAPABILITY_PLANNING_DEMONSTRATED=true
CAPABILITY_PLAN_DERIVED_FROM_VOGON_PACKET_CONTENT=false
PLANNER_HINT_FREE=false
```

V1.2 tests whether capability requirements can instead be derived from raw
request and actual packet content plus legitimate environment facts. The
historical V1.1 artifacts and run are not rewritten or rescored.
