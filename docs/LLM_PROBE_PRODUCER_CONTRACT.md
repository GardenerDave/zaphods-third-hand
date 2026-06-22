# ZTH Smoke-Probe Producer Contract

`local_harness/llm_probe_smoke_probe.py` is a ZTH-owned producer for the
verified-YAML preflight input shape.

It exists to unblock supervised local endpoint smoke runs. It is not an
external upstream LLM-probe implementation, does not claim compatibility with
an unknown upstream CLI, and is not a general model benchmark.

## Purpose

The producer fills one bounded gap:

```text
operator-supplied OpenAI-compatible endpoint
→ tiny ZTH smoke probes
→ verified YAML plus raw local evidence
→ existing ZTH preflight importer
```

The tool calls only the endpoint supplied by the operator. It never starts,
stops, downloads, or configures a model server.

## Identity and Versions

Generated evidence records:

```text
producer: zth_smoke_probe
producer_contract_version: zth.llm_probe_smoke_probe.v0.1
schema_version: llm_probe.verified_yaml.v1
```

`llm_probe.verified_yaml.v1` identifies the verified-YAML shape accepted by
the existing ZTH importer. It does not imply that this producer is the
official implementation of any external project.

The producer identity remains explicit in the YAML, raw records, and run
metadata. The importer preserves the YAML bytes so those fields remain
auditable even when they are not copied into the aggregate capability
manifest.

## Output Layout

One successful producer invocation writes only under `--out-dir`:

```text
<out-dir>/
  verified/
    zth-smoke-probe.yaml
  raw/
    tool_call_basic.json
    json_schema_basic.json
    think_block_leak.json
  run_metadata.json
```

The output path must not already exist. The producer refuses to overwrite an
existing file or directory.

- `verified/zth-smoke-probe.yaml` contains one model and one result for each
  required probe in the importer-compatible verified-YAML shape.
- `raw/*.json` preserves the prompt, visible response, full API response,
  mechanical evaluation, duration, HTTP status, and errors for local review.
- `run_metadata.json` records producer identity, model ID, redacted endpoint
  metadata, parameters, probe IDs, status counts, output paths, and safety
  boundaries.

Raw responses may contain sensitive or model-generated material. Keep
operational output under ignored `.work/` and summarize only reviewed,
sanitized evidence in durable reports.

## Fixed Probe Set

Version `v0.1` intentionally runs three small probes.

### `tool_call_basic`

Requests a compact JSON object with:

```json
{
  "route": "smoke",
  "confidence": 0.9,
  "next_action": "review"
}
```

The check requires a parseable JSON object and the three required keys. This
probe permits a JSON object embedded in extra text but records that condition
as a diagnostic.

The name follows the existing verified-YAML convention. This probe does not
exercise an actual tool invocation or grant tool authority.

### `json_schema_basic`

Requests strict JSON with:

```json
{
  "status": "ok",
  "checks": [],
  "next_action": "review"
}
```

The visible response must be a JSON object with all required keys. Markdown
fences or surrounding prose fail strict parsing.

### `think_block_leak`

Requests the exact visible response:

```text
READY
```

The check fails if the response differs or contains visible markers such as
`<think>`, `reasoning_content`, or labeled analysis/reasoning text.

This checks visible leakage only. It does not inspect or make claims about
unavailable internal model state.

## Status Model

Producer raw evidence uses:

- `pass`: the endpoint responded and the mechanical probe checks passed;
- `fail`: the endpoint responded but the mechanical checks failed;
- `error`: transport, HTTP, timeout, or response-shape processing failed.

The verified YAML records `passed: true` only for producer `pass` results.
Both `fail` and `error` become `passed: false`. The existing importer therefore
maps either condition to a conservative failed preflight observation.

The capability manifest can be `pass` only when all three required probes
pass. A pass means the model may enter a separately authorized gated audition;
it does not mean the model is capable, promoted, assigned, or production-ready.

## Endpoint and Credential Handling

The request target is:

```text
<base-url>/chat/completions
```

The producer accepts a base URL that already ends in `/v1`. It sends:

```json
{
  "model": "<model>",
  "messages": [{"role": "user", "content": "<probe prompt>"}],
  "temperature": 0,
  "max_tokens": 120,
  "stream": false
}
```

An `Authorization: Bearer` header is added only when `--api-key` is non-empty
and is not the local sentinel `not-needed-for-local`.

The endpoint URL is not written to `run_metadata.json`, plan output, or normal
CLI summaries. Those surfaces use `<redacted>` and retain only the
`/chat/completions` path. Raw API responses are stored locally, but the
producer does not print response text by default.

Committed examples use environment-variable references. Do not commit private
endpoint URLs, internal hostnames, API keys, or raw local responses.

## Plan Without Calling the Endpoint

Use `--dry-run` or its alias `--print-plan`:

```bash
source config.env
python3 local_harness/llm_probe_smoke_probe.py \
  --base-url "$ICM_ROUTER_BASE_URL" \
  --model "$ICM_ROUTER_MODEL" \
  --out-dir .work/llm_probe_real_smoke_2026-06-21 \
  --timeout-seconds 30 \
  --max-tokens 120 \
  --dry-run
```

Plan mode validates arguments and output-path availability, prints a redacted
JSON plan, performs no network calls, and writes no files.

## Producer → Importer → Planner

Run the producer against an already-running endpoint:

```bash
source config.env
python3 local_harness/llm_probe_smoke_probe.py \
  --base-url "$ICM_ROUTER_BASE_URL" \
  --model "$ICM_ROUTER_MODEL" \
  --out-dir .work/llm_probe_real_smoke_2026-06-21 \
  --timeout-seconds 30 \
  --max-tokens 120
```

Inspect the local evidence before importing:

```bash
python3 -m json.tool \
  .work/llm_probe_real_smoke_2026-06-21/run_metadata.json
sed -n '1,220p' \
  .work/llm_probe_real_smoke_2026-06-21/verified/zth-smoke-probe.yaml
```

Import the verified YAML:

```bash
python3 local_harness/llm_probe_preflight_ingest.py \
  --probe-output .work/llm_probe_real_smoke_2026-06-21/verified/zth-smoke-probe.yaml \
  --input-format llm-probe-yaml \
  --out-dir .work/llm_probe_preflight/real_llm_probe_smoke_2026-06-21
```

Inspect the capability manifest, then create the existing operator plan:

```bash
python3 -m json.tool \
  .work/llm_probe_preflight/real_llm_probe_smoke_2026-06-21/preflight_capability_manifest.json

python3 local_harness/preflight_audition_plan.py \
  --manifest .work/llm_probe_preflight/real_llm_probe_smoke_2026-06-21/preflight_capability_manifest.json \
  --model .work/preflight_smoke/private_model_real_llm_probe.json \
  --suite local_harness/auditions/suites/baseline_micro_v0.json \
  --out-dir .work/model_auditions/real_llm_probe_preflight_smoke_2026-06-21 \
  --write-plan .work/preflight_audition_plans/real_llm_probe_preflight_smoke_2026-06-21.md \
  --print-commands
```

The private model config remains an operator-managed ignored file. The
producer does not create audition configs or run the planner automatically.

## Preflight and Waiver Boundaries

- No preflight manifest: an audition remains ungated under the runner's
  existing optional-gate behavior.
- Manifest `pass`: the gated audition may proceed after operator review.
- Manifest `fail`: the gated audition blocks by default.
- Manifest `fail` plus explicit `--waive-preflight`: the runner may proceed
  and records the waiver reason. The waiver is evidence, not authority.

Neither the producer nor a pass/waiver promotes, approves, ranks, routes, or
assigns a model.

## Safety Boundaries

The producer does not:

- start, stop, download, or configure endpoints;
- upload source material or telemetry;
- delete or clean evidence;
- run model auditions;
- create capability cards or rankings;
- promote, approve, route, or assign models;
- move lifecycle state;
- establish production readiness.

All output remains reviewable local evidence. Passing probes and tests are
evidence, not authority.
