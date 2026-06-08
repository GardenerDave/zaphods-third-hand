# Conversation Context File

## Source
- Source ID: LOCAL-0027
- Source type: local run-folder artifacts
- Source file or link: `10_agent_runs/2026-06-08_037_gemma-direct-edit-block-readme/`
- Conversation title: Block-replacement prompt-limit failure (run 037)
- Approximate date range: 2026-06-08
- Project: ICM Workflow Optimization Handoff (sanitized subset)
- Confidence: high (grounded in run-folder `METRICS.json`, `OUTPUT.md`, `REVIEW.md`, and `ACCEPTED.md`)

## Executive Summary
The first deterministic block-replacement probe on `local_harness/README.md` failed before the direct-edit logic could run. Preflight showed the exact issue: the prompt shape was valid in principle, but `prompt_char_count: 828` exceeded the then-current deterministic manager limit of `600`, so the wrapper fell through to whole-file Aider and reproduced the known timeout path.

## Durable Facts
- Run folder: `10_agent_runs/2026-06-08_037_gemma-direct-edit-block-readme/`.
- Target file: `local_harness/README.md`.
- Preflight stayed within total token budget (`within_budget: true`) but direct-edit classification reported `reason: prompt_too_long`.
- `prompt_char_count: 828`, `prompt_char_limit: 600`.
- Because direct-edit did not trigger, the wrapper launched Aider, prewarm succeeded, and the run exited through manager timeout (`exit_code: 124`).
- Run-folder validation remained possible after review.

## Decisions Made
- Widen the deterministic direct-edit prompt cap so real block-replacement prompts can route through short-circuit instead of falling through to Aider.

## Open Questions
- How much farther the prompt cap can safely grow before the deterministic envelope becomes too permissive.

## Bugs / Issues Identified
- The direct-edit prompt cap was too low for practical block-replacement instructions on a real repo file.

## Rules Added
- None merged directly; the cap increase is justified in the follow-up proof run.

## Version / Release Notes
- No release/version changes from this source alone.

## Files / Artifacts Mentioned
- `10_agent_runs/2026-06-08_037_gemma-direct-edit-block-readme/OUTPUT.md`
- `10_agent_runs/2026-06-08_037_gemma-direct-edit-block-readme/METRICS.json`
- `10_agent_runs/2026-06-08_037_gemma-direct-edit-block-readme/REVIEW.md`
- `10_agent_runs/2026-06-08_037_gemma-direct-edit-block-readme/ACCEPTED.md`

## Next Actions
- Re-run the same block-replacement task after widening the deterministic prompt limit.

## Suggested ICM Destination
- Session summary archive: `02_sessions/2026-06-08_gemma-aider-037-block-limit.md`
- Proposed updates for human review: `07_review_queue/context_patch_LOCAL-0027.md`

## Compression Notes
This source matters because it isolates the actual blocker precisely: not anchors, not file size, not transport, but a deterministic manager prompt limit that was too low for the intended block-replacement shape.
