# Scope Rule Clause-Order Control

Exploratory interface-control experiment; not Stage B evidence and not a
model-size comparison.

## Question

The generic calibration showed that reversing a true/false clause pair can
change boolean selection. This paired control tests whether the same effect
explains the TRUE bias in the existing neutral constrained scope probe.

## Fixed inputs

The exact crossed 16-task scope manifest is reused byte-for-byte, including
task order, evidence, expected values, factor labels, and distractors. The
neutral constrained JSON Schema and value-neutral output instruction are also
reused unchanged. The same Qwen3 1.7B-labeled / 2.032B operative runtime and
Level-2 GTX 1650 telemetry are used.

## Arms

TF uses the existing semantic rule order: true clause, false clause, held-
target clarification. FT swaps only the first two clauses: false clause,
true clause, held-target clarification. The third clause is byte-identical and
last in both arms. No worked boolean object, default, const, example, or enum
is present.

## Execution

Each of the 16 tasks runs in both arms, for 32 supplier calls. Eight tasks use
TF→FT temporal order and eight use FT→TF, assigned by a frozen SHA256 parity
rule. There are no teachers, retries, escalations, or adaptations.

## Interpretation

The primary comparison is inside-authority recovery under FT while retaining
outside-authority TRUE performance. Results remain descriptive and do not
establish universal model capability or a parameter floor.
