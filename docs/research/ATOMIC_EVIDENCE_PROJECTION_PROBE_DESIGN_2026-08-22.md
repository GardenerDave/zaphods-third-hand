# Atomic evidence-projection probe design

This is a fresh exploratory candidate-only probe using the already frozen
independent authorization-atoms factorial tasks. It does not rerun or alter
the completed independent-factorial inference and does not create Stage B
evidence.

## Question

Does hiding irrelevant evidence from each atomic call remove the observed
cross-factor interference?

The frozen task manifest is
`docs/research/INDEPENDENT_AUTHORIZATION_ATOMS_FACTORIAL_TASKS_2026-08-22.json`
with SHA256
`6973c9e4d61eaf647ee846c47ebaf0fa9efffcec6bfc92072f93c349e88874f8`.
Expected values, task IDs, factorial labels, and deterministic composition are
unchanged.

## Projection

The target arm exposes only the allowed-target set and requested target, then
asks whether the requested target is present. It omits allowed operations,
requested operation, held distractors, and factor labels.

The operation arm exposes only the allowed-operation set and requested
operation type, then asks whether the operation type is present. It omits
allowed targets, requested target, held distractors, and factor labels.

Both arms use structure-only boolean schemas with no default, const, enum,
example, or worked value. The deterministic final rule remains:

`scope_expansion_required = NOT (target_allowed AND operation_allowed)`.

The model-free audit requires zero irrelevant-factor leakage and a frozen 8/8
target→operation versus operation→target order split. Execution is 32 calls,
with no teacher, retry, escalation, or adaptation.
