# Context Patch LOCAL-0026

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Expand the documented deterministic manager route to include unique-anchor insertion (`insert ... after ...` or `insert ... before ...`) under the same one-file, bounded-prompt, bounded-file-size, exact-match guardrails.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Record that deterministic insert-after is now live-proven on a real repo file with zero Aider and zero endpoint usage.
- Distinguish proof levels clearly: insert-after is live-proven, insert-before is implemented and unit-tested under the same guardrails.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add note that manager-side deterministic routing now covers an additive one-file edit shape, reducing pressure to send small documentation/config edits through unstable whole-file Aider.

## Unmerged / Needs Human Review
- Canonical workflow language should decide whether insert-before needs its own live proof before being promoted at the same level as insert-after.
