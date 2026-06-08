# Context Patch LOCAL-0022

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Add active routing rule: for one-file deterministic replacements that fit the direct-edit fallback envelope, a timeout-shaped Aider failure on this local Gemma endpoint should route to manager fallback rather than repeated Aider retry.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Record that direct-edit fallback is now live-validated, not only unit-tested.
- Capture the current fallback envelope explicitly: one selected file, small file size, prompt-parsed deterministic replacement, and exactly one unique match in target content.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add boundary note: run `2026-06-08_032_*` confirms the underlying post-dispatch Aider stall still exists even when the manager recovers the requested edit through fallback.

## Unmerged / Needs Human Review
- Canonical workflows should decide whether the current direct-edit envelope is narrow enough to mark as default policy or should remain a troubleshooting-specific routing rule.
