# Capability Router V1.2 packet-derived planning slice

## Result

`PACKET_DERIVED_CAPABILITY_PLANNING_DEMONSTRATED=true`

The slice demonstrates a planning boundary distinct from V1.1 validation:
capability requirements were derived from raw requests, actual triage and
orchestration packet content, and legitimate environment facts without
planner-annotation inputs.

The preserved V1.1 result remains:

`ORACLE_FREE_RUNTIME_VALIDATION_DEMONSTRATED=true`

No historical artifact was modified or rescored.

## Corrected V1.1 interpretation

V1.1 consumed planner-like fields from `world_facts` even though its runtime
validator read zero evaluator fields. Those fields were planner annotations,
not environmental truth. The additive correction is:

```text
CANONICAL_FACT_GROUNDED_CAPABILITY_PLANNING_DEMONSTRATED=true
CAPABILITY_PLAN_DERIVED_FROM_VOGON_PACKET_CONTENT=false
PLANNER_HINT_FREE=false       # V1.1 boundary
PLANNER_HINT_FREE=true        # V1.2 runtime input boundary
```

## Packet inventory

The reused triage/orchestration packets expose `task_type`, allowed and held
targets, risk flags, output contract, validation hooks, review state,
authority boundaries, and provenance. They do not expose a canonical
action/object parse or a capability list.

V1.2 uses those packet fields, the raw request, and independent
`environment_facts`. It extracts a uniquely named request target with a
bounded deterministic adapter. It does not add `requires_*`, semantic-shape,
tool-ID, or expected-route fields to runtime input.

## Results

| Metric | Result |
|---|---:|
| Planner hint input fields | 0 |
| Runtime evaluator-field reads | 0 |
| Packet-content-affected-planning test | true |
| Capability requirements matched | 8/8 |
| Complete-coverage plans | 6/6 |
| Incomplete-coverage plans | 2/2 |
| Capability assignments matched on complete plans | 6/6 |
| Terminal successes | 3/8 |
| Review states | 5/8 |
| Model calls | 4 |
| Deterministic steps | 6 |
| Tool steps/calls | 0 |
| Oracle-corruption invariant tests | 8/8 |

The six complete plans were the two deterministic plans and four
MODEL-plus-`DETERMINISTIC_CODE` compositions. The reference-entity capability
and repository-observation capability were derived but uncovered by the
current registry, so they failed closed without model or tool calls.

The runtime evaluator result was 5/8 because the supplier returned the exact
object expression for one semantic task but appended words such as `record`,
`artifact`, or `entry` on three others. The conservative equality contract
correctly routed those three to review. This is a bounded supplier/interface
result, not a planner-derivation failure.

## Derivation accounting

- deterministic packet derivations: 6;
- semantic interpretations: 5 (four minimal action/object requirements and
  one reference-entity requirement);
- environmental requirements: 1 (current repository observation);
- unresolved derivations: 0;
- uncovered qualified supplier routes: 2.

Every plan and requirement derivation carries packet/environment provenance.
Execution steps retain `step_id`, `requires_inputs`, `produces_outputs`,
`depends_on`, and input provenance. Success contracts contain no worked answer.

## Adversarial controls

Prepared runtime artifacts contain zero occurrences of the forbidden input-side
planner fields: `semantic_request_shape`, `requires_target_binding`,
`requires_reference_entity`, `requires_tool_observation`, `tool_capability_id`,
and `required_capabilities`. The latter appears only as the derivation/plan
output field.

Changing evaluator expectations does not change planner facts, plans, or
runtime execution. Changing the legitimate packet `task_type` changes the
semantic plan to an incomplete plan, proving packet content participates in
planning rather than merely being copied into provenance.

## Resources and boundaries

- Supplier: Qwen3 1.7B-labeled / 2.032B operative;
- model-route latency mean/median/p95: `2156.967 / 2121.127 /
  2366.731 ms` (inclusive percentile over four calls);
- gross device-only energy mean/median/total: `60.644 / 61.868 / 242.578 J`;
- teacher calls: 0; retries: 0; escalations: 0;
- V100/30B calls: 0; tool calls: 0; external calls: 0;
- production routing and qualification state: unchanged.

Measurements are descriptive Level-2 GTX1650 `gpu_device_only` observations,
not causal claims.

## Provenance and next boundary

- authoritative V1.1 closeout: `91a3fdf5dc6be9aafc63426a99b964dbbea6ba5f`;
- V1.2 freeze: `904820514c4103fc3c6acf4cdd90aec33fe09970`;
- run directory:
  `.work/model_size_supplier_floor/capability_router_v1_2_packet_planning/run_20260822T161315Z/`;
- run manifest SHA256:
  `472de9470c7a61ffd8eb379991da78018c914c621216dbd1d02c89461be42b75`.

The planning/grounding boundary is demonstrated. The next exploratory
boundary remains:

`NEXT_DECISION=ADD_BOUNDED_TOOL_SUPPLIER_AND_ITERATIVE_OBSERVATION`

That step is not executed here.
