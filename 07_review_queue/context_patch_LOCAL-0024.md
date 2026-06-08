# Context Patch LOCAL-0024

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Promote direct-edit short-circuit to the default first route for eligible one-file deterministic replacements on the local Gemma endpoint, instead of waiting for timeout-shaped Aider failure.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Record that `validated_shape_match: false` does not block the deterministic direct-edit path, because that route bypasses Aider payload behavior entirely.
- Add a new routing note: no-prewarm/no-Aider zero-attempt success is now live-proven for eligible direct-edit tasks.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add boundary note: run `2026-06-08_034_*` shows a successful manager-side bypass of the unstable Aider path for deterministic one-file work.

## Unmerged / Needs Human Review
- Canonical workflow should decide whether the short-circuit is broad enough to be called “default” or should remain an endpoint-specific optimization rule.
