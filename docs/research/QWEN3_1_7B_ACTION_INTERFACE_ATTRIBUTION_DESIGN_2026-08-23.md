# Qwen3 1.7B action-interface attribution experiment

## Question

Does the supplier provide more decision-useful operation evidence through the
historical `action` field or the newer `action_expression` field when both are
processed by the same deterministic, request-context-gated normalizer?

This is a paired attribution experiment, not a rerun of the prior 12-call
experiment and not a production interface decision.

## Frozen boundary

The old arm emits `action` and `object_expression`; the new arm emits
`action_expression` and `object_expression`. The downstream normalizer,
context grammar, authority records, target comparison, model, runtime settings,
and evaluator are shared. The arms receive the same request independently.

The normalizer maps bounded presence expressions (`determine`, `check`,
`verify`, `confirm`, `find`, `exists`) to `observe_presence` only when the
request is deterministically classified as a presence-observation request.
`inspect`, `amend`, `index`, and `dispatch` remain distinct direct operations.
Ambiguous, unsupported, and unknown cases fail closed.

## Holdout

The fresh holdout has 12 tasks: four presence cases, four direct-operation
controls, two ambiguous requests, and two unsupported requests. It is separate
from the prior action-expression holdout and the teaching holdout. The bounded
request grammar exposes enough operation structure for all 12 tasks to be
classified deterministically; this is recorded as a model-necessity audit, not
as a routing change.

The execution order is counterbalanced by task index. There are 12 independent
old-interface calls and 12 independent action-expression calls. No arm consumes
the other arm's result.

## Safety and interpretation

Canonical operation is the only value considered for independent authority
membership. Model output never grants authority. No fuzzy matching, substring
repair, tool call, teacher call, retry, or qualification promotion is allowed.

Surface lexical exactness is secondary. Primary comparison is canonical
operation correctness on applicable tasks, normalization decision correctness
including fail-closed cases, object-expression exactness, safe target binding,
and authority broadening.
