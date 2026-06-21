# Agent Task Sessions

Agent Task Sessions are model-free, plain-file work packets for scoped Codex
or external-agent tasks. They implement the ZTH operating model directly:

- ZTH provides procedural constraint and verification.
- The supervised agent provides semantic critique or implementation.
- Humans retain decision authority.

The objective is to maximize trusted work per unit of human attention without
turning a packet into unattended execution authority.

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
