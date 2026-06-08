# Conversation To Context Workflow

Author: [REDACTED]

## Goal

Convert long conversations into concise, durable, reviewable markdown context files.

## Workflow

1. Capture source: official export ZIP, local plain-text transcript, browser-saved snapshot, shared link, or copied raw chat.
2. Register source in the appropriate manifest or index.
3. Save local snapshot before summarizing hosted content.
4. Extract with `ICM/08_import_tools/prompts/ICM_EXTRACTION_PROMPT.md`.
5. Save conversation-specific summaries into `ICM/02_sessions/`.
6. Save proposed project-level updates into `ICM/07_review_queue/`.
7. Review uncertain material and contradictions before canonical merge.
8. Merge approved durable facts into `ICM/01_context/`, `ICM/04_decisions/`, `ICM/05_bugs_and_tests/`, and `ICM/06_releases/`.
9. Update `ICM/09_indexes/CONVERSATION_INDEX.csv` and the relevant source manifest.

## Source Priority

Prefer official exports or local transcript/export files for extraction. Use browser-saved local snapshots next. Treat hosted shared links as source pointers until their visible content has been saved locally.

Delayed official exports should not block wrapper scaffolding. If a hosted link fails but a local transcript exists, preserve the failed link record and extract from the local transcript.

An empty `ICM/00_sources/shared_links/SharedLinks.txt` means no active hosted links are queued. Prefer LOCAL-0001 or other local transcript/export files when available.

## Context Distillation Rules

- Do not blindly append raw transcripts to canonical context.
- Preserve original export ZIPs and `conversations.json` unchanged for future reevaluation.
- Distill raw conversations into reviewed session summaries, decision updates, bug updates, rules, next actions, and review patches.
- Keep stable reference material separate from run-specific working artifacts.
- Early distiller outputs may include `SESSION_SUMMARY.md`, `DECISIONS_APPEND.md`, `BUGS_APPEND.md`, and `TODO_APPEND.md` before human-reviewed merge.

## Merge Rules

- Do not duplicate entries already present.
- Prefer appending dated entries over rewriting history.
- Clearly mark uncertain items as uncertain.
- Never invent implementation facts.
- Never silently resolve contradictions.
- Put contradictions in `ICM/07_review_queue/`.
