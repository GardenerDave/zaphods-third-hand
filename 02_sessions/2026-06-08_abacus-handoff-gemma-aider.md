# Abacus Handoff: Gemma + Aider Local Endpoint

## Scope

This note captures the current manager-side state for the local Gemma+Aider workflow in the sanitized ICM bundle, with enough detail for Abacus to continue without replaying the full terminal history.

Date: 2026-06-08

Repository root:

```text
/home/owner/Desktop/ICM_Workflow_Optimization_Handoff_SANITIZED/ICM_Workflow_Optimization_Handoff
```

## What Changed

### 1. `icm_call` was split and hardened

Files:

- `local_harness/icm_call.py`
- `local_harness/icm_spec.py`
- `local_harness/icm_parsers.py`

Result:

- `icm_call.py` now resolves OpenAI-style aliases such as `openai/gemma4` by calling `/v1/models` first and swapping in the first concrete model id for the real request.
- Direct local worker calls remain the baseline sanity check for the endpoint.

### 2. `run_aider_worker.py` was rebuilt as a thin orchestrator

Files:

- `local_harness/run_aider_worker.py`
- `local_harness/aider_prep.py`
- `local_harness/aider_runtime.py`

Important context:

- The wrapper source file was missing at one point while the split helper modules still existed.
- I reconstructed `run_aider_worker.py` around those helper modules instead of relying on bytecode cache.

Result:

- The CLI contract used by the test suite is preserved.
- Intermixed argument parsing works again, so calls like `run_folder --flag value file_a file_b` are supported.

### 3. The Aider test surface was split

Files:

- `local_harness/tests/test_run_aider_worker.py`
- `local_harness/tests/test_aider_prep.py`
- `local_harness/tests/test_aider_runtime.py`

Reason:

- The old single `test_run_aider_worker.py` was too large for efficient local-model editing.
- The split creates smaller real-code targets for future Aider runs.

### 4. Manager-side timeout bounding was added

File:

- `local_harness/run_aider_worker.py`

Result:

- Aider subprocesses are now bounded slightly above the model timeout.
- Timeout failures are recorded explicitly in `METRICS.json` as:
  - `manager_timeout_detected`
  - `timeout_event_detected`
  - `fatal_error_detected`

### 5. Deterministic direct-edit fallback was added

Files:

- `local_harness/run_aider_worker.py`
- `local_harness/tests/test_run_aider_worker.py`
- `local_harness/README.md`

Result:

- After a timeout-shaped Aider attempt with no edits, the wrapper now tries a narrow fallback for one-file deterministic direct-edit requests parsed from `MODEL_REQUEST.md`.
- The current supported shapes are unique literal replacement and unique-anchor insertion.
- The fallback applies only when there is exactly one unique match in the target file or exactly one unique anchor occurrence for insertion.
- It writes `AIDER_DIRECT_EDIT.json` for applied and classified non-applied cases.
- `METRICS.json` now records `direct_edit_fallback_triggered` and `aider_debug.direct_edit_path`.
- Existing manager timeout bounding behavior remains in place.

### 6. Direct-edit fallback was live-validated

Run folder:

- `10_agent_runs/2026-06-08_032_gemma-aider-direct-edit-proof/`

Result:

- A one-file real-code Aider run on `local_harness/tests/test_aider_runtime.py` still stalled after dispatch and exited via manager timeout.
- The wrapper then applied the deterministic replacement successfully through the direct-edit fallback.
- Repo tests still passed after the fallback-applied change.
- This is now proven behavior, not just unit-tested behavior.

### 7. Thin-file real-code Aider still stalls despite `validated_shape_match`

Run folder:

- `10_agent_runs/2026-06-08_033_gemma-aider-metrics-thin-file/`

Result:

- A bounded one-file run targeted the much smaller `local_harness/aider_metrics.py` surface.
- Preflight stayed within budget and still reported `validated_shape_match: true`.
- Prewarm succeeded.
- The run still stalled after dispatch and exited through manager timeout with no edits.

Meaning:

- `validated_shape_match` is useful as a routing hint only.
- It does not predict successful real-code completion.

### 8. Direct-edit short-circuit was live-validated

Run folder:

- `10_agent_runs/2026-06-08_034_gemma-aider-direct-edit-shortcut/`

Result:

- A one-file deterministic replacement on `local_harness/tests/test_aider_runtime.py` completed before any Aider or prewarm call.
- `final_attempt_number` was `0`, with empty `aider_attempts` and `prewarm_attempts`.

Meaning:

- The manager can now bypass the unstable Aider path completely for eligible deterministic one-file changes.

### 9. The direct-edit envelope was widened and live-proven on a larger real file

Run folder:

- `10_agent_runs/2026-06-08_035_gemma-direct-edit-large-readme/`

Result:

- The manager classified a deterministic change on `local_harness/README.md` as direct-edit eligible and applied it immediately.
- Target file size was `10507` bytes, above the previous `4096`-byte ceiling.
- Current live-proven guardrails are `prompt_char_limit: 1200` and `file_size_limit_bytes: 16384`.

Meaning:

- The deterministic manager path now reaches materially larger one-file changes without any endpoint or Aider cost.

### 10. Deterministic insert-after was live-validated

Run folder:

- `10_agent_runs/2026-06-08_036_gemma-direct-edit-insert-readme/`

Result:

- A deterministic insert-after change on `local_harness/README.md` completed before any Aider or prewarm call.
- Target file size at run time was `11895` bytes.
- Preflight direct-edit classification reported `operation: insert_after` and `eligible: true`.

Meaning:

- The deterministic manager path is no longer replacement-only.
- Additive one-file edits can now bypass the unstable Aider path under the same guardrails.

### 11. Deterministic block replacement exposed a prompt-cap limit, then moved it

Run folders:

- `10_agent_runs/2026-06-08_037_gemma-direct-edit-block-readme/`
- `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/`

Result:

- `037` showed the first real block-replacement prompt was valid in shape but too long for the old deterministic manager limit (`prompt_char_count: 828`, `prompt_char_limit: 600`), so the wrapper fell through to whole-file Aider and timed out.
- The deterministic prompt cap was then widened to `1200`.
- `038` reran the same block-replacement task and classified it as direct-edit eligible with `operation: replace_block`, `start_anchor_match_count: 1`, and `end_anchor_match_count: 1`.
- `038` completed with `final_attempt_number: 0`, empty `aider_attempts`, and empty `prewarm_attempts`.

Meaning:

- The next real limit was not block-replacement logic, but the deterministic prompt cap.
- Widening that cap moved the manager boundary in a measurable way and enabled real-file block replacement without Aider.

### 12. Sequential one-file direct-edit batching was live-validated

Run folder:

- `10_agent_runs/2026-06-08_039_gemma-direct-edit-batch-readme/`

Result:

- A two-step deterministic edit plan on `local_harness/README.md` completed before any Aider or prewarm call.
- Preflight classified the request as direct-edit eligible with `operation: batch`, `operation_count: 2`, and `operation_types: ["replace", "insert_after"]`.
- The second step used an anchor that only existed after the first step ran.

Meaning:

- The deterministic manager path now supports small sequential one-file edit plans, not only single operations.

### 13. Excerpt SEARCH/REPLACE patch routing exposed a prompt-cap limit, then moved it

Run folders:

- `10_agent_runs/2026-06-08_040_gemma-excerpt-patch-readme/`
- `10_agent_runs/2026-06-08_041_gemma-excerpt-patch-readme-fixed/`

Result:

- `040` showed that the excerpt patch grammar matched a real two-hunk README patch, but the shared deterministic prompt cap of `1200` was too low (`prompt_char_count: 1620`), so the wrapper fell through to whole-file Aider and timed out.
- The excerpt patch prompt cap was then widened to `4096`.
- `041` reran the same README patch and completed before any Aider or prewarm call.
- Preflight classified `041` as direct-edit eligible with `operation: excerpt_patch`, `patch_count: 2`, and `prompt_char_limit: 4096`.

Meaning:

- Excerpt SEARCH/REPLACE patch sets are now manager-routable under a wider prompt budget than literal one-line edits.

### 14. Bounded multi-file deterministic batching exposed a budget-gate/file-size limit, then moved both

Run folders:

- `10_agent_runs/2026-06-08_042_gemma-direct-edit-multi-file-docs/`
- `10_agent_runs/2026-06-08_043_gemma-direct-edit-multi-file-docs-fixed/`

Result:

- `042` showed a valid two-file deterministic documentation batch on `local_harness/README.md` and `02_sessions/2026-06-08_abacus-handoff-gemma-aider.md`, but the old manager path still blocked it because the handoff file exceeded the old `16384`-byte direct-edit ceiling and the Aider budget gate ran before the short-circuit.
- The deterministic file-size ceiling was then widened to `24576` bytes per targeted file.
- The manager was also updated so direct-edit-eligible work can bypass the Aider budget gate.
- `043` reran the same two-file batch and completed before any Aider or prewarm call even though `within_budget: false`.
- Preflight classified `043` as direct-edit eligible with `operation: multi_file_batch`, `operation_count: 3`, `target_file_count: 2`, `file_size_limit_bytes: 24576`, and `direct_edit_budget_bypass_available: true`.

Meaning:

- The deterministic manager path no longer stops at one file when the plan stays bounded and unique.
- Over-budget deterministic work no longer has to pay the whole-file Aider path first.
- Mixed excerpt-plus-literal batches across selected files are now live-proven.

### 15. Mixed excerpt-plus-literal batching exposed escaped-newline prompt friction, then moved it

Run folders:

- `10_agent_runs/2026-06-08_044_gemma-direct-edit-mixed-batch-docs/`
- `10_agent_runs/2026-06-08_045_gemma-direct-edit-mixed-batch-docs-fixed/`

Result:

- `044` showed that the new mixed route already parsed correctly as `operation: mixed_batch` with one excerpt patch plus one literal insert across two selected files, but the literal step failed unique matching because the authored prompt used escaped newline text and the old literal parser treated `\n` as two characters.
- Literal direct-edit parsing was then updated to decode escaped newline, tab, and carriage-return sequences inside backticked literal text.
- `045` reran the same two-file task unchanged and completed before any Aider or prewarm call even though `within_budget: false`.
- Preflight classified `045` as direct-edit eligible with `operation: mixed_batch`, `operation_count: 2`, `operation_types: ["excerpt_patch", "insert_after"]`, `target_file_count: 2`, `prompt_char_limit: 4096`, and `direct_edit_budget_bypass_available: true`.

Meaning:

- One manager batch can now mix an excerpt SEARCH/REPLACE patch with literal deterministic steps across selected files.
- Authored prompts no longer need manual newline expansion for common literal line-based edits.

## Current Validated Operating Envelope

Confirmed successful synthetic/task-shaping runs:

- `10_agent_runs/2026-06-07_024_gemma-aider-eight-file/`
- `10_agent_runs/2026-06-07_025_gemma-aider-ten-file/`
- `10_agent_runs/2026-06-07_026_gemma-aider-ten-file-read-context/`
- `10_agent_runs/2026-06-08_032_gemma-aider-direct-edit-proof/`
- `10_agent_runs/2026-06-08_034_gemma-aider-direct-edit-shortcut/`
- `10_agent_runs/2026-06-08_035_gemma-direct-edit-large-readme/`
- `10_agent_runs/2026-06-08_036_gemma-direct-edit-insert-readme/`
- `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/`
- `10_agent_runs/2026-06-08_039_gemma-direct-edit-batch-readme/`
- `10_agent_runs/2026-06-08_041_gemma-excerpt-patch-readme-fixed/`
- `10_agent_runs/2026-06-08_043_gemma-direct-edit-multi-file-docs-fixed/`
- `10_agent_runs/2026-06-08_045_gemma-direct-edit-mixed-batch-docs-fixed/`

What those prove:

- With prewarm, the local Gemma+Aider path can complete at least:
  - 10 tiny editable files
  - plus 1 trimmed read-only file
  - in a single run
- For one-file deterministic replacements, the manager can now:
  - recover a timeout-shaped Aider failure through direct-edit fallback
  - bypass Aider entirely through direct-edit short-circuit
  - operate on at least one real `10507`-byte file under the widened deterministic guardrails
- For one-file deterministic additive edits, the manager can now:
  - insert after a unique anchor through direct-edit short-circuit
  - do so on at least one real `11895`-byte file
- For one-file deterministic block rewrites, the manager can now:
  - replace a block between unique start and end anchors through direct-edit short-circuit
  - do so on at least one real `12967`-byte file
- For one-file deterministic edit sequences, the manager can now:
  - apply a small batch of steps sequentially through direct-edit short-circuit
  - do so on at least one real `13805`-byte file
- For one-file deterministic excerpt patches, the manager can now:
  - apply a bounded SEARCH/REPLACE patch set through direct-edit short-circuit
  - do so on at least one real `14579`-byte file
- For mixed excerpt-plus-literal deterministic batches, the manager can now:
  - apply one excerpt SEARCH/REPLACE patch plus literal deterministic steps in the same short-circuit run
  - do so across at least two real repo files in one manager-only run
  - accept authored literal prompts that use escaped newline text
- For bounded deterministic multi-file edit sequences, the manager can now:
  - apply a small batch across multiple selected files through direct-edit short-circuit
  - do so on at least two real repo files in one manager-only run
  - bypass the Aider budget gate when direct-edit eligibility is already known

Current routing hint in `run_aider_worker.py`:

- repo map disabled
- compacted prompt
- up to 10 editable files
- up to 1 read-only file
- about 500 estimated input tokens or less

This is only a validated floor for tiny Aider tasks, not a guarantee for real code edits. Direct-edit routing is a separate manager envelope.

## Most Important New Findings

### Run `028`: real two-file code task fits budget but still stalls

Run folder:

- `10_agent_runs/2026-06-07_028_gemma-aider-runtime-token-commas/`

Task shape:

- editable: `local_harness/aider_runtime.py`
- editable: `local_harness/tests/test_aider_runtime.py`
- no read-only context

Preflight outcome:

- `estimated_total_input_tokens`: 3837
- `protocol_overhead_tokens`: 1400
- `estimated_total_with_overhead_tokens`: 5237
- `within_budget`: true

Observed behavior:

- prewarm succeeded
- attempt 1 timed out at provider level
- attempt 2 stalled badly enough that I had to terminate the child manually

Meaning:

- Budget fit alone is not enough on this endpoint.
- Real code payload shape is the next limit.

### Run `029`: manager timeout fix validated

Run folder:

- `10_agent_runs/2026-06-07_029_gemma-aider-timeout-bounded/`

Task shape:

- same real two-file code task as `028`
- `--timeout 30`
- `--manager-retries 0`

Observed behavior:

- prewarm succeeded
- wrapper exited on its own in about 53.8 seconds
- `exit_code`: 124
- `manager_timeout_detected`: true

Meaning:

- The workflow no longer hangs indefinitely when Aider stalls after request dispatch.
- The failure is now operationally usable because it is bounded and auditable.

### Run `033`: thin real-code surface still stalls

Run folder:

- `10_agent_runs/2026-06-08_033_gemma-aider-metrics-thin-file/`

Task shape:

- editable: `local_harness/aider_metrics.py`
- no read-only context

Observed behavior:

- prewarm succeeded
- preflight stayed within budget and still reported `validated_shape_match: true`
- run stalled after dispatch and exited through manager timeout

Meaning:

- `validated_shape_match` should not be interpreted as a success predictor for real-code Aider work.

### Run `034`: direct-edit short-circuit bypass validated

Run folder:

- `10_agent_runs/2026-06-08_034_gemma-aider-direct-edit-shortcut/`

Task shape:

- editable: `local_harness/tests/test_aider_runtime.py`
- deterministic one-file literal replacement

Observed behavior:

- no Aider call
- no prewarm call
- direct-edit short-circuit applied the replacement immediately

Meaning:

- Eligible deterministic one-file changes should route to short-circuit first, not to whole-file Aider.

### Run `035`: widened deterministic envelope validated

Run folder:

- `10_agent_runs/2026-06-08_035_gemma-direct-edit-large-readme/`

Task shape:

- editable: `local_harness/README.md`
- deterministic one-file literal replacement
- target size: `10507` bytes

Observed behavior:

- preflight direct-edit classification reported `eligible: true`
- no Aider call
- no prewarm call
- direct-edit short-circuit applied the replacement immediately

Meaning:

- The deterministic manager path is now live-proven above the old `4096`-byte ceiling, with current guardrails of `prompt_char_limit: 1200` and `file_size_limit_bytes: 16384`.

### Run `036`: additive deterministic route validated

Run folder:

- `10_agent_runs/2026-06-08_036_gemma-direct-edit-insert-readme/`

Task shape:

- editable: `local_harness/README.md`
- deterministic one-file insert-after operation
- target size: `11895` bytes

Observed behavior:

- preflight direct-edit classification reported `operation: insert_after` and `eligible: true`
- no Aider call
- no prewarm call
- direct-edit short-circuit inserted the new line immediately after the requested unique anchor

Meaning:

- The deterministic manager path now covers additive one-file edits, not only replacements.
- `insert_after` is live-proven; `insert_before` is implemented and unit-tested under the same guardrails but not yet separately live-proven.

### Run `037`: initial block route hit prompt-cap ceiling

Run folder:

- `10_agent_runs/2026-06-08_037_gemma-direct-edit-block-readme/`

Task shape:

- editable: `local_harness/README.md`
- deterministic one-file block replacement

Observed behavior:

- preflight direct-edit classification reported `reason: prompt_too_long`
- `prompt_char_count: 828`
- old `prompt_char_limit: 600`
- wrapper fell through to whole-file Aider and timed out

Meaning:

- The block route itself was valid; the deterministic manager envelope was too narrow.

### Run `038`: deterministic block replacement validated

Run folder:

- `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/`

Task shape:

- editable: `local_harness/README.md`
- deterministic one-file block replacement
- target size: `12967` bytes

Observed behavior:

- preflight direct-edit classification reported `operation: replace_block`, `eligible: true`, `prompt_char_count: 828`, `prompt_char_limit: 1200`, `start_anchor_match_count: 1`, and `end_anchor_match_count: 1`
- no Aider call
- no prewarm call
- direct-edit short-circuit replaced the requested block immediately

Meaning:

- The deterministic manager path now covers one-file block rewrites.
- The prompt-cap increase from `600` to `1200` moved a real limit, not just a theoretical one.

### Run `039`: sequential one-file batching validated

Run folder:

- `10_agent_runs/2026-06-08_039_gemma-direct-edit-batch-readme/`

Task shape:

- editable: `local_harness/README.md`
- deterministic one-file batch
- target size: `13805` bytes

Observed behavior:

- preflight direct-edit classification reported `operation: batch`, `operation_count: 2`, and `operation_types: ["replace", "insert_after"]`
- no Aider call
- no prewarm call
- operation 2 matched against text created by operation 1 and still short-circuited cleanly

Meaning:

- The deterministic manager path now supports sequential one-file edit plans, not only standalone operations.
- Small real chores no longer need to be split into separate runs just to stay off the unstable Aider path.

## Current Bottleneck

The next blocker is not discovery, not cold start, and not missing subprocess control.

It is this:

- A real two-file code task can stay within preflight budget and still fail to return a usable completion on the local Gemma+Aider path.

Practical reading:

- The endpoint is good enough for small synthetic edits.
- The endpoint is also operationally usable through manager-side deterministic one-file edits, block rewrites, and small one-file edit sequences, even when Aider itself should be bypassed.
- The endpoint plus Aider transport is still unreliable for moderately sized whole-file code editing.
- The whole-file payload style Aider uses is probably the core reason this shape stalls.

## Files Abacus Should Read First

Read these in order:

1. `local_harness/README.md`
2. `local_harness/run_aider_worker.py`
3. `local_harness/aider_prep.py`
4. `local_harness/aider_runtime.py`
5. `10_agent_runs/2026-06-08_033_gemma-aider-metrics-thin-file/REVIEW.md`
6. `10_agent_runs/2026-06-08_034_gemma-aider-direct-edit-shortcut/REVIEW.md`
7. `10_agent_runs/2026-06-08_035_gemma-direct-edit-large-readme/REVIEW.md`
8. `10_agent_runs/2026-06-07_029_gemma-aider-timeout-bounded/REVIEW.md`

If Abacus wants the successful envelope first, then also read:

1. `10_agent_runs/2026-06-07_024_gemma-aider-eight-file/REVIEW.md`
2. `10_agent_runs/2026-06-07_025_gemma-aider-ten-file/REVIEW.md`
3. `10_agent_runs/2026-06-07_026_gemma-aider-ten-file-read-context/REVIEW.md`

## Commands That Passed

Repo tests:

```text
python3 -m unittest discover -s local_harness/tests
python3 -m unittest discover -s XX_backend/tests
git diff --check
```

Run-folder validation:

```text
python3 XX_backend/validate_agent_run.py 10_agent_runs/2026-06-07_028_gemma-aider-runtime-token-commas
python3 XX_backend/validate_agent_run.py 10_agent_runs/2026-06-07_029_gemma-aider-timeout-bounded
```

## Commands Abacus Can Reuse

Preflight a real code task:

```text
python3 local_harness/run_aider_worker.py \
  10_agent_runs/2026-06-07_028_gemma-aider-runtime-token-commas \
  --preflight-only \
  local_harness/aider_runtime.py \
  local_harness/tests/test_aider_runtime.py
```

Run a bounded live recheck:

```text
python3 local_harness/run_aider_worker.py \
  10_agent_runs/2026-06-07_029_gemma-aider-timeout-bounded \
  --init-stubs \
  --timeout 30 \
  --manager-retries 0 \
  local_harness/aider_runtime.py \
  local_harness/tests/test_aider_runtime.py
```

Direct endpoint sanity check:

```text
python3 local_harness/icm_call.py handoff \
  --base-url http://localhost:8083/v1 \
  --model openai/gemma4 \
  --json \
  --final-only \
  "Reply with exactly: ok"
```

## Environment Notes

- The copied Aider environment is in `./_aider-chat/`.
- The wrapper uses `./_aider-chat/bin/python -m aider`.
- The local endpoint is:

```text
http://localhost:8083/v1
```

- Cold-start retries were previously real. Prewarm materially helped.
- Sandbox-localhost behavior can still produce false negatives. Live Aider checks should be treated as outside-sandbox operations when possible.

## Recommended Next Moves For Abacus

### Best next engineering move

Reduce real code payload size further before asking Aider to edit it.

Concrete options:

1. Split `local_harness/aider_runtime.py` again into smaller modules.
2. Add an excerpt-based or patch-targeted manager mode so the local model does not need the whole file.

### Best next workflow move

Use the direct-edit short-circuit intentionally for eligible deterministic one-file changes, and keep whole-file Aider edits limited to the previously validated synthetic envelope.

Rationale:

- The manager now has live proof that both the fallback and the zero-attempt short-circuit paths work.
- It gives a productive path for deterministic one-file changes while preserving auditability.

### What I would do next

1. Keep whole-file Aider usage bounded and evidence-driven for real-code tasks.
2. Use direct-edit short-circuit first when preflight says the deterministic envelope is eligible.
3. Build the next manager route for changes that exceed one-file deterministic batching, likely bounded multi-file routing or richer excerpt-scoped patch syntax.

## Do Not Re-Learn These Lessons

- Prewarm matters.
- Budget fit does not imply successful real-code completion.
- `validated_shape_match` does not imply successful real-code completion.
- Synthetic success does not transfer automatically to whole-file code editing.
- Manager-side timeout bounding is required on this endpoint.
- Direct-edit short-circuit can bypass the unstable Aider path entirely for eligible deterministic one-file changes.
- Additive deterministic edits can also bypass the unstable Aider path when a unique anchor exists.
- Block replacement can bypass the unstable Aider path when both block anchors are unique and the deterministic prompt fits the current `1200`-character manager cap.
- Small one-file deterministic edit plans can now bypass the unstable Aider path as a batch, as long as each step stays unique when it is applied.
- Keep run-folder artifacts reviewed and validated before treating findings as durable.
