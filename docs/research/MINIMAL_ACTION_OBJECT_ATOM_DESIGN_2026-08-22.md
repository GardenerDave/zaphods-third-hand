# Minimal action-object atom probe

Status: frozen exploratory design; no inference executed at freeze time.

## Question

Can the Qwen3 1.7B-labeled / 2.032B operative supplier extract only the two
decision-critical semantic operands from one clause:

```text
action
direct_object
```

The supplier does not emit `reference_entity`, a requested target, a boolean,
or any authorization, scope, membership, routing, supplier, escalation, or
policy decision.

## Contract and interface

The output object contains exactly two strings: `action` and `direct_object`.
The prompt is declarative and defines the fields without an imperative
instruction verb that could be emitted as the action.

## Fresh balanced tasks

There are 8 fresh clauses: 4 `DIRECT_ENTITY_OBJECT` and 4
`SUBOBJECT_WITH_REFERENCE`. Four fresh action verbs each appear once in both
regimes. The mentioned entity is retained only as model-free analysis metadata
and is not in the output contract.

The subobject regime tests distinguishing the directly acted-upon object from
another named entity without requiring reference-entity extraction.

## Deterministic analysis

For analysis only, a frozen requested target is set to the expected direct
object in direct-entity cases and to the mentioned entity in subobject cases.
Observed direct-target binding is then computed by deterministic equality. The
model does not emit this boolean.

This probe isolates the proposed decision-critical atom from optional semantic
enrichment and does not modify routing or the Vogon Printer.
