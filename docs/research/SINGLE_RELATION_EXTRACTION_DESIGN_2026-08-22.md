# Single-relation extraction probe

Status: frozen exploratory design; no inference executed at freeze time.

## Question

Can the Qwen3 1.7B-labeled / 2.032B operative supplier extract one
`action`, `direct_object`, and `reference_entity` reliably when the
multi-relation composition burden is removed?

## Contract

The model receives one short clause and returns exactly three strings:

`action`, `direct_object`, and `reference_entity`.

The schema has no arrays, nested objects, booleans, enums, examples, defaults,
or decision fields. An empty string represents no separate reference entity.

The prompt defines the three factual fields but asks for no target binding,
authorization, scope, membership, routing, escalation, or policy judgment.

## Fresh balanced tasks

The 8-task manifest contains four `DIRECT_ENTITY_OBJECT` clauses and four
`SUBOBJECT_WITH_REFERENCE` clauses. Each of four action verbs appears once in
each regime, so action identity cannot predict regime. The exact task set is
frozen in `SINGLE_RELATION_EXTRACTION_TASKS_2026-08-22.json`.

## Interpretation

This probe isolates atomic factual extraction. It does not alter the IR ontology
and does not test deterministic target binding or multi-relation composition.
If both regimes are strong, a later experiment may test whether packing
multiple reliable atoms into one call causes the prior degradation.
