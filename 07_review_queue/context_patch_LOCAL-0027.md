# Context Patch LOCAL-0027

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Record the failure mode where a deterministic block-replacement prompt is valid in principle but exceeds the manager prompt cap, causing an avoidable fallthrough to whole-file Aider.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Add routing rule: when `direct_edit_candidate.reason` is `prompt_too_long`, treat that as a manager-envelope problem first, not as evidence that the underlying deterministic edit shape is invalid.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Add limit note: run `2026-06-08_037_*` showed the old deterministic prompt cap of `600` was too low for practical block-replacement instructions on a real repo file.

## Unmerged / Needs Human Review
- Canonical workflow should decide whether future prompt-cap increases need live proof every time or can be justified by deterministic parser safety alone.
