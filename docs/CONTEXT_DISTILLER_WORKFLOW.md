# Context Distiller Workflow

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md).

## Purpose

The context distiller turns source transcripts or logs into durable, reviewable project context without treating raw source text as canonical memory.

If you are new, run [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md) first.
For endpoint assumptions and examples, see [`docs/OPENAI_COMPATIBLE_ENDPOINTS.md`](OPENAI_COMPATIBLE_ENDPOINTS.md).

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

For smoke tests, use a tiny source and lower the optional output budgets:

```bash
export ZTH_DISTILLER_SESSION_MAX_TOKENS="320"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="240"
```

Some model endpoints need an explicit final-answer-only hint to avoid spending the response budget on hidden reasoning. Enable this when short direct harness tests work with `--final-only` but distiller calls time out or return reasoning-only content:

```bash
export ZTH_DISTILLER_FINAL_ONLY="1"
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
- `session_metadata.json`
- `patch_prompt.md`
- `patch_metadata.json`
- `OUTPUT.md`
- `REVIEW.md`
- `METRICS.json`
- `ACCEPTED.md`

Chunked runs also include chunk prompts, summaries, per-chunk metadata files, and error logs when retries fail.

`MODEL_REQUEST.md` and `METRICS.json` record the chunk line size, token budgets, timeout, endpoint, and model used for the run.
They also record whether final-only/no-think mode was enabled through `ZTH_DISTILLER_FINAL_ONLY`.
They record `run_profile` and `run_purpose` labels for separating setup checks from real work. The script infers defaults from mode and token budgets, or you can set them explicitly with `ZTH_DISTILLER_RUN_PROFILE` and `ZTH_DISTILLER_RUN_PURPOSE`.
When the model endpoint returns OpenAI-style metadata, `METRICS.json` records actual prompt, completion, and total tokens, finish reasons, and timing fields for the session and review-patch calls. If the endpoint does not return usage, the distiller still records estimated tokens from file size.

`METRICS.json` also records passive telemetry for later human review and tuning:

- Source, prompt, session, and review-patch byte counts.
- Approximate token estimates based on file size.
- Actual model usage tokens when the endpoint reports them.
- Finish reasons such as `stop` or `length` when the endpoint reports them.
- Prompt and generation timing fields when the endpoint reports them.
- Completion cap utilization and completion-to-output-estimate ratios in the metrics advisor.
- Budget tuning advice such as `raise_session_budget`, `raise_patch_budget`, `consider_lowering_budget`, or `profile_looks_good`.
- Run labels such as `smoke/connectivity`, `normal/handoff`, `chunked/handoff`, or `custom/tuning`.
- Elapsed seconds for chunk splitting, chunk summaries, session generation, and review-patch generation.
- Chunk summary attempt, retry, success, and failure counts.
- Failure stage when a run exits before completion.

Chunked runs write per-chunk telemetry to:

```text
outputs/run_records/<SOURCE_ID>_<SHORT_TITLE>/chunk_metrics.tsv
```

These metrics are evidence only. They do not automatically tune settings or accept generated context.

### Metrics Advisor and Filters

You can summarize recent runs and get advisory profile suggestions:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --limit 6
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --limit 6 --json
```

The JSON output includes `recommended_profile`, `recommended_settings`, `recommendation_reason`, `recommendation_confidence`, `confidence_reason`, `readiness`, `readiness_reason`, `blocking_signals`, `interviewer_verdict`, `interviewer_verdict_reason`, `role_critique_summary`, `role_critiques_strict`, `calibration_metrics`, `filters`, token-usage summaries, and `thresholds` for read-only guidance.

You can tune threshold behavior from CLI:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --limit 6 --json --min-recent-runs-for-chunked 2
```

You can append unseen runs to the interviewer ledger and include rolling calibration metrics:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --limit 6 --advisor-only --json --write-ledger --calibration-window 20
```

You can include role-critique findings in the verdict gate:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --advisor-only --json --role-critiques-file outputs/role_critiques.jsonl
```

You can force unresolved role critiques to block handoff:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --advisor-only --json --role-critiques-file outputs/role_critiques.jsonl --role-critiques-strict
```

You can use advisor-only summaries for handoff:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --limit 6 --advisor-only
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --limit 6 --advisor-only --json
```

If the latest run was only a connectivity or clipping test, exclude it from normal handoff advice:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir outputs/run_records --limit 6 --advisor-only --exclude-purpose connectivity
```

Flag behavior:

- `--json`: full JSON payload with per-run details.
- `--advisor-only`: concise text advisory summary.
- `--advisor-only --json`: concise advisor JSON payload without per-run `runs` details; includes `recommendation_confidence`, `confidence_reason`, `readiness`, `readiness_reason`, `blocking_signals`, `interviewer_verdict`, `interviewer_verdict_reason`, `role_critique_summary`, `role_critiques_strict`, `calibration_metrics`, `filters`, and `confidence_signals`.
- `--profile`, `--purpose`, and `--exclude-purpose`: filter advisory windows by run labels; flags can be repeated or passed as comma-separated values.

A displayed run label is formed as `<profile>/<purpose>`, such as
`smoke/connectivity` or `normal/handoff`. The two values are stored and
filtered separately:

- `--profile smoke` matches the exact `run_profile` value `smoke`.
- `--purpose connectivity` matches the exact `run_purpose` value
  `connectivity`.
- Use both flags to select the compound combination.
- `--profile smoke/connectivity` does not match the displayed compound label;
  the current implementation has no single compound-label filter.

Threshold scenarios:

- Default threshold 3 and fewer than 3 analyzed runs: a most-recent chunked run
  stays on `normal`.
- Default threshold 3 and at least 3 analyzed runs: can recommend `chunked`
  when the analyzed window has no failures, no chunk retries, average elapsed
  time at most 600 seconds, and the most-recent run is chunked, completed, and
  records zero chunk failures in both aggregate metrics and `chunk_metrics.tsv`.
- Override threshold 2 lowers only the minimum analyzed-run count to 2.

“Clean chunked run” is informal shorthand, not a separate stored field. The
current advisor checks the window and most-recent run as described above; it
does not require every analyzed run to be chunked, and it does not use semantic
output quality, finish reason, or length truncation in the profile
recommendation. Finish reasons still inform separate budget-tuning advice.
Using `--completed-only` excludes failed runs before this analysis.

## Suggested Profiles

Use these as starting points, then adjust from `METRICS.json` and human review.

### Smoke Profile

Use this first on a new machine, new endpoint, or slow model server.

```bash
export ZTH_DISTILLER_SESSION_MAX_TOKENS="320"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="240"
export ZTH_DISTILLER_TIMEOUT="240"
export ZTH_DISTILLER_RUN_PROFILE="smoke"
export ZTH_DISTILLER_RUN_PURPOSE="connectivity"
./scripts/run_context_distiller_head.sh smoke-001 examples/toy_source.txt smoke --compact
```

Expected use:

- `examples/toy_source.txt` is a harmless checked-in smoke fixture; replace it
  with any plain UTF-8 text file for your own test.
- Compact mode only.
- Confirms endpoint, model routing, output paths, telemetry, and review-patch generation.

### Normal Compact Profile

Use this for ordinary notes, short transcripts, or small docs after the smoke profile works. This profile favors token efficiency over maximum completeness and was tuned from actual usage telemetry on a slower local model server.

```bash
export ZTH_DISTILLER_SESSION_MAX_TOKENS="700"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="280"
export ZTH_DISTILLER_TIMEOUT="900"
export ZTH_DISTILLER_RUN_PROFILE="normal"
export ZTH_DISTILLER_RUN_PURPOSE="handoff"
./scripts/run_context_distiller_head.sh source-001 <SOURCE_FILE> short-title --compact
```

Expected use:

- Single source that fits one model call reliably.
- More complete session summaries than the smoke profile without the broad `1200/900` completion-token budget.
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

- `outputs/context/`: reserved for generated context artifacts. The current
  `run_context_distiller_head.sh` creates this directory but does not write an
  artifact there.
- `outputs/indexes/`: reserved for generated indexes or manifests. The current
  head script creates this directory but does not write an artifact there.
- `outputs/sessions/`: final generated session summaries.
- `outputs/review_patches/`: proposed context review patches.
- `outputs/run_records/`: prompts, copied input, metadata, metrics, stage
  evidence, and review placeholders for each run.

## Human Review

After generation:

1. Read the source if needed.
2. Read the session summary.
3. Read the review patch.
4. Decide Accepted, Rejected, Superseded, or Needs Rework.
5. Create a separate packet for any canonical update.

## Manifest Mode Addendum

Manifest mode adds a review-only, multi-pass workflow on top of the existing Context Distiller. It does not replace the legacy compact/chunked flow, and it does not auto-merge into canonical context.

### Legacy Comprehensive Mode

The legacy positional invocation remains supported for simple runs:

```bash
./scripts/run_context_distiller.sh <SOURCE_ID> <SOURCE_FILE> <SHORT_TITLE>
```

The compatibility wrapper constructs a default `comprehensive` manifest and routes through the same manifest-driven implementation.

### Manifest Mode

Use a manifest when you need deterministic input selection, independent focused passes, and optional synthesis:

```bash
./scripts/run_context_distiller.sh --manifest path/to/distiller_pass_manifest.json --plan-only
```

Remove `--plan-only` to execute the validated pass plan with the configured model-call abstraction.

The source-controlled focus profile registry lives at:

```text
docs/reports/model_auditions/CONTEXT_DISTILLER_FOCUS_PROFILES_v1.json
```

### Input Selection

Supported selectors are explicit and model-free:

```json
{
  "sources": ["repo-relative/source.txt"],
  "include_globs": [],
  "exclude_globs": [],
  "line_ranges": [],
  "chunk_indices": []
}
```

- source paths must be repository-relative;
- absolute paths and traversal are rejected;
- empty optional selectors mean no additional restriction;
- selected source hashes are recorded;
- excluded selector values are preserved.

### Chunk Controls

Manifest mode exposes the current effective chunk settings:

```json
{
  "target_chars": 12000,
  "overlap": 1,
  "offset": 1,
  "start_chunk": null,
  "end_chunk": null
}
```

### Passes and Synthesis

Each pass declares its own profile, input dependencies, and output filename. Passes do not automatically see one another.

An optional synthesis stage consumes only validated prior pass artifacts and emits a review-only bundle.

### Artifact Provenance

Each pass writes its own namespaced attempt directory containing:

- `pass_manifest.json`
- `source_manifest.json`
- `selected_input.txt`
- `prompt.md`
- `model_output.raw.json`
- `model_metadata.json`
- `model_content.json`
- `validation.json`
- `metrics.json`
- `provenance.json`

Retries create new linked attempt directories rather than overwriting evidence. The top-level job directory contains `job_manifest.json`, `plan.json`, `status.json`, and `review_bundle/`.

### Review Boundary

Raw source text, validated pass outputs, and synthesis outputs are evidence. None of them become canonical context automatically.

### Example Manifest

```json
{
  "schema": 1,
  "source_id": "demo-001",
  "inputs": {
    "sources": ["docs/CONTEXT_DISTILLER_WORKFLOW.md"],
    "include_globs": [],
    "exclude_globs": [],
    "line_ranges": [[1, 40]],
    "chunk_indices": []
  },
  "chunking": {
    "target_chars": 12000,
    "overlap": 1,
    "offset": 1,
    "start_chunk": null,
    "end_chunk": null
  },
  "passes": [
    {
      "id": "architecture",
      "profile": "architecture",
      "questions": [],
      "inputs_from_passes": [],
      "output": {
        "artifact_type": "focused_distillation",
        "filename": "architecture.md"
      }
    },
    {
      "id": "decisions",
      "profile": "decisions",
      "questions": [],
      "inputs_from_passes": [],
      "output": {
        "artifact_type": "focused_distillation",
        "filename": "decisions.md"
      }
    },
    {
      "id": "failures",
      "profile": "failures-and-corrections",
      "questions": [],
      "inputs_from_passes": [],
      "output": {
        "artifact_type": "focused_distillation",
        "filename": "failures.md"
      }
    }
  ],
  "synthesis": {
    "enabled": true,
    "input_passes": ["architecture", "decisions", "failures"],
    "profile": "synthesis",
    "output": {
      "artifact_type": "review_bundle",
      "filename": "synthesis.md"
    }
  }
}
```
