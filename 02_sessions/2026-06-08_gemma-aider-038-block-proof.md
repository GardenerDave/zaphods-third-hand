# Conversation Context File

## Source
- Source ID: LOCAL-0028
- Source type: local run-folder artifacts
- Source file or link: `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/`
- Conversation title: Direct-edit block replacement live proof (run 038)
- Approximate date range: 2026-06-08
- Project: ICM Workflow Optimization Handoff (sanitized subset)
- Confidence: high (grounded in run-folder `METRICS.json`, `OUTPUT.md`, `REVIEW.md`, and `ACCEPTED.md`)

## Executive Summary
The same deterministic block-replacement task that failed under the old prompt cap was rerun after widening the deterministic manager limit to `1200` characters. The manager classified the request as direct-edit eligible and replaced the requested README block immediately, with zero Aider and zero endpoint usage.

## Durable Facts
- Run folder: `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/`.
- Target file: `local_harness/README.md`.
- Target file size at run time: `12967` bytes.
- Preflight direct-edit classification reported `operation: replace_block`, `eligible: true`, `prompt_char_count: 828`, `prompt_char_limit: 1200`, `start_anchor_match_count: 1`, `end_anchor_match_count: 1`, and `anchor_order_valid: true`.
- Preflight stayed within budget (`estimated_total_with_overhead_tokens: 4891`, `within_budget: true`) but did not match the tiny Aider heuristic (`validated_shape_match: false`).
- No Aider or prewarm attempt was made (`final_attempt_number: 0`, empty `aider_attempts`, empty `prewarm_attempts`).
- Run-folder validation passed.

## Decisions Made
- Widen the deterministic direct-edit prompt cap to `1200`.
- Expand the documented manager route to include unique-anchor block replacement, not only unique literal replacement and insertion.

## Open Questions
- Whether the next manager route should be multi-block deterministic replacement or a richer excerpt-scoped patch format.

## Bugs / Issues Identified
- None in the deterministic block-replacement route once the prompt cap was widened.

## Rules Added
- None merged directly; workflow promotion is proposed in review patch.

## Version / Release Notes
- No release/version changes from this source.

## Files / Artifacts Mentioned
- `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/OUTPUT.md`
- `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/METRICS.json`
- `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/AIDER_DIRECT_EDIT.json`
- `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/REVIEW.md`
- `10_agent_runs/2026-06-08_038_gemma-direct-edit-block-readme-fixed/ACCEPTED.md`

## Next Actions
- Use block replacement through short-circuit for deterministic one-file block rewrites.
- Focus further engineering effort on the next gap beyond deterministic block routing.

## Suggested ICM Destination
- Session summary archive: `02_sessions/2026-06-08_gemma-aider-038-block-proof.md`
- Proposed updates for human review: `07_review_queue/context_patch_LOCAL-0028.md`

## Compression Notes
The important durable lesson is the whole before/after pair: `037` isolated the prompt-cap limit, and `038` proved that widening it moved the real manager boundary and eliminated the Aider call completely.
