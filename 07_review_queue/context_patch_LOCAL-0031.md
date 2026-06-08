# Context Patch LOCAL-0031

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Expand deterministic manager routing from one-file batches to bounded multi-file batches.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Record that direct-edit-eligible work can bypass the Aider budget gate even when `within_budget: false`.
- Document the current configured multi-file envelope: up to 4 selected files, 2400 prompt characters, and 24576 bytes per targeted file.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add boundary note: run `2026-06-08_042_*` exposed that the old manager ordering and file ceiling blocked a valid multi-file deterministic task; run `2026-06-08_043_*` fixed both limits and live-proved the new path.

## Unmerged / Needs Human Review
- Canonical workflow should decide whether the 4-file deterministic batch ceiling is conservative enough or whether more live proofs are needed before widening it.
