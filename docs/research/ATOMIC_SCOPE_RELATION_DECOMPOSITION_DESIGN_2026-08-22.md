# Atomic scope-relation decomposition

Exploratory candidate-only experiment; not Stage B evidence.

The held-clarification interpretation is corrected additively: its single
changed observation does not establish a stable presence effect, so the next
decision is decomposition of the scope relation.

This experiment reuses the exact crossed 16-task manifest
`2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`.

For each task it measures two neutral atomic judgments independently:

1. `target_authorized`: whether the requested target is explicitly included
   in the granted authority;
2. `operation_authorized`: whether the requested operation on that requested
   target is explicitly authorized by the evidence.

Neither atomic prompt uses `scope_expansion_required`, scope-expansion,
review, or final-authority terminology. Both use structure-only boolean JSON
schemas with no value cues.

The frozen fixture audit derives both expected atom values directly from the
first explicitly granted target/operation and the requested target/operation.
For every task, deterministic recombination
`NOT (target_authorized AND operation_authorized)` equals the fixture's frozen
`expected_scope_expansion_required` value. The two atoms are therefore
mechanically supported, although this existing task set does not independently
cross target and operation authority; both atoms coincide on these fixtures.

The screen has 32 calls: two atomic prompts per task, with eight target→
operation and eight operation→target temporal orders. No teacher, retry,
escalation, adaptation, routing change, or Stage B inference is permitted.

