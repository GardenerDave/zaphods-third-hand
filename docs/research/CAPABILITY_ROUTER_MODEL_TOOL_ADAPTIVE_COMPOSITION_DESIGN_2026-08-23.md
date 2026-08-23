# First MODEL -> TOOL -> observation -> REPLAN composition slice

This is an exploratory, non-production vertical slice. It preserves the prior
V0 tool-loop evidence and tests one bounded composition:

```text
request
  -> semantic action/object extraction
  -> exact authority validation
  -> read-only repository metadata observation
  -> deterministic observation policy
  -> runtime success-contract evaluation
```

The model emits only `action` and `object_expression`. It does not select a
capability, authorize a target, perform equality, observe state, or decide the
terminal result. The planner derives the tool requirement only after a
contract-valid semantic output is safely bound to an allowed observation
operation and exact authorized target.

## Bounded responsibilities

The semantic request family is intentionally narrow: a request asks whether a
named repository-relative target currently exists or is present. The request
parser exposes one target token, but the initial plan still requires the
semantic atom so that the model route is exercised. The tool reads only
metadata for an exact authorized target. A validated observation changes the
plan to one of two deterministic policies.

Authority provenance is explicit:

```text
authorized_targets <- ENVIRONMENT_AUTHORITY_RECORD
action/object       <- PRIOR_MODEL_STEP
observation         <- PRIOR_TOOL_STEP
```

No evaluator field enters runtime planning, execution, validation, or
terminal-state selection. Evaluator annotations are stored separately for
closeout only.

## Plan sequence

Successful tasks preserve three plans and two deltas:

```text
plan_0: semantic.minimal_action_object_extraction
plan_1: tool.read_only_repository_observation
plan_2: deterministic.observation_{exists,absence}_policy
```

`MAX_REPLANS=2`. A missing observation, unsafe target, unsupported operation,
or repeated identical capability fails closed. The generic success-contract
evaluator records each predicate result in
`success_contract_evaluation_{0,1,2}.json`; no branch may bypass it for a
terminal success.

## Frozen branches

The six fresh tasks contain two authorized existing targets, one authorized
absent target, one semantically extracted unauthorized target, one deterministic
control, and one unsupported capability. The first four semantic requests are
bounded and do not depend on the known subobject weakness. The control path
uses no model or tool. The unsupported path has no qualified supplier and
fails closed without improvisation.

This slice makes no claim about general language understanding, tool use,
autonomy, or production readiness.
