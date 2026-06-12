# First Success Guide

Start here: [`README.md`](../README.md).

This guide is the shortest path to a successful first run for a new technical user.

## Safety Model First

This repository is supervised and file-based by design:

- Human-supervised operation only.
- No unattended execution.
- No automatic lifecycle movement.
- No automatic canonicalization.
- Generated outputs stay reviewable until a human accepts follow-up changes.

## Prerequisites

Required:

- Python 3
- Bash
- Git

Optional:

- Any OpenAI-compatible chat-completions endpoint if you want model-backed runs

For the model-free smoke test below, no model endpoint is required.

## 1) Clone and enter the repo

```bash
git clone https://github.com/GardenerDave/zaphods-third-hand.git
cd zaphods-third-hand
```

## 2) Model-free metrics smoke test

Run the built-in metrics report on bundled sample data:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir examples --limit 3
```

Expected result:

- A readable summary report prints to terminal.
- No endpoint configuration is needed.

This confirms your local Python environment can run the distiller reporting tool.

## 3) Optional endpoint smoke test

Only do this if you have a running OpenAI-compatible endpoint.

Create a private config file, edit it first, then load it:

```bash
cp config.example.env config.env
# Edit config.env first: set real ZTH_BASE_URL and ZTH_MODEL for your endpoint.
set -a
source config.env
set +a
```

`ZTH_BASE_URL` and `ZTH_MODEL` must match your actual running endpoint and accepted model id.

If you source placeholder values unchanged, endpoint smoke tests will fail.

Run a tiny connectivity call:

```bash
python3 local_harness/icm_call.py handoff \
  --api openai-chat \
  --base-url "$ZTH_BASE_URL" \
  --model "$ZTH_MODEL" \
  --max-tokens 16 \
  --timeout 60 \
  --final-only \
  "Reply with exactly: ok"
```

If this times out on your endpoint, retry once without `--final-only`.

Expected result:

- Response contains `ok`.

If this fails, fix endpoint URL/model/auth before running the context distiller.

### Optional: First full model-backed run

Use this short path after you have edited and sourced `config.env`:

```bash
set -a
source config.env
set +a
python3 local_harness/icm_call.py handoff \
  --api openai-chat \
  --base-url "$ZTH_BASE_URL" \
  --model "$ZTH_MODEL" \
  --max-tokens 16 \
  --timeout 60 \
  --final-only \
  "Reply with exactly: ok"
mkdir -p sources
printf 'Decision: keep role runs supervised. Next action: write a small job packet.\n' > sources/toy_source.txt
export ZTH_DISTILLER_SESSION_MAX_TOKENS="320"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="240"
export ZTH_DISTILLER_TIMEOUT="240"
export ZTH_DISTILLER_RUN_PROFILE="smoke"
export ZTH_DISTILLER_RUN_PURPOSE="connectivity"
./scripts/run_context_distiller_head.sh toy-001 sources/toy_source.txt toy-source --compact
ls -1 outputs/sessions outputs/review_patches outputs/run_records
```

Success here means files are generated under `outputs/` for human review. Generated outputs are not automatically accepted.

## 4) Context Distiller toy input

Create a tiny source file:

```bash
mkdir -p sources
printf 'Decision: keep role runs supervised. Next action: write a small job packet.\n' > sources/toy_source.txt
```

Run a small compact distiller pass:

```bash
export ZTH_DISTILLER_SESSION_MAX_TOKENS="320"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="240"
export ZTH_DISTILLER_TIMEOUT="240"
export ZTH_DISTILLER_RUN_PROFILE="smoke"
export ZTH_DISTILLER_RUN_PURPOSE="connectivity"
./scripts/run_context_distiller_head.sh toy-001 sources/toy_source.txt toy-source --compact
```

## 5) Expected output files

After a successful toy run, inspect:

- `outputs/sessions/`
- `outputs/review_patches/`
- `outputs/run_records/`

Typical run record files include:

- `TASK.md`
- `INPUT.md`
- `MODEL_REQUEST.md`
- `session_prompt.md`
- `patch_prompt.md`
- `session_metadata.json`
- `patch_metadata.json`
- `METRICS.json`

## 6) What success looks like

Minimum success criteria:

- Model-free metrics smoke test runs cleanly.
- Optional endpoint smoke test returns `ok`.
- Toy distiller run produces session summary, review patch, and run record artifacts.
- You can review generated outputs in plain files before accepting any downstream action.

## 7) Common failure modes

- Placeholder endpoint values are still present in environment.
  - Fix `ZTH_BASE_URL` and `ZTH_MODEL`.
- Endpoint rejects auth.
  - Set `ZTH_API_KEY` in private env if needed by your endpoint.
- Distiller timeout on slow backend.
  - Lower token budgets or raise `ZTH_DISTILLER_TIMEOUT`.
- Source file path not found.
  - Run from repo root or use an absolute source path.
- Output exists but quality is weak.
  - Do not auto-accept. Keep outputs as review material and iterate under supervision.

## Next Step

If this first run worked, continue with:

- [`README.md`](../README.md) for primary workflows.
- [`config.example.env`](../config.example.env) for environment variable reference.
- [`docs/OPENAI_COMPATIBLE_ENDPOINTS.md`](OPENAI_COMPATIBLE_ENDPOINTS.md) for endpoint patterns.
- [`docs/CONTEXT_DISTILLER_WORKFLOW.md`](CONTEXT_DISTILLER_WORKFLOW.md) for profile tuning and advisor usage.
- [`docs/MANAGEMENT_TEAM_OVERVIEW.md`](MANAGEMENT_TEAM_OVERVIEW.md) when you are ready for supervised role workflow.
