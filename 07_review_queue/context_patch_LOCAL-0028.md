# Context Patch LOCAL-0028

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Expand the documented deterministic manager route to include unique-anchor block replacement with `replace the block from ... through ... with ...`.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Update the current deterministic prompt cap to `1200` characters.
- Record that unique-anchor block replacement is now live-proven on a real repo file with zero Aider and zero endpoint usage.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add limit-moved note: run `2026-06-08_038_*` proves that widening the deterministic prompt cap moved a real manager boundary and enabled block replacement on a large repo file.

## Unmerged / Needs Human Review
- Canonical workflow should decide whether `1200` is treated as the stable ceiling or remains provisional pending more real-file block proofs.
