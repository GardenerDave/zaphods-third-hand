# Bounded read-only tool observation and single replan slice

Status: frozen exploratory design; not production routing.

## V1.2 audit

The preserved V1.2 planning and validation results remain unchanged. Its tool
task supplied `environment_facts.observation_requirement` and the planner
mapped that field directly to a tool capability. The additive audit is:

```text
TOOL_REQUIREMENT_DERIVATION_REQUEST_GROUNDED=false
OBSERVATION_REQUIREMENT_HINT_CANDIDATE=true
NEXT_DECISION=ADD_BOUNDED_READ_ONLY_TOOL_AND_SINGLE_REPLAN_CYCLE
```

This slice removes that input hint and derives a bounded repository-observation
need from the request grammar, packet content, and an exact authority record.

## Scientific question

Can the router perform one bounded ACT -> OBSERVE -> RE-PLAN cycle without a
model, then terminate successfully or fail closed?

The loop is limited to one read-only metadata observation. It never writes,
deletes, renames, changes permissions, executes commands, accesses a network,
or controls processes.

## Reused repository mechanisms

The slice reuses the existing deterministic triage/orchestration packet
builders and validators, the evidence-linked registry shape, and the existing
repository root/runtime provenance conventions. No existing safe filesystem
observer was present, so the new adapter is a small Python-only implementation
using `pathlib` resolution and `hashlib.sha256`; it returns metadata only.

## Tool contract

Supplier: `python_read_only_repository_observer_v0`.

Input contains one repository-relative target and the exact allowed target set
from the authority record. The adapter rejects absolute paths, `..`
traversal, root escapes, symlink escapes, and targets not exactly present in
the allowed set. It returns:

```text
repository_relative_path
exists
is_file
size_bytes
sha256
```

An absent authorized target is a valid observation with `exists=false` and
`sha256=null`; it is not a tool failure.

## Replanning

`plan_0` contains the tool step. After a validated observation, the planner
receives only that observation and produces `plan_1`:

- existing regular file -> deterministic observation-exists policy;
- authorized absent target -> deterministic observation-absent policy.

The post-observation capability changes with the observed state, so the
replan is not a hard-coded success transition. Missing or invalid observation
data prevents successful replanning. A second identical tool request is
`REPLAN_STALLED` and fails closed. `MAX_REPLANS=1`.

## Frozen matrix

Six model-free fixtures cover two authorized existing targets, one authorized
absent target, one unauthorized target, one deterministic/no-tool control, and
one unsupported observation capability. Runtime inputs contain no
`observation_requirement`, `requires_tool_observation`, `tool_capability_id`,
`required_capabilities`, or expected route fields.

## Qualification and boundaries

The deterministic tool is qualified only for exact-target, repository-relative,
read-only metadata observation under explicit authority. No broader filesystem
or tool capability is implied, and qualification is not auto-promoted.

Success markers, if all frozen branches pass:

```text
BOUNDED_READ_ONLY_TOOL_SUPPLIER_DEMONSTRATED=true
SINGLE_OBSERVATION_REPLAN_LOOP_DEMONSTRATED=true
REQUEST_GROUNDED_TOOL_REQUIREMENT_DERIVATION_DEMONSTRATED=true
FIRST_BOUNDED_ADAPTIVE_AGENT_LOOP=true
NEXT_DECISION=COMPOSE_MODEL_AND_TOOL_IN_ONE_ITERATIVE_TASK
```
