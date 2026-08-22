# Bounded read-only tool observation and single replan closeout

## Preserved V1.2 audit

The V1.2 results remain preserved:

```text
PACKET_DERIVED_CAPABILITY_PLANNING_DEMONSTRATED=true
ORACLE_FREE_RUNTIME_VALIDATION_DEMONSTRATED=true
PLANNER_HINT_FREE=true
```

Its tool requirement was not fully request-grounded because
`environment_facts.observation_requirement` directly named the observation
class. The additive correction is:

```text
TOOL_REQUIREMENT_DERIVATION_REQUEST_GROUNDED=false
OBSERVATION_REQUIREMENT_HINT_CANDIDATE=true
NEXT_DECISION=ADD_BOUNDED_READ_ONLY_TOOL_AND_SINGLE_REPLAN_CYCLE
```

No V1.2 evidence or run artifact was modified.

## Result

This six-task model-free slice demonstrated a bounded
ACT -> OBSERVE -> RE-PLAN loop with one read-only repository metadata tool.

| Metric | Result |
|---|---:|
| Tasks correct under separate evaluator | 6/6 |
| Initial capability requirements matched | 6/6 |
| Plan-1 capability requirements matched | 6/6 |
| Tool supplier assignments matched | 4/4 |
| Planned tool steps | 4 |
| Authorized tool calls executed | 3/3 |
| Unauthorized calls prevented | 1/1 |
| Valid observations | 3/3 |
| Observation-dependent replans | 3/3 |
| Replans with changed capability set | 3/3 |
| Terminal successes | 4/6 |
| Ready-for-review states | 2/6 |
| REPLAN_STALLED | 0 |
| Duplicate tool calls | 0 |
| Unnecessary tool calls | 0 |
| Model calls | 0 |
| Runtime evaluator reads | 0 |
| Planner-hint input fields | 0 |

The four terminal successes were two existing authorized files, one authorized
absent target, and the deterministic/no-tool control. The unauthorized target
was denied before any tool call. The unsupported service observation failed
closed without a tool call.

The absent target was preserved as `VALID_OBSERVATION_ABSENT`; it was not
treated as a tool failure or converted into an expected answer.

## Tool boundary

The repository observer accepts exactly one repository-relative target and an
exact authorized target set. It rejects absolute paths, `..` traversal,
symlink escapes, and non-member targets. It returns only path, existence,
regular-file status, size, and SHA-256 metadata. It performs no writes,
commands, network access, process control, or content return.

The registry qualification is limited to exact-target repository-relative
metadata observation under explicit authority. It is not automatic promotion
and implies no broader filesystem capability.

## Replan evidence

For each authorized observation, `capability_plan_0.json` contains the tool
capability. After validated observation:

- `exists=true` produces `deterministic.observation_exists_policy`;
- `exists=false` produces `deterministic.observation_absence_policy`.

`replan_delta.json` records the consumed observation and the changed capability
set. Missing/invalid observations retain the tool requirement and are handled
as stalled/fail-closed rather than assumed success. `MAX_REPLANS=1`.

## Architecture markers

```text
BOUNDED_READ_ONLY_TOOL_SUPPLIER_DEMONSTRATED=true
SINGLE_OBSERVATION_REPLAN_LOOP_DEMONSTRATED=true
REQUEST_GROUNDED_TOOL_REQUIREMENT_DERIVATION_DEMONSTRATED=true
FIRST_BOUNDED_ADAPTIVE_AGENT_LOOP=true
NEXT_DECISION=COMPOSE_MODEL_AND_TOOL_IN_ONE_ITERATIVE_TASK
```

“Adaptive” here means only that the second deterministic plan changes after a
validated runtime observation. This is not a generalized-agent or production
readiness claim.

## Provenance

- authoritative V1.2 closeout: `5c0ccdec4d161b546cc6fd61f0e1aab3875fc3c4`;
- freeze commit: `1f50bf2216246289288e935324e7da9b48eda1ef`;
- run directory:
  `.work/model_size_supplier_floor/capability_router_tool_observation_v0/run_20260822T162810Z/`;
- run manifest SHA256:
  `cd4d8b4e6139de19d065751ffb5fa7211eaa63c3701a9115dd632d630d2cdf70`;
- task manifest SHA256:
  `2ba049f3c46c8eca6874cdf61b3b1f7f69dcc328c6601394ac7bd8cfcfdab7be`.

Teacher calls, retries, escalations, external calls, V100/30B use, and
production changes were all zero/false.
