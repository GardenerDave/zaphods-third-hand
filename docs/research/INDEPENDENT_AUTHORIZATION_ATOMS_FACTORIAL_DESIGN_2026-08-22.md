# Independent authorization-atoms factorial probe design

This is a fresh exploratory, candidate-only probe for the Qwen3 1.7B-labeled /
2,031,739,904-operative supplier. It does not rerun or alter the completed
decomposition and does not create Stage B evidence.

## Independent atoms

- `target_allowed`: the requested target is explicitly present in the
  allowed-target set;
- `operation_allowed`: the requested operation type is explicitly present in
  the allowed-operation set.

The operation judgment is intentionally not conditioned on a target. The final
field is computed model-free as:

`scope_expansion_required = NOT (target_allowed AND operation_allowed)`.

## Factorial population

Sixteen fresh tasks cross target membership, operation-type membership, and
held-distractor presence. There are two tasks per 2×2×2 cell, eight expected
true and eight expected false values for each atom, and four tasks in each of
the four target×operation combinations. The derived scope population is
naturally four false and twelve true; analysis is cell-wise rather than based
on raw overall scope accuracy.

Each task exposes separate allowed-target and allowed-operation sets. No
target-operation pair is encoded. The atomic prompts contain no scope field,
scope-expansion question, worked boolean, default, const, example, or enum.

Execution is 32 supplier calls: one target membership and one operation-type
membership judgment per task, with a frozen 8/8 target→operation versus
operation→target order split. Teacher calls, retries, escalation, and adaptive
changes are zero.

The architecture/training-generation and 1.7B-labeled/2.032B operative
supplier confounds remain descriptive provenance, not causal size evidence.
