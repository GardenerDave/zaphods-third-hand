# ChatGPT Export Distiller

This page documents the early ChatGPT export flow: ingestion first, optional context-aware chunk
planning, extraction packet generation, supervised packet execution, raw-signal validation,
deterministic raw-signal dedupe, then review-bundle generation.

## Local Export Placement

Keep real ChatGPT exports outside tracked files. A safe local pattern is:

```text
sources/chatgpt_exports/<private-label>/conversations.json
```

The `sources/` directory is gitignored. You can also use a temporary directory under `/tmp`.

Do not commit real ChatGPT export files. They can contain private prompts, personal data, credentials, or project material that should not enter the repository.

## Run Ingestion

From the repo root:

```bash
python3 local_harness/chatgpt_export_ingest.py \
  --export-dir sources/chatgpt_exports/<private-label> \
  --out-dir /tmp/zth_chatgpt_export_test/sources
```

For the bundled synthetic fixture:

```bash
python3 local_harness/chatgpt_export_ingest.py \
  --export-dir examples/chatgpt_export_fixture \
  --out-dir /tmp/zth_chatgpt_export_test/sources
```

## Produced Files

The ingester writes UTF-8 plain files:

```text
<out-dir>/normalized/
<out-dir>/manifests/conversations.jsonl
```

Each conversation gets one normalized markdown file under `normalized/`. The JSONL manifest records one row per conversation with the stable conversation id, title, slug, timestamps, normalized file path, source hash, turn count, and byte count.

## Run Chunk Planning

Chunk planning operates on the normalized markdown files produced by ingestion. It reads the ingestion manifest:

```bash
python3 local_harness/context_chunker.py \
  --manifest /tmp/zth_chatgpt_export_test/sources/manifests/conversations.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/chunks \
  --profile small-model-offset
```

Optional sizing overrides:

```bash
python3 local_harness/context_chunker.py \
  --manifest /tmp/zth_chatgpt_export_test/sources/manifests/conversations.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/chunks \
  --profile small-model \
  --target-chars 12000 \
  --overlap-turns 1 \
  --offset-turns 1
```

Sizing is approximate and deterministic. The current planner uses character counts rather than a tokenizer so it has no mandatory third-party dependency.

## Chunk Profiles

Supported profiles:

- `semantic`: preserves turn boundaries and groups user/assistant exchanges where possible. It writes `pass_A` only.
- `small-model`: preserves turn boundaries where possible and uses `--target-chars` as an approximate maximum for non-oversized chunks. It writes `pass_A` only.
- `small-model-offset`: uses the `small-model` strategy and also writes a shifted `pass_B_offset` pass.

The offset pass starts later by `--offset-turns` turns. It is for human review of context that may fall near chunk boundaries in `pass_A`; it is not a deduplication or synthesis step.

## Chunk Outputs

For each conversation, the planner writes:

```text
<out-dir>/<conversation_id>/
  chunk_plan.json
  pass_A/
    chunk_000.md
  pass_B_offset/
    chunk_000.md
```

`pass_B_offset/` is created only for the `small-model-offset` profile.

Each chunk markdown file has a metadata header with the conversation id, title, source hash, source path, chunk id, pass name, index, profile, turn range, oversized flag, and chunk strategy. The source turns follow under `## Source Turns`.

`chunk_plan.json` records the profile settings and points to every chunk file. Stable chunk ids are derived from the conversation id, pass name, chunk index, turn range, and source hash.

If a single turn is larger than `--target-chars`, this slice keeps it whole in one oversized chunk and marks it with `oversized: true`. It does not split inside a turn.

## Generate Extraction Packets

Extraction packet generation reads chunk plans and chunk markdown files. It does not call a model.

```bash
python3 local_harness/signal_extraction_packets.py \
  --chunk-root /tmp/zth_chatgpt_export_test/chunks \
  --out-dir /tmp/zth_chatgpt_export_test/extraction_packets
```

For real-export canaries and CPU-bound local models, cap requested extraction volume:

```bash
python3 local_harness/signal_extraction_packets.py \
  --chunk-root /tmp/zth_chatgpt_export_test/chunks \
  --out-dir /tmp/zth_chatgpt_export_test/extraction_packets \
  --max-signals-per-packet 2
```

Real canary runs showed that some local CPU models can return useful pretty-printed JSON objects and
then continue into another object until the response hits `--max-tokens`, leaving an incomplete
trailing JSON region. The runner preserves that raw output and the normalizer correctly fails the
incomplete region. `--max-signals-per-packet 2` keeps packet prompts bounded by asking the model to
return only the highest-confidence durable signals and stop after the cap.

The packet generator writes:

```text
<out-dir>/packets.jsonl
<out-dir>/packet_files/
  packet_000001.md
<out-dir>/packet_summary.json
```

Each packet is a model-ready prompt containing the chunk metadata, raw-signal JSONL output contract,
allowed labels, review-only rules, and the source chunk. Packet ids are deterministic from the
conversation id, chunk id, chunk pass, and source hash.

When `--max-signals-per-packet` is set, the cap is recorded in `packets.jsonl` rows and
`packet_summary.json`; uncapped packet generation remains the default when the flag is omitted.

Use these packets manually with a model later if you choose. This generation step only creates plain
files for review and does not batch, route, or execute model calls.

## Plan Real-Export Packet Runs

Before running a large private export against a local model, generate a scale summary and reviewable
batch ranges from the existing manifests:

```bash
python3 local_harness/chatgpt_export_run_plan.py \
  --ingest-manifest /tmp/zth_chatgpt_export_test/sources/manifests/conversations.jsonl \
  --chunk-root /tmp/zth_chatgpt_export_test/chunks \
  --packets /tmp/zth_chatgpt_export_test/extraction_packets/packets.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/run_plan \
  --batch-size 10
```

The planner writes:

```text
<out-dir>/run_plan_summary.json
<out-dir>/batch_manifest.jsonl
<out-dir>/batch_commands.sh
<out-dir>/README.md
```

`run_plan_summary.json` records conversation, chunk, packet, pass, and batch counts. `batch_manifest.jsonl`
contains deterministic 1-based packet ranges. `batch_commands.sh` is intentionally comments only: it
shows commands to copy and run manually, one batch at a time, using `--start-index`, `--end-index`,
`--resume`, and `--validate`.

Optional planner flags such as `--base-url`, `--model`, `--timeout-seconds`, `--max-tokens`,
`--retries`, and `--retry-delay-seconds` are copied into the commented batch commands or environment
comments. The planner does not call models and does not execute the generated commands.

## Run Packet Extraction

The packet runner is supervised and explicit. It reads `packets.jsonl`, sends selected packet files to
an OpenAI-compatible `/chat/completions` endpoint, and writes raw model output files. It does not
canonicalize, dedupe, promote, or update lifecycle state.

Verify the synthetic dry run before pointing this at any private export-derived packets:

```bash
python3 local_harness/run_signal_extraction_packets.py \
  --packets /tmp/zth_chatgpt_export_test/extraction_packets/packets.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/model_raw_signals \
  --limit 1 \
  --dry-run
```

Dry runs do not call an endpoint and do not write raw output placeholders. They write:

```text
<out-dir>/run_manifest.jsonl
<out-dir>/run_summary.json
```

Configure a local OpenAI-compatible endpoint explicitly:

```bash
export ZTH_SIGNAL_EXTRACT_BASE_URL="http://127.0.0.1:8081/v1"
export ZTH_SIGNAL_EXTRACT_API_KEY="not-needed-for-local"
export ZTH_SIGNAL_EXTRACT_MODEL="local-signal-extractor"
export ZTH_SIGNAL_EXTRACT_TIMEOUT_SECONDS="120"
export ZTH_SIGNAL_EXTRACT_MAX_TOKENS="1200"
export ZTH_SIGNAL_EXTRACT_TEMPERATURE="0"
```

Run one packet:

```bash
python3 local_harness/run_signal_extraction_packets.py \
  --packets /tmp/zth_chatgpt_export_test/extraction_packets/packets.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/model_raw_signals \
  --limit 1
```

You can also override configuration with `--base-url`, `--api-key`, `--model`,
`--timeout-seconds`, `--max-tokens`, and `--temperature`. Use `--packet-id <packet-id>` to run a
specific packet.

For survivable long local-model runs, run explicit small batches:

```bash
python3 local_harness/run_signal_extraction_packets.py \
  --packets /tmp/zth_chatgpt_export_test/extraction_packets/packets.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/model_raw_signals \
  --start-index 1 \
  --end-index 10 \
  --resume \
  --retries 1 \
  --retry-delay-seconds 2
```

`--start-index` and `--end-index` are 1-based positions in `packets.jsonl`, with `--end-index`
inclusive. Selection is deterministic: range filtering happens first, then `--packet-id`, then
`--limit`.

`--resume` reads the existing `run_manifest.jsonl` in the output directory and skips selected packets
that already have `status: "ok"` plus an existing raw output file. Failed, missing, or incomplete
packets are run again. Resume only avoids repeated endpoint calls; it does not accept, dedupe,
promote, or update memory.

Single-packet repair runs write a fresh current `run_manifest.jsonl`, so that file may only describe
the repaired packet. Resume also checks deterministic `raw_outputs/<packet_id>.jsonl` and
`normalized_outputs/<packet_id>.jsonl` files for every selected packet. With `--validate`, existing raw
outputs must normalize successfully or the packet remains eligible to rerun; missing normalized files
are regenerated from valid raw output without calling the model. Failed, empty, or truncated raw
outputs are not silently accepted.

`--retries` retries failed endpoint calls only. It does not retry packet-file errors, normalization
failures, validation failures, or any later review step. The manifest records `attempt_count`,
`resume_skipped`, `resume_source`, and `selected_index` for each selected packet.

During non-dry-run execution, the runner prints concise progress lines such as `Running packet 1/12`,
`OK packet 1/12`, `ERROR packet 1/12`, or `SKIP packet 1/12`.

Successful model responses are written exactly as returned by the model:

```text
<out-dir>/raw_outputs/<packet_id>.jsonl
<out-dir>/run_manifest.jsonl
<out-dir>/run_summary.json
```

Endpoint and packet-file errors are recorded per packet in `run_manifest.jsonl`; the runner continues
to the next selected packet.

To validate successful raw outputs in the same supervised run:

```bash
python3 local_harness/run_signal_extraction_packets.py \
  --packets /tmp/zth_chatgpt_export_test/extraction_packets/packets.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/model_raw_signals \
  --limit 1 \
  --validate
```

`--validate` concatenates successful raw outputs into `combined_raw_signals.jsonl` and writes validator
outputs under `<out-dir>/validated/`. It still does not dedupe.

Before validation, the runner performs deterministic output-shape normalization and writes the result
separately:

```text
<out-dir>/normalized_outputs/<packet_id>.jsonl
<out-dir>/combined_raw_signals.jsonl
<out-dir>/normalization_summary.json
<out-dir>/validated/
```

Raw output files are preserved unchanged. Normalized output files are compact JSONL and are the files
used for validation.

When `--resume` and `--validate` are used together, normalization and validation are rebuilt from all
successful selected raw output files, including resume-skipped packets. This makes interrupted runs
recoverable without calling the endpoint again for completed packets.

Normalization accepts:

- Already-valid JSONL.
- A single JSON object.
- A JSON array of objects.
- A JSON object or array inside one markdown JSON fence.
- JSONL objects inside one markdown JSON or JSONL fence.
- Multiple complete top-level JSON objects or arrays inside one markdown JSON or JSONL fence.
- Multiple complete top-level JSON objects or arrays separated only by whitespace and/or commas.
- Leading/trailing prose only when one JSON object or array can be extracted unambiguously.

Some local models may return pretty-printed multi-object JSON instead of JSONL, or wrap JSONL and
multi-object JSON in markdown fences. When this shape is safe, the runner writes one compact JSONL
row per object and flattens arrays only when every array element is an object. Raw output files are
still preserved exactly as returned by the model.

Normalization rejects unparseable text, prose between multiple JSON regions, prose outside or inside
markdown JSON fences, incomplete trailing JSON objects or arrays, scalar JSON values, and arrays
containing non-object items.

Normalization repairs output shape only. It does not invent missing fields, rewrite claims, change
meaning, dedupe, or decide canonical status. Field defaults and label normalization remain the
validator's job.

## Validate Raw Signals

Raw signal validation checks a JSONL file before dedupe:

```bash
python3 local_harness/raw_signal_validate.py \
  --raw-signals examples/chatgpt_export_fixture/raw_signals.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/validated_signals
```

The validator writes:

```text
<out-dir>/valid_raw_signals.jsonl
<out-dir>/invalid_raw_signals.jsonl
<out-dir>/validation_summary.json
```

Validation requires a non-empty `claim`. Empty claims are written to `invalid_raw_signals.jsonl`.
Invalid JSON lines are also written there with the line number and parse error.

Missing optional fields are filled with conservative defaults. Missing `raw_signal_id` values receive
deterministic generated ids. Unknown `signal_type`, `status_hint`, or `confidence` labels are
normalized to `unknown`.

Validation does not dedupe and does not call a model. Dedupe remains a separate step.

## Run Signal Dedupe

Signal dedupe reads an explicit raw signals JSONL file. This is not model-backed extraction; the tool
does not inspect chunks or infer claims by itself.

For the bundled synthetic fixture:

```bash
python3 local_harness/signal_dedupe.py \
  --raw-signals /tmp/zth_chatgpt_export_test/validated_signals/valid_raw_signals.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/signals
```

After running packet extraction with `--validate`, manually run dedupe on the validated output:

```bash
python3 local_harness/signal_dedupe.py \
  --raw-signals /tmp/zth_chatgpt_export_test/model_raw_signals/validated/valid_raw_signals.jsonl \
  --out-dir /tmp/zth_chatgpt_export_test/signals
```

The raw signal rows may include claim text, signal type, status hint, confidence, conversation id,
chunk id, chunk pass, turn range, source path, evidence note, and optional `topic_key`.

## Signal Dedupe Outputs

The dedupe tool writes:

```text
<out-dir>/deduped_signals.jsonl
<out-dir>/duplicate_links.jsonl
<out-dir>/conflict_candidates.jsonl
<out-dir>/dedupe_summary.json
```

`deduped_signals.jsonl` collapses exact normalized claims and very high-overlap near duplicates while
preserving supporting raw signal ids, source conversation ids, and source chunk ids.

`duplicate_links.jsonl` records which raw signals were linked to an earlier canonical raw signal and why.

`conflict_candidates.jsonl` records simple version/conflict candidates when signals share an explicit
`topic_key` but have conflicting status hints such as `historical` and `current`.

`dedupe_summary.json` records raw counts, deduped counts, duplicate-link counts, conflict-candidate
counts, and any skipped empty claims.

Conflict candidates require human review. The tool does not resolve them and does not decide which
claim is canonical.

## Build Review Bundle

Review bundle generation converts deduped signals, duplicate links, and conflict candidates into
human-readable review files and canonical-context candidate markdown files. It does not update any
canonical memory.

```bash
python3 local_harness/signal_review_bundle.py \
  --signals-dir /tmp/zth_chatgpt_export_test/signals \
  --out-dir /tmp/zth_chatgpt_export_test/review_bundle
```

The review bundle writes:

```text
<out-dir>/review_summary.md
<out-dir>/review_bundle.json
<out-dir>/canonical_candidates/
  current_state.md
  open_questions.md
  conflicts.md
```

Only candidate files with content are created. Signal types are mapped to candidate files such as
`current_state.md`, `decisions.md`, `open_questions.md`, `rules_and_preferences.md`,
`artifacts_and_files.md`, `commands_and_settings.md`, `next_actions.md`, `version_changes.md`, and
`conflicts.md`.

Unknown or unexpected signal types are placed in `current_state.md` under an `Unclassified` section
for review.

Each candidate includes the proposed claim, signal type, status, confidence, supporting raw signal ids,
source conversations, source chunks, review decision checkboxes, and reviewer notes space.

`conflicts.md` includes conflict ids, topic keys, classifications, claims, raw signal ids, status
hints, review decision checkboxes, and reviewer notes space.

`review_bundle.json` records machine-readable counts and relative candidate file paths. These files
are review material only; accepting any candidate into durable project context remains a separate
manual action outside this tool.

## Scope

This flow is still supervised source preparation only. It normalizes a ChatGPT export into reviewable
files, can plan reviewable chunks from those files, can generate extraction packets, can explicitly run
selected packets against a configured endpoint, can validate explicit raw signal JSONL, and can dedupe
validated raw signals into review scaffolding, and can generate review-only canonical candidates.

The normalized files, chunk files, extraction packets, validated raw signals, deduped signals,
duplicate links, conflict candidates, review bundles, and canonical candidate files are not canonical
memory and are not automatically accepted into any durable project context. They are source material
for human review.

Automatic signal extraction from chunks, live model batching, model-backed distillation, conflict
resolution, lifecycle promotion, and canonical memory promotion remain out of scope.
