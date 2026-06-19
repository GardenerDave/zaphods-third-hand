# Small-Model Audition Harness

This directory contains optional exploratory tooling for testing small models
against Zaphod's Third Hand prompts. Core ZTH workflows normally connect to an
existing OpenAI-compatible endpoint; this harness additionally can:

- download configured candidate GGUFs;
- start and stop temporary local llama.cpp servers in tmux;
- call an already-running local OpenAI-compatible endpoint;
- call an already-running OpenAI-compatible endpoint on another LAN host.

The harness preserves raw responses and scores observable behavior. It does not
provide production service management, hardening, monitoring, or availability.
It does not promote models, assign production roles, or change ZTH routing
configuration. Server lifecycle actions and audition results remain evidence
for human review.

## What It Measures

The included scorers distinguish several failure modes that look similar at a
glance:

- empty assistant `content` with output or token use in `reasoning_content`;
- invalid JSON versus recoverable markdown-fenced JSON;
- valid JSON with the wrong route;
- schema or type drift, such as `"confidence": "high"` instead of a number;
- high-confidence `unknown` on known workflow-specific terms;
- exact bullet-count and required-section failures;
- missing required concepts;
- possible invented file paths;
- finish reason and llama.cpp timing fields when the endpoint reports them.

Scoring is mechanical evidence, not a promotion decision.

## Files

```text
local_harness/model_auditions/
├── models.example.json       model downloads, local starts, and endpoint URLs
├── prompts.example.json      prompt suites and expected output contracts
├── download_models.py        repo-and-glob GGUF downloader
├── start_models.py           local llama.cpp tmux launcher
├── stop_models.py            local tmux shutdown helper
├── run_audition.py           OpenAI-compatible request runner
├── score_results.py          score and report generator
└── scoring.py                deterministic scoring rules
```

## 1. Prepare Hugging Face Tooling Safely

The runtime harness uses the Python standard library. Only model downloading
needs `huggingface_hub`.

Ubuntu and Debian may reject global package installation under PEP 668. Use a
dedicated virtual environment. Do not use `--break-system-packages`.

```bash
sudo apt update
sudo apt install -y python3-venv python3-full

python3 -m venv ~/ai/tools/hf-venv
~/ai/tools/hf-venv/bin/python -m pip install -U pip
~/ai/tools/hf-venv/bin/python -m pip install -U "huggingface_hub[cli]" hf_xet
```

The installed command may be named `hf`, but the downloader uses the Python
library directly and should be run with the venv interpreter.

## 2. Configure Models and Endpoints

Each entry under `models` supports either:

- `host` plus `port`; `host` defaults to `127.0.0.1`;
- a full `base_url`, normally ending in `/v1`.

Existing local configs that only specify `path` and `port` remain valid. The
request URL defaults to `http://127.0.0.1:<port>/v1/chat/completions`.

### Local llama.cpp model

The primary local example binds llama.cpp to loopback only:

```json
{
  "models": {
    "local_qwen": {
      "label": "Local Qwen",
      "path": "~/ai/models/qwen/model-Q4_K_M.gguf",
      "host": "127.0.0.1",
      "port": 8112,
      "server_host": "127.0.0.1",
      "threads": 6,
      "ctx": 4096,
      "session": "small_qwen"
    }
  }
}
```

`host` controls where the audition client connects. `server_host` controls the
bind address used when this harness starts llama.cpp. Set `server_host`
explicitly to `127.0.0.1` for loopback-only evaluation. Public or reusable
configs should not omit this field.

### Intentional LAN exposure

Use `0.0.0.0` only when the temporary llama.cpp endpoint is intentionally
meant to accept traffic through network interfaces:

```json
{
  "models": {
    "lan_exposed_qwen": {
      "path": "~/ai/models/qwen/model-Q4_K_M.gguf",
      "host": "127.0.0.1",
      "port": 8112,
      "server_host": "0.0.0.0",
      "session": "small_qwen_lan"
    }
  }
}
```

The implementation retains `0.0.0.0` as a backward-compatible fallback when
`server_host` is omitted. Omitting the field therefore does not produce a
loopback-only server.

`0.0.0.0` binds the server on all available interfaces; it does not restrict
access to the local machine. Before using it, review firewall rules, interface
exposure, host access controls, and the llama.cpp server's authentication
capabilities. The audition harness does not add authentication headers.

Use only networks and endpoints you are authorized to expose or access. Keep
the client-facing LAN address in private configuration using `<LAN_HOST>` in
committed examples.

### Explicit local endpoint

```json
{
  "models": {
    "local_qwen": {
      "path": "~/ai/models/qwen/model-Q4_K_M.gguf",
      "base_url": "http://127.0.0.1:8112/v1",
      "port": 8112
    }
  }
}
```

The `port` is still used to start the local server. `base_url` is used by the
audition client.

### Already-running LAN endpoint

```json
{
  "models": {
    "lan_qwen": {
      "label": "Qwen on LAN worker",
      "base_url": "http://<LAN_HOST>:8112/v1",
      "api_model": "Qwen/Qwen3-4B-GGUF",
      "expected_role": "router_candidate"
    }
  }
}
```

An endpoint-only entry does not need `path`, `repo`, `filename_pattern`,
`session`, or local server settings. `start_models.py` and `stop_models.py`
skip it because no local tmux lifecycle is managed.

`api_model` controls the OpenAI request's `model` value. It defaults to
`"local"` for llama.cpp compatibility; set it when a LAN endpoint requires its
served model ID.

The equivalent host-and-port form is:

```json
{
  "models": {
    "lan_qwen": {
      "host": "<LAN_HOST>",
      "port": 8112
    }
  }
}
```

Only use LAN endpoints you are authorized to access. The harness does not add
authentication headers.
Replace `<LAN_HOST>` in a private config before use; do not commit a real
internal address.

## 3. Inspect Configuration Without Network Calls

Validate both config files and print resolved endpoints:

```bash
python3 local_harness/model_auditions/run_audition.py \
  --models local_harness/model_auditions/models.example.json \
  --prompts local_harness/model_auditions/prompts.example.json \
  --dry-run
```

The output shows each model's resolved `/v1` base URL, chat-completions URL,
local/remote lifecycle mode, model path, tmux session, and selected prompts.
Dry-run does not create a run directory or contact model servers.

Use `--only-models` and `--only-prompts` to inspect a subset.

## 4. Download Candidate GGUFs

Model repository filenames drift over time. `download_models.py` lists files in
the configured Hugging Face repository and selects the first deterministic
match for `filename_pattern`; it does not depend on a hand-typed current
filename.

```bash
~/ai/tools/hf-venv/bin/python \
  local_harness/model_auditions/download_models.py \
  --models local_harness/model_auditions/models.example.json
```

Download selected models:

```bash
~/ai/tools/hf-venv/bin/python \
  local_harness/model_auditions/download_models.py \
  --models local_harness/model_auditions/models.example.json \
  --only qwen3_1_7b,qwen3_4b
```

Preview repository and glob resolution without downloading:

```bash
~/ai/tools/hf-venv/bin/python \
  local_harness/model_auditions/download_models.py \
  --models local_harness/model_auditions/models.example.json \
  --only qwen3_4b \
  --dry-run
```

This preview still contacts Hugging Face to list repository files.
Endpoint-only models without a local `path` are skipped.

## 5. Start Local llama.cpp Endpoints

This optional step starts temporary evaluation servers. Skip it when using an
already-running local or LAN endpoint.

The default llama.cpp server path is:

```text
~/ai/src/llama.cpp/build/bin/llama-server
```

Preview commands:

```bash
python3 local_harness/model_auditions/start_models.py \
  --models local_harness/model_auditions/models.example.json \
  --only qwen3_4b \
  --dry-run
```

Start selected local models in tmux:

```bash
python3 local_harness/model_auditions/start_models.py \
  --models local_harness/model_auditions/models.example.json \
  --only qwen3_4b
```

Override the llama.cpp binary if needed:

```bash
python3 local_harness/model_auditions/start_models.py \
  --models local_harness/model_auditions/models.example.json \
  --only qwen3_4b \
  --llama-server /opt/llama.cpp/bin/llama-server
```

Inspect sessions and logs:

```bash
tmux list-sessions
tmux attach -t small_qwen4
```

Detach from tmux with `Ctrl-b`, then `d`.

For already-running local or LAN endpoints, skip this entire step.

Starting a server establishes only a test endpoint for evidence gathering. It
does not establish production readiness, service ownership, model approval, or
promotion.

## 6. Run an Audition

Run all configured models and prompts:

```bash
python3 local_harness/model_auditions/run_audition.py \
  --models local_harness/model_auditions/models.example.json \
  --prompts local_harness/model_auditions/prompts.example.json \
  --out .work/model_auditions/run_$(date -u +%Y%m%dT%H%M%SZ)
```

Run a selected endpoint and prompt subset:

```bash
python3 local_harness/model_auditions/run_audition.py \
  --models /path/to/models.json \
  --prompts local_harness/model_auditions/prompts.example.json \
  --only-models lan_qwen \
  --only-prompts router_docs_update,router_model_audition \
  --timeout 180 \
  --out .work/model_auditions/lan_qwen_$(date -u +%Y%m%dT%H%M%SZ)
```

Thinking-capable Qwen-style models may put output in `reasoning_content` and
leave `content` empty. The included prompts use `/no_think` to request normal
assistant output. Keep it unless a test intentionally measures thinking mode.

The runner writes each response immediately, so partial evidence survives if a
later endpoint is slow or unavailable.

## 7. Score Results

```bash
python3 local_harness/model_auditions/score_results.py \
  --run .work/model_auditions/<run_id>
```

The scorer reads `responses.jsonl` and writes:

```text
scores.jsonl   per-response score envelopes and diagnostics
rollup.json    model-level aggregate metrics
summary.md     human-readable aggregate and prompt-level table
```

Review raw responses before relying on aggregate scores:

```bash
python3 -m json.tool .work/model_auditions/<run_id>/run_metadata.json
sed -n '1,20p' .work/model_auditions/<run_id>/responses.jsonl
sed -n '1,240p' .work/model_auditions/<run_id>/summary.md
```

## Output Locations

Normal runs live under `.work/model_auditions/` unless `--out` specifies
another directory:

```text
<run-dir>/
├── run_metadata.json   resolved model, endpoint, and prompt configuration
├── responses.jsonl    raw requests and complete endpoint response JSON
├── scores.jsonl       deterministic per-response checks
├── rollup.json        aggregate metrics
└── summary.md         human-readable review report
```

`.work/` is disposable local evidence. Preserve selected reviewed findings
under `docs/reports/model_auditions/`, while keeping raw private or
environment-specific responses out of committed reports unless explicitly
sanitized.

## Common Failure Modes

- **Empty `content`, populated `reasoning_content`:** add or retain
  `/no_think`; also inspect finish reason and token budget.
- **Markdown-fenced JSON:** recoverable JSON may still be semantically useful,
  but it failed raw controller discipline.
- **Valid JSON, wrong route:** schema compliance does not imply routing
  correctness. Review `route_match`.
- **Wrong JSON types:** values such as `"confidence": "high"` fail the numeric
  schema even if the route is correct.
- **High-confidence `unknown`:** on text containing known ZTH terms such as
  model, audition, JSON, scoring, or route, this is an escalation signal rather
  than a safe fallback.
- **Exact-shape drift:** labeled lines are not bullets; polished prose may
  still fail a required section contract.
- **Endpoint errors:** verify the resolved URL with `--dry-run`, confirm the
  server exposes `/v1/chat/completions`, and check LAN routing/firewall rules.

## Stop Local tmux Sessions

Preview shutdown:

```bash
python3 local_harness/model_auditions/stop_models.py \
  --models local_harness/model_auditions/models.example.json \
  --dry-run
```

Stop selected managed sessions:

```bash
python3 local_harness/model_auditions/stop_models.py \
  --models local_harness/model_auditions/models.example.json \
  --only qwen3_4b
```

Stop all locally managed sessions in the config:

```bash
python3 local_harness/model_auditions/stop_models.py \
  --models local_harness/model_auditions/models.example.json
```

Endpoint-only LAN models are skipped. The harness never stops remote services.
It stops only the configured local tmux sessions used for exploratory
evaluation.

## Audition Is Not Promotion

Keep these decisions separate:

```text
Audition evidence:
- What happened?
- Which probes passed?
- Which failure modes appeared?
- What raw output did the endpoint return?

Human promotion decision:
- Should the model receive a ZTH role?
- What guardrails and fallbacks are required?
- What separate configuration change is approved?
```

Do not auto-promote a model from `rollup.json` or `summary.md`. A fast or
high-scoring result can still hide semantically wrong routes, brittle output
contracts, or workflow-specific blind spots.
