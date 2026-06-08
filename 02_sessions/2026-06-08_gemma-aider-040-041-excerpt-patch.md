# Conversation Context File

## Source
- Source ID: LOCAL-0030
- Source type: local run-folder artifacts
- Source file or link: `10_agent_runs/2026-06-08_040_gemma-excerpt-patch-readme/;10_agent_runs/2026-06-08_041_gemma-excerpt-patch-readme-fixed/`
- Conversation title: Excerpt patch limit and fix (runs 040/041)
- Approximate date range: 2026-06-08
- Project: ICM Workflow Optimization Handoff (sanitized subset)
- Confidence: high (grounded in run-folder `METRICS.json`, `OUTPUT.md`, `REVIEW.md`, and `ACCEPTED.md`)

## Executive Summary
Run `040` showed that a real two-hunk excerpt SEARCH/REPLACE patch on `local_harness/README.md` was blocked by the old shared deterministic prompt cap of `1200`. Run `041` widened that excerpt-specific cap to `4096` and then short-circuited the same patch entirely through the manager path with no Aider and no endpoint usage.

## Durable Facts
- Run `040` targeted `local_harness/README.md` and reported `prompt_char_count: 1620`, `prompt_char_limit: 1200`, `reason: prompt_too_long`, and manager timeout after fallthrough to whole-file Aider.
- Run `041` targeted the same file at `14579` bytes and reported `operation: excerpt_patch`, `patch_count: 2`, `prompt_char_limit: 4096`, and `eligible: true`.
- Run `041` completed with `final_attempt_number: 0`, empty `aider_attempts`, empty `prewarm_attempts`, and a populated `AIDER_DIRECT_EDIT.json`.

## Decisions Made
- Split deterministic prompt budgeting by operation type instead of sharing one `1200`-character ceiling across all manager routes.
- Promote excerpt SEARCH/REPLACE patch sets into the documented manager route for bounded one-file changes.

## Open Questions
- Whether excerpt patch batching should remain one-file-only policy or eventually be generalized into mixed deterministic multi-file plans.

## Bugs / Issues Identified
- The old shared deterministic prompt cap was too low for a practical two-hunk excerpt patch even though the grammar and unique matching logic were otherwise sound.

## Files / Artifacts Mentioned
- `10_agent_runs/2026-06-08_040_gemma-excerpt-patch-readme/OUTPUT.md`
- `10_agent_runs/2026-06-08_040_gemma-excerpt-patch-readme/METRICS.json`
- `10_agent_runs/2026-06-08_041_gemma-excerpt-patch-readme-fixed/OUTPUT.md`
- `10_agent_runs/2026-06-08_041_gemma-excerpt-patch-readme-fixed/METRICS.json`
- `10_agent_runs/2026-06-08_041_gemma-excerpt-patch-readme-fixed/AIDER_DIRECT_EDIT.json`

## Next Actions
- Use excerpt SEARCH/REPLACE routing for bounded one-file tasks before escalating to whole-file Aider.
- Keep the excerpt prompt cap and matching rules explicit in the manager docs.

## Suggested ICM Destination
- Session summary archive: `02_sessions/2026-06-08_gemma-aider-040-041-excerpt-patch.md`
- Proposed updates for human review: `07_review_queue/context_patch_LOCAL-0030.md`
