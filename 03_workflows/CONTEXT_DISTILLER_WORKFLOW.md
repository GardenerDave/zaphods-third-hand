# Context Distiller Workflow

Author: [REDACTED]

## Purpose

The Context Distiller Workflow converts raw conversation sources into durable, reviewable ICM context for ProjectName / InternalCodename.

Raw chats are not canonical project memory. They are source material. The distiller extracts stable facts, decisions, bugs, rules, preferences, release notes, and next actions while preserving the original source unchanged.

## Core Principle

Do not blindly append raw transcripts to canonical context.

Raw conversations contain stale plans, repeated explanations, dead ends, temporary assumptions, and unresolved contradictions. Canonical ICM files should contain only reviewed, durable distillations.

## Source Priority

Use sources in this order when available:

1. Official ChatGPT export ZIP or `conversations.json`
2. Local plain-text transcript
3. Browser-saved local HTML / markdown / PDF snapshot
4. Copied raw chat text
5. Hosted shared link, only after its visible content is saved locally

Hosted links are source pointers, not durable archives. If a hosted link returns a login page, JavaScript/cookie challenge, placeholder, or missing content, preserve the failed capture and mark the source `failed`.

## Input Locations

Primary source intake paths:

```text
ICM/00_sources/chatgpt_exports/
ICM/00_sources/terminal_exports/
ICM/00_sources/shared_links/snapshots/
ICM/00_sources/shared_links/SharedLinks.txt
```

Index and manifest paths:

```text
ICM/09_indexes/CONVERSATION_INDEX.csv
ICM/00_sources/shared_links/shared_links_manifest.md
ICM/00_sources/shared_links/shared_links_manifest.csv
```

## Output Locations

Each processed source should produce at least:

```text
ICM/02_sessions/YYYY-MM-DD_short-title.md
ICM/07_review_queue/context_patch_SOURCE-ID.md
```

Canonical merge targets include:

```text
ICM/01_context/PROJECT_CONTEXT.md
ICM/01_context/ARCHITECTURE.md
ICM/01_context/PLANNING_RULES.md
ICM/01_context/AGENT_BRIEF.md
ICM/03_workflows/CONVERSATION_TO_CONTEXT_WORKFLOW.md
ICM/03_workflows/SHARED_LINK_SNAPSHOT_WORKFLOW.md
ICM/03_workflows/DEV_AGENT_WORKFLOW.md
ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md
ICM/04_decisions/DECISION_LOG.md
ICM/05_bugs_and_tests/BUG_HISTORY.md
ICM/06_releases/RELEASE_TIMELINE.md
ICM/09_indexes/CONVERSATION_INDEX.csv
```

## Source ID Rules

Use stable IDs so source history remains auditable.

```text
LOCAL-0001, LOCAL-0002, ...   local transcript/export/copy sources, including copied terminal exports
VP-0001, VP-0002, ...         hosted ProjectName shared-link sources
WRAP-0001, WRAP-0002, ...     wrapper-generated scaffold/source summaries
EXPORT-0001, EXPORT-0002, ... official ChatGPT export packages
```

When a ZIP export contains multiple per-conversation Markdown files, assign one `EXPORT-000N` ID per extracted conversation and record the ZIP package path in the session summary and index notes.

Do not reuse IDs. If a failed source is later replaced by a local transcript, preserve the failed source and add a new local source ID.

Example:

```text
VP-0001 = failed hosted shared-link attempt
LOCAL-0001 = usable local transcript for the same or related conversation
```

## Processing Stages

### Stage 1 — Discover Sources

Inspect source intake directories for new files or queued links.

Checklist:

- Look for new files under `ICM/00_sources/chatgpt_exports/`.
- Look for new files under `ICM/00_sources/terminal_exports/`.
- Look for new files under `ICM/00_sources/shared_links/snapshots/`.
- Check whether `ICM/00_sources/shared_links/SharedLinks.txt` contains active hosted links.
- Compare discovered sources against `ICM/09_indexes/CONVERSATION_INDEX.csv`.
- Identify unindexed sources.

If `SharedLinks.txt` is empty or whitespace-only, treat it as no active hosted links queued.

### Stage 2 — Preserve Raw Source

Never modify raw source files directly.

For hosted links:

- Save visible content locally before extraction.
- If content cannot be accessed, save the failed page or a failure note.
- Mark the source `failed` if no conversation content is visible.

For local transcripts or exports:

- Leave the source file unchanged.
- Record path, size, line count, and date processed.

### Stage 3 — Assign Source ID

Assign the next available source ID based on source type.

Examples:

```text
LOCAL-0003
EXPORT-0001
VP-0019
```

Add or prepare an index row with:

```text
id
source_type
source_path_or_link
project
date_range
title
status
summary_path
context_patch_path
notes
```

### Stage 4 — Extract Session Summary

Create a session summary in `ICM/02_sessions/`.

Filename format:

```text
YYYY-MM-DD_short-title.md
```

Required structure:

```markdown
# Conversation Context File

## Source
- Source ID:
- Source type:
- Source file or link:
- Conversation title:
- Approximate date range:
- Project:
- Confidence:

## Executive Summary

## Durable Facts

## Decisions Made

## Open Questions

## Bugs / Issues Identified

## Rules Added

## Version / Release Notes

## User Preferences

## Files / Artifacts Mentioned

## Next Actions

## Suggested ICM Destination

## Compression Notes
```

### Stage 5 — Create Context Patch

Create a review patch in `ICM/07_review_queue/`.

Filename format:

```text
context_patch_SOURCE-ID.md
```

Required structure:

```markdown
# Context Patch SOURCE-ID

## Proposed updates to ICM/01_context/PROJECT_CONTEXT.md

## Proposed updates to ICM/01_context/ARCHITECTURE.md

## Proposed updates to ICM/01_context/PLANNING_RULES.md

## Proposed updates to ICM/01_context/AGENT_BRIEF.md

## Proposed updates to ICM/03_workflows/CONVERSATION_TO_CONTEXT_WORKFLOW.md

## Proposed updates to ICM/03_workflows/SHARED_LINK_SNAPSHOT_WORKFLOW.md

## Proposed updates to ICM/03_workflows/DEV_AGENT_WORKFLOW.md

## Proposed updates to ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md

## Proposed updates to ICM/04_decisions/DECISION_LOG.md

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md

## Proposed updates to ICM/06_releases/RELEASE_TIMELINE.md

## Unmerged / Needs Human Review
```

The patch should separate high-confidence durable facts from uncertain, contradictory, or review-needed material.

### Stage 6 — Merge Canonical Updates Cautiously

Only merge high-confidence durable information into canonical files.

Merge rules:

- Do not duplicate existing entries.
- Prefer appending dated entries over rewriting history.
- Do not silently resolve contradictions.
- Put contradictions in `ICM/07_review_queue/`.
- Do not infer implementation facts not present in the source.
- Mark uncertainty explicitly.
- Preserve user-tested behavior and project decisions.

### Stage 7 — Update Indexes And Manifests

Update `ICM/09_indexes/CONVERSATION_INDEX.csv` after successful processing.

Status values:

```text
unprocessed
snapshot_saved
extracted
reviewed
merged
deprecated
failed
```

For shared links, update the shared-link manifest only when the link itself is part of the active queue or historical shared-link audit trail.

### Stage 8 — Report Work Done

Every distillation run should end with a report.

Required report structure:

```markdown
# Context Distiller Report

## Sources Found
- source path or link
- indexed or unindexed
- file size and line count when applicable
- selected for processing or skipped

## Sources Processed
| ID | Title / Topic | Status | Size / Lines | Summary Path | Patch Path |
|---|---|---|---|---|---|

## Canonical Files Updated
- file path
- summary of change

## Review Queue Items
- file path
- why review is needed

## Failed / Skipped Sources
- source
- reason

## Git Status
Include `git status --short`.
If the workspace root is not a git repository, also check the nested app repo if present.
If the distiller run was committed, include the commit hash.

## Recommended Next Action
Give the single most useful next step.

## Local Agent Usage
If local models were used, include model names, run paths, estimated input/output tokens, elapsed time, observed tokens per second when available, accepted/rejected status, and conservative cloud-token savings estimate.
```

### Stage 9 — Validate And Commit

After a successful distiller run:

1. Run `git diff --check`.
2. Review `git status --short`.
3. Stage only the raw source, generated session summary, generated review patch, index updates, and canonical/workflow docs touched by the distillation.
4. Commit the completed distiller output.
5. Include the commit hash in the final report.

Do not modify raw source files only to satisfy whitespace checks. If a copied terminal transcript or other raw source contains trailing whitespace, preserve it unchanged, run the whitespace check against generated/canonical files separately, and report the raw-source whitespace exception in the distiller report.

Use a commit message in this shape:

```text
Distill SOURCE-ID short-title
```

Skip auto-commit only when:

- The user explicitly asks not to commit.
- Validation fails.
- The workspace contains unrelated changes that cannot be separated safely.
- The distillation is incomplete or needs user input before becoming durable.

## What Counts As Durable Context

Durable context includes:

- Project identity and naming decisions
- Architecture decisions
- Planning rules
- Parser rules
- UI behavior rules
- Agent workflow rules
- User preferences relevant to the project
- Bugs, symptoms, expected behavior, and tested outcomes
- Release/version notes
- Source-handling decisions
- Open questions that affect future work
- Constraints that future agents must obey

## What Should Not Be Merged Directly

Do not merge these directly into canonical context without review:

- Raw conversation text
- Repeated explanations
- Temporary speculation
- Stale implementation plans
- Failed approaches unless recorded as lessons or bug history
- External paper metadata not independently verified
- Contradictory claims
- Model guesses about source contents
- Hosted-link content that was not locally captured

## Review Queue Policy

Use `ICM/07_review_queue/` for:

- Contradictions
- Unverified external facts
- Conflicting source records
- Proposed major architecture changes
- Ambiguous user preferences
- Failed source captures
- Anything that might be important but should not be canonical yet

## Existing Source State As Of 2026-05-22

Known extracted local sources:

```text
LOCAL-0001 = ProjectName ICM conversation plain-text transcript
LOCAL-0002 = Interpretable Context Methodology conversation plain-text transcript
LOCAL-0003 = ProjectName / InternalCodename agent workflow conversation archive
LOCAL-0004 = ICM workflow milestone and Navigator assistant-persona naming note
```

Known extracted export-batch sources:

```text
EXPORT-0001 through EXPORT-0017 = per-conversation Markdown files extracted from ICM/00_sources/chatgpt_exports/Export.zip
```

Where EXPORT sources overlap LOCAL-0001 through LOCAL-0003, treat the EXPORT sources as preferred and keep the LOCAL rows as lower-confidence audit history.

As of LOCAL-0004, [REDACTED_AUTHOR] stated that EXPORT-0001 through EXPORT-0017 represent every prior InternalCodename project conversation before that milestone conversation. Treat that as the current source-coverage marker for project conversations unless later evidence contradicts it.

Known failed hosted-link sources:

```text
VP-0001 through VP-0018 = failed ChatGPT hosted-link captures
```

These failed records should remain audit history unless [REDACTED_AUTHOR] explicitly instructs otherwise.

## Future Automation Direction

The first automated distiller should support local transcript and export files before attempting hosted-link automation.

The current manual Context Distiller pipeline remains the default workflow until a better method is discovered.

Local models may draft source discovery reports, session summaries, and context patches when the inputs are narrow and the output is reviewed before canonical merge. Use `ICM/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md` and record nontrivial runs under `ICM/10_agent_runs/`.

Recommended implementation order:

1. Detect new local transcript/export files.
2. Compare them against `CONVERSATION_INDEX.csv`.
3. Assign a new source ID.
4. Draft session summary and context patch.
5. Apply only safe canonical updates.
6. Produce a report.
7. Leave raw source unchanged.
8. Validate and commit the completed distiller output.

Hosted-link automation should remain secondary because hosted links may require authentication, JavaScript, cookies, or browser state.

## Agent Constraints

- Do not delete raw sources.
- Do not delete failed shared-link audit records.
- Do not modify app source code during context distillation.
- Commit completed distiller output automatically after validation unless the user explicitly asks not to commit or the run is unsafe/incomplete.
- Do not add dependencies unless explicitly instructed.
- Preserve author attribution to [REDACTED_AUTHOR].
- Do not add open-source license assumptions.
- Prefer careful, auditable markdown over aggressive summarization.
- Be transparent about uncertainty and inaccessible content.
