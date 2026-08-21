# Scope field-name isolation

Exploratory, candidate-only, not Stage B evidence.

This paired screen reuses the exact 16-task crossed scope manifest and the
single-predicate representation. It changes only the output field label:
`scope_expansion_required` in Arm S versus `decision_flag` in Arm N. The
predicate sentence order and held-target clarification are unchanged. The two
schemas are structurally identical apart from that property/required-field
label and use the same neutral JSON-schema wrapper name.

Frozen task manifest SHA256:
`2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`.

Frozen single-predicate text SHA256:
`e4f8ed438ccd3fca6d660e4575ce8f3c8931c5818cedc2b21da8869015df21c3`.

The run uses 32 calls: each task in both arms, with eight S→N and eight N→S
temporal orders assigned by a deterministic hash. There are no teachers,
retries, escalations, or adaptive changes. Both schemas permit TRUE and FALSE;
neither contains a default, const, example, or enum.

If the neutral field materially restores balanced performance, a deterministic
post-inference rename could be studied separately as protocol adaptation. This
probe itself does not implement such a conversion or change routing.
