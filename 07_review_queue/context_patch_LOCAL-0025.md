# Context Patch LOCAL-0025

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Expand the documented deterministic direct-edit envelope to `prompt_char_limit: 600` and `file_size_limit_bytes: 16384`, with the existing exact-target and unique-match requirements.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Add new routing signal: preflight should surface direct-edit eligibility explicitly, and eligible tasks should bypass Aider even when `validated_shape_match: false`.
- Record that the widened direct-edit envelope is live-proven on a real file above the old 4096-byte ceiling.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add limit-moved note: run `2026-06-08_035_*` proves the widened deterministic path on a 10507-byte real file while avoiding the unstable whole-file Aider route.

## Unmerged / Needs Human Review
- Canonical workflow should decide whether the 16384-byte guardrail is final policy or still provisional pending more real-file proofs.
