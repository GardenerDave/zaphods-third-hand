# Live ZTH Smoke-Probe Preflight Run

Date: 2026-06-22

## Summary

Status: **completed**.

The supervised live chain reached an honest terminal result:

```text
already-running local OpenAI-compatible endpoint
→ ZTH smoke-probe producer
→ verified YAML
→ ZTH preflight capability manifest
→ operator plan
→ unwaived gated audition
→ durable report
```

All three producer probes passed. The imported capability manifest recorded
`preflight_status: pass`. The gate allowed one bounded audition case with
`basis: preflight_pass`; no waiver or override was used.

The audition completed and returned parseable JSON, but its deterministic
score retained `expected_contains_missing`. Completing this chain is workflow
evidence, not a model promotion, role assignment, or production-readiness
claim.

## Scope

This run exercised the newly merged ZTH-owned
`local_harness/llm_probe_smoke_probe.py` against the existing configured local
endpoint.

It tested:

- producer endpoint access and three fixed smoke probes;
- importer compatibility with the generated verified YAML;
- source-byte preservation and conservative capability-manifest status;
- operator-plan generation from the canonical manifest;
- an unwaived direct audition gate;
- one bounded endpoint-backed audition case.

No synthetic fixture was used.

## Inputs

- Endpoint configuration source: private `config.env` variables
  `ICM_ROUTER_BASE_URL` and `ICM_ROUTER_MODEL`
- Producer output:
  `.work/llm_probe_real_smoke_2026-06-22/`
- Verified YAML:
  `.work/llm_probe_real_smoke_2026-06-22/verified/zth-smoke-probe.yaml`
- Preflight manifest:
  `.work/llm_probe_preflight/live_zth_smoke_probe_2026-06-22/preflight_capability_manifest.json`
- Private model config:
  `.work/preflight_smoke/private_model_live_zth_smoke.json`
- Suite:
  `local_harness/auditions/suites/baseline_micro_v0.json`
- Operator plan:
  `.work/preflight_audition_plans/live_zth_smoke_probe_2026-06-22.md`
- Audition output:
  `.work/model_auditions/live_zth_smoke_probe_2026-06-22/`

All operational evidence remains ignored under `.work/`. The endpoint host,
credentials, and raw response text are not included in this report.

## Commands Run

Private configuration inspection with redaction:

```bash
rg -n 'ICM_ROUTER_BASE_URL|ICM_ROUTER_MODEL|ZTH_BASE_URL|ZTH_MODEL' \
  config.env config.example.env .env 2>/dev/null |
  sed -E 's#(https?://)[^/ ]+#\1<REDACTED_HOST>#g; s#=.*MODEL.*$#=<REDACTED_MODEL>#'
```

Producer dry run:

```bash
source config.env
python3 local_harness/llm_probe_smoke_probe.py \
  --base-url "$ICM_ROUTER_BASE_URL" \
  --model "$ICM_ROUTER_MODEL" \
  --out-dir .work/llm_probe_real_smoke_2026-06-22 \
  --timeout-seconds 30 \
  --max-tokens 120 \
  --dry-run
```

Endpoint availability:

```bash
source config.env
python3 local_harness/icm_call.py router \
  --base-url "$ICM_ROUTER_BASE_URL" \
  --timeout 10 \
  --list-models
```

Live producer:

```bash
source config.env
python3 local_harness/llm_probe_smoke_probe.py \
  --base-url "$ICM_ROUTER_BASE_URL" \
  --model "$ICM_ROUTER_MODEL" \
  --out-dir .work/llm_probe_real_smoke_2026-06-22 \
  --timeout-seconds 30 \
  --max-tokens 120 \
  --producer-run-id live-zth-smoke-probe-2026-06-22
```

Producer evidence inspection:

```bash
python3 -m json.tool \
  .work/llm_probe_real_smoke_2026-06-22/run_metadata.json

sed -n '1,240p' \
  .work/llm_probe_real_smoke_2026-06-22/verified/zth-smoke-probe.yaml

find .work/llm_probe_real_smoke_2026-06-22/raw \
  -maxdepth 1 -type f -printf '%f\n' |
  sort
```

Preflight import:

```bash
python3 local_harness/llm_probe_preflight_ingest.py \
  --probe-output .work/llm_probe_real_smoke_2026-06-22/verified/zth-smoke-probe.yaml \
  --input-format llm-probe-yaml \
  --out-dir .work/llm_probe_preflight/live_zth_smoke_probe_2026-06-22
```

Manifest inspection:

```bash
python3 -m json.tool \
  .work/llm_probe_preflight/live_zth_smoke_probe_2026-06-22/preflight_capability_manifest.json
```

Private model config preparation:

```bash
mkdir -p .work/preflight_smoke
source config.env
python3 -c 'import json, os, pathlib; p=pathlib.Path(".work/preflight_smoke/private_model_live_zth_smoke.json"); payload={"model_ref":"live_zth_smoke_probe_private","model_id":os.environ["ICM_ROUTER_MODEL"],"base_url":os.environ["ICM_ROUTER_BASE_URL"],"api_key_default":"not-needed-for-local","notes":"Private live ZTH smoke-probe config; do not commit."}; p.write_text(json.dumps(payload, indent=2, sort_keys=True)+"\n", encoding="utf-8")'
```

Operator planner:

```bash
python3 local_harness/preflight_audition_plan.py \
  --manifest .work/llm_probe_preflight/live_zth_smoke_probe_2026-06-22/preflight_capability_manifest.json \
  --model .work/preflight_smoke/private_model_live_zth_smoke.json \
  --suite local_harness/auditions/suites/baseline_micro_v0.json \
  --out-dir .work/model_auditions/live_zth_smoke_probe_2026-06-22 \
  --write-plan .work/preflight_audition_plans/live_zth_smoke_probe_2026-06-22.md \
  --print-commands
```

Bounded unwaived gated audition:

```bash
python3 local_harness/run_model_audition.py \
  --model .work/preflight_smoke/private_model_live_zth_smoke.json \
  --suite local_harness/auditions/suites/baseline_micro_v0.json \
  --preflight-manifest .work/llm_probe_preflight/live_zth_smoke_probe_2026-06-22/preflight_capability_manifest.json \
  --out-dir .work/model_auditions/live_zth_smoke_probe_2026-06-22 \
  --limit 1 \
  --max-tokens 200 \
  --timeout-seconds 180
```

No `--waive-preflight`, `--allow-intermittent-preflight`, or
`--allow-unknown-preflight` flag was used.

## Results

### Endpoint

- The existing endpoint's `/models` request succeeded.
- The configured model was available.
- No endpoint was started, stopped, exposed, mutated, or reconfigured.

### ZTH smoke producer

- Producer: `zth_smoke_probe`
- Producer contract: `zth.llm_probe_smoke_probe.v0.1`
- Run ID: `live-zth-smoke-probe-2026-06-22`
- Verified-YAML schema: `llm_probe.verified_yaml.v1`
- Required probes: 3
- Status counts: 3 pass
- HTTP status: 200 for all three probes
- Failures: none
- Diagnostics: none
- Average response time: 13,270 ms

Probe durations:

| Probe | Status | Duration |
|---|---|---:|
| `tool_call_basic` | pass | 14,392 ms |
| `json_schema_basic` | pass | 19,234 ms |
| `think_block_leak` | pass | 6,185 ms |

The producer wrote:

```text
verified/zth-smoke-probe.yaml
run_metadata.json
raw/tool_call_basic.json
raw/json_schema_basic.json
raw/think_block_leak.json
```

Raw response contents remain local and were not copied into this report.

### Preflight import

- Valid observations: 3
- Invalid observations: 0
- Status counts: 3 pass
- Models observed: 1
- Probes observed: 3
- Manifest status: `pass`
- Scope: `preflight_only`
- Promotion performed: `false`
- Requires human review: `true`

The producer YAML and importer-preserved `source/results.yaml` had matching
SHA-256 values.

### Operator planner and gate

- Planner mode: `single-suite`
- Source kind: `manifest`
- Plan file written only because `--write-plan` was explicit.
- The plan printed the existing direct-runner `--preflight-manifest` command.
- Gate decision: `allowed`
- Gate basis: `preflight_pass`
- Manifest status recorded by the audition: `pass`
- Waiver reason: empty
- Override flags: false

The planner did not execute the audition.

### Audition

- Suite: `baseline_micro_v0`
- Cases selected: 1 of 6
- Cases completed: 1
- API/runtime errors: 0
- Wall time: 28.698474 seconds
- Mechanical overall score: 0.775
- JSON parse metric: 1.0
- Runtime metric: 1.0
- Expected-contains metric: 0.5
- Failure mode: `expected_contains_missing`
- Scorer detail: `local_model_ops` was found; `confidence` was missing.

The output included:

```text
run_metadata.json
case_manifest.jsonl
capability_card.json
capability_card.md
rendered_prompts/base_route_001.md
raw_outputs/base_route_001.json
scores/base_route_001.json
```

This one-case score is not a ranking or general capability claim.

## Validation

- Focused producer and planner tests: 24 passed.
- Full `local_harness/tests` suite: 470 passed.
- Tracked Markdown link check: 66 files checked, no missing targets.
- Public-surface privacy check: passed.
- Boundary-language check: passed.
- `git diff --check`: passed.
- Producer, importer, planner, and audition-runner `--help` checks: passed.
- A report-specific grep found no private RFC1918 address, username, absolute
  home path, expanded endpoint URL, or endpoint-variable assignment containing
  a URL.

The repository-health privacy check excludes durable reports by design, so the
report-specific grep was required before commit. The requested broader grep
also returned established loopback examples, synthetic privacy-check fixtures,
and one pre-existing checked-in LAN model-config value outside this report
patch; none was introduced or modified by this run.

## Safety Boundaries

- No model was promoted.
- No model was ranked.
- No model was routed.
- No model was assigned or approved for a production role.
- No waiver or gate override was used.
- No upload occurred.
- No `.work` evidence was committed, cleaned, or deleted.
- No endpoint lifecycle action occurred.
- The preflight pass was used only as permission to attempt the bounded
  audition, not as a score or approval.
- Passing probes, manifests, auditions, and tests are evidence, not authority.
- This report does not establish production readiness.

## Follow-up

1. Preserve this producer→importer→planner→gate chain as the baseline smoke
   procedure for future contract changes.
2. Treat the audition's repeated `expected_contains_missing` result as separate
   scorer/model evidence; do not weaken the completed workflow result or turn
   it into a model assignment.
