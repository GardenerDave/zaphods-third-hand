# Context Patch LOCAL-0029

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Expand the documented deterministic manager route to include sequential one-file operation batches, not only single deterministic operations.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Record that the manager now supports sequential one-file deterministic batches where later operations may rely on text created by earlier operations.
- Keep the routing rule explicit: every step must remain unique at the moment it is applied.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add capability note: run `2026-06-08_039_*` proves that a small one-file edit plan can bypass whole-file Aider entirely through manager-side deterministic sequencing.

## Unmerged / Needs Human Review
- Canonical workflow should decide whether sequential batching should remain one-file-only policy or whether a future bounded multi-file variant is acceptable.
