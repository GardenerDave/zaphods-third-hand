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

The default `gemma-local` profile sets `openai/gemma4`, `http://localhost:8083/v1`, `--map-tokens 0`, a 90 second API timeout, compacted prompt text, read-only file snapshots, protocol-overhead budgeting, automatic endpoint prewarm, one manager-side rerun after a pure connection-retry failure, a manager subprocess timeout guard slightly above the model timeout, minimal-prompt env flags, request/event capture, optional read bundling, optional inline read digests, and a deterministic direct-edit path that can short-circuit Aider before launch or recover after timeout when the selected files fit a bounded literal replacement, unique-anchor insertion, block replacement, excerpt SEARCH/REPLACE patch, or deterministic batch plan.

Current direct-edit prompt shapes:

- Replace: ``- In `path`, replace `old` with `new`.`` then ``- Edit only the listed file.``
- Insert after: ``- In `path`, insert `new` after `anchor`.`` then ``- Edit only the listed file.``
- Insert before: ``- In `path`, insert `new` before `anchor`.`` then ``- Edit only the listed file.``
- Replace block: ``- In `path`, replace the block from `start` through `end` with `new`.`` then ``- Edit only the listed file.``
- Excerpt patch: ``- In `path`, apply excerpt patches.`` then a fenced ``SEARCH/REPLACE`` patch set, then ``- Edit only the listed file.``
- One-file batch: multiple operation bullets targeting the same file, followed by ``- Edit only the listed file.`` The steps run sequentially, so later steps may rely on text created by earlier ones.
- Mixed batch: one excerpt patch plus literal deterministic operations across the selected files, followed by ``- Edit only the listed files.`` Each step still has to stay unique at the point where it is applied.
- Multi-file batch: multiple operation bullets targeting up to 4 selected files, followed by ``- Edit only the listed files.`` Each step still has to stay unique at the point where it is applied.

Literal replace/insert/block routes now decode escaped ``\n``, ``\r``, and ``\t`` sequences inside backticked text, so authored `MODEL_REQUEST.md` files do not need manual newline expansion for common line-based edits.

Guardrails remain strict:

- exactly one selected file for replacement, insertion, block replacement, excerpt patch, and one-file batch routes
- up to 4 selected files for deterministic multi-file batches
- prompt length at or below 1200 characters for one-file replacement, insertion, block replacement, and one-file batch routes
- prompt length at or below 2400 characters for deterministic multi-file batches
- prompt length at or below 4096 characters for excerpt SEARCH/REPLACE patch sets
- file size at or below 24576 bytes per targeted file
- each target, anchor, or SEARCH excerpt appears exactly once at the step where it is used

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

For Aider specifically, the main failure modes seen so far were:

- Oversized combined context from prompt plus repo map plus read-only files.
- Planning-heavy output that consumed time without producing edits.
- Long silent runs that ended in timeout.
- Cold-endpoint retry loops that surface as `OpenAIException - Connection error` from the Aider/LiteLLM path before a later success.
- False connection failures when the run is executed inside the Codex sandbox, because the sandbox cannot reliably reach the local endpoint.

The `gemma-local` Aider profile is meant to fail early on the sizing problems, and to make the transport story explicit when a run does go out. It now records `fatal_error_detected`, `connection_error_detected`, `timeout_hint_detected`, `manager_timeout_detected`, `direct_edit_fallback_triggered`, `direct_edit_short_circuit_triggered`, retry counts, prewarm results, manager rerun attempts, direct-edit classification artifacts, and Aider request/event summaries in `METRICS.json`. `AIDER_PREFLIGHT.json` now also records explicit `direct_edit_candidate` eligibility metadata plus `direct_edit_budget_bypass_available` so the manager can see when Aider should be bypassed before launch and when a deterministic route can ignore the Aider token budget entirely.

Historical internal run folders are intentionally not included in this public toolkit. Treat the boundaries below as design notes, not bundled evidence.

The wrapper now reports `validated_shape_match` in `AIDER_PREFLIGHT.json` and `METRICS.json` when a run stays inside the current Gemma-local routing heuristic:

- repo map disabled
- compacted prompt
- up to 10 editable files
- up to 1 read-only file snapshot
- about 500 estimated input tokens or less

Treat that as a routing hint, not a guarantee or proven upper bound.

## Current Boundary

The audited runs now show a more useful boundary story:

- Direct local `/v1` chat calls still work on `http://localhost:8083/v1`.
- Aider can complete at least ten tiny editable files, plus one real trimmed read-only input, when the run is outside the sandbox and the wrapper performs one direct prewarm call first.
- For one-file deterministic replacements, the manager-side direct-edit path is now live-proven both as a pre-Aider shortcut and as a post-timeout fallback.
- The deterministic direct-edit file-size ceiling is now 24576 bytes per targeted file, and run `2026-06-08_043_*` live-proved the widened ceiling on a 20301-byte handoff document.
- Deterministic insert-after and insert-before edits are now manager-routable when each anchor stays unique at the step where it is used.
- Batched one-file deterministic edits are now manager-routable when each step stays unique.
- Excerpt SEARCH/REPLACE patch sets are now manager-routable when each search stays unique at the step where it is applied.
- Mixed excerpt-plus-literal batches are now manager-routable when the excerpt SEARCH block and every literal step stay unique at the point where each step is applied.
- Bounded deterministic multi-file batches are now manager-routable for up to 4 selected files, and run `2026-06-08_043_*` live-proved the path on 2 real repo files.
- Literal deterministic routes now decode escaped newline/tab/carriage-return sequences from authored prompts, which removed the prompt-shaping friction exposed by `2026-06-08_044_*`.
- `validated_shape_match` is only a routing hint for Aider-sized work. Run `2026-06-08_033_*` showed a thin real-code file can still stall while matching that heuristic.
- Without prewarm, the same tiny one-file run may burn multiple transient retries before succeeding.
- The wrapper can now rerun Aider once automatically after a pure connection-retry failure with no edits, preserving attempt-by-attempt artifacts.
- Deterministic block replacement is now manager-routable when both block anchors are unique.
- Direct-edit-eligible work can now bypass the Aider budget gate even when `within_budget: false`, which is necessary for over-budget deterministic multi-file runs like `2026-06-08_043_*`.
- Runs launched inside the sandbox can look like provider failures even when the same run succeeds immediately outside the sandbox.

The newer read-context experiments are still valuable:

- Preflight must account for the full model request footprint, not only visible user prompt text.
- Direct endpoint prewarm can reduce cold-start retry noise before Aider-backed work.
- `validated_shape_match` is only a routing hint. It is not a guarantee that a model-backed edit will finish.
- Deterministic direct-edit shortcuts are useful for tiny, explicit, uniquely anchored edits.
- Direct-edit-eligible work can bypass model budget gates only when the manager-side parser can prove the edit is bounded and unique.
- Escaped newline, tab, and carriage-return sequences in authored prompts should be decoded before unique matching.
