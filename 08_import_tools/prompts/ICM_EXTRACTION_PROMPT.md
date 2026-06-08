# ICM Extraction Prompt

Use this prompt to convert a shared-link snapshot, copied raw chat, or export conversation into durable markdown context.

```markdown
You are converting a ChatGPT project conversation into an Interpretable Context Methodology markdown file for ProjectName / InternalCodename.

Project naming:
- Public-facing name: ProjectName.
- Internal/project continuity name: InternalCodename.
- Treat InternalCodename and ProjectName as interchangeable unless versioning or public-facing naming matters.

Author/legal:
- The author on project docs should be [REDACTED_AUTHOR].
- Do not add open-source license assumptions.
- Preserve rights-sensitive language unless [REDACTED_AUTHOR] explicitly chooses a license later.

Read the provided conversation snapshot and produce a durable project-context markdown summary.

Output only markdown.

Use this structure:

# Conversation Context File

## Source
- Source ID:
- Shared link:
- Local snapshot:
- Conversation title:
- Approximate date range:
- Project:
- Confidence:

## Executive Summary
Summarize the conversation in 5 to 10 sentences.

## Durable Facts
List facts that should persist across future project sessions.

## Decisions Made
List concrete project decisions, including naming, architecture, rules, UI behavior, licensing, versioning, or implementation direction.

## Open Questions
List unresolved questions or ambiguities.

## Bugs / Issues Identified
List bugs, symptoms, suspected causes, and affected versions when available.

## Rules Added
List behavioral, planning, parsing, UI, or agent rules that should govern future work.

## Version / Release Notes
List version references and what changed.

## User Preferences
List preferences relevant to future work. Do not include private or sensitive details unless directly relevant to the project.

## Files / Artifacts Mentioned
List any filenames, folders, ZIPs, screenshots, videos, code files, or docs referenced.

## Next Actions
List actionable next steps.

## Suggested ICM Destination
Recommend one or more paths where this summary should be saved.

## Compression Notes
Explain what was omitted and why.
```

## Patch Requirement

After creating a session summary, create a review patch in `ICM/07_review_queue/` using this structure:

```markdown
# Context Patch VP-0001

## Proposed updates to ICM/01_context/PROJECT_CONTEXT.md

## Proposed updates to ICM/01_context/ARCHITECTURE.md

## Proposed updates to ICM/01_context/PLANNING_RULES.md

## Proposed updates to ICM/01_context/AGENT_BRIEF.md

## Proposed updates to ICM/04_decisions/DECISION_LOG.md

## Proposed updates to ICM/05_bugs_and_tests/BUG_HISTORY.md

## Proposed updates to ICM/06_releases/RELEASE_TIMELINE.md

## Unmerged / Needs Human Review
```

