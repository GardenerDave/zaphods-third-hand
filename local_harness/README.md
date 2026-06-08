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
  --model gemma-4-12B-it-qat-UD-Q4_K_XL.gguf \
  --final-only \
  "Reply with exactly: ok"
```

When `icm_call.py` is pointed at an OpenAI-compatible local endpoint and the configured model looks like an alias such as `openai/gemma4`, it now queries `/v1/models` first and swaps in the first discovered concrete model id for the actual request. Response metadata preserves both the configured alias and the resolved model used on the wire.

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
  10_agent_runs/2026-06-07_004_aider-worker-wrapper \
  --preflight-only \
  --read local_harness/run_single_worker.py \
  --read-head-lines 120 \
  local_harness/run_aider_worker.py
```

This wrapper reads the Aider prompt from `MODEL_REQUEST.md`, writes the effective compacted prompt to `AIDER_MESSAGE.md`, writes the budget analysis to `AIDER_PREFLIGHT.json`, snapshots trimmed `--read` inputs into `00_read_snippets/`, can bundle or inline compact read digests for Gemma-local routing, writes `AIDER_PREWARM.json` when prewarm is enabled, captures `AIDER_REQUEST.json` plus `AIDER_EVENTS.jsonl`, archives per-attempt artifacts under `00_aider_attempts/`, writes combined stdout/stderr to `OUTPUT.md`, records run metadata in `METRICS.json`, and preserves the usual `REVIEW.md` plus `ACCEPTED.md` manager checkpoints.

## Endpoint Note

On the current `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf` runtime, short prompts on `chat/completions` can return clean final content when `--final-only` is used. Broader prompts may still spend the token budget inside `reasoning_content`. Treat the short smoke test as connection validation first, then tune prompt shape and token budget before relying on richer outputs.

For Aider specifically, the main failure modes seen so far were:

- Oversized combined context from prompt plus repo map plus read-only files.
- Planning-heavy output that consumed time without producing edits.
- Long silent runs that ended in timeout.
- Cold-endpoint retry loops that surface as `OpenAIException - Connection error` from the Aider/LiteLLM path before a later success.
- False connection failures when the run is executed inside the Codex sandbox, because the sandbox cannot reliably reach the local endpoint.

The `gemma-local` Aider profile is meant to fail early on the sizing problems, and to make the transport story explicit when a run does go out. It now records `fatal_error_detected`, `connection_error_detected`, `timeout_hint_detected`, `manager_timeout_detected`, `direct_edit_fallback_triggered`, `direct_edit_short_circuit_triggered`, retry counts, prewarm results, manager rerun attempts, direct-edit classification artifacts, and Aider request/event summaries in `METRICS.json`. `AIDER_PREFLIGHT.json` now also records explicit `direct_edit_candidate` eligibility metadata plus `direct_edit_budget_bypass_available` so the manager can see when Aider should be bypassed before launch and when a deterministic route can ignore the Aider token budget entirely.

Validated success cases now exist for:

- `10_agent_runs/2026-06-07_005_gemma-aider-smoke/`: one tiny editable file, about 94 estimated input tokens, completed in about 9.2 seconds.
- `10_agent_runs/2026-06-07_006_gemma-aider-two-file/`: two tiny editable files, about 145 estimated input tokens, completed in about 17.1 seconds.
- `10_agent_runs/2026-06-07_007_gemma-aider-read-context/`: one tiny editable file plus one trimmed read-only file, about 173 estimated input tokens, completed in about 12.2 seconds.
- `10_agent_runs/2026-06-07_008_gemma-aider-three-file/`: three tiny editable files, about 195 estimated input tokens, completed in about 15.0 seconds.
- `10_agent_runs/2026-06-07_020_gemma-aider-clean-smoke/`: one tiny editable file succeeded after eight transient retries and one eventual success, proving the cold-start issue is recoverable.
- `10_agent_runs/2026-06-07_021_gemma-aider-prewarm-smoke/`: one tiny editable file completed with zero retries after a direct prewarm call.
- `10_agent_runs/2026-06-07_022_gemma-aider-four-file/`: four tiny editable files completed with one request after prewarm.
- `10_agent_runs/2026-06-07_023_gemma-aider-six-file/`: six tiny editable files completed with one request after prewarm.
- `10_agent_runs/2026-06-07_024_gemma-aider-eight-file/`: eight tiny editable files completed with one request after prewarm.
- `10_agent_runs/2026-06-07_025_gemma-aider-ten-file/`: ten tiny editable files completed with one request after prewarm.
- `10_agent_runs/2026-06-07_026_gemma-aider-ten-file-read-context/`: ten tiny editable files plus one real trimmed read-only input completed with one request after prewarm.
- `10_agent_runs/2026-06-08_032_gemma-aider-direct-edit-proof/`: one real one-file code task still timed out on the Aider path, but the manager-side direct-edit fallback applied the requested unique replacement successfully and preserved passing tests.
- `10_agent_runs/2026-06-08_034_gemma-aider-direct-edit-shortcut/`: one real one-file deterministic change completed entirely through manager-side direct-edit short-circuit, with zero Aider and zero endpoint usage.
- `10_agent_runs/2026-06-08_035_gemma-direct-edit-large-readme/`: one real 10507-byte file change completed entirely through manager-side direct-edit short-circuit, proving the widened deterministic envelope beyond the old 4096-byte ceiling.
- `10_agent_runs/2026-06-08_036_gemma-direct-edit-insert-readme/`: one real 11895-byte file change completed entirely through manager-side direct-edit `insert_after` short-circuit, proving the additive edit shape on a large repo file.
- `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/`: one real 12967-byte file change completed entirely through manager-side direct-edit `replace_block` short-circuit after widening the deterministic prompt cap to 1200.
- `10_agent_runs/2026-06-08_039_gemma-direct-edit-batch-readme/`: one real 13805-byte file change completed entirely through manager-side direct-edit batch short-circuit, proving sequential one-file deterministic edits.
- `10_agent_runs/2026-06-08_041_gemma-excerpt-patch-readme-fixed/`: one real 14579-byte file change completed entirely through manager-side direct-edit `excerpt_patch` short-circuit after widening the excerpt prompt cap to 4096.
- `10_agent_runs/2026-06-08_043_gemma-direct-edit-multi-file-docs-fixed/`: one over-budget two-file documentation change completed entirely through manager-side multi-file deterministic short-circuit, proving that direct-edit-eligible work can bypass the Aider budget gate.
- `10_agent_runs/2026-06-08_045_gemma-direct-edit-mixed-batch-docs-fixed/`: one over-budget two-file documentation change completed entirely through manager-side `mixed_batch` short-circuit, proving that one excerpt patch plus one literal deterministic operation can share the same manager batch.

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

- `2026-06-07_009_*` showed the old preflight undercounted real Aider request footprint.
- `2026-06-07_010_*` through `2026-06-07_015_*` showed that overhead reservation, read fitting, read bundling, and tiny bundled read budgets were not enough once the Aider transport entered the current failing state.
- `2026-06-07_016_*` showed that inline read digests alone do not solve the cold-start retry issue.
- `2026-06-07_020_*` and `2026-06-07_021_*` isolated the real fix for cold starts: direct prewarm before Aider.
- `2026-06-07_024_*` through `2026-06-07_026_*` moved the validated boundary from six tiny files to ten tiny files plus one trimmed read-only input.
- `2026-06-07_028_*` showed that a real two-file code task could stay within budget and still stall long enough to require manual intervention.
- `2026-06-07_029_*` validated the manager-side subprocess timeout guard: the same two-file code shape now exits cleanly with explicit timeout classification instead of hanging indefinitely.
- `2026-06-08_032_*` validated the direct-edit fallback on a real one-file code task after the Aider path stalled, proving that tiny deterministic changes can now be recovered automatically within the manager wrapper.
- `2026-06-08_033_*` showed that even a thin one-file real-code task can still stall while reporting `validated_shape_match: true`, so that heuristic must remain only a routing hint.
- `2026-06-08_034_*` showed that eligible deterministic one-file replacements can bypass Aider entirely through direct-edit short-circuit, with zero prewarm and zero endpoint usage.
- `2026-06-08_035_*` moved the direct-edit ceiling by proving the widened `16384`-byte file-size guardrail on a real `10507`-byte project file.
- `2026-06-08_036_*` extended the direct-edit route from replacement-only to additive editing by live-proving `insert_after` on a real `11895`-byte project file.
- `2026-06-08_037_*` showed that the old deterministic prompt cap of `600` was too low for a practical real-file block-replacement request, even though the edit shape itself was valid.
- `2026-06-08_038_*` fixed that boundary by widening the cap to `1200` and live-proving `replace_block` on a real `12967`-byte project file.
- `2026-06-08_039_*` extended the direct-edit route from single-operation edits to sequential one-file batches by live-proving a two-step edit plan on a real `13805`-byte project file.
- `2026-06-08_040_*` showed that the shared `1200`-character deterministic prompt cap was too low for a real two-hunk excerpt patch request (`prompt_char_count: 1620`), even though the patch grammar itself was valid.
- `2026-06-08_041_*` fixed that boundary by widening the excerpt patch cap to `4096` and live-proving a two-hunk README patch through manager-only short-circuit.
- `2026-06-08_042_*` showed that the old manager path still blocked a valid multi-file deterministic plan because one target file exceeded the old `16384`-byte limit and the Aider budget gate ran before the direct-edit short-circuit.
- `2026-06-08_043_*` fixed that boundary by widening the deterministic file-size ceiling to `24576` bytes and allowing direct-edit-eligible work to bypass the Aider budget gate, then live-proved a two-file over-budget documentation batch with zero Aider and zero endpoint usage.
- `2026-06-08_044_*` showed that mixed excerpt-plus-literal routing already worked logically, but authored literal prompts using escaped newline text still failed unique matching because the old parser treated `\n` as two characters.
- `2026-06-08_045_*` fixed that friction by decoding escaped newline/tab/carriage-return sequences in literal direct-edit operations and live-proved a two-file over-budget mixed batch with zero Aider and zero endpoint usage.
