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

For smoke tests or slower model servers, use a tiny source and lower the optional output budgets:

```bash
export ZTH_DISTILLER_SESSION_MAX_TOKENS="900"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="700"
```

## Chunked Mode

Chunked mode splits long sources into fixed-size chunks. Each chunk gets its own summary before a final synthesis step.

Use chunked mode when a source is too long for one reliable model call.

Chunked mode makes multiple model calls, so it can be much slower than compact mode on CPU-bound or small model servers. For smoke tests, lower `ZTH_DISTILLER_CHUNK_LINES`, `ZTH_DISTILLER_CHUNK_MAX_TOKENS`, `ZTH_DISTILLER_SESSION_MAX_TOKENS`, and `ZTH_DISTILLER_PATCH_MAX_TOKENS`.

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

`MODEL_REQUEST.md` and `METRICS.json` record the chunk line size, token budgets, timeout, endpoint, and model used for the run.

`METRICS.json` also records passive telemetry for later human review and tuning:

- Source, prompt, session, and review-patch byte counts.
- Approximate token estimates based on file size.
- Elapsed seconds for chunk splitting, chunk summaries, session generation, and review-patch generation.
- Chunk summary attempt, retry, success, and failure counts.
- Failure stage when a run exits before completion.

Chunked runs write per-chunk telemetry to:

```text
outputs/run_records/<SOURCE_ID>_<SHORT_TITLE>/chunk_metrics.tsv
```

These metrics are evidence only. They do not automatically tune settings or accept generated context.

You can summarize recent runs and get advisory profile suggestions:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --limit 6
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --limit 6 --json
```

The JSON output includes `recommended_profile`, `recommended_settings`, and `recommendation_reason` for read-only guidance.

## Suggested Profiles

Use these as starting points, then adjust from `METRICS.json` and human review.

### Smoke Profile

Use this first on a new machine, new endpoint, or slow model server.

```bash
export ZTH_DISTILLER_SESSION_MAX_TOKENS="320"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="240"
export ZTH_DISTILLER_TIMEOUT="240"
./scripts/run_context_distiller_head.sh smoke-001 sources/toy_source.txt smoke --compact
```

Expected use:

- Tiny source file.
- Compact mode only.
- Confirms endpoint, model routing, output paths, telemetry, and review-patch generation.

### Normal Compact Profile

Use this for ordinary notes, short transcripts, or small docs after the smoke profile works.

```bash
export ZTH_DISTILLER_SESSION_MAX_TOKENS="1200"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="900"
export ZTH_DISTILLER_TIMEOUT="600"
./scripts/run_context_distiller_head.sh source-001 <SOURCE_FILE> short-title --compact
```

Expected use:

- Single source that fits one model call reliably.
- More complete session summaries than the smoke profile.
- Good default for CPU-bound or slower backends before trying chunked mode.

### Chunked Profile

Use this only when a source is too long for one reliable compact call.

```bash
export ZTH_DISTILLER_CHUNK_LINES="200"
export ZTH_DISTILLER_CHUNK_MAX_TOKENS="600"
export ZTH_DISTILLER_SESSION_MAX_TOKENS="1200"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="900"
export ZTH_DISTILLER_TIMEOUT="900"
./scripts/run_context_distiller_head.sh source-002 <SOURCE_FILE> long-source --chunked
```

Expected use:

- Longer transcripts or logs.
- Multiple model calls: chunk summaries, synthesis, and review patch.
- Slower than compact mode; watch `chunk_metrics.tsv` and stage timings.

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
