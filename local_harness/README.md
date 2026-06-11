# Local Harness

This folder contains the manager-side helper scripts for supervised local-worker runs.

## Scripts

- `icm_call.py`: configurable one-shot worker caller for native `/completion` and OpenAI-compatible `/v1` endpoints.
- `run_single_worker.py`: executes one audited single-worker run folder and writes `OUTPUT.md` plus `METRICS.json`.
- `run_aider_worker.py`: executes one audited Aider task from `MODEL_REQUEST.md`, adds Gemma-local preflight safeguards, can prewarm the endpoint, and records command output plus debug artifacts.

## Internal Modules

- `aider_prep.py`: prompt compaction, read-context shaping, and preflight budgeting helpers used by `run_aider_worker.py`.
- `aider_runtime.py`: thin compatibility layer that re-exports the smaller runtime helper modules used by `run_aider_worker.py`.
- `aider_transport.py`: command construction and environment helpers for Aider runs.
- `aider_reporting.py`: attempt archiving, output summarization, and event-log parsing helpers for Aider runs.
- `aider_metrics.py`: run metadata assembly helpers for Aider runs.
- `tests/test_run_aider_worker.py`, `tests/test_aider_prep.py`, and `tests/test_aider_runtime.py`: split test surfaces so local Aider tasks can target smaller real-code files.

## Configuration

The defaults preserve the sanitized placeholder hosts from the handoff bundle. Override them per call with CLI flags or environment variables:

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
  --base-url http://localhost:8083/v1 \
  --list-models
```

Call a live worker and force final-answer output:

```text
python3 local_harness/icm_call.py handoff \
  --base-url http://localhost:8083/v1 \
  --model <MODEL_NAME> \
  --final-only \
  "Reply with exactly: ok"
```

When `icm_call.py` is pointed at an OpenAI-compatible local endpoint and the configured model looks like an alias such as `openai/gemma4`, it now queries `/v1/models` first and swaps in the first discovered concrete model id for the actual request. Response metadata preserves both the configured alias and the resolved model used on the wire.

Run a supervised single-worker smoke test folder:

```text
python3 local_harness/run_single_worker.py \
  outputs/agent_runs/example-smoke-test \
  handoff \
  --base-url http://localhost:8083/v1 \
  --model <MODEL_NAME> \
  --final-only \
  --init-stubs \
  "Reply with exactly: ok"
```

When the worker call succeeds, review `OUTPUT.md`, edit `REVIEW.md`, promote any approved content into `ACCEPTED.md`, and rerun `python3 local_harness/validate_agent_run.py <run-folder>` before downstream use.

Run a supervised Aider task from the same run-folder shape:

```text
python3 local_harness/run_aider_worker.py \
  outputs/agent_runs/example-aider-task \
  --init-stubs \
  --read local_harness/run_single_worker.py \
  --read-head-lines 120 \
  local_harness/run_aider_worker.py
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

This wrapper reads the Aider prompt from `MODEL_REQUEST.md`, writes the effective compacted prompt to `AIDER_MESSAGE.md`, writes the budget analysis to `AIDER_PREFLIGHT.json`, snapshots trimmed `--read` inputs into `00_read_snippets/`, can bundle or inline compact read digests for Gemma-local routing, writes `AIDER_PREWARM.json` when prewarm is enabled, captures `AIDER_REQUEST.json` plus `AIDER_EVENTS.jsonl`, archives per-attempt artifacts under `00_aider_attempts/`, writes combined stdout/stderr to `OUTPUT.md`, records run metadata in `METRICS.json`, and preserves the usual `REVIEW.md` plus `ACCEPTED.md` manager checkpoints.

## Endpoint Note

Some OpenAI-compatible local runtimes can return cleaner final content when `--final-only` is used. Broader prompts may still spend the token budget inside hidden reasoning fields or long internal planning. Treat the short smoke test as connection validation first, then tune prompt shape and token budget before relying on richer outputs.

For operator notes and historical boundary details, see [`docs/OPERATOR_NOTES.md`](../docs/OPERATOR_NOTES.md).
