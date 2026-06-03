# Context Distiller Workflow

## Purpose

The context distiller turns source transcripts or logs into durable, reviewable project context without treating raw source text as canonical memory.

## Compact Mode

Compact mode asks the model for a concise summary using a fixed structure:

- Source.
- Executive Summary.
- Durable Facts.
- Decisions Made.
- Open Questions.
- Bugs / Issues Identified.
- Rules Added.
- Version / Release Notes.
- User Preferences.
- Files / Artifacts Mentioned.
- Next Actions.
- Suggested Destination.
- Compression Notes.

Use compact mode for most sources.

## Chunked Mode

Chunked mode splits long sources into fixed-size chunks. Each chunk gets its own summary before a final synthesis step.

Use chunked mode when a source is too long for one reliable model call.

## Chunk Summaries

Each chunk summary records:

- Chunk source.
- Durable facts.
- Decisions.
- Open questions.
- Issues.
- Rules.
- Preferences.
- Mentioned files/artifacts.
- Next actions.
- Compression notes.

## Synthesis Prompt

The synthesis prompt combines chunk summaries into one final session summary. It should not copy raw transcript text unless needed as evidence.

## Final Session

The final session summary is written to:

```text
outputs/sessions/
```

This file is evidence. It is not canonical context by itself.

## Review Patch

The review patch is written to:

```text
outputs/review_patches/
```

Review patches propose durable updates, but they are not canonical until a human accepts them and a separate packet applies the accepted update.

## Metrics And Audit Files

Each run records audit files under:

```text
outputs/run_records/
```

Typical audit files include:

- `TASK.md`
- `INPUT.md`
- `MODEL_REQUEST.md`
- `session_prompt.md`
- `patch_prompt.md`
- `OUTPUT.md`
- `REVIEW.md`
- `METRICS.json`
- `ACCEPTED.md`

Chunked runs also include chunk prompts, summaries, and error logs when retries fail.

## Expected Output Paths

```text
outputs/context/
outputs/indexes/
outputs/sessions/
outputs/review_patches/
outputs/run_records/
```

## Human Review

After generation:

1. Read the source if needed.
2. Read the session summary.
3. Read the review patch.
4. Decide Accepted, Rejected, Superseded, or Needs Rework.
5. Create a separate packet for any canonical update.
