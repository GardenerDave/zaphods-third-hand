# Context Patch LOCAL-0020

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Extend troubleshooting guidance with a new observed class: reduced real-code two-file tasks can still stall after `send_completion_start` even when prewarm succeeds and preflight budget passes.
- Keep manager timeout classification fields (`exit_code`, `manager_timeout_detected`, `timeout_hint_detected`) as required evidence for post-dispatch stall diagnosis.

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Add escalation rule: after one additional reduced-surface repro still times out with no edits, route tiny deterministic changes through a direct-edit fallback path instead of repeating same-shape Aider retries.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add follow-on bug note: runtime/provider stall reproduced on reduced two-file parser/test surface (`icm_parsers.py` + `test_icm_call.py`) with `within_budget: true` and successful prewarm.

## Unmerged / Needs Human Review
- This source supports escalation toward direct-edit fallback for tiny deterministic edits, but final workflow policy should be approved after one one-file real-code confirmation run.
