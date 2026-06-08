# Context Patch LOCAL-0032

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Document mixed excerpt-plus-literal deterministic batches as a manager-side option for bounded multi-file chores.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Record that literal direct-edit text now decodes escaped newline, tab, and carriage-return sequences.
- Document the mixed route rule: one excerpt SEARCH/REPLACE patch may be combined with literal deterministic operations across the selected files, as long as each step stays unique when applied.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add boundary note: runs `2026-06-08_044_*` and `2026-06-08_045_*` prove that mixed routing worked conceptually before the fix, and that the real blocker was escaped-newline prompt decoding for literal operations.

## Unmerged / Needs Human Review
- Canonical workflow should decide whether mixed routing remains one-excerpt-patch-only policy or can expand to multiple excerpt patches in one batch.
