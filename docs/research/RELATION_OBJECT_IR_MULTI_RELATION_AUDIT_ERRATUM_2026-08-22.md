# Additive audit: relation-object IR representation versus supplier extraction

This note preserves the completed fresh multi-relation result and does not
modify or rescore any historical response, validator, scorecard, aggregate, or
matrix.

## Representation versus supplier capability

The prior model-free projection established that the three-field relation
representation (`action`, `direct_object`, `reference_entity`) can represent
all eight frozen semantic cases and reproduce the expected deterministic
selection 8/8. That establishes representation adequacy for those cases, not
supplier extraction success.

Additive interpretation:

`RELATION_OBJECT_IR_REPRESENTATION_SUPPORTED=true`

`QWEN3_1_7B_MULTI_RELATION_IR_EXTRACTION_SUPPORTED=false`

The fresh supplier result remains unchanged: all-six exact 0/8, deterministic
selection 5/8, evaluable 5/8, ambiguous 3/8, with parse/contract 8/8.

## Failure breadth audit

Preserved fresh outputs show:

- action-field failures: 4 field errors across 2 tasks;
- direct-object failures: 6 field errors across 5 tasks;
- reference-entity failures: 9 field errors across 6 tasks;
- relation-order failures: 2 tasks (`fresh-relation-004`,
  `fresh-relation-006`);
- collapsed/missing relation: 1 task (`fresh-relation-006`);
- multiple direct-target bindings: 3 tasks (`fresh-relation-003`,
  `fresh-relation-004`, `fresh-relation-007`).

Therefore the failure is not reference-entity-only. The narrow supported
hypothesis is:

`MULTI_RELATION_EXTRACTION_OVERLOAD_CANDIDATE=true`

This is a hypothesis, not a causal conclusion. The next atomic question removes
the multi-relation composition burden without changing the three-field IR.

`NEXT_DECISION=ISOLATE_SINGLE_RELATION_EXTRACTION`

No model calls were made for this audit.
