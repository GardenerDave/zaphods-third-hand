# Local Harness

This folder contains the manager-side helper scripts for supervised local-worker runs.

## Scripts

- `icm_call.py`: configurable one-shot worker caller for native `/completion` and OpenAI-compatible `/v1` endpoints.
- `run_single_worker.py`: executes one audited single-worker run folder and writes `OUTPUT.md` plus `METRICS.json`.
- `run_aider_worker.py`: executes one audited Aider task from `MODEL_REQUEST.md`, adds Gemma-local
  preflight safeguards, can prewarm the endpoint, and records command output plus debug artifacts.
- `llm_probe_smoke_probe.py`: calls one operator-supplied OpenAI-compatible endpoint with three fixed ZTH smoke probes and writes importer-compatible verified YAML plus raw local evidence; see [`docs/LLM_PROBE_PRODUCER_CONTRACT.md`](../docs/LLM_PROBE_PRODUCER_CONTRACT.md).
- `llm_probe_preflight_ingest.py`: imports versioned LLM-probe JSON as preflight-only plain-file evidence; see [`docs/LLM_PROBE_PREFLIGHT.md`](../docs/LLM_PROBE_PREFLIGHT.md).
- `llm_probe_preflight_compare.py`: compares two canonical preflight capability manifests and writes aggregate, human-reviewable regression evidence; see [`docs/LLM_PROBE_PREFLIGHT.md`](../docs/LLM_PROBE_PREFLIGHT.md).
- `preflight_audition_plan.py`: validates operator-supplied paths and prints a model-free, non-executing command plan from LLM-probe evidence or a capability manifest to a gated suite or board audition; see [`docs/PREFLIGHT_AUDITION_PLAN.md`](../docs/PREFLIGHT_AUDITION_PLAN.md).
- `model_auditions/`: optional exploratory small-model harness that can download candidate GGUFs, manage temporary local llama.cpp tmux sessions, or call existing local/LAN OpenAI-compatible endpoints; see [`model_auditions/README.md`](model_auditions/README.md).
- `logic_probe.py`: validates and mechanically scores ZTH-specific model logic probes, and can preserve raw evidence from existing OpenAI-compatible endpoints; see [`docs/LOGIC_PROBES.md`](../docs/LOGIC_PROBES.md).
- `failure_training/*.py`: model-free helpers for validating failure-curriculum
  JSONL, mixing curriculum rows, scoring eval JSONL, extracting miss-review
  scaffolds, converting completed reviews to draft curriculum candidates, and
  writing compact round reports; see
  [`docs/FAILURE_CURRICULUM_TRAINING.md`](../docs/FAILURE_CURRICULUM_TRAINING.md).
- `change_closeout.py`: prepares a bounded, model-free final-review evidence packet and Markdown closeout scaffold; see [`docs/CHANGE_CLOSEOUT.md`](../docs/CHANGE_CLOSEOUT.md).
- `tool_maker.py`: prepares a bounded, model-free workflow evidence packet and Markdown lifecycle draft scaffold; see [`docs/TOOL_MAKER.md`](../docs/TOOL_MAKER.md).
- `validate_scaffold.py`: validates Tool Maker and Change Closeout scaffold shape and metadata consistency without reading original sources or judging truth, safety, completeness, or promotion readiness.
- `repo_health_check.py`: reports Markdown-link, public-surface privacy, boundary-language, scaffold, diff-hygiene, and optional test health without changing files.
- `git_sync_cleanup.py`: reports local post-merge Git sync and branch-cleanup evidence and prints human-reviewable commands without executing cleanup.
- `agent_task_session.py`: creates a scoped, model-free Agent Task Session review packet under `.work/agent_tasks/` without running agents, checks, or Git commands.
- `historian_context_query.py`: one-command Project Historian ask plus exact-result ZTH context binding through the existing binder; see the Historian Context section below.
- `historian_ask_runner.py`: structured single-query runner executed by the Historian retrieval runtime on behalf of `historian_context_query.py`.
- `zth_preflight.py`: single read-only, fail-closing ZTH + Project Historian baseline preflight; see the ZTH + Historian Baseline Preflight section below.
- `zth_preflight_historian_runner.py`: structured baseline-validation runner executed by the Historian retrieval runtime on behalf of `zth_preflight.py`.
- `zth_task.py`: supervised task front door that composes the preflight, Historian ask-and-bind, Agent Task Sessions, and execution/review records into one bounded prepare/status/handoff workflow; see the Supervised Task Front Door section below.
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

The reusable endpoint workflow keeps three separate questions apart:

- Did the endpoint respond?
- Did the fixture scorer accept the response?
- Did the recorded raw evidence include usable duration diagnostics?

Those answers can differ. A raw run may succeed at transport but still fail
the behavioral checks, and a preserved raw directory can be rescored later
without another model call when only the scorer or summary changed.

For reviewer discipline:

- VM/Git host authority stays with the local machine running the tools;
- the endpoint is inference-only and does not grant execution authority;
- prompt patch v1 is behavioral guidance, while prompt patch v2 may be an
  exact-contract compatibility repair;
- `.work/` holds transient evidence, while `docs/reports/` holds selected
  durable summaries;
- failed evidence should remain intact so later scoring or review can compare
  before and after results.

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

## Supervised Task Front Door

`zth_task.py` is the single front door from an ordinary-language objective to
a validated, context-backed, execution-ready Agent Task Session. It composes
the existing mechanisms — baseline preflight, Historian ask-and-bind, Agent
Task Session packets, and execution/review records — without forking a second
task-packet implementation or lifecycle:

```text
python3 local_harness/zth_task.py prepare \
  "<objective in ordinary language>" \
  --historian-repo /path/to/project-historian \
  --interpreter-endpoint http://127.0.0.1:8084/v1 \
  --interpreter-model <MODEL_NAME>
```

The bare form `python3 local_harness/zth_task.py "<objective>"` is equivalent
to `prepare`. The interpreter endpoint and model may also be supplied through
`ZTH_TASK_INTERPRETER_ENDPOINT` / `ZTH_TASK_INTERPRETER_MODEL`.

Preparation records the objective verbatim under
`.work/zth_tasks/<task-id>/` (`objective.json`, `preflight.json`,
`semantic_interpretation.json`, `historian/index.json`,
`task_session_ref.json`, `task_summary.md`), asks the interpreter's proposed
Historian questions, binds the cited evidence, deterministically validates
the proposed scope (existing files or new files under existing directories
only; no wildcards, `.git`, `.work`, `outputs/`, `sources/`, private
configuration, or secret material), and creates plus validates a draft Agent
Task Session that carries the bound scope, required checks, non-goals, and
context references.

Task state is always derived from these durable artifacts — never a mutable
status flag:

```text
python3 local_harness/zth_task.py status <task-id>
python3 local_harness/zth_task.py handoff <task-id>
```

`status` reports `created`, `context_bound`, `ready_for_execution`,
`executed`, `reviewed` (with the recorded decision), or `blocked`, with the
next required operator action. `handoff` emits the exact validated agent
prompt and the exact `agent_task_session_record.py record-execution` command
for the returned evidence. Preparation grants no execution authority: a
validated packet is review material, not permission to act; execution
evidence is not acceptance; a commit is not acceptance; human review remains
a separate, required step. Preparation failures are preserved in the task
workspace (`failure.json`) and never auto-repaired or deleted. Focused
tests: `tests/test_zth_task.py`.

## Historian Context

Bind Project Historian query results into plain-file ZTH evidence, either
directly from an existing query directory or as one consolidated ask-and-bind
operation.

Bind an existing Historian ask query directory:

```text
python3 local_harness/historian_context.py bind \
  --query-dir <historian-repo>/.work/historian_queries/<query-id> \
  --records-dir <historian-repo>/records \
  --out-dir .work/<task>/evidence
```

Ask Project Historian and bind the exact result in one command:

```text
python3 local_harness/historian_context_query.py ask-bind \
  --question "What historical decisions constrain this task?" \
  --historian-repo <historian-repo> \
  --output-dir .work/<task>/evidence
```

Repeat `--question` to ask and bind several questions in one command; each
question produces its own independent `zth.historian_context.v0.1` artifact
through the same binder. Add `--json` for a machine-readable summary
(query id, exact query directory, context artifact paths, cited canonical
record ids, retrieval corpus fingerprint).

The consolidated command captures the exact query identity (request id and
request directory) from the structured Historian service result — it never
discovers queries by scanning or sorting Historian work directories. It
requires the reasoner endpoint via `HISTORIAN_REASONER_ENDPOINT` or
`--endpoint` (never hardcoded) and the supported bundled Historian retrieval
runtime (override with `--historian-python`). It fails closed on Historian
failures, missing query artifacts, identity mismatches, and binder failures,
preserving failed query artifacts for inspection. The Historian answer remains
advisory; a successful query or bind is not approval, and Project Historian
and its canonical records are never modified.

## ZTH + Historian Baseline Preflight

`zth_preflight.py` is a single read-only, fail-closing command that reports
the operational baseline for both repositories — replacing the repeated
per-repo status ceremony (`git status`, `git rev-parse HEAD`,
Historian canonical/projection validation, and a separate retrieval-state
currency check) with one invocation:

```bash
python3 local_harness/zth_preflight.py \
  --historian-repo /path/to/project-historian-v1
```

- `--zth-repo` defaults to the repository containing the module.
- Historian-side checks (canonical validation count, projection validation
  count, count agreement, retrieval-state currency) run through the supported
  bundled Historian retrieval runtime (`--historian-python` overrides it) via
  `zth_preflight_historian_runner.py`, a structured JSON runner executed by
  that runtime; nothing is inferred from timestamps.
- Retrieval state is classified as `current`, `stale`, `missing`, or
  `invalid` using Historian's own `historian.retrieval.validate_state` corpus
  fingerprint check plus a minimal embeddings artifact consistency check.
  Stale state is never silently rebuilt.
- Optional expectations (`--expect-zth-head`, `--expect-historian-head`,
  `--expect-record-count`) are explicit operator-supplied policy; phase
  expectations are never hardcoded in the tool.
- `--json` emits a machine-readable report (`zth.historian_baseline_preflight.v1`).
- Exit code 0 means every requested invariant was observed; any drift (dirty
  worktree, validation failure, count mismatch, non-current retrieval state,
  unsupported runtime, subprocess failure) exits 1 with actionable errors.
- The tool is an observer only: it mutates neither repository and grants no
  execution, file-modification, commit, merge, lifecycle, review, promotion,
  or training authority.

Focused tests: `tests/test_zth_preflight.py` (including a deliberate
negative control against real temporary Git fixture repositories).

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
