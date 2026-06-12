# OpenAI-Compatible Endpoints

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md).

This repository expects an OpenAI-compatible endpoint for model-backed operations.

It does not install, host, or manage model servers.

## What "OpenAI-compatible endpoint" means here

For this toolkit, an endpoint is considered compatible when it accepts a chat-completions style request at a URL under your configured base, typically:

- `<BASE_URL>/chat/completions` when base includes `/v1`

Common request shape used by this repo:

- `model`
- `messages`
- `max_tokens`
- `temperature`
- `stream`

Optional capabilities used by some helper flows:

- `GET <BASE_URL>/models` for model listing/alias resolution

## What this repo assumes

- You provide a reachable endpoint URL.
- You provide a model name that your endpoint accepts.
- You provide auth through environment variables if required.

## What this repo does not do

- It does not start model servers.
- It does not download models.
- It does not configure GPU/CPU runtime settings.
- It does not manage provider accounts.

## Configuration pattern

Set environment variables in your private shell or `config.env`:

```bash
export ZTH_BASE_URL="http://localhost:8080/v1"
export ZTH_MODEL="your-model-id"
# Optional if endpoint requires bearer auth:
# export ZTH_API_KEY="your-secret-key"
```

Then run endpoint smoke test:

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

## Example: llama.cpp server

Example pattern (may vary by build and launch options):

```bash
./llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080
export ZTH_BASE_URL="http://127.0.0.1:8080/v1"
export ZTH_MODEL="your-model-name"
```

Notes:

- Keep `/v1` in base URL for OpenAI-style paths.
- Model id must match what your server exposes.
- If endpoint/model tends to return reasoning-heavy outputs, distiller runs can use:

```bash
export ZTH_DISTILLER_FINAL_ONLY="1"
```

## Example: LM Studio local server

You must start or enable the LM Studio Local Server first. This repo does not launch LM Studio or start its server.

Typical local pattern:

```bash
export ZTH_BASE_URL="http://127.0.0.1:1234/v1"
export ZTH_MODEL="your-loaded-model-name"
```

Notes:

- Confirm the loaded model id in LM Studio server UI/API.
- Run the same `icm_call.py` smoke test before distiller runs.

## Example: Generic OpenAI-compatible API

Typical remote pattern:

```bash
export ZTH_BASE_URL="https://api.example.com/v1"
export ZTH_MODEL="provider-model-name"
export ZTH_API_KEY="<PRIVATE_KEY>"
```

Notes:

- Ensure provider supports compatible chat-completions semantics.
- Keep secrets out of git-tracked files.

## Known-good local examples

These are practical local patterns used by many setups. Treat them as starting points, not guarantees for every install.

### llama.cpp-style local server

```bash
./llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080
export ZTH_BASE_URL="http://127.0.0.1:8080/v1"
export ZTH_MODEL="your-model-name"
```

### LM Studio local server

Enable Local Server in LM Studio first, then set:

```bash
export ZTH_BASE_URL="http://127.0.0.1:1234/v1"
export ZTH_MODEL="your-loaded-model-name"
```


## Troubleshooting

- HTTP 404 on completion path:
  - Base URL or endpoint path mismatch. Re-check provider docs and include `/v1` where required.
- HTTP 401/403:
  - Missing/invalid API key or auth policy mismatch.
- Empty/low-value content on smoke call:
  - Try `--final-only` and smaller requests first.
- Distiller fails but smoke call works:
  - Lower distiller token budgets and verify timeout settings in `config.example.env`.
