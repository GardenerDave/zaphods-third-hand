# Capability Router V1 planning and composition slice

## Outcome

`CAPABILITY_PLANNING_AND_COMPOSITION_LOOP_DEMONSTRATED=true`

Router V0 remains preserved as:

`FIRST_END_TO_END_CAPABILITY_ROUTER_LOOP=true`

V1 added packet-derived capability planning, per-capability supplier coverage,
multi-supplier registry representation, multi-supplier-type composition, and
lazy model backend initialization. It did not modify V0 artifacts or
production routing.

## Results

| Metric | Result |
|---|---:|
| Tasks correct | 10/10 |
| Capability plans correct | 10/10 |
| Complete-coverage tasks executed correctly | 7/7 |
| Incomplete-coverage tasks failed closed | 3/3 |
| Individual assignments correct on complete plans | 7/7 |
| Deterministic steps | 7 |
| Model steps/calls | 5 |
| Tool steps/calls | 0 |
| Model calls avoided | 3 |
| Unnecessary model calls | 0 |
| Unnecessary escalations | 0 |
| Duplicate supplier calls | 0 |
| Review states | 3 |
| Tasks using more than one supplier type | 5 |

The five multi-supplier-type tasks used:

```text
semantic.minimal_action_object_extraction -> MODEL
deterministic.direct_target_binding      -> DETERMINISTIC_CODE
```

The one-covered/one-unqualified edge case did not execute its covered model
step; the whole plan was incomplete and failed closed.

## Packet-derived planning

Each task was first converted through the existing triage and orchestration
packet machinery. V1 then built a runtime packet from packet inputs and
derived capabilities from those fields. The executor did not use
`expected_required_capabilities`, expected supplier annotations, expected
terminal states, expected validation, or expected call counts for planning.

The evaluator retained those fields only in scorecards for comparison.
Focused tests mutate expected capability annotations and confirm that the
derived plan is unchanged.

Every task preserves plain-file:

```text
vogon_triage_packet.json
orchestration_packet.json
runtime_packet.json
capability_plan.json
route_trace.json
scorecard.json
```

## Registry and coverage

The V1 registry is a list of evidence-linked supplier records and is indexed as
`capability_id -> list[supplier record]`. Duplicate capability IDs are retained
and tested with a synthetic in-memory second supplier. Selection discards
`NOT_QUALIFIED` and `UNKNOWN` candidates and chooses only an explicit
`QUALIFIED_EXPLORATORY` candidate. No routing-cost score or unsupported
probability was invented.

Coverage is task-wide: one covered capability cannot mask another uncovered
capability. The three incomplete tasks reached `ready_for_review` without
model, tool, or deterministic execution steps.

## Lazy backend and tool boundary

Planning precedes backend initialization. This run had five planned model
steps, so the Qwen3 1.7B runtime and GTX1650 telemetry were initialized. The
model-free test suite verifies that plans with no model steps do not invoke a
backend initializer, including when that initializer would be unavailable.

The registry supports a first-class `TOOL` supplier record shape, but no
genuine read-only tool was available or executed:

```text
TOOL_SUPPLIER_INTERFACE_SUPPORTED=true
TOOL_SUPPLIER_BRANCH_DEMONSTRATED=false
```

## Runtime and resources

- Supplier: Qwen3 1.7B-labeled / 2.032B operative
- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Operative parameters: `2031739904`
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`
- Effective/training context: `32768/32768`
- GPU: GTX 1650, `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`
- Model-route latency mean/median/p95: 2020.946 / 2001.261 / 2199.958 ms
- Model-route gross energy: 291.9275 J total; 58.3855 J mean per call
- V100/30B calls: 0; external calls: 0

These are descriptive device-only measurements, not causal supplier claims.

## Execution invariants

- Supplier model calls: 5
- Teacher calls: 0
- Retries: 0
- Escalations: 0
- Adaptations: 0
- Automatic qualification promotion: false
- Production routing changed: false

## Provenance

- V0 authoritative closeout: `ba2da0864d4ba29d5826ebe08edbcb039dd13bf8`
- V1 freeze commit: `47bb46655b8e87bc6d7fffd906928f68b0062869`
- Run directory: `.work/capability_router_v1/run_20260822T110000Z/`
- Run manifest SHA256: `6ed9d36e20290b3f26ea52e2fdfe42be3ec806a177442dfd33ea53acca64e111`
- V1 task manifest SHA256: `see matrix artifact`
- V1 registry SHA256: `see matrix artifact`

## Interpretation

This is a capability-planning and composition result, not a generalized-agent
capability claim. The next boundary is:

`NEXT_DECISION=ADD_BOUNDED_TOOL_SUPPLIER_AND_ITERATIVE_OBSERVATION`

That step is not executed here.
