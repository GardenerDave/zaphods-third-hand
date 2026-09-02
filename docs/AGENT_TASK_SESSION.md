# Agent Task Sessions

Agent Task Sessions are model-free, plain-file work packets for scoped Codex
or external-agent tasks. They implement the ZTH operating model directly:

- ZTH provides procedural constraint and verification.
- The supervised agent provides semantic critique or implementation.
- Humans retain decision authority.

The objective is to maximize trusted work per unit of human attention without
turning a packet into unattended execution authority.

Agent Task Session is part of the informal
[`Vogon Printer`](VOGON_PRINTER.md) family of model-free packet, scaffold,
validation, and advisory tools. The family name does not change this tool's
contract or grant execution authority.

## What the Builder Does

`local_harness/agent_task_session.py new` records:

- a specific goal and intended branch;
- repository-relative allowed paths;
- required checks;
- draft status and human-review requirements;
- a bounded agent prompt;
- optional Change Closeout guidance.

It writes under `.work/agent_tasks/<task-id>/`:

```text
task.yaml
codex_prompt.md
allowed_paths.txt
required_checks.txt
status.md
closeout_request.md
```

`task.yaml` uses JSON syntax, which is valid YAML, so the standard library can
read and validate the contract without adding a YAML dependency.

The builder does not run an agent, execute required checks, inspect model
output, switch branches, or perform any Git operation.

## Create a Session

```bash
python3 local_harness/agent_task_session.py new \
  --name "Add focused parser validation" \
  --goal "Add parser checks without changing unrelated behavior" \
  --branch agent-task-parser-validation \
  --allow local_harness/example.py \
  --allow local_harness/tests/test_example.py \
  --check "python3 -m pytest local_harness/tests/test_example.py" \
  --check "python3 local_harness/repo_health_check.py"
```

The default task ID is a deterministic slug plus a hash of the normalized
packet inputs. An explicit `--task-id` must contain only lowercase letters,
digits, and internal hyphens.

Allowed paths must be repository-relative and may not contain `..` or `.git`.
The builder refuses to overwrite an existing task-session directory.

## Validate a Session

```bash
python3 local_harness/agent_task_session.py validate \
  .work/agent_tasks/<task-id>
```

Validation checks:

- required files and contract version;
- draft and human-review metadata;
- safe, unique allowed paths;
- non-empty required checks;
- consistency between metadata and plain-text lists;
- consistency between metadata, the agent prompt, and closeout guidance;
- required no-authority language in the prompt, status, and closeout request.

Validation does not execute checks, read the allowlisted source files, judge
implementation quality, or establish task completion.

Add `--json` to `new` or `validate` for a machine-readable handoff. Repository
paths are emitted relative to the checkout when practical.

## Record Execution Evidence and Review Decisions

After a supervised executor performs the task, the separate recorder tool
`local_harness/agent_task_session_record.py` records what happened against the
existing packet. It is model-free and fail-closed, and it never mutates the
packet the builder produced.

Record one execution-evidence entry, supplying one observed outcome per
required check, in packet order:

```bash
python3 local_harness/agent_task_session_record.py record-execution \
  .work/agent_tasks/<task-id> \
  --outcome "passed: 30 passed in 0.51s" \
  --outcome "passed: health ok" \
  --evidence-file docs/reports/<report>.md \
  --note "implementation and focused tests complete"
```

Record a human review decision against recorded execution evidence:

```bash
python3 local_harness/agent_task_session_record.py record-review \
  .work/agent_tasks/<task-id> \
  --decision accepted \
  --reviewer <reviewer-identity> \
  --reason "checks and evidence reviewed"
```

Validate the packet plus all recorded records and derive the session stage:

```bash
python3 local_harness/agent_task_session_record.py validate \
  .work/agent_tasks/<task-id>
```

Records land under `execution/` and `review/` inside the task-session
directory. The recorder:

- validates the base packet first and fails closed if it is invalid;
- binds each required check to one recorded outcome (outcomes are recorded
  operator/agent input, not tool-verified results);
- binds each evidence file by path, size, and sha256, and fails closed if a
  bound file later drifts or disappears;
- binds each record to the exact `task.yaml` hash at record time and fails
  closed if the packet changes afterwards;
- requires review decisions to reference existing execution evidence and
  requires a superseding decision to explicitly supersede the latest one;
- derives the session stage (`draft` -> `executed` -> `reviewed`) from the
  validated records.

Boundaries preserved by every record:

- the source packet is never mutated; `task.yaml` remains a draft packet;
- records are evidence, not authority, and grant no merge, release,
  promotion, cleanup, deletion, or lifecycle authority;
- reviewer identity is supplied input, not tool-verified identity;
- the derived stage is recorded evidence, not a lifecycle promotion;
- the recorder executes no checks, agents, shell commands, or Git operations.

Repo health can validate an explicitly named private packet without scanning
`.work/` generally:

```bash
python3 local_harness/repo_health_check.py \
  --task-session .work/agent_tasks/<task-id>
```

## Human Review Boundary

An Agent Task Session is a review packet, not an active worker or authority
source. It does not:

- authorize edits outside its allowlist;
- mark work complete;
- accept generated output;
- commit, merge, release, promote, clean up, or move lifecycle state;
- claim that required checks passed.

Passing checks are evidence, not authority. Humans decide whether to hand the
packet to an agent, whether resulting work is acceptable, and what lifecycle
or repository action follows.

`closeout_request.md` records an optional human-run Change Closeout command.
It does not create or promote a closeout automatically.

For independent role packets and output comparison, see
[`AGENT_ADAPTER.md`](AGENT_ADAPTER.md). For final change review, see
[`CHANGE_CLOSEOUT.md`](CHANGE_CLOSEOUT.md).
