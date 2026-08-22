# Fresh relation-object IR extraction probe

Status: frozen exploratory supplier probe design; no inference at freeze time.

## Scientific question

Test whether the Qwen3 1.7B-labeled / 2.032B operative supplier can populate a
refined three-part relation representation on fresh two-action language:

```text
action
direct_object
reference_entity
```

The supplier extracts relations only. Deterministic code compares each
`direct_object` with the already-known requested target and selects the unique
matching action. The supplier is not asked to select a relevant relation or to
make authorization, scope, membership, routing, escalation, or policy
decisions.

## Contract

The flat output object contains exactly six strings:

`action_1`, `direct_object_1`, `reference_entity_1`, `action_2`,
`direct_object_2`, and `reference_entity_2`.

`reference_entity_N` is an empty string when no separate referenced entity is
expressed. The schema has no enum, example, default, boolean, or answer field.

## Fresh balanced task set

The task manifest contains 8 fresh tasks in 4 matched role-reversal pairs. Each
pair keeps the target and two action verbs while reversing which action's
`direct_object` is the target. The target-bound relation occurs in positions 1
and 2 equally. Reference-bearing and empty-reference target relations are both
present, so empty-reference presence is not a perfect answer shortcut. Action
identity, action position, clause order, target surface placement, and
reference presence are audited before inference.

The exact frozen manifest is
`RELATION_OBJECT_IR_EXTRACTION_TASKS_2026-08-22.json`.

## Deterministic selection

```text
DIRECT_TARGET_BINDING =
    normalized(direct_object) == normalized(requested_target)
```

Reference-entity equality alone never binds. Exactly one direct match selects
the action; zero matches returns `NO_DIRECT_TARGET_BINDING`; multiple matches
returns `AMBIGUOUS_DIRECT_TARGET_BINDING`.

## Bounded architecture

```text
natural language
  -> semantic relations
  -> canonical task IR
  -> deterministic capability routing / policy computation
```

This is exploratory evidence for a candidate semantic IR only. It does not
modify the Vogon Printer, production routing, or Stage B evidence.
