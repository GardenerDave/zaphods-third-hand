# Context Patch LOCAL-0021

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Promote escalation rule from provisional to active: if one-file real-code bounded Aider run still ends in post-dispatch timeout with no edits, switch tiny deterministic changes to direct-edit fallback for the current endpoint/runtime.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Add explicit endpoint-state note: `within_budget: true` and successful prewarm do not imply completion reliability for real-code Aider payloads on this local Gemma path.
- Keep post-dispatch stall classification anchored on event sequence (`send_completion_start` only) plus manager timeout fields.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add escalation evidence: one-file real-code run (`2026-06-08_031_*`) reproduces the same stall mode previously seen on two-file surfaces.

## Unmerged / Needs Human Review
- Direct-edit fallback activation is supported by repeated bounded failures (030, 031), but canonical workflow merge should still be approved by maintainer review.
