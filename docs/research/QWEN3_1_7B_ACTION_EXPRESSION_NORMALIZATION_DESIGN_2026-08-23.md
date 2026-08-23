# Action-expression -> deterministic operation normalization V0

This experiment separates the language-facing expression from the operation
used by authority and routing code. The supplier emits:

```json
{"action_expression":"...", "object_expression":"..."}
```

Deterministic code maps the exact, case-folded action expression to one frozen
canonical operation. No fuzzy matching, embeddings, substring fallback, or
teacher patch is used.

## Frozen canonical vocabulary

- `observe_presence`: determine, check, verify, confirm, find, exists, when
  used as a bounded presence-observation expression;
- `inspect`: inspect;
- `amend`: amend;
- `index`: index;
- `dispatch`: dispatch.

The presence mappings are deliberately bounded to the experiment's
presence-observation request family. `exists` is a state predicate, not a
surface operation verb, but it can represent the same downstream presence
observation in that bounded context. The canonical authority token remains
`observe_presence`; raw model text never grants authority.

Exact multi-operation expressions return `AMBIGUOUS`. Empty, unknown, or
unsupported expressions return `UNRESOLVED`. No nearest operation is chosen.

## Historical projection

The baseline outputs from the completed teaching holdout are projected
additively before new inference. This does not change historical exact-action
scores. The projection asks whether deterministic canonicalization would have
preserved useful downstream meaning despite lexical variation.

## Fresh holdout

Twelve fresh tasks are evaluated once with the renamed two-string interface:
four presence requests, four direct-operation controls, two ambiguous requests,
and two unsupported requests. The primary metric is canonical operation
correctness; exact surface expression is secondary.

Authority records contain canonical operation sets independently of model
output. A normalized operation is checked against that set, and ambiguous or
unresolved results fail closed. `MODEL_OUTPUT_GRANTED_AUTHORITY=0` is frozen.

No end-to-end tool confirmation is included in this slice; it is optional only
after this boundary is independently supported.
