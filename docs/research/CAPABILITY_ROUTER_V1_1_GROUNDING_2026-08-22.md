# Capability Router V1.1 grounding slice

## Outcome

`PACKET_GROUNDED_ORACLE_FREE_ROUTER_LOOP_DEMONSTRATED=true`

This is an exploratory, bounded Router V1.1 result. It does not change
production routing, promote capabilities, touch V100/30B, execute tools, or
grant authority.

## Additive V1 audit

The preserved V1 result remains 10/10 task-correct, with 10/10 complete plan
matches, 7/7 complete plans executed, and 3/3 incomplete plans failed closed.
The corrected assignment terminology is:

- `COMPLETE_PLAN_ASSIGNMENT_SETS_CORRECT=7/7`;
- `INDIVIDUAL_CAPABILITY_ASSIGNMENTS_CORRECT=12/12` (2 deterministic-only
  assignments plus 5 two-step compositions).
- `ZERO_MODEL_PLANS=5`;
- `INCOMPLETE_PLANS_PREVENTING_PARTIAL_MODEL_EXECUTION=3`.

V1 boundaries remain `CAPABILITY_PLAN_DERIVED_FROM_CANONICAL_RUNTIME_FACTS=true`,
`CAPABILITY_PLAN_DERIVED_FROM_VOGON_PACKET_CONTENT=false`, and
`RUNTIME_VALIDATION_ORACLE_FREE=false`.

## V1.1 design boundary

The new runtime separates `runtime_task.json`, packet artifacts,
`planner_facts.json`, `capability_plan.json`, and `success_contract.json` from
evaluator-only `evaluator.json`. Planning uses packet content plus independently
supplied world facts. Runtime execution never loads evaluator expectations.
Closeout reads those expectations only after execution for scoring.

Success contracts validate structured model output, allowed operation
membership, exact normalized target equality, deterministic policy
computation, and coverage state. They contain no worked model answer.

Plans carry explicit `step_id`, `requires_inputs`, `produces_outputs`, and
`depends_on` fields. The semantic step produces `action` and
`object_expression`; deterministic target binding consumes those outputs and
the requested target.

## Frozen matrix and execution

The fresh matrix contains two deterministic tasks, four semantic plus
deterministic compositions, one not-qualified reference-entity task, and one
unknown tool-needed task. The last two are incomplete and fail closed without
model calls.

| Metric | Result |
|---|---:|
| Tasks correct | 8/8 |
| Capability plans matched evaluator expectations | 8/8 |
| Complete-coverage tasks executed | 6/6 |
| Incomplete-coverage tasks failed closed | 2/2 |
| Complete plan assignment sets correct | 6/6 |
| Individual capability assignments correct | 10/10 |
| Deterministic steps | 6 |
| Model steps/calls | 4 |
| Tool steps/calls | 0 |
| Model calls avoided | 4 |
| Unnecessary model calls | 0 |
| Unnecessary escalations | 0 |
| Duplicate supplier calls | 0 |
| Review states | 2 |
| Tasks using more than one supplier type | 4 |
| Runtime evaluator-field reads | 0 |

The four composed tasks used `MODEL` for minimal action/object extraction and
`DETERMINISTIC_CODE` for direct-target binding. The unqualified and unknown
capabilities did not execute partial plans.

## Oracle-corruption and lazy-backend checks

The focused adversarial test replaces every evaluator expectation with wrong
values, rebuilds the runtime-grounded facts/plan/contract, and confirms that
the plan and runtime result remain unchanged. Only evaluator scoring is
permitted to change.

The no-model workload test replaces the backend initializer with a function
that raises. Deterministic and incomplete/review plans do not touch it. In the
live run, backend initialization occurred only because four frozen model steps
were planned.

## Runtime and resources

- Supplier: Qwen3 1.7B-labeled / 2.032B operative;
- operative parameters: `2031739904`;
- model artifact: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`;
- effective/training context: `32768/32768`;
- GPU: GTX 1650, `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`;
- model-route latency mean/median/p95: `1926.211 / 1913.944 /
  2112.078 ms` (inclusive percentile over four calls);
- model-route gross energy mean/median/total: `54.119 / 52.948 / 216.478 J`;
- model calls: 4; 30B/V100 calls: 0; tool calls: 0; external calls: 0.

Energy and latency are descriptive Level-2 `gpu_device_only` measurements, not
causal claims.

## Provenance

- Preserved V1 closeout: `2d97310f54db3ea5bcee825419f9f2359d2afd3f`;
- V1 interpretation erratum: see
  `CAPABILITY_ROUTER_V1_INTERPRETATION_ERRATUM_2026-08-22.md`;
- V1.1 freeze commit: `2f2b2e8`;
- telemetry harness correction: `567770f`;
- corrected run directory:
  `.work/model_size_supplier_floor/capability_router_v1_1_grounding/run_20260822T154500Z/`;
- run manifest SHA256:
  `824b1f3454ff04444cec6fce0c440845912c95763f3266c3810f9c694361b294`;
- task and registry hashes are recorded in the matrix artifact.

An earlier escalated preflight reached the local endpoint but stopped before
the first supplier response because of a missing telemetry import; that
zero-response interruption is preserved separately and was not reused. The
completed run is the fresh corrected preparation.

## Interpretation and boundary

The slice demonstrates packet-grounded planning, full per-capability coverage,
dependency-aware composition, oracle-free runtime validation, and lazy model
initialization. It is not a generalized-agent capability claim.

`NEXT_DECISION=ADD_BOUNDED_TOOL_SUPPLIER_AND_ITERATIVE_OBSERVATION`

That step is not executed here.
