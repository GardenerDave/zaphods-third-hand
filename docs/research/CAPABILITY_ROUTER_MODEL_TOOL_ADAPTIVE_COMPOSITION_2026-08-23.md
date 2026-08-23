# MODEL -> TOOL -> observation -> REPLAN closeout

This exploratory vertical slice used the existing bounded Qwen3 1.7B semantic
interface and the existing read-only repository metadata observer. Historical
V0–V1.2 evidence and the V0 run were not modified or rescored.

## Preserved V0 audit

The prior bounded adaptive tool loop remains preserved:

```text
BOUNDED_READ_ONLY_TOOL_SUPPLIER_DEMONSTRATED=true
SINGLE_OBSERVATION_REPLAN_LOOP_DEMONSTRATED=true
REQUEST_GROUNDED_TOOL_REQUIREMENT_DERIVATION_DEMONSTRATED=true
FIRST_BOUNDED_ADAPTIVE_AGENT_LOOP=true
```

Its additive implementation findings remain:

```text
SUCCESS_CONTRACT_ARTIFACTS_GENERATED=true
SUCCESS_CONTRACT_RUNTIME_ENFORCEMENT_DEMONSTRATED=false
TOOL_AUTHORITY_ENFORCEMENT_DEMONSTRATED=true
TOOL_PLAN_AUTHORITY_PROVENANCE_LABEL_MISMATCH=true
NEXT_DECISION=COMPOSE_MODEL_AND_TOOL_IN_ONE_ITERATIVE_TASK
```

This slice corrects those two implementation boundaries locally: authority is
labeled `ENVIRONMENT_AUTHORITY_RECORD`, and terminal success is gated by the
generic predicate evaluator in `success_contract_evaluation_*.json`.

## Result

| Metric | Result |
|---|---:|
| Tasks correct under evaluator | 6/6 |
| Plan-0 requirements matched | 6/6 |
| Plan-1 requirements matched | 6/6 |
| Plan-2 requirements matched | 5/6 |
| Semantic outputs contract-valid | 4/4 |
| Semantic outputs safely bound | 3/4 |
| Model outputs deriving TOOL | 3/4 |
| Authorized tool calls | 3/3 |
| Unauthorized tool calls prevented | 1/1 |
| Valid observations | 3/3 |
| MODEL -> TOOL replans | 3 |
| TOOL -> deterministic replans | 3 |
| Full MODEL -> TOOL -> deterministic chains | 3 |
| Success contracts evaluated | 6/6 |
| Success-contract predicate failures | 1 |
| Terminal success | 4/6 |
| Ready for review | 2/6 |
| Duplicate calls | 0 |
| REPLAN_STALLED | 0 |
| Model calls | 4 |
| Tool calls | 3 |
| 30B/V100 calls | 0 |
| External calls | 0 |
| Runtime expected-field reads | 0 |
| Planner-hint input fields | 0 |
| Model output granted authority | 0 |

The three successful chains each used one model call, one authorized
read-only tool call, two replans, and one deterministic post-observation policy.
The fourth semantic route extracted a target outside the environment authority
record and failed closed with zero tool calls. The deterministic control used
neither backend. The unsupported external-service capability failed closed
without an improvised supplier.

## Fixture-state qualification

The frozen task matrix intended two existing authorized targets and one absent
authorized target. The model correctly extracted the second target, but the
frozen request named `docs/CAPABILITY_ROUTER_V1_2_PACKET_PLANNING_DESIGN_2026-08-22.md`,
which is not a repository path; the actual tracked design is under
`docs/research/`. The tool therefore returned a valid absence observation.

This is a fixture allocation defect, not a tool failure and not a rescore:

```text
FROZEN_EXISTING_ABSENT_ALLOCATION_MATCHED=false
```

The run still contains both valid existing and valid absent observations, and
the observation-dependent replan and contract gating were exercised. The
allocation defect should be repaired before a confirmatory composition slice.

## Runtime responsibility boundary

```text
MODEL: action + object_expression
CODE: exact equality, authority membership, TOOL derivation, observation validation
TOOL: repository-relative metadata only
CODE: observation policy, success-contract evaluation, terminal state
```

The observer returned only repository-relative path, existence, regular-file
status, size, and SHA-256 metadata. It performed no content read, mutation,
shell execution, network access, or process control.

## Provenance and recovery

- authoritative prior closeout: `c53396addf97a50ec92d1c63b930703a725648bd`;
- freeze commit: `0a36d83`;
- preflight serialization correction: `d4fd16b`;
- no-replay continuation correction: `06eccd6`;
- final branch-separation correction: `3ed6cd1`;
- final run: `.work/model_size_supplier_floor/capability_router_model_tool_adaptive_composition/run_20260823T045554Z/`;
- model response artifacts: 4, one per semantic task;
- tool observation artifacts: 3, one per authorized tool route.

The run encountered two harness crashes after the first model response and
after three subsequent semantic responses. The existing response was treated
as spent, recorded in additive recovery state, and never replayed. The final
run contains exactly four distinct model responses and no duplicate supplier
call.

## Resource description

Level-2 GTX1650 `gpu_device_only` model-call telemetry was recorded. Model
latency was median 2089.616 ms, mean 2335.985 ms, and p95 3369.577 ms. Gross
device energy across the four model calls was 257.6675 J. Tool execution was
local bounded Python code and did not use GPU telemetry. These are descriptive
measurements, not causal claims about composition wording.

## Markers

```text
MODEL_TO_TOOL_CAPABILITY_TRANSITION_DEMONSTRATED=true
TOOL_TO_DETERMINISTIC_REPLAN_DEMONSTRATED=true
SUCCESS_CONTRACT_RUNTIME_ENFORCEMENT_DEMONSTRATED=true
FIRST_MODEL_TOOL_ADAPTIVE_COMPOSITION_LOOP=true
NEXT_DECISION=ADD_FAILURE_DIAGNOSIS_AND_BOUNDED_TEACHING_INTERVENTION
```

This is bounded adaptive control-flow evidence, not general autonomy,
production readiness, self-training, or automatic capability promotion.
