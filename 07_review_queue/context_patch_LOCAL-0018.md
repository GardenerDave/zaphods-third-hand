# Context Patch LOCAL-0018

## Proposed updates to ICM/01_context/PROJECT_CONTEXT.md
- Add a note that the sanitized handoff repo may not include full canonical context tree folders, so distillation outputs can temporarily live in `02_sessions/`, `07_review_queue/`, and `09_indexes/` until canonical targets are restored.

## Proposed updates to ICM/01_context/ARCHITECTURE.md
- Add a tooling interoperability note: local OpenAI-compatible endpoints used by Aider require provider-qualified model IDs (for example `openai/<model>`), plus expected provider auth environment variables where applicable.

## Proposed updates to ICM/01_context/PLANNING_RULES.md
- Add a path-safety rule: when using interactive tool commands that interpret paths internally, do not assume shell `~` expansion; verify the resolved path before adding to chat/edit context.

## Proposed updates to ICM/01_context/AGENT_BRIEF.md
- Add a reminder that raw transcript files are source evidence only and must be distilled into session summaries and review patches before any canonical merge.

## Proposed updates to ICM/03_workflows/CONVERSATION_TO_CONTEXT_WORKFLOW.md
- Add explicit mention of terminal transcript pitfalls to extract during distillation: auth/config errors, path resolution mistakes, and reproducible command-shape failures.

## Proposed updates to ICM/03_workflows/SHARED_LINK_SNAPSHOT_WORKFLOW.md
- No high-confidence update from this source.

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md
- Add a practical rule to include command-shape validation for local model tooling (model name format, endpoint shape, auth env) before deeper troubleshooting.

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
- Add a manager checkpoint to classify failures as endpoint-health vs transport-layer/tool-wrapper issues when direct API calls succeed but wrapper workflows fail.

## Proposed updates to ICM/04_decisions/DECISION_LOG.md
- Proposed entry: prefer `pipx` over system `pip` for standalone CLI installation in externally managed Python environments.

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md
- Proposed bug pattern entry: accidental creation of literal `./~` directories when interactive path inputs bypass shell expansion assumptions.

## Proposed updates to ICM/06_releases/RELEASE_TIMELINE.md
- No release update proposed from this source.

## Unmerged / Needs Human Review
- The transcript includes extensive run-by-run claims around Aider transport health and specific run-folder outcomes; these should be merged only after direct verification against current artifacts.
- Assistant persona naming notes (“Navigator” / “Nav”) are user preference context, not architecture decisions.
- Some transcript sections are verbose and iterative; avoid overfitting workflow rules to one environment snapshot.