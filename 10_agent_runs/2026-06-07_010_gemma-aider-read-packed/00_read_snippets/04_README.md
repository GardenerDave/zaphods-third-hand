# Read-only snippet
# Source: local_harness/README.md

# Local Harness

This folder contains the manager-side helper scripts for supervised local-worker runs.

## Scripts

- `icm_call.py`: configurable one-shot worker caller for native `/completion` and OpenAI-compatible `/v1` endpoints.
- `run_single_worker.py`: executes one audited single-worker run folder and writes `OUTPUT.md` plus `METRICS.json`.
- `run_aider_worker.py`: executes one audited Aider task from `MODEL_REQUEST.md`, adds Gemma-local preflight safeguards, and records the command output plus metrics.

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
  --model gemma-4-12B-it-qat-UD-Q4_K_XL.gguf \
  --final-only \
  "Reply with exactly: ok"
```

Run a supervised single-worker smoke test folder:

```text
python3 local_harness/run_single_worker.py \
  10_agent_runs/2026-06-07_001_smoke-test \
  handoff \
  --base-url http://localhost:8083/v1 \
  --model gemma-4-12B-it-qat-UD-Q4_K_XL.gguf \
  --final-only \
  --init-stubs \
  "Reply with exactly: ok"
```

When the worker call succeeds, review `OUTPUT.md`, edit `REVIEW.md`, promote any approved content into `ACCEPTED.md`, and rerun `python3 XX_backend/validate_agent_run.py <run-folder>` before downstream use.

Run a supervised Aider task from the same run-folder shape:

```text
python3 local_harness/run_aider_worker.py \
  10_agent_runs/2026-06-07_004_aider-worker-wrapper \
  --init-stubs \
  --read local_harness/run_single_worker.py \
  --read-head-lines 120 \
  local_harness/run_aider_worker.py
```

The default `gemma-local` profile sets `openai/gemma4`, `http://localhost:8083/v1`, `--map-tokens 0`, a 90 second API timeout, compacted prompt text, read-only file snapshots, and a context-budget preflight.

Use preflight first when a task looks even slightly large:

```text
python3 local_harness/run_aider_worker.py \
  10_agent_runs/2026-06-07_004_aider-worker-wrapper \
  --preflight-only \
  --read local_harness/run_single_worker.py \
  --read-head-lines 120 \
  local_harness/run_aider_worker.py
```

This wrapper reads the Aider prompt from `MODEL_REQUEST.md`, writes the effective compacted prompt to `AIDER_MESSAGE.md`, writes the budget analysis to `AIDER_PREFLIGHT.json`, snapshots trimmed `--read` inputs into `00_read_snippets/` when requested, writes combined stdout/stderr to `OUTPUT.md`, records run metadata in `METRICS.json`, and preserves the usual `REVIEW.md` plus `ACCEPTED.md` manager checkpoints.

## Endpoint Note

On the current `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf` runtime, short prompts on `chat/completions` can return clean final content when `--final-only` is used. Broader prompts may still spend the token budget inside `reasoning_content`. Treat the short smoke test as connection validation first, then tune prompt shape and token budget before relying on richer outputs.


[truncated after 88 lines]
