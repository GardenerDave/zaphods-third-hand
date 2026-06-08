# Local Agent Task

## Task
- Task ID: 2026-06-07_007_gemma-aider-read-context
- Assigned model: openai/gemma4 via Aider v0.86.2
- Role: supervised local Aider read-context test
- Objective: verify that the `gemma-local` profile can use a trimmed `--read` input while editing one tiny target file

## Inputs
- `10_agent_runs/2026-06-07_007_gemma-aider-read-context/MODEL_REQUEST.md`
- `10_agent_runs/2026-06-07_007_gemma-aider-read-context/TARGET.md`
- `10_agent_runs/2026-06-07_007_gemma-aider-read-context/REFERENCE.md`

## Constraints
- Edit only `TARGET.md`.
- Use `REFERENCE.md` as read-only context.
- Do not touch any repo files outside this run folder.
- Do not commit.
