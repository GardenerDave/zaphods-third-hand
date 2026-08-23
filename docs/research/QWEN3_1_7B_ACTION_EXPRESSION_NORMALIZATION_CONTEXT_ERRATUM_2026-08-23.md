# Action-expression normalization context erratum

This additive erratum preserves the completed action-expression normalization
experiment and corrects its bounded implementation context.

The prior normalizer accepted `request_context` but did not use it. The frozen
rules described `find` and `exists` as presence expressions only within a
bounded presence-query family, so the implementation now derives one of four
explicit contexts from the request grammar: presence, direct operation,
ambiguous, or unsupported/unknown. Presence expressions normalize to
`observe_presence` only in presence context; direct operations remain distinct;
unknown and coordinated operations fail closed.

This is a model-free harness correction. It does not replay or rescore the
completed 12-call run. The historical execution and closeout driver hashes and
all raw evidence remain preserved in that run's artifacts.

Preserved historical interpretation:

- `ACTION_EXPRESSION_INTERFACE_DEMONSTRATED=true` means schema/structural
  success only.
- `ACTION_EXPRESSION_SCHEMA_CONTRACT_DEMONSTRATED=true`.
- `ACTION_EXPRESSION_SEMANTIC_EXTRACTION_DEMONSTRATED=false`.
- `ACTION_EXPRESSION_SUPPLIER_FLOOR_DEMONSTRATED=false`.
- `INTERFACE_EFFECT_NOT_YET_ISOLATED=true` before the paired experiment.

The paired attribution experiment uses the corrected normalizer identically for
the old `action` and new `action_expression` interfaces.
