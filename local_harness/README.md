# Local Harness

This folder contains the manager-side helper scripts for supervised local-worker runs.

## Scripts

- `icm_call.py`: configurable one-shot worker caller for native `/completion` and OpenAI-compatible `/v1` endpoints.
- `run_single_worker.py`: executes one audited single-worker run folder and writes `OUTPUT.md` plus `METRICS.json`.
- `run_aider_worker.py`: executes one audited Aider task from `MODEL_REQUEST.md`, adds Gemma-local
  preflight safeguards, can prewarm the endpoint, and records command output plus debug artifacts.
- `llm_probe_preflight_ingest.py`: imports versioned LLM-probe JSON as preflight-only plain-file evidence; see [`docs/LLM_PROBE_PREFLIGHT.md`](../docs/LLM_PROBE_PREFLIGHT.md).
- `llm_probe_preflight_compare.py`: compares two canonical preflight capability manifests and writes aggregate, human-reviewable regression evidence; see [`docs/LLM_PROBE_PREFLIGHT.md`](../docs/LLM_PROBE_PREFLIGHT.md).
- `auditions/`: board/capability-card workflow using suites, fixtures, scorer profiles, board comparisons, capability cards, and optional preflight gates; see [`auditions/README.md`](auditions/README.md).
- `model_auditions/`: optional exploratory small-model harness that can download candidate GGUFs, manage temporary local llama.cpp tmux sessions, or call existing local/LAN OpenAI-compatible endpoints; see [`model_auditions/README.md`](model_auditions/README.md).
- `zth_agent_packet.py`: generates one independent role/context packet for an external agent.
- `zth_compare_agent_outputs.py`: compares completed external-agent outputs that follow the ZTH contract.
- `zth_coverage_auditor.py`: reports obvious pre-synthesis coverage areas and blind spots.

## Choose an Audition Workflow

- Use [`auditions/`](auditions/README.md) when you need the structured
  suite/board workflow, capability cards, comparisons, or optional preflight
  gating.
- Use [`model_auditions/`](model_auditions/README.md) when you need exploratory
  GGUF download, temporary llama.cpp/tmux lifecycle support, existing
  local/LAN endpoints, raw prompt responses, and mechanical scoring.

Of the two audition workflows, only the board/capability-card workflow consumes
preflight manifests. The small-model exploratory harness does not currently
consume preflight gates. Their output files and schemas differ, so keep
evidence under separate roots such as `.work/model_auditions/board_runs/` and
`.work/model_auditions/exploratory_runs/`.

Neither workflow promotes, approves, assigns, or production-certifies a model.

## Internal Modules

- `aider_prep.py`: prompt compaction, read-context shaping, and preflight budgeting helpers used by `run_aider_worker.py`.
- `aider_runtime.py`: thin compatibility layer that re-exports the smaller runtime helper modules used by `run_aider_worker.py`.
- `aider_transport.py`: command construction and environment helpers for Aider runs.
- `aider_reporting.py`: attempt archiving, output summarization, and event-log parsing helpers for Aider runs.
- `aider_metrics.py`: run metadata assembly helpers for Aider runs.
- `tests/test_run_aider_worker.py`, `tests/test_aider_prep.py`, and `tests/test_aider_runtime.py`:
  split test surfaces so local Aider tasks can target smaller real-code files.

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
