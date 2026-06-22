# Local Harness

This folder contains the manager-side helper scripts for supervised local-worker runs.

## Scripts

- `icm_call.py`: configurable one-shot worker caller for native `/completion` and OpenAI-compatible `/v1` endpoints.
- `run_single_worker.py`: executes one audited single-worker run folder and writes `OUTPUT.md` plus `METRICS.json`.
- `run_aider_worker.py`: executes one audited Aider task from `MODEL_REQUEST.md`, adds Gemma-local
  preflight safeguards, can prewarm the endpoint, and records command output plus debug artifacts.
- `llm_probe_preflight_ingest.py`: imports versioned LLM-probe JSON as preflight-only plain-file evidence; see [`docs/LLM_PROBE_PREFLIGHT.md`](../docs/LLM_PROBE_PREFLIGHT.md).
- `llm_probe_preflight_compare.py`: compares two canonical preflight capability manifests and writes aggregate, human-reviewable regression evidence; see [`docs/LLM_PROBE_PREFLIGHT.md`](../docs/LLM_PROBE_PREFLIGHT.md).
- `preflight_audition_plan.py`: validates operator-supplied paths and prints a model-free, non-executing command plan from LLM-probe evidence or a capability manifest to a gated suite or board audition; see [`docs/PREFLIGHT_AUDITION_PLAN.md`](../docs/PREFLIGHT_AUDITION_PLAN.md).
- `model_auditions/`: optional exploratory small-model harness that can download candidate GGUFs, manage temporary local llama.cpp tmux sessions, or call existing local/LAN OpenAI-compatible endpoints; see [`model_auditions/README.md`](model_auditions/README.md).
- `logic_probe.py`: validates and mechanically scores ZTH-specific model logic probes, and can preserve raw evidence from existing OpenAI-compatible endpoints; see [`docs/LOGIC_PROBES.md`](../docs/LOGIC_PROBES.md).
- `change_closeout.py`: prepares a bounded, model-free final-review evidence packet and Markdown closeout scaffold; see [`docs/CHANGE_CLOSEOUT.md`](../docs/CHANGE_CLOSEOUT.md).
- `tool_maker.py`: prepares a bounded, model-free workflow evidence packet and Markdown lifecycle draft scaffold; see [`docs/TOOL_MAKER.md`](../docs/TOOL_MAKER.md).
- `validate_scaffold.py`: validates Tool Maker and Change Closeout scaffold shape and metadata consistency without reading original sources or judging truth, safety, completeness, or promotion readiness.
- `repo_health_check.py`: reports Markdown-link, public-surface privacy, boundary-language, scaffold, diff-hygiene, and optional test health without changing files.
- `git_sync_cleanup.py`: reports local post-merge Git sync and branch-cleanup evidence and prints human-reviewable commands without executing cleanup.
- `agent_task_session.py`: creates a scoped, model-free Agent Task Session review packet under `.work/agent_tasks/` without running agents, checks, or Git commands.
- `zth_agent_packet.py`: generates one independent role/context packet for an external agent.
- `zth_compare_agent_outputs.py`: compares completed external-agent outputs that follow the ZTH contract.
- `zth_coverage_auditor.py`: reports obvious pre-synthesis coverage areas and blind spots.

## Vogon Printer Family

[`docs/VOGON_PRINTER.md`](../docs/VOGON_PRINTER.md) groups these existing
model-free tools for operator navigation:

- packet/scaffold printers: `agent_task_session.py`, `tool_maker.py`, and
  `change_closeout.py`;
- validators/advisors: `validate_scaffold.py`, `repo_health_check.py`, and
  `git_sync_cleanup.py`.

Vogon Printer is an informal family name, not a wrapper command or autonomous
workflow. Each script keeps its existing CLI and contract. No family member
automatically runs another, executes a task packet, accepts evidence, or
grants merge, release, promotion, cleanup, or lifecycle authority.

## Internal Modules

- `aider_prep.py`: prompt compaction, read-context shaping, and preflight budgeting helpers used by `run_aider_worker.py`.
- `aider_runtime.py`: thin compatibility layer that re-exports the smaller runtime helper modules used by `run_aider_worker.py`.
- `aider_transport.py`: command construction and environment helpers for Aider runs.
- `aider_reporting.py`: attempt archiving, output summarization, and event-log parsing helpers for Aider runs.
- `aider_metrics.py`: run metadata assembly helpers for Aider runs.
- `tests/test_run_aider_worker.py`, `tests/test_aider_prep.py`, and `tests/test_aider_runtime.py`:
  split test surfaces so local Aider tasks can target smaller real-code files.

## Local Model Logic Probes

Validate the checked-in fixture set without a model call:

```text
python3 local_harness/logic_probe.py validate \
  --fixtures local_harness/logic_probes.example.json
```

Run the probes against configured, already-running OpenAI-compatible
endpoints:

```text
python3 local_harness/logic_probe.py run \
  --fixtures local_harness/logic_probes.example.json \
  --models local_harness/model_auditions/models.example.json \
  --out-dir .work/model_auditions/logic_probe_runs \
  --run-id <run-id>
```

The command preserves raw per-model/per-probe responses, writes mechanically
scored JSON, and produces `LOGIC_PROBE_SUMMARY.md`. Endpoint errors become
reviewable error evidence instead of stopping the full run. The runner does
not start model servers or add authentication headers.

Probe results diagnose bounded ZTH behaviors; they do not rank models
generally or grant implementation, cleanup, role-assignment, promotion,
release, or lifecycle authority. See
[`docs/LOGIC_PROBES.md`](../docs/LOGIC_PROBES.md) for score mode, output
contracts, and interpretation.

## Repository Health

Run the fast default checks for tracked Markdown links, public setup surfaces,
and authority-expanding wording:

```text
python3 local_harness/repo_health_check.py
```

Run every supported check, including `git diff --check` and the full
`local_harness/tests` suite:

```text
python3 local_harness/repo_health_check.py --all
```

Validate a private scaffold explicitly without scanning `.work/` generally:

```text
python3 local_harness/repo_health_check.py \
  --scaffolds \
  --scaffold .work/change_closeouts/example.md
```

The helper reports health and exits nonzero on failures. It does not fix or
delete files, validate semantic truth or safety, or grant merge, acceptance,
promotion, or lifecycle authority. Full pytest is optional and is not part of
the default check. The privacy scan excludes durable historical material under
`docs/reports/`; review reports separately before publication.

## Git Sync and Cleanup Advice

Inspect local Git and remote-tracking refs after a merge:

```text
python3 local_harness/git_sync_cleanup.py
python3 local_harness/git_sync_cleanup.py \
  --after-merge-branch roadmap-mutual-supervision-clarity
python3 local_harness/git_sync_cleanup.py --run-health
python3 local_harness/git_sync_cleanup.py --json
```

The advisor is read-only. It does not fetch, pull, prune, switch, merge, reset,
push, or delete branches. Remote findings reflect the currently available
local remote-tracking refs and may be stale. It prints inspection commands
before destructive cleanup suggestions, especially after squash merges, and
requires a human to confirm branch deletion. Use `--include-fetch-advice` to
print `git fetch --prune` as an optional command; it is never run by the
advisor. Passing repo health remains evidence, not cleanup or acceptance
authority.

## Agent Task Sessions

Create a draft work packet for a supervised Codex or external-agent task:

```text
python3 local_harness/agent_task_session.py new \
  --name "Add focused parser validation" \
  --goal "Add parser checks without changing unrelated behavior" \
  --branch agent-task-parser-validation \
  --allow local_harness/example.py \
  --allow local_harness/tests/test_example.py \
  --check "python3 -m pytest local_harness/tests/test_example.py" \
  --check "python3 local_harness/repo_health_check.py"
```

The command writes `task.yaml`, `codex_prompt.md`, `allowed_paths.txt`,
`required_checks.txt`, `status.md`, and `closeout_request.md` under
`.work/agent_tasks/<task-id>/`. It records scope and verification
instructions but does not execute the task, run checks, invoke an agent, or
perform Git operations. The packet remains draft review evidence: passing
checks are evidence, not authority, and humans retain acceptance, commit,
merge, release, promotion, cleanup, and lifecycle decisions.

Validate packet shape and authority boundaries without executing its checks:

```text
python3 local_harness/agent_task_session.py validate \
  .work/agent_tasks/<task-id>
```

Add `--json` to `new` or `validate` for a machine-readable handoff. See
[`docs/AGENT_TASK_SESSION.md`](../docs/AGENT_TASK_SESSION.md) for the output
contract, path rules, and human-review boundary.

To include a specific private packet in repo health without scanning `.work/`
generally:

```text
python3 local_harness/repo_health_check.py \
  --task-session .work/agent_tasks/<task-id>
```

## Configuration

The defaults preserve the sanitized placeholder hosts from the handoff bundle.
Override them per call with CLI flags or environment variables:

```text
ICM_HANDOFF_BASE_URL
ICM_HANDOFF_URL
ICM_HANDOFF_MODEL
ICM_HANDOFF_API
```

The same suffix pattern works for `DEEP`, `CODER`, and `ROUTER`.

## Examples

List models on a live OpenAI-compatible worker:

```text
python3 local_harness/icm_call.py handoff \
  --base-url http://127.0.0.1:8083/v1 \
  --list-models
```

Call a live worker and force final-answer output:

```text
python3 local_harness/icm_call.py handoff \
  --base-url http://127.0.0.1:8083/v1 \
  --model <MODEL_NAME> \
  --final-only \
  "Reply with exactly: ok"
```

When `icm_call.py` is pointed at an OpenAI-compatible local endpoint and the configured model looks
like an alias such as `openai/gemma4`, it now queries `/v1/models` first and swaps in the first
discovered concrete model id for the actual request. Response metadata preserves both the configured
alias and the resolved model used on the wire.

Run a supervised single-worker smoke test folder:

```text
python3 local_harness/run_single_worker.py \
  outputs/agent_runs/example-smoke-test \
  handoff \
  --base-url http://127.0.0.1:8083/v1 \
  --model <MODEL_NAME> \
  --final-only \
  --init-stubs \
  "Reply with exactly: ok"
```

When the worker call succeeds, review `OUTPUT.md`, edit `REVIEW.md`, promote any approved content
into `ACCEPTED.md`, and rerun `python3 local_harness/validate_agent_run.py <run-folder>` before
downstream use.

Run a supervised Aider task from the same run-folder shape:

```text
python3 local_harness/run_aider_worker.py \
  outputs/agent_runs/example-aider-task \
  --init-stubs \
  --read local_harness/run_single_worker.py \
  --read-head-lines 120 \
  local_harness/run_aider_worker.py
```

Run a supervised Aider task against a remote OpenAI-compatible endpoint:

```text
python3 local_harness/run_aider_worker.py \
  outputs/agent_runs/example-aider-remote \
  --aider-python ~/.local/share/uv/tools/aider-chat/bin/python \
  --openai-api-base http://<LAN_HOST>:8081/v1 \
  --model openai/<MODEL_ID> \
  --timeout 360 \
  --read README.md \
  --read-head-lines 20 \
  --compact-request-max-chars 700 \
  smoke_aider_note.txt
```

Use preflight first when a task looks even slightly large:

```text
python3 local_harness/run_aider_worker.py \
  outputs/agent_runs/example-aider-task \
  --preflight-only \
  --read local_harness/run_single_worker.py \
  --read-head-lines 120 \
  local_harness/run_aider_worker.py
```

This wrapper reads the Aider prompt from `MODEL_REQUEST.md`, writes the effective compacted prompt to
`AIDER_MESSAGE.md`, writes the budget analysis to `AIDER_PREFLIGHT.json`, snapshots trimmed `--read`
inputs into `00_read_snippets/`, can bundle or inline compact read digests for Gemma-local routing,
writes `AIDER_PREWARM.json` when prewarm is enabled, captures `AIDER_REQUEST.json` plus
`AIDER_EVENTS.jsonl`, archives per-attempt artifacts under `00_aider_attempts/`, writes combined
stdout/stderr to `OUTPUT.md`, records run metadata in `METRICS.json`, and preserves the usual
`REVIEW.md` plus `ACCEPTED.md` manager checkpoints.
It also passes `--no-gitignore` so Aider does not modify `.gitignore` during supervised smoke runs.

## Endpoint Note

Core endpoint-backed ZTH workflows expect an existing OpenAI-compatible
server. The `model_auditions/` download/start/stop scripts are a separate,
optional exception for exploratory evidence gathering. They are not a
production model-server manager, and starting or stopping a candidate server
does not promote or approve its model or establish production readiness. The
small-model audition harness does not add authentication headers; review
firewall and access controls before intentionally exposing a temporary server
to a LAN.

Some OpenAI-compatible local runtimes can return cleaner final content when `--final-only` is used.
Broader prompts may still spend the token budget inside hidden reasoning fields or long internal planning.
Treat the short smoke test as connection validation first, then tune prompt shape and token budget before
relying on richer outputs.

For a tiny supervised Aider smoke path, see [`docs/AIDER_FIRST_SUCCESS.md`](../docs/AIDER_FIRST_SUCCESS.md).
For external agent packet, comparison, and coverage tools, see
[`docs/AGENT_ADAPTER.md`](../docs/AGENT_ADAPTER.md).

If Aider runs time out, reduce read payload and prompt size first:

```text
--read-head-lines 20
--compact-request-max-chars 700
```

When using remote OpenAI-compatible backends with Aider, prefer `--model openai/<MODEL_ID>` so provider resolution remains explicit.
Treat endpoint prewarm as connectivity evidence only; slower local backends can still time out on the full Aider edit request.

For operator notes and historical boundary details, see [`docs/OPERATOR_NOTES.md`](../docs/OPERATOR_NOTES.md).
