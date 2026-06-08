# Context Distiller Report

## Sources Found
- `10_agent_runs/2026-06-08_037_gemma-direct-edit-block-readme/`
  - indexed or unindexed: unindexed at run start
  - selected for processing or skipped: selected for processing

## Sources Processed
| ID | Title / Topic | Status | Size / Lines | Summary Path | Patch Path |
|---|---|---|---|---|---|
| LOCAL-0027 | Block-replacement prompt-limit failure (run 037) | extracted | run-folder artifact set | `02_sessions/2026-06-08_gemma-aider-037-block-limit.md` | `07_review_queue/context_patch_LOCAL-0027.md` |

## Canonical Files Updated
- None in this sanitized tree.

## Review Queue Items
- `07_review_queue/context_patch_LOCAL-0027.md`
  - why review is needed: it promotes a specific direct-edit preflight failure mode into workflow guidance.

## Failed / Skipped Sources
- None.

## Recommended Next Action
Use the follow-up proof run to justify widening the deterministic prompt limit, then prefer short-circuit routing for block replacements that fit the new envelope.

## Local Agent Usage
One manager-wrapped run fell through to whole-file Aider after preflight classified the block-replacement prompt as too long; the run then timed out in the known bounded failure mode.
