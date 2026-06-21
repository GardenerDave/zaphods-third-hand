# First Success Guide

Start here: [`README.md`](../README.md).

This is the smallest practical check that ZTH can run in your environment.

## Safety Boundary

- Supervised operation only; humans and agents may perform scoped steps.
- No unattended execution or automatic lifecycle movement.
- Generated output remains evidence until authorized review. An acting agent
  cannot approve its own output.
- A successful smoke test does not promote a model or establish production
  readiness.

## Prerequisites

- Bash
- Python 3
- Git, if you are cloning the repository

The first check is model-free and uses only the Python standard library.

## 1. Enter the Repository

If needed:

```bash
git clone https://github.com/GardenerDave/zaphods-third-hand.git
cd zaphods-third-hand
```

Otherwise, run the following commands from the existing repository root.

## 2. Run the Model-Free Smoke Test

```bash
python3 local_harness/report_distiller_metrics.py \
  --runs-dir examples \
  --limit 3
```

Expected result:

- A readable metrics summary prints to the terminal.
- No model endpoint or third-party Python package is required.

This confirms that the repository and local Python environment can run a basic
ZTH reporting path.

## 3. Optionally Verify an Existing Endpoint

Skip this section if you only need the model-free check.

Core model-backed ZTH workflows expect an already-running OpenAI-compatible
endpoint. Copy the private configuration template, replace its placeholder
endpoint and model values, then load it:

```bash
cp config.example.env config.env
# Edit config.env before loading it.
set -a
source config.env
set +a
```

If you are unsure which model ID the endpoint exposes, try:

```bash
python3 local_harness/icm_call.py handoff \
  --base-url "$ZTH_BASE_URL" \
  --list-models
```

Use a returned model ID for `ZTH_MODEL`. Not every compatible provider exposes
model listing; if this check fails, use the model ID configured by your
provider or server.

Run one small connectivity request:

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

Expected result: a short response containing `ok`.

If the request times out, retry once without `--final-only`. If it still fails,
verify the endpoint URL, model ID, and authentication before continuing.

## What First Success Means

You have completed first success when:

- the model-free metrics command succeeds; and
- if you chose the optional endpoint step, the endpoint returns `ok`.

This validates basic local execution and, optionally, connectivity. It does not
validate output quality, production readiness, model suitability, or lifecycle
authorization.

## Continue

- [`QUICKSTART.md`](../QUICKSTART.md) — normal Context Distiller and review
  workflow.
- [`OPENAI_COMPATIBLE_ENDPOINTS.md`](OPENAI_COMPATIBLE_ENDPOINTS.md) —
  endpoint setup and security boundaries.
- [`CONTEXT_DISTILLER_WORKFLOW.md`](CONTEXT_DISTILLER_WORKFLOW.md) — detailed
  profiles, metrics, advisor, and calibration options.
- [`docs/README.md`](README.md) — full documentation map.
