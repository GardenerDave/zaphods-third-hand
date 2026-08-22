# Action-object relation extraction probe

Status: frozen exploratory design; no inference executed at freeze time.

## Purpose

The preceding target-bound action probe showed partial scalar action-head
selection. This probe separates local relation extraction from selecting which
relation is relevant.

The supplier extracts two factual action/object relations in sentence order:
`action_1 -> object_1` and `action_2 -> object_2`. It is not asked which
operation matters, which action is target-bound, or any authorization, scope,
membership, review, or policy question.

The requested target is frozen outside the model prompt. Deterministic code
selects the unique extracted relation whose object equals that target. Zero
matches are unevaluable; multiple matches are ambiguous.

## Frozen design

There are eight fresh tasks in four matched role-reversal pairs. Each pair uses
one target and the same two action verbs. Both verbs occur in both roles across
the pair, while clause order and target position vary. The exact sentences and
expected relations are frozen in
`ACTION_OBJECT_RELATION_EXTRACTION_TASKS_2026-08-22.json`.

## Contract and analysis

The schema requires exactly four strings: `action_1`, `object_1`, `action_2`,
and `object_2`. There are no examples, enums, booleans, or answer cues.

Score all four relation fields independently. Then deterministically compare
objects with the frozen requested target and select the matching action. The
probe reports relation correctness, selected-operation correctness,
evaluable/unevaluable/ambiguous selection, pairwise reversal, and whether
extraction errors are contained by deterministic selection.

This is an interface/decomposition experiment only. The emerging router
intermediate representation is:

`natural language -> semantic entities and relations -> deterministic computation`
