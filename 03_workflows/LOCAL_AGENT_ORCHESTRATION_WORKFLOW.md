# Local Agent Orchestration Workflow

Author: [REDACTED]

## Purpose

Use local models as file-mediated workers for low-risk, easily verified subtasks while keeping Codex/Nav responsible for coordination, context stewardship, review, integration, and high-risk decisions.

The goal is to reduce cloud token usage without weakening ICM's auditability. Local agents should work from narrow markdown task files and write inspectable outputs back to disk.

## Current Local Model Baseline

As of 2026-05-25:

- `ggml-org/gemma-3-1b-it-GGUF:Q4_K_M` is the fast local worker. Synthetic markdown pilots observed about 11.1 output tokens per second; earlier rough observation was 20+ tokens per second. `/v1/models` reported `n_ctx: 2048`.
- `Qwen/Qwen3-32B-GGUF:Q4_K_M` is the slow clean analyst. A synthetic `/no_think` pipeline test observed 1.093 output tokens per second; earlier rough observation was around 0.69 tokens per second.

Recheck observed throughput when model files, quantization, hardware, runtime, or context size changes.

## Current Local Worker Pool

As of LOCAL-0005, the local AI workspace is `/home/localuser/<path><path>` and the current control command is:

```text
~/ai/agentctl status
```

Verified worker endpoints:

| Worker | URL | Intended role |
|---|---|---|
| `agent32` | `http://<LAN_HOST>:8080` | deep/slow reasoning |
| `coder7` | `http://<LAN_HOST>:8081` | code and log compression |
| `router3` | `http://<LAN_HOST>:8082` | intent routing / task classification |
| `handoff7` | `http://<LAN_HOST>:8083` | Codex prompt packing |

Useful commands:

```text
~/ai/agentctl status
~/ai/agentctl logs coder 80
~/ai/agentctl stop all
~/ai/agentctl start all
```

Use this worker pool for compression, routing, handoff prompt packing, and bounded support tasks. Do not use it for uncontrolled coding.

Manual lifecycle control is acceptable during the supervised pilot. Codex/Nav does not need direct `agentctl` access for file-mediated workflows as long as the endpoints are reachable and the run artifacts capture what happened.

## Manager Role

Codex/Nav should act as the manager when a Codex session is active:

- Select the smallest relevant context bundle.
- Decide whether work should stay in Codex or be delegated locally.
- Write local-agent task files with clear inputs, outputs, constraints, and acceptance criteria.
- Review local-agent outputs before canonical docs, source code, or release records are changed.
- Run or record verification evidence.
- Track resource usage and output value.

Local agents should not be treated as independent sources of truth.

The current maturity status is supervised pilot ready. Treat local workers as bounded preprocessors, not autonomous developers.

## Manager Context Boundary

Local/testing agents may process personal planner/runtime data when [REDACTED_AUTHOR] or a manager prompt explicitly delegates that work. The point of delegation is to keep raw personal data and noisy testing detail out of the manager Codex context by default.

When a local/testing agent touches personal data, its handoff back to Codex/Nav should be sanitized: include status, metrics, file paths, verification evidence, issues, and conclusions, but do not paste raw tasks, routines, calendar entries, screenshots, database rows, or copied planner output into the manager handoff unless [REDACTED_AUTHOR] explicitly asks for that detail.

Codex/Nav should prefer reviewing summarized findings and repo artifacts first. Load raw personal inputs only when needed for a concrete decision and after [REDACTED_AUTHOR] has intentionally widened the scope.

## Model Routing

Use the fast Gemma model for:

- Source discovery summaries.
- File and manifest triage.
- Checklist extraction.
- Markdown cleanup drafts.
- Simple duplicate detection.
- Fixture or test-case idea generation.
- First-pass report formatting.

Gemma markdown-output tasks should explicitly request raw markdown with no enclosing code fences. A synthetic pilot without that instruction wrapped the report in a markdown code fence; the raw-markdown pilot fixed the issue. Consider increasing Gemma context beyond 2k for future source-triage work if memory allows.

Use the slow Qwen model for:

- Narrow code-inspection summaries.
- Patch-plan critique.
- Second-pass review of Gemma output.
- Context-distillation drafts for one bounded source chunk.
- Risk analysis for a clearly scoped behavior change.

Keep Qwen prompts and expected outputs short. At roughly 0.69 tokens per second, a 1,000-token answer can take about 24 minutes.

Qwen worker tasks should use `/no_think` or an equivalent final-answer-only request convention when final assistant `content` is required. A synthetic test without that convention consumed the output budget in `reasoning_content` and returned empty final content. Use explicit output budgets and prefer short markdown reports.

Use `router3` for compact routing classification only:

- Small synthetic or sanitized task descriptions.
- A bounded label set supplied in the prompt.
- One-label-per-case output with brief evidence.
- Manager-reviewed routing decisions before downstream action.

`router3` should not receive raw personal/runtime data by default and should not be used as an autonomous planner. It is a routing helper for deciding where work should go next.

Keep work in Codex/Nav for:

- Final canonical ICM merges.
- Commits.
- Destructive or irreversible actions.
- Broad architecture decisions.
- High-risk source edits.
- Cross-file implementation where the correct change is unclear.
- Legal/license posture.
- Any task where local output cannot be cheaply verified.

## Delegation Criteria

Delegate to a local model only when all of these are true:

- The task is narrow and self-contained.
- The input files are explicitly listed.
- The expected output format is specified.
- The result can be checked by Codex, tests, git diff, or source inspection.
- The local agent can work read-only or draft-only.
- Failure would waste time but not damage project state.

Do not delegate when the next critical step depends on slow output and Codex can do the work faster with less coordination overhead.

## Run Folder Convention

Use `ICM/10_agent_runs/` for nontrivial local-agent work.

Typical structure:

```text
ICM/10_agent_runs/YYYY-MM-DD_short-task/
  RUN.md
  00_inputs/
    INPUT_MANIFEST.md
  01_fast_gemma/
    TASK.md
    OUTPUT.md
    METRICS.md
  02_deep_qwen/
    TASK.md
    OUTPUT.md
    METRICS.md
  03_manager_review/
    REVIEW.md
  FINAL_REPORT.md
```

For new single-worker supervised pilot runs, prefer the simpler promoted-artifact shape:

```text
ICM/10_agent_runs/YYYY-MM-DD_###_short-task/
  TASK.md
  INPUT.md
  MODEL_REQUEST.md
  OUTPUT.md
  REVIEW.md
  METRICS.json
  ACCEPTED.md
```

`TASK.md` is the complete audit record for humans/Codex. `MODEL_REQUEST.md` is the compact prompt actually sent to the worker when the full task packet would waste local context or cause timeouts. `OUTPUT.md` is the raw worker result. `REVIEW.md` is the Codex/Nav or human evaluation. `ACCEPTED.md` is the cleaned, approved artifact for reuse.

Only `ACCEPTED.md`, or another explicitly reviewed and sanitized artifact, may feed another worker or a Codex prompt. Do not chain raw local-agent outputs.

Before manager review, downstream promotion, or commit, run the backend validator for this single-worker shape:

```text
python3 ICM/XX_backend/validate_agent_run.py ICM/10_agent_runs/YYYY-MM-DD_###_short-task/
```

When running from `ICM/XX_backend`, use:

```text
python3 validate_agent_run.py ../10_agent_runs/YYYY-MM-DD_###_short-task/
```

The validator checks file presence only and must not be used as a substitute for manager review of `OUTPUT.md`, `REVIEW.md`, `METRICS.json`, and `ACCEPTED.md`.

Do not duplicate large raw sources into run folders unless a bounded excerpt is needed for reproducibility. Prefer file paths, line ranges, command outputs, and short excerpts.

For trivial local-agent calls, a single `RUN.md` and `FINAL_REPORT.md` is enough.

## Required Task File

Every local-agent task should include:

- Task ID.
- Assigned model.
- Role: fast triage, deep analyst, reviewer, or formatter.
- Objective.
- Input files or excerpts.
- Output path.
- Output format.
- Hard constraints.
- Stop conditions.
- Acceptance criteria.
- Resource reporting requirements.

For Qwen tasks, include `/no_think` or an equivalent final-answer-only instruction in the prompt/request unless the task is explicitly testing reasoning output. Keep `max_tokens` large enough for final content but the requested answer short.

For Gemma markdown-output tasks, include a raw-markdown instruction and explicitly forbid enclosing code fences around the whole response.

Use `ICM/08_import_tools/prompts/LOCAL_AGENT_TASK_PROMPT.md` as the base template.

## Compact Request Mode

Use compact request mode when a local worker is slow, has a small context window, or times out on the full task packet.

Keep `TASK.md` complete enough for audit, but write `MODEL_REQUEST.md` as the smallest prompt that can produce useful draft output. For `coder7` build/test log compression, prefer this shape:

```text
Here is a build log.
Return 5 bullets max:
Outcome:
Evidence:
Noise:
Risk:
Next action:
```

The first closed-loop `coder7` build-log pilot showed this boundary clearly: two larger prompts timed out with no response bytes, while a 226-token compact request produced a 50-token response in 56.968678 seconds at about 1.98 output tokens per second. The successful run was accepted only after manager review corrected the worker's recommendation and promoted `ACCEPTED.md`.

## Validated Coder7 Compression Patterns

As of LOCAL-0017, `coder7` is validated for bounded first-pass compression in four artifact classes:

| Task class | Request shape | Pilot result |
|---|---|---|
| Build/test log compression | Outcome, evidence, noise, risk, next action | LOCAL-0007: 205 prompt tokens, 38 completion tokens, 46.564434 seconds, accepted without substantive correction |
| Error-log compression | Outcome, evidence, noise, risk, next action | LOCAL-0008: 161 prompt tokens, 77 completion tokens, 59.532860 seconds, accepted with edits |
| Artifact-only git-diff compression | Change, evidence, risk, review focus, next action | LOCAL-0009: 202 prompt tokens, 125 completion tokens, 92.948045 seconds, accepted |
| Real app verification-log compression | Outcome, evidence, noise, risk, next action | LOCAL-0017: `npm run agent:verify` passed; 363 prompt tokens, 96 completion tokens, 81.464610 seconds, accepted with risk wording correction |

These validations do not make `coder7` a source-code decision maker. Use it to compress evidence and separate signal from noise; Codex/Nav or [REDACTED_AUTHOR] still reviews risk, fixes, and any promoted context.

For verification logs, scope risk claims to the supplied evidence. A passing build log can show that the command completed and that no build failure appeared in that log; it does not prove runtime behavior, test coverage, or security status.

## Validated Handoff7 Prompt-Packing Patterns

`handoff7` is validated for compact Codex prompt packing from reviewed artifacts only:

| Task class | Request shape | Pilot result |
|---|---|---|
| Accepted-artifact testing brief | Reviewed `ACCEPTED.md` artifacts to compact Codex-ready brief | LOCAL-0010: 648 prompt tokens, 167 completion tokens, 153.399036 seconds, accepted with manager edits |
| Implementation-brief compression | One small objective plus explicit file list, no coding | LOCAL-0011: 370 prompt tokens, 178 completion tokens, 113.522638 seconds, accepted with manager edits |

Manager review remains required for exact file paths, next-test wording, context gates, and any claim about what has been validated. Raw `OUTPUT.md` from `handoff7` should not feed another agent directly.

## Validated Router3 Classification Patterns

`router3` is validated as a compact classification helper, with clear prompt-size limits:

| Task class | Request shape | Pilot result |
|---|---|---|
| Broad simple task classification | 7 synthetic cases, bounded labels | LOCAL-0013: 246 prompt tokens, 183 completion tokens, 108.573260 seconds, accepted, 7/7 correct |
| Handoff-readiness classification | 8 synthetic cases with adjacent labels | LOCAL-0014: 300 prompt tokens, 162 completion tokens, 102.722676 seconds, partial, 6/8 correct |
| Adjacent-label contrast sweep | 9 cases for `manager_review`, `handoff7_prompt_packing`, `codex_coding` | LOCAL-0015: 414 estimated prompt tokens, timed out after 120.002356 seconds with no response bytes |
| Small adjacent-label contrast | 3 cases for the same adjacent labels | LOCAL-0016: 163 prompt tokens, 85 completion tokens, 42.262906 seconds, accepted, 3/3 correct |

Use small contrast sets when validating routing boundaries. For compact `router3` contrast prompts, `max_tokens` around 128 and a timeout around 150 seconds are reasonable pilot defaults. The stronger rule is to keep prompts compact; increasing the timeout alone did not solve the broad nine-case shape.

## Manager-Side Deterministic Direct-Edit Boundary

The Aider wrapper now includes a manager-side deterministic direct-edit path. This path is for narrow, mechanical edits that can be parsed, checked, applied, and audited without asking a model to reason about the change. It may short-circuit before Aider starts or recover after an Aider timeout when the request fits the deterministic envelope.

This is not permission for autonomous source editing. Codex/Nav or the human manager still owns file selection, prompt authoring, review, verification, and commit decisions.

Current supported prompt shapes:

- Literal replacement: ``- In `path`, replace `old` with `new`.`` followed by ``- Edit only the listed file.``
- Insert after or before a unique anchor.
- Replace a unique block from a start anchor through an end anchor.
- Apply one-file excerpt SEARCH/REPLACE patches.
- Apply sequential one-file deterministic batches.
- Apply bounded multi-file deterministic batches.
- Apply mixed excerpt-plus-literal batches across selected files.

Current guardrails:

- Replacement, insertion, block replacement, excerpt patch, and one-file batch routes target exactly one selected file.
- Multi-file deterministic batches target up to 4 selected files.
- One-file literal/block/batch prompts must stay at or below 1200 characters.
- Multi-file deterministic batch prompts must stay at or below 2400 characters.
- Excerpt SEARCH/REPLACE patch prompts must stay at or below 4096 characters.
- Each targeted file must stay at or below 24576 bytes.
- Every target string, anchor, block boundary, or SEARCH excerpt must be unique at the step where it is applied.
- Literal deterministic routes decode escaped `\n`, `\r`, and `\t` sequences in authored prompts.
- Direct-edit-eligible work may bypass the Aider budget gate even when `within_budget: false`.

Validated evidence:

- Runs `2026-06-08_032_*` and `2026-06-08_034_*` proved one-file deterministic replacement as both fallback and pre-Aider short-circuit.
- Runs `2026-06-08_036_*` and `2026-06-08_038_*` proved insertion and block replacement.
- Run `2026-06-08_039_*` proved sequential one-file deterministic batches.
- Runs `2026-06-08_040_*` and `2026-06-08_041_*` proved the excerpt patch grammar and the need for the larger excerpt prompt cap.
- Runs `2026-06-08_042_*` and `2026-06-08_043_*` proved the current bounded multi-file batch route and the 24576-byte file-size ceiling.
- Runs `2026-06-08_044_*` and `2026-06-08_045_*` proved mixed excerpt-plus-literal routing and the escaped-newline decoding fix.

Stop and use the normal manager-reviewed implementation path when:

- The prompt does not match a supported deterministic grammar.
- Any selected file is missing or exceeds the size limit.
- Any target, anchor, block boundary, or SEARCH excerpt is not unique.
- The requested edit is semantic, architectural, generated-output related, dependency-related, or security-sensitive.
- More than 4 files are selected.
- The manager cannot verify the result cheaply.

## Required Output Report

Every local-agent output should include:

- Summary.
- Findings or draft output.
- Evidence references.
- Uncertainty.
- Files inspected.
- Recommended next action.
- Resource report.
- Sanitization note when personal or runtime data was part of the local-agent input.

Use `ICM/08_import_tools/prompts/LOCAL_AGENT_REPORT_TEMPLATE.md` and `ICM/08_import_tools/prompts/LOCAL_AGENT_RESOURCE_REPORT.md`.

## Metrics

Record local-agent runs in `ICM/10_agent_runs/AGENT_RUNS.csv`.

Minimum fields:

```text
date,task_id,model,provider,stage,input_est_tokens,output_est_tokens,elapsed_seconds,observed_tokens_per_second,accepted_by_manager,cloud_tokens_avoided_estimate,rework_required,verification_result,run_path,notes
```

If exact token counts are unavailable, estimate tokens with one of:

- `characters / 4`
- `words * 1.33`

Mark estimated values as estimates in the run report.

`cloud_tokens_avoided_estimate` should be conservative. Count only work Codex would likely have performed directly, not every token seen by the local model.

## Review And Integration

Codex/Nav or [REDACTED_AUTHOR] must review local-agent outputs before they affect canonical state.

Raw local-agent outputs are not canonical and should not be reused as context until promoted through manager review. Promotion should produce `ACCEPTED.md` for file-mediated runs when the output may be consumed downstream.

For single-worker local-agent pilot folders, use `ICM/XX_backend/validate_agent_run.py` as a handoff-readiness check before promotion or commit. Passing validation means only that the expected files exist; it does not make raw worker output canonical.

Manager review should decide:

- Accepted.
- Accepted with edits.
- Rejected.
- Needs another local pass.
- Needs Codex implementation.
- Needs human decision.

Record the reason, especially when local work is rejected. Rejection data is useful for model-routing decisions.

## Suggested Starting Uses

Start with low-risk, high-volume support work:

- Build or test log compression.
- Error-log compression.
- Codex prompt packing.
- Task classification.
- Distiller source discovery reports.
- Context patch draft cleanup.
- Review queue summaries.
- Parser fixture idea generation.
- `git diff` narrative summaries.
- Test checklist generation.
- Bug report cleanup.
- Documentation cleanup.
- Release-note draft bullets from verified commits.

Avoid model-authored local-agent source edits unless a separate supervised pilot explicitly validates the route. Manager-side deterministic direct-edit is allowed only inside the envelope above and must remain mechanical, selected-file bounded, auditable, and verified. Avoid dependency changes, database/schema edits, security decisions, unreviewed task decomposition, private raw-data cross-agent chaining, and autonomous agent chaining.
