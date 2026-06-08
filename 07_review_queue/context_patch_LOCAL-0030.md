# Context Patch LOCAL-0030

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Document excerpt SEARCH/REPLACE patch routing as a manager-side deterministic option for bounded one-file changes.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Record that excerpt patch requests need a larger prompt budget than literal single-line deterministic edits.
- Keep the routing rule explicit: each SEARCH block must remain unique at the moment it is applied.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add capability note: runs `2026-06-08_040_*` and `2026-06-08_041_*` prove the excerpt patch grammar and identify the old shared prompt cap as the blocking issue that had to be widened.

## Unmerged / Needs Human Review
- Canonical workflow should decide whether excerpt patch routing remains one-file-only policy or eventually becomes part of mixed deterministic multi-file batches.
