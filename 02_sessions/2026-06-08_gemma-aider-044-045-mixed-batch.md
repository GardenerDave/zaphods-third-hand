# Conversation Context File

## Source
- Source ID: LOCAL-0032
- Source type: local run-folder artifacts
- Source file or link: `10_agent_runs/2026-06-08_044_gemma-direct-edit-mixed-batch-docs/;10_agent_runs/2026-06-08_045_gemma-direct-edit-mixed-batch-docs-fixed/`
- Conversation title: Mixed excerpt-plus-literal batch limit and fix (runs 044/045)
- Approximate date range: 2026-06-08
- Project: ICM Workflow Optimization Handoff (sanitized subset)
- Confidence: high (grounded in run-folder `METRICS.json`, `OUTPUT.md`, `REVIEW.md`, and `ACCEPTED.md`)

## Executive Summary
Run `044` showed that the new mixed route already worked conceptually, but authored literal prompts using escaped newline text still failed matching because the old parser treated `\n` as two characters. Run `045` added escape decoding for literal direct-edit text and then short-circuited the same two-file mixed batch entirely through the manager path.

## Durable Facts
- Both runs targeted `local_harness/README.md` plus `02_sessions/2026-06-08_abacus-handoff-gemma-aider.md`.
- Both runs classified the prompt as `operation: mixed_batch` with one excerpt patch plus one literal insert across 2 selected files.
- Run `044` failed direct-edit eligibility at operation 2 with `reason: no_unique_match` and `match_count: 0` on the literal insert anchor.
- Run `045` decoded escaped newline text in literal direct-edit parsing and then completed the same task with `eligible: true`, `within_budget: false`, `direct_edit_budget_bypass_available: true`, and `final_attempt_number: 0`.

## Decisions Made
- Keep excerpt patch and literal operations in one deterministic manager route rather than splitting them into separate worker types.
- Decode escaped newline, tab, and carriage-return sequences inside backticked literal direct-edit text to reduce prompt-authoring friction.

## Open Questions
- Whether escaped quote/backslash handling should be widened further or kept to the current small set of line-editing escapes.

## Bugs / Issues Identified
- The old literal parser was too literal for practical authored prompts, causing false negative matching whenever a human wrote `\n` instead of inserting a real newline inside backticks.

## Files / Artifacts Mentioned
- `10_agent_runs/2026-06-08_044_gemma-direct-edit-mixed-batch-docs/METRICS.json`
- `10_agent_runs/2026-06-08_045_gemma-direct-edit-mixed-batch-docs-fixed/METRICS.json`
- `10_agent_runs/2026-06-08_045_gemma-direct-edit-mixed-batch-docs-fixed/AIDER_DIRECT_EDIT.json`

## Next Actions
- Use mixed excerpt-plus-literal batches for bounded real chores that need one richer excerpt patch plus a few simple deterministic follow-up edits.
- Decide whether the next expansion should be multiple excerpt patches in one batch or 3-4 file mixed routing.

## Suggested ICM Destination
- Session summary archive: `02_sessions/2026-06-08_gemma-aider-044-045-mixed-batch.md`
- Proposed updates for human review: `07_review_queue/context_patch_LOCAL-0032.md`
