# Failure diagnosis -> bounded teaching intervention V0

This exploratory slice uses the preserved `composition-v0-003` failure from
the first MODEL -> TOOL composition run. The raw failure remains immutable.

The experiment separates deterministic localization, one local 30B diagnostic
teacher call, one experimental prompt patch, and a fresh paired 1.7B holdout.
The teacher cannot solve the repository task, call tools, grant authority,
change the registry, weaken validation, or modify weights. The patch is a
candidate artifact only; qualification and promotion remain supervised.

The student arms use the existing two-string `action` /
`object_expression` interface. Eight fresh tasks are run once with the frozen
baseline prompt and once with the same prompt plus the validated patch: four
operation-versus-state-predicate tasks and four direct-operation controls.

The primary comparison is targeted action accuracy, state-predicate-as-action
errors, invalid contracts, and control-regime regression. No end-to-end tool
confirmation is required to score the semantic intervention.

## Provenance boundary

The teacher packet contains the preserved request, actual response, validator
diagnostics, interface/schema, and two prior passing examples. It contains no
fresh holdout material. The student runtime reads no evaluator answer keys.

`qualification_change=false` is frozen for the entire experiment.
