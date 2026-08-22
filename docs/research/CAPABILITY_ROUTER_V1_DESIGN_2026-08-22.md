# Capability Router V1 planning slice

Status: frozen exploratory design; not production routing.

## Change from V0

V1 derives required capabilities from runtime packet facts after the existing
Vogon Printer/triage and orchestration packets are built. Fixture expectation
fields are evaluator-only and are never read by the planner or executor.

The registry is represented as a list of supplier records and indexed as:

```text
capability_id -> list[supplier record]
```

This preserves multiple suppliers for one capability. Candidates with
`NOT_QUALIFIED` or `UNKNOWN` status are uncovered rather than improvised.
Every required capability must have an independently selected qualified route
before execution can proceed.

## Reused components

V1 reuses `route_messy_input`, the triage packet schema,
`assemble_orchestration_packet`/`validate_orchestration_packet`, the existing
prompt-patch library, the local structured model-call harness, frozen Qwen3
runtime bindings, and Level-2 GTX1650 telemetry. The V1 driver is an
experimental adapter that adds packet-derived planning and route traces; it
does not replace the packet system or change production routing.

## Packet-derived planning

The adapter creates a bounded runtime packet from the request and packet facts
that are genuinely available to the route. It derives capabilities from
fields such as canonical flags, semantic request shape, target-binding need,
reference-entity need, and tool-observation need. It never reads
`expected_required_capabilities`, expected suppliers, expected terminal states,
expected validation, or expected call counts while planning.

## Coverage and composition

A complete plan may contain multiple supplier types. For example:

```text
semantic.minimal_action_object_extraction -> MODEL
deterministic.direct_target_binding      -> DETERMINISTIC_CODE
```

The plan records ordered steps, per-capability candidate lists, qualified
candidates, selected suppliers, reasons, and coverage. One covered capability
does not allow a task with another uncovered capability to proceed.

## Lazy backends

Planning occurs before backend initialization. Model listing, model runtime
binding, endpoint access, and GPU telemetry preflight occur only when the plan
contains a model step. All-deterministic and review-only workloads can run
with the model endpoint unavailable in model-free tests.

The registry describes a first-class `TOOL` supplier shape, but no genuine
read-only tool is available in this slice. Therefore:

```text
TOOL_SUPPLIER_INTERFACE_SUPPORTED=true
TOOL_SUPPLIER_BRANCH_DEMONSTRATED=false
```

## Fixture branches

V1 contains 10 fresh fixtures: 2 pure deterministic, 4 semantic plus
deterministic composition, 2 unsupported/incomplete capability cases, and 2
coverage-edge cases. The edge cases include one fully covered two-capability
plan and one plan with one qualified and one unqualified capability; the
latter must fail closed.

## Success condition

V1 succeeds when packet-derived plans cover every required capability before
execution, multi-capability composition works, incomplete coverage cannot
proceed, deterministic work remains model-free, model backends are lazy, and
route traces remain inspectable. This is not yet a generalized-agent claim.
