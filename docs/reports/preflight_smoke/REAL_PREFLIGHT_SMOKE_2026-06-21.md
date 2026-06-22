# Real Preflight Smoke Run

Date: 2026-06-21 (local operator date)

## Summary

Status: **partially completed**.

The supervised preflight → manifest → planner → gated audition path reached an
already-running local OpenAI-compatible endpoint and completed one audition
case. The gate also failed closed before the endpoint call when presented with
an unwaived `preflight_status: fail`.

The remaining limitation is source provenance: no real local LLM-probe
`verified/<provider>.yaml` output was available. The run used the checked-in,
upstream-shaped synthetic YAML fixture. This report therefore does not mark
the roadmap's real-output smoke item complete.

## Scope

This was a supervised smoke run of:

```text
upstream-shaped LLM-probe fixture
→ preflight importer
→ preflight capability manifest
→ operator planner
→ fail-closed gate check
→ explicit reviewed waiver
→ one-case endpoint-backed audition
```

The planner printed commands; it did not execute them. The audition command
was selected and run separately after source, manifest, model configuration,
suite, endpoint availability, and planner output were inspected.

## Inputs

- LLM-probe source evidence:
  `examples/llm_probe_preflight_fixture/verified-provider.yaml`
- Preflight manifest:
  `.work/llm_probe_preflight/real_smoke_2026-06-21/preflight_capability_manifest.json`
- Private model config:
  `.work/preflight_smoke/private_model.json`
- Suite:
  `local_harness/auditions/suites/baseline_micro_v0.json`
- Audition output:
  `.work/model_auditions/real_preflight_smoke_2026-06-21/`
- Planner output:
  `.work/preflight_audition_plans/real_preflight_smoke_2026-06-21.md`
- Endpoint:
  an already-running local OpenAI-compatible endpoint selected from private
  configuration; the host is intentionally omitted.

The private model config, plan, manifest, and raw audition evidence remain
ignored local files. They were not copied into this report.

## Commands Run

Endpoint discovery:

```bash
source config.env
python3 local_harness/icm_call.py router \
  --base-url "$ICM_ROUTER_BASE_URL" \
  --timeout 10 \
  --list-models
```

Private model config preparation:

```bash
mkdir -p .work/preflight_smoke
source config.env
python3 -c 'import json, os, pathlib; p=pathlib.Path(".work/preflight_smoke/private_model.json"); payload={"model_ref":"real_preflight_smoke_private","model_id":os.environ["ICM_ROUTER_MODEL"],"base_url":os.environ["ICM_ROUTER_BASE_URL"],"api_key_default":"not-needed-for-local","notes":"Private local smoke config; do not commit."}; p.write_text(json.dumps(payload, indent=2, sort_keys=True)+"\n", encoding="utf-8")'
```

The command read the endpoint and model from private environment variables and
did not print either value.

Preflight import:

```bash
python3 local_harness/llm_probe_preflight_ingest.py \
  --probe-output examples/llm_probe_preflight_fixture/verified-provider.yaml \
  --input-format llm-probe-yaml \
  --out-dir .work/llm_probe_preflight/real_smoke_2026-06-21
```

Manifest inspection:

```bash
python3 -m json.tool \
  .work/llm_probe_preflight/real_smoke_2026-06-21/preflight_capability_manifest.json
```

Planner:

```bash
python3 local_harness/preflight_audition_plan.py \
  --manifest .work/llm_probe_preflight/real_smoke_2026-06-21/preflight_capability_manifest.json \
  --model .work/preflight_smoke/private_model.json \
  --suite local_harness/auditions/suites/baseline_micro_v0.json \
  --out-dir .work/model_auditions/real_preflight_smoke_2026-06-21 \
  --write-plan .work/preflight_audition_plans/real_preflight_smoke_2026-06-21.md \
  --print-commands
```

Unmodified gated audition command, expected to fail closed:

```bash
python3 local_harness/run_model_audition.py \
  --model .work/preflight_smoke/private_model.json \
  --suite local_harness/auditions/suites/baseline_micro_v0.json \
  --preflight-manifest .work/llm_probe_preflight/real_smoke_2026-06-21/preflight_capability_manifest.json \
  --out-dir .work/model_auditions/real_preflight_smoke_2026-06-21
```

One-case endpoint-backed audition with an explicit recorded waiver:

```bash
python3 local_harness/run_model_audition.py \
  --model .work/preflight_smoke/private_model.json \
  --suite local_harness/auditions/suites/baseline_micro_v0.json \
  --preflight-manifest .work/llm_probe_preflight/real_smoke_2026-06-21/preflight_capability_manifest.json \
  --out-dir .work/model_auditions/real_preflight_smoke_2026-06-21 \
  --limit 1 \
  --max-tokens 200 \
  --timeout-seconds 180 \
  --waive-preflight "Synthetic upstream-shaped fixture contains an intentional failed test; waiver only exercises one supervised endpoint-backed audition case and grants no promotion or role authority."
```

Validation:

```bash
python3 -m pytest local_harness/tests/test_preflight_audition_plan.py
python3 local_harness/repo_health_check.py
python3 local_harness/repo_health_check.py --all
git diff --check
```

## Planner Output Summary

The planner:

- validated the canonical capability-manifest contract;
- inspected the model and suite paths;
- printed the direct runner's existing `--preflight-manifest` command;
- identified the configured audition output directory;
- printed focused and repository-health validation commands;
- stated that it does not run models, start endpoints, clean evidence, or
  promote models;
- wrote the Markdown plan only because `--write-plan` was explicit.

The unmodified gated audition command was selected first. It stopped with:

```text
preflight gate blocked audition: status=fail
```

It created no audition output directory. The second command added a
human-readable waiver and `--limit 1` to test the endpoint-backed path while
keeping the run minimal.

## Results

### Preflight import

- Input format: `llm_probe_verified_yaml`
- Input schema: `llm_probe.verified_yaml.v1`
- Valid observations: 7
- Invalid observations: 0
- Status counts: 6 pass, 1 fail
- Conservative manifest status: `fail`
- Scope: `preflight_only`
- Promotion performed: `false`
- Requires human review: `true`
- Source preservation: the original fixture and preserved
  `source/results.yaml` had matching SHA-256 values.

### Planner and gate

- Planner completed and wrote the explicitly requested local plan.
- The initial gate attempt blocked before creating output or calling the
  endpoint.
- The endpoint-backed attempt recorded `basis: waiver`,
  `preflight_status: fail`, and the full waiver reason in
  `run_metadata.json`.

### Audition

- Endpoint model listing succeeded before the audition.
- Selected model: `Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M`
- Suite: `baseline_micro_v0`
- Cases selected: 1 of 6
- Cases completed: 1
- API/runtime errors: 0
- Wall time: 28.960473 seconds
- Mechanical overall score: 0.775
- JSON parse metric: 1.0
- Runtime metric: 1.0
- Expected-contains metric: 0.5
- Failure mode: `expected_contains_missing`
- Observed scorer detail: `local_model_ops` was found and `confidence` was
  missing.

This one-case result is not a general model capability claim. The synthetic
preflight fixture did not describe the endpoint model and was waived only to
exercise the supervised integration path.

### Output files produced

Preflight evidence:

```text
import_metadata.json
probe_manifest.jsonl
invalid_records.jsonl
preflight_capability_manifest.json
preflight_summary.json
preflight_summary.md
source/results.yaml
```

Audition evidence:

```text
run_metadata.json
case_manifest.jsonl
capability_card.json
capability_card.md
rendered_prompts/base_route_001.md
raw_outputs/base_route_001.json
scores/base_route_001.json
```

Raw response text and the private endpoint URL remain only in ignored local
evidence.

### Validation

- Focused planner tests: 11 passed.
- Full `local_harness/tests` suite: 457 passed.
- Tracked Markdown link check: 63 files checked, no missing targets.
- Public-surface privacy check: passed.
- Boundary-language check: passed.
- `git diff --check`: passed.
- Planner, importer, and audition-runner `--help` checks: passed.
- A separate grep of the new report, report index, and roadmap found no private
  RFC1918 address, username, absolute home path, or expanded endpoint value.

The repository-health privacy check excludes durable reports by design, so the
separate report-specific grep was necessary before committing this summary.

## Safety Boundaries

- No model was promoted.
- No model was assigned a production role.
- No ranking or routing authority was granted.
- No upload was performed.
- No `.work` cleanup or deletion was performed.
- No endpoint was started, stopped, or reconfigured.
- The preflight status was not treated as a score.
- The waiver was recorded evidence, not approval.
- Passing checks are evidence, not authority.

## Failures or Blockers

- No genuine local LLM-probe output was available. The checked-in
  upstream-shaped synthetic fixture was used instead.
- The fixture intentionally produced `preflight_status: fail`.
- The initial audition attempt correctly failed closed.
- A deliberate waiver was required to exercise the endpoint-backed portion.
- The single model response parsed as JSON but missed one mechanically required
  term.

## Follow-up

1. Run LLM-probe against the same local endpoint and retain its real
   `verified/<provider>.yaml` output.
2. Repeat this exact planner and one-case gated audition path without a waiver
   when the real capability manifest permits it, or preserve the truthful
   blocked result if it does not.
