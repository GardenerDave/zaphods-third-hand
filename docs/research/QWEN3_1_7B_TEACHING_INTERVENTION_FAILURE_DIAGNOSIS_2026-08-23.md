# Model-free diagnosis of the first teaching intervention failure

Authoritative closeout: `9d031192a1d96b9acb9c7ea503e139a1e304cb0e`.

This is an additive audit only. No historical response, validator, scorecard,
prompt, or closeout was modified or rescored.

## Diagnosis

The preserved seed supports the teacher's bounded mechanism diagnosis:
`exists` is a state predicate, while the frozen semantic action contract is
validated against an operation vocabulary. The failure was correctly
localized to the `action` field before tool planning.

The teacher's intervention was different from its diagnosis. The patch said:

> When the request clause involves checking for the presence of a file path,
> the action must be `check` instead of `exists`.

and explicitly mapped `determine` to `check`. On the patched arm, every one of
the eight outputs was `check`, including direct-operation controls. This is
observed intervention overgeneralization, not evidence that the teacher's
mechanism diagnosis was wholly wrong.

## Per-task reconstruction

| Task | Regime | Expected | Baseline action / object | Patched action / object | Baseline exact | Patched exact | Baseline failure | Patched failure | Safe binding B/P |
|---|---|---|---|---|---:|---:|---|---|---|
| 001 | presence | determine / alpha | exists / alpha | check / alpha | no | no | STATE_PREDICATE_AS_ACTION | OTHER_ACTION_FAILURE | no / yes |
| 002 | presence | check / beta | check / beta | check / beta | yes | yes | — | — | yes / yes |
| 003 | presence | verify / gamma | find / gamma | check / gamma | no | no | OTHER_ACTION_FAILURE | OTHER_ACTION_FAILURE | no / yes |
| 004 | presence | confirm / delta | confirm / delta | check / delta | yes | no | — | OTHER_ACTION_FAILURE | yes / yes |
| 005 | control | inspect / epsilon | inspect / epsilon | check / file path | yes | no | — | OBJECT_EXPRESSION_FAILURE | yes / no |
| 006 | control | amend / zeta | Amend / zeta | check / file path | no | no | OTHER_ACTION_FAILURE | OBJECT_EXPRESSION_FAILURE | no / no |
| 007 | control | index / eta | Index / eta | check / eta | no | no | OTHER_ACTION_FAILURE | OTHER_ACTION_FAILURE | no / yes |
| 008 | control | dispatch / theta | Dispatch / theta | check / theta | no | no | OTHER_ACTION_FAILURE | OTHER_ACTION_FAILURE | no / yes |

The raw objects above are the preserved output strings; filenames are shortened
only in this table for readability. Exact historical scoring remains unchanged.

Action transition counts are one each:

| Expected action | Baseline | Patched |
|---|---|---|
| determine | exists | check |
| check | check | check |
| verify | find | check |
| confirm | confirm | check |
| inspect | inspect | check |
| amend | Amend | check |
| index | Index | check |
| dispatch | Dispatch | check |

The patched arm therefore removed the single `exists` error but replaced
lexically distinct expected actions with one canonical-looking token.

## Why safe binding rose while competence fell

`safe_semantic_binding` in the retest driver is not exact semantic scoring. It
is true when the contract is valid, the action is in a hard-coded broad set
(`determine`, `check`, `verify`, `confirm`, `inspect`, `amend`, `index`, or
`dispatch`), and the object expression begins with `docs/`.

It does not compare the action with the frozen expected action, and it does not
use the actual per-task authority operation set. Consequently, the patch made
all four targeted actions `check` while retaining their `docs/...` objects,
raising safe binding from 2/4 to 4/4 in that regime even though action exactness
fell from 2/4 to 1/4. Two control objects changed to the generic phrase `file
path`, so control safe binding fell. Overall this produced:

- safe binding: 3/8 -> 6/8;
- action exact: 3/8 -> 1/8;
- both fields exact: 3/8 -> 1/8;
- object exact: 8/8 -> 6/8;
- state-predicate-as-action: 1 -> 0.

Safe binding is therefore a coarse boundedness/safety signal, not a competence-
equivalent metric and not evidence of successful learning.

## Action ontology and downstream roles

The frozen prompt defines `action` as “the operation expressed in the request
clause,” which is closest to `SURFACE_REQUESTED_ACTION`. The fresh evaluator
therefore consistently expected `determine`, `check`, `verify`, `confirm`,
`inspect`, `amend`, `index`, and `dispatch` as written. That evaluator is valid
under the frozen test design; the holdout was not rescored.

The composition router uses the same field differently. In
`derive_requirements()`, `action` is compared directly with
`environment_facts.authority_record.allowed_observation_operations`. The
success contract's `action_allowed` predicate performs the same direct
membership check. The action consequently participates in:

- surface operation extraction from natural language;
- canonical/authority operation membership;
- derivation of the repository-observation capability;
- success-contract validation.

No deterministic operation-normalization layer exists between those roles.
The same scalar field is therefore serving incompatible responsibilities.

`ACTION_FIELD_ROLE_OVERLOAD=true`.

The cleanest bounded refinement candidate is:

```text
action_expression
    -> deterministic.operation_normalization
    -> canonical_operation
```

The model would preserve the expressed operation phrase. Deterministic code
would own normalization into an explicit authority/capability vocabulary.
This is an architectural candidate, not an implemented or experimentally
validated change.

## Downstream information requirements

| Stage | Needs exact surface verb? | Needs canonical operation? | Other required fact |
|---|---:|---:|---|
| semantic extraction | yes, or an action expression | no | object expression |
| capability derivation | no | yes | exact target binding |
| authority validation | no | yes | independent allowed-operation set and target set |
| tool selection | no | yes | qualified tool capability |
| success-contract evaluation | no | yes | validated observation and exact target |

The current implementation incorrectly asks the extraction field to satisfy
both columns. A deterministic normalization layer can reduce model burden
without weakening authority, provided its vocabulary and ambiguous cases are
frozen and fail closed.

## Evaluator, validator, and variance audit

`EVALUATOR_ACTION_EXPECTATIONS_VALID=true` and
`EVALUATOR_CONSISTENT_WITH_FROZEN_TEST_DESIGN=true`. The scorer correctly
performed exact action/object comparisons. No evaluator or scorer defect was
found.

`INTERVENTION_SAFETY_VALIDATION_PASSED=true`: the validator checked target
capability/interface, holdout leakage, authority/tool/evaluator language,
fuzzy matching, promotion, and size constraints.

`INTERVENTION_SEMANTIC_INVARIANT_VALIDATION_DEMONSTRATED=false`: it did not
establish that the patch preserved the action ontology or remained compatible
with the authority operation vocabulary. That is a missing semantic-invariant
check, not a demonstrated validator bug.

Each task had one baseline and one patched sample. The per-task transitions
strongly document an observed patch-associated change, but they cannot estimate
a stable causal effect apart from ordinary supplier variation.

`REPLICATION_REQUIRED_FOR_STABLE_EFFECT_ESTIMATE=true`.

## Classification

The evidence supports a mixed diagnosis:

- teacher mechanism diagnosis: supported at the bounded failure-class level;
- intervention design: failed through over-broad canonicalization to `check`;
- interface ontology: role-overload candidate supported by the code-path audit;
- evaluator/scorer: no defect found;
- supplier variance: remains a causal limitation because each pair was sampled
  once.

`INTERVENTION_OVERGENERALIZATION_DEMONSTRATED=true` describes the observed
patched outputs, not a universal or stable effect.

`ACTION_REPRESENTATION_REFINEMENT_CANDIDATE=true`.

Historical markers remain unchanged:

`FAILURE_LOCALIZATION_TO_CAPABILITY_INTERFACE_DEMONSTRATED=true`

`BOUNDED_TEACHER_INTERVENTION_LOOP_DEMONSTRATED=true`

`TEACHER_PROPOSED_INTERVENTION_IMPROVED_FRESH_HOLDOUT=false`

`SUPPLIER_CAPABILITY_IMPROVEMENT_EVIDENCE_DEMONSTRATED=false`

`SELF_TEACHING_DEMONSTRATED=false`

`QUALIFICATION_PROMOTED=false`

`INTERVENTION_SUPPORTED=false`

`PRIMARY_CHARACTERIZATION=BOUNDED_TEACHER_INTERVENTION_COMPLETED_INTERVENTION_NOT_SUPPORTED`

`NEXT_DECISION=TEST_ACTION_EXPRESSION_PLUS_DETERMINISTIC_OPERATION_NORMALIZATION`

No next experiment was executed.
