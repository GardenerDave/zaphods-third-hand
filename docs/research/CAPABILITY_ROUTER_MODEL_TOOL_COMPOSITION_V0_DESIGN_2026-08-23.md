# First bounded MODEL -> TOOL -> OBSERVATION -> REPLAN composition slice

This fresh exploratory slice preserves the prior bounded tool-loop milestones
and reuses its corrected composition engine, semantic interface, registry
shape, authority validator, and read-only repository observer. It does not
modify or rescore historical artifacts.

## Preserved prior milestones

```text
BOUNDED_READ_ONLY_TOOL_SUPPLIER_DEMONSTRATED=true
SINGLE_OBSERVATION_REPLAN_LOOP_DEMONSTRATED=true
REQUEST_GROUNDED_TOOL_REQUIREMENT_DERIVATION_DEMONSTRATED=true
FIRST_BOUNDED_ADAPTIVE_AGENT_LOOP=true
```

The prior implementation boundaries remain additive observations:

```text
SUCCESS_CONTRACT_ARTIFACTS_GENERATED=true
SUCCESS_CONTRACT_RUNTIME_ENFORCEMENT_DEMONSTRATED=false
TOOL_AUTHORITY_ENFORCEMENT_DEMONSTRATED=true
TOOL_PLAN_AUTHORITY_PROVENANCE_LABEL_MISMATCH=true
```

This slice corrects authority provenance to
`ENVIRONMENT_AUTHORITY_RECORD` and makes terminal state depend on an explicit
deterministic success-contract evaluator.

## Runtime loop

```text
request
 -> Vogon/triage + orchestration packet
 -> plan_0: semantic.minimal_action_object_extraction
 -> Qwen3 1.7B: action + object_expression
 -> exact semantic/authority validation
 -> plan_1: tool.read_only_repository_observation
 -> bounded repository metadata observation
 -> plan_2: deterministic observation policy
 -> executable success contract
 -> terminal_success or ready_for_review
```

`MAX_REPLANS=2`. The model never selects a capability or grants authority.
The tool never returns file contents and performs no mutation, shell, network,
or process operation.

## Fresh matrix

The six tasks include two authorized existing targets, one authorized absent
target, one unauthorized semantic target, one deterministic control, and one
unsupported service-observation request. The existing-target paths are
verified repository-relative paths in the frozen task manifest. Runtime inputs
contain only request/packet/environment facts; evaluator expectations are
stored separately and are not consumed by planning or validation.

## Boundaries

```text
MODEL: action + object_expression only
CODE: exact equality, operation vocabulary, authority membership, planning,
      tool validation, observation policy, success-contract evaluation
TOOL: exact-authorized repository-relative metadata observation only
```

This is bounded control-flow evidence, not general autonomy, production
readiness, generalized tool use, self-training, or automatic qualification.
