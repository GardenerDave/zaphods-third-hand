# Relation-object intermediate representation design

Status: model-free exploratory refinement; no inference executed.

This design follows the action-object relation probe and addresses the
observed conflation between a direct semantic object and an explicitly named
parent/reference entity. It does not rescore the completed supplier run.

## Relation shape

Each action relation is represented as exactly:

```text
action
direct_object
reference_entity
```

`action` is the expressed operation. `direct_object` is the thing directly
acted upon. `reference_entity` is an explicitly named entity that the direct
object belongs to, comes from, describes, is contained by, or is otherwise
anchored to. It is an empty string when no separate reference entity is
expressed.

The requested target remains an external deterministic input. It is not an
output field and is not inferred by the model in this representation.

## Deterministic target selection

For each relation:

```text
DIRECT_TARGET_BINDING =
    normalized(direct_object) == normalized(requested_target)
```

`reference_entity` equality alone never establishes direct target binding.

- exactly one direct match: select that relation's `action`;
- zero direct matches: return `NO_DIRECT_TARGET_BINDING` and no operation;
- multiple direct matches: return `AMBIGUOUS_DIRECT_TARGET_BINDING` and no
  operation.

The policy is implemented model-free in
`scripts/zth_relation_object_ir.py`.

## Projection of the completed eight fixtures

The old sentences can be represented cleanly with this three-field relation
shape. The model-free projection is recorded in
`RELATION_OBJECT_IR_PROJECTION_2026-08-22.json` and yields:

`RELATION_OBJECT_IR_REPRODUCES_EXPECTED_SELECTION=8/8`

This is an analysis-only projection. It neither changes the old output
ontology nor rescoring of the eight supplier responses.

## Architectural boundary

The emerging router flow is:

```text
natural language
  -> entities + actions + object/reference relations
  -> canonical task IR
  -> deterministic computation and capability routing
```

The model extracts semantic representation. Downstream deterministic code
owns canonicalization, direct-target matching, policy composition, supplier
selection, and escalation handling. This experiment does not modify the Vogon
Printer or production routing.
