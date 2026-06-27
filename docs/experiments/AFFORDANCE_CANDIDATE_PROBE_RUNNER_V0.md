# Affordance Candidate Probe Runner v0

Status: experimental scaffold

Affordance Candidate Probe Runner v0 turns one
`affordance_patch_candidate.json` into a reviewable prompt packet and probe-run
report. It is the next step after LARQL Affordance Patch Probe v0 and
Affordance Dogfood Report v0.

The runner is not a LARQL integration, training tool, adapter manager, or
promotion gate. It does not run LARQL, train LoRA, mutate weights, create model
artifacts, or decide that a candidate is ready to use.

## Purpose

The runner helps an operator test whether a model respects a host-specific
affordance candidate before anything is considered for a LARQL patch, LoRA
curriculum, or stacked repair path.

## Inputs

- One `affordance_patch_candidate.json`.

The candidate must include host ids, source failure id, repair lane, host
affordance context, source digests, probe prompts, regression prompts, and
draft review/promotion status.

## Outputs

The runner writes exactly:

```text
probe_prompt_packet.json
probe_run.jsonl
probe_report.json
probe_report.md
```

The prompt packet records the prompts and host-specific context. The JSONL file
records either pending model calls or explicit endpoint responses. The reports
summarize the run and preserve the boundary that the artifact grants no
promotion authority.

## Dry-run mode

Dry-run is the default. It makes no model calls and writes each probe or
regression prompt as a `pending_model_call` event.

```bash
python3 local_harness/affordance_candidate_probe_runner.py \
  --candidate .work/larql_affordance_probe/navigator_cuda_real_v3/affordance_patch_candidate.json \
  --out .work/affordance_candidate_probe_runs/navigator_cuda_probe_v0 \
  --dry-run
```

Dry-run reports use:

```text
run_mode: dry_run
overall_verdict: not_evaluated
promotion_verdict: hold_pending_probe
```

## Explicit endpoint mode

Endpoint mode is available only when the operator explicitly provides endpoint
arguments and `--allow-model-calls`.

```bash
python3 local_harness/affordance_candidate_probe_runner.py \
  --candidate .work/larql_affordance_probe/navigator_cuda_real_v3/affordance_patch_candidate.json \
  --out .work/affordance_candidate_probe_runs/navigator_cuda_probe_v0 \
  --endpoint-url http://127.0.0.1:1234/v1 \
  --model-id qwen3-1.7b-gpu-40k \
  --allow-model-calls
```

Endpoint mode calls an OpenAI-compatible `/chat/completions` endpoint with a
fixed supervised system prompt and conservative generation settings. It does
not retry, stream, start endpoints, or manage endpoint lifecycle.

## Deterministic v0 scoring limits

The v0 scorer uses simple text checks only. It checks whether responses mention
candidate constraints or the host profile, avoid known-bad paths in probe
responses, mention known-good paths or reinspection when appropriate, and avoid
cross-host generalization in regression responses.

This is useful screening evidence. It is not semantic proof that a model
understood the candidate or that the candidate is safe to apply.

## Why promotion is held

Even when all endpoint probes pass, `promotion_verdict` remains
`hold_pending_probe_review`. A probe report is evidence for supervised review.
It is not an applied LARQL patch, not LoRA training data, and not promotion
evidence by itself.

## Fit after Dogfood Report v0

Use the dogfood report to check candidate shape and provenance. Use this runner
to package and optionally execute the candidate’s probe prompts. Any later
LARQL, LoRA, or stacked repair decision remains a separate reviewed workflow.

## Non-goals

- No LARQL execution.
- No LoRA training.
- No adapter, checkpoint, model, or vindex artifacts.
- No model-weight mutation.
- No automatic promotion or lifecycle movement.
- No background jobs.
- No dependency additions.
