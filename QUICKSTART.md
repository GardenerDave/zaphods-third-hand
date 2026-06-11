# Quickstart

## License Note

Before using this toolkit, confirm your use is noncommercial or obtain written permission for commercial use. See `LICENSE.md` and `COMMERCIAL_USE.md`.

## Prerequisites

You need:

- Bash.
- Python 3.
- A git working tree or another folder where you can review file changes.
- An OpenAI-compatible chat-completions endpoint.
- A source transcript or log that is safe for your local environment.

The model endpoint can be local or remote. Zaphod's Third Hand does not include a model server.

## Step 0: Copy Or Clone The Toolkit

Put `zaphods-third-hand/` inside the repository or workspace where you want to keep generated outputs and job evidence.

```bash
cd <REPO_ROOT>/zaphods-third-hand
```

## Step 1: Configure Local Or Remote Model Endpoint

Use an OpenAI-compatible chat-completions endpoint.

```bash
cd <REPO_ROOT>/zaphods-third-hand
cp config.example.env config.env
# Edit config.env with your endpoint and model, then load it.
set -a
source config.env
set +a
```

You can also export values directly:

```bash
export ZTH_BASE_URL="http://<LLAMA_CPP_BASE_URL>/v1"
export ZTH_MODEL="<MODEL_NAME>"
```

If your endpoint requires authorization, set your own key in your private shell or `config.env`:

```bash
export ZTH_API_KEY="<YOUR_PRIVATE_KEY>"
```

## Step 2: Add A Source Transcript Or Log

Place a source file somewhere in your private working tree. Use a stable source ID and a short title.

```text
SOURCE_ID=<SOURCE_ID>
SOURCE_FILE=<SOURCE_FILE>
SHORT_TITLE=<SHORT_TITLE>
```

Do not commit private transcripts unless you have reviewed and approved them for sharing.

For a tiny first test, create a short toy source in a private scratch folder:

```bash
mkdir -p sources
printf 'Decision: keep role runs supervised. Next action: write a small job packet.\n' > sources/toy_source.txt
```

## Step 3: Run The Context Distiller In Compact And Chunked Mode

```bash
./scripts/run_context_distiller_head.sh toy-001 sources/toy_source.txt toy-source --compact --chunked
```

Compact mode asks the model for a tight durable summary. Chunked mode splits long sources into chunks, summarizes each chunk, and then synthesizes a final session summary.

For a slow model server or a smoke test, lower the output budgets before running:

```bash
export ZTH_DISTILLER_CHUNK_MAX_TOKENS="600"
export ZTH_DISTILLER_SESSION_MAX_TOKENS="900"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="700"
export ZTH_DISTILLER_TIMEOUT="600"
```

Use higher values again for real source distillation when you need more complete summaries.

## Step 4: Review The Generated Session And Patch

Inspect:

```text
outputs/sessions/
outputs/review_patches/
outputs/run_records/
```

Generated review patches are not canonical. Review them against the source and session summary before accepting anything.

Generated outputs can include source paths, endpoint names, and model names from your environment. Keep `outputs/` private unless you have reviewed it for sharing.

## Step 5: Create Or Activate A Job Packet

Use `templates/job_packet_template.md` to create a narrow packet. The packet should name:

- Route.
- Objective.
- Files allowed to edit.
- Files off limits.
- Verification commands.
- Stop conditions.
- Human approval requirement.

Move a packet to active only after human review.

Example manual lifecycle:

```bash
mkdir -p job_queue active_jobs completed_jobs
cp templates/job_packet_template.md job_queue/example-job.md
# Edit job_queue/example-job.md by hand.
mv job_queue/example-job.md active_jobs/example-job.md
# After execution and review:
mv active_jobs/example-job.md completed_jobs/example-job.md
```

Each move should be paired with a status update inside the packet.

## Step 6: Use Role Prompts Only Under Human Supervision

Use prompts from `prompts/` only through an active packet. Keep role outputs advisory unless the human accepts them through lifecycle review.

## Step 7: Record Acceptance Or Rework Decisions

Use `workflows/REVIEW_PATCH_ACCEPTANCE_WORKFLOW.md` and `workflows/SUPERVISED_ROLE_RUN_EVIDENCE_NOTE_FORMAT.md` to record decisions.

Any recommended next action requires separate human approval and a separate lifecycle packet.

## Portable Script Limitation

The distiller script is package-relative and writes to `outputs/`, but it still expects an OpenAI-compatible endpoint. If `ZTH_BASE_URL` and `ZTH_MODEL` are placeholders, the script exits before making model calls.

## Common Failure Modes

- Placeholder endpoint or model: load `config.env` or export `ZTH_BASE_URL` and `ZTH_MODEL`.
- Source file not found: run from `zaphods-third-hand/` or pass an absolute path to a private source file.
- Endpoint rejects the request: confirm the URL, model name, and `ZTH_API_KEY` if your endpoint requires one.
- Slow backend: test with a tiny source, compact mode, and lower `ZTH_DISTILLER_*_MAX_TOKENS` values before running long chunked jobs.
- Generated patch looks wrong: do not accept it; record rework or create a narrow follow-up packet.
- Role output expands scope: stop and return to the active packet boundaries.
