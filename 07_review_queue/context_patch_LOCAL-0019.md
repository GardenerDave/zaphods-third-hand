# Context Patch LOCAL-0019

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Add failure classification guidance for local Aider orchestration:
  - Distinguish preflight/token-fit failures (`within_budget: false`), provider/runtime timeout failures (provider timeout or stalled completion after dispatch), and cold-start/connectivity failures (prewarm failure).
  - Require run-level evidence fields (`prewarm.success`, preflight budget fields, event summary, timeout flags) when classifying root cause.

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Add a bounded-repro rule: after changing wrapper timeout/termination behavior, run one bounded real-code repro and require explicit timeout classification in artifacts (`exit_code`, timeout indicators) before considering the fix validated.

## Proposed updates to ICM/01_context/PROJECT_CONTEXT.md
- Add local harness model-resolution note: OpenAI-style alias model names (for example `openai/gemma4`) may be resolved through `/v1/models` discovery to a concrete model id for request execution.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add bug pattern entry: Aider subprocess can stall after request dispatch even when prewarm succeeds.
- Add mitigation note: manager-side subprocess timeout guard with explicit metrics/summary classification (`manager_timeout_detected`, bounded timeout exit code) to prevent silent hangs.

## Proposed updates to ICM/04_decisions/DECISION_LOG.md
- No high-confidence decision-log addition from these sources beyond workflow-level operational rules.

## Proposed updates to ICM/06_releases/RELEASE_TIMELINE.md
- No release update proposed from this source.

## Unmerged / Needs Human Review
- The run sequence suggests improved observability and containment, but not yet improved accepted-edit rate; a fresh small-surface real task should be reviewed before canonizing stronger success claims.
- `02_sessions/2026-06-08_abacus-handoff-gemma-aider.md` corroborates alias-resolution and timeout-bounding context, but canonical merge should still rely on direct code + run artifacts as primary evidence.
