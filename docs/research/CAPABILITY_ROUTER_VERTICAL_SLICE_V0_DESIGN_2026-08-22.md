# Capability Router Vertical Slice V0

Status: frozen exploratory router design; not production routing.

## Purpose

This slice exercises the first bounded ZTH capability-router control loop:

messy request -> existing triage/orchestration packets -> required capability
-> evidence-linked supplier registry -> deterministic code, bounded model, or
review -> validation -> plain-file route trace and scorecard.

It does not grant authority, modify production routing, promote capabilities,
touch the V100/30B runtime, or perform destructive tool work.

## Reused repository components

- `local_harness.triage_router_rules.route_messy_input` creates the existing
  bounded Vogon Printer/triage packet.
- `local_harness.orchestration_packet.assemble_orchestration_packet` and
  `validate_orchestration_packet` preserve the existing orchestration packet,
  review requirement, and authority boundaries.
- `local_harness.prompt_patch_library.PromptPatchLibrary` loads the existing
  `examples/prompt_patches` library.
- `scripts.zth_qwen3_1_7b_minimal_action_object_atom` runtime bindings and
  `scripts.zth_qwen3_1_7b_atomic_scope_relation_decomposition.structured_call`
  provide the frozen local model transport and structured call.
- Existing Level-2 GTX1650 device-only telemetry is used for model calls.

The adapter adds only router-specific capability decomposition and route
traces around these components. It does not replace the canonical packet
schemas.

## Supplier model

The model path exposes only the bounded two-string semantic atom:

```json
{"action":"...","object_expression":"..."}
```

The router compares `object_expression` to the already-known requested target
using conservative normalized equality. It does not use substring, fuzzy, or
model-based equality. A non-match fails closed for this slice.

## Experimental capability registry

The registry is evidence-linked and uses `QUALIFIED_EXPLORATORY`,
`NOT_QUALIFIED`, and `UNKNOWN`. It does not use production-readiness or
autonomy claims and never changes status automatically.

Qualified exploratory paths:

- deterministic normalization/equality/boolean composition;
- minimal action extraction through the Qwen3 1.7B-labeled / 2.032B operative
  supplier, bounded to the tested interface;
- deterministic direct-target binding.

Not qualified:

- richer reference-entity extraction;
- multi-relation six-field extraction.

## Fixture branches

The frozen matrix contains 2 deterministic/no-model fixtures, 4 direct-entity
semantic-model fixtures, and 2 unsupported-capability fixtures. The first
branch must make zero model calls. The second uses only the exposed 1.7B
endpoint and then validates deterministically. The third reaches
`ready_for_review` without improvising or calling a stronger supplier.

## Success condition

The slice succeeds when all three control-flow branches are observed in
inspectable traces: deterministic routing with zero model calls, bounded model
routing with deterministic validation, and fail-closed review routing for an
unqualified capability.

## Non-goals

No production routing change, automatic qualification promotion, destructive
tool action, external call, teacher call, V100/30B call, SSH/admin grant, or
generalized-agent claim is in scope.
