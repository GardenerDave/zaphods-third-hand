# Generic Boolean Selection Prior Probe

Exploratory calibration; not scope evidence, Stage B evidence, or production
routing authority.

## Question

The neutral constrained scope probe produced valid objects but selected TRUE
16/16. This calibration tests whether that behavior generalizes to arbitrary
boolean selection, while separately reversing rule-clause order to detect
primacy.

## Tasks and arms

Sixteen fresh atomic tasks contain only one arbitrary marker fact: eight
contain `KAPPA-7` and eight contain `LAMBDA-4`. The neutral field is
`decision_flag`. The expected mapping is true for KAPPA-7 and false for
LAMBDA-4.

Every task runs under both arms:

- TF: true/KAPPA-7 clause first, false/LAMBDA-4 clause second;
- FT: the identical mapping with those two clauses reversed.

The expected value is identical task-by-task across arms. No scope or
authority semantics appear in task content, the field name, the mapping, or
the output instruction.

## Structure-only output constraint

The natural-language instruction is value-neutral and includes no worked JSON
object. The external JSON Schema requires exactly one boolean field,
`decision_flag`, with no default, const, example, examples, or enum. Both
boolean values are allowed.

## Ordering and execution

Each task runs in one of two frozen orders, TF→FT or FT→TF. Eight tasks use
each order, assigned by SHA256 parity of the fixed seed
`zth-generic-boolean-order-v1` plus task ID. There are 32 calls total, with no
teacher, retry, escalation, adaptation, or production change.

## Interpretation

Report per-arm boolean selection, marker-conditioned accuracy, confusion
matrices, and task-paired order transitions. This calibration does not itself
rescore any prior scope run.
