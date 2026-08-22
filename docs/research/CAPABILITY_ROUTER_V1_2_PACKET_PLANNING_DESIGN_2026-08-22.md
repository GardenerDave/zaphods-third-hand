# Capability Router V1.2 packet-derived planning slice

Status: frozen exploratory design; not production routing.

## Question

Can the router derive capability requirements from the raw request, actual
Vogon/triage and orchestration packets, and legitimate environment facts
without receiving fixture-level planner annotations?

This is separate from the already demonstrated V1.1 oracle-free runtime
validator.

## Runtime categories

Runtime preparation contains:

- `input_request` and actual triage/orchestration packets;
- `environment_facts`, limited to independently available authority or current
  state records;
- derived `planner_facts`, capability requirement derivations, plans, and
  success contracts.

Evaluator expectations are written separately and are never read by runtime
planning or execution.

The forbidden input-side planner-hint fields are:
`semantic_request_shape`, `requires_target_binding`,
`requires_reference_entity`, `requires_tool_observation`,
`tool_capability_id`, and `required_capabilities`. A `required_capabilities`
field may appear only as the output of the derivation stage.

## Packet inventory

The existing packets provide usable `task_type`, `allowed_targets`,
`held_targets`, `risk_flags`, `output_contract`, `validation_hooks`,
`review_required`, `authority_boundaries`, and request provenance. They do not
provide a canonical action/object semantic parse or a capability list.

V1.2 therefore uses a small deterministic adapter: it extracts a uniquely
named target token from bounded request text, consumes allowed operations from
an independent authority record, and uses packet task type/request language to
identify whether semantic interpretation or current observation is required.
If that bounded derivation is not justified, the requirement is unresolved and
the plan fails closed.

## Requirement derivation

Every proposed capability is recorded in
`capability_requirement_derivation.json` with derivation type, source
artifacts, source fields, and reason. Derivation types are:

- `DETERMINISTIC_PACKET_RULE`;
- `SEMANTIC_INTERPRETATION`;
- `ENVIRONMENTAL_REQUIREMENT`;
- `UNRESOLVED`.

The planner never consumes evaluator expected routes or supplier IDs.

## Composition and contracts

Plans retain explicit `step_id`, `requires_inputs`, `produces_outputs`,
`depends_on`, and input provenance. Semantic extraction produces `action` and
`object_expression`; deterministic target binding consumes those values and a
request-derived target. Canonical authority operands are handled by
deterministic code. A current-state observation request is mapped to the
existing tool capability ID only as a derivation result; no tool is qualified,
so it fails closed.

Success contracts validate observations and packet/environment constraints,
not worked answers. Runtime execution and evaluator scoring remain separate.

## Frozen matrix

The eight fresh tasks contain two canonical deterministic requests, four
bounded semantic requests, one unresolved reference-entity request, and one
current-state observation request with no qualified tool. No task contains
planner annotation fields in its runtime input.

## Boundaries

No model is initialized for deterministic or unresolved/review-only plans.
Only justified semantic model steps may run. No tool executes in this slice;
no production routing, qualification promotion, V100/30B use, external call,
destructive action, or SSH/admin authority is introduced.

Success markers:

```text
PACKET_DERIVED_CAPABILITY_PLANNING_DEMONSTRATED=true
ORACLE_FREE_RUNTIME_VALIDATION_DEMONSTRATED=true
NEXT_DECISION=ADD_BOUNDED_TOOL_SUPPLIER_AND_ITERATIVE_OBSERVATION
```
