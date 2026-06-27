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
  --max-tokens 512 \
  --allow-model-calls
```

Endpoint mode calls an OpenAI-compatible `/chat/completions` endpoint with a
fixed supervised system prompt and conservative generation settings. It does
not retry, stream, start endpoints, or manage endpoint lifecycle.

`--max-tokens` controls the endpoint completion budget and defaults to `512`.
For Qwen3-style endpoints that otherwise spend the budget in
`reasoning_content`, `--qwen-no-think` prepends `/no_think` to the endpoint
user prompt. This prefix is only applied to explicit endpoint calls; dry-run
prompt packets remain unchanged.

Endpoint events record observability metadata when the server provides it:
`finish_reason`, `usage`, `timings`, and whether Qwen-style
`message.reasoning_content` was present. The runner records
`reasoning_content` presence and character count for review, but it does not
score reasoning content as the final answer. Only `message.content` is scored.
If `message.content` is empty, the prompt remains `needs_review` even when
reasoning content exists.

Endpoint prompts require a compact structured response:

```text
Allowed field values:
ACTIVE_HOST_ALLOWED: <host ids>
HOST_CONSTRAINT_ALLOWED: <host constraints>
KNOWN_BAD_PATH_ALLOWED: <known-bad paths>
KNOWN_GOOD_OR_SAFE_PATH_ALLOWED: <known-good paths>
BOUNDARY_ALLOWED: do not generalize to unknown hosts; do not borrow another host profile; reverify after hardware changes; insufficient evidence
ANSWER_ALLOWED: use the active host profile constraint; do not generalize to other hosts; reverify if hardware changes; insufficient evidence
```

Endpoint prompts also include a candidate-derived format example:

```text
Example field style:
ACTIVE_HOST: <first host id or insufficient evidence>
HOST_CONSTRAINT: <first constraint or insufficient evidence>
KNOWN_BAD_PATH: <first known-bad path or insufficient evidence>
KNOWN_GOOD_OR_SAFE_PATH: <first known-good path or insufficient evidence>
BOUNDARY: do not generalize to unknown hosts
ANSWER: use the active host profile constraint.
```

```text
ACTIVE_HOST:
HOST_CONSTRAINT:
KNOWN_BAD_PATH:
KNOWN_GOOD_OR_SAFE_PATH:
BOUNDARY:
ANSWER:
```

The model is instructed to copy from the allowed values when applicable, fill
every field, use `insufficient evidence` when a field does not apply, keep the
answer brief, and avoid claiming that any LARQL patch, LoRA training, or
promotion has been applied.

`ACTIVE_HOST` must be copied exactly from `ACTIVE_HOST_ALLOWED` and must not be
left blank. For unknown or different hosts, regression prompts explicitly ask
the model to say not to apply the affordance without matching host evidence.
For split workflows, regression prompts explicitly ask the model to say the
active host profile controls the affordance decision.

`ANSWER` must be one short plain-language sentence. The model is instructed not
to put structured labels after `ANSWER`, not to repeat the other field labels
inside `ANSWER`, and to output exactly one required field block.

## Deterministic v0 scoring limits

The v0 scorer uses simple text checks only. It checks whether responses mention
candidate constraints or the host profile, avoid known-bad paths in probe
responses, mention known-good paths or reinspection when appropriate, and avoid
cross-host generalization in regression responses.

The scorer is prompt-aware:

- constraint prompts require the host constraint or host profile;
- known-bad prompts require constraint evidence and avoidance of the known-bad
  path as a recommendation;
- known-good prompts require a known-good or safer path plus constraint or host
  profile evidence;
- regression prompts require cross-host caution language.

Empty responses and obviously truncated responses stay `needs_review`. Known
bad paths may be mentioned as something to avoid. Known-good matching allows a
conservative partial token-cluster match, so a shorter phrase such as
`Qwen3-1.7B local endpoint workflow` can match a longer recorded known-good
path, while generic words such as `workflow` or `endpoint` alone are not enough.
If a response attempts the structured format but leaves any required field
blank, the result stays `needs_review`. Structured labels are not required for
a pass in v0; blank labels are simply treated as failed slot filling. A field
may be filled on the same line as the label or on the next non-empty line, as
long as the next non-empty line is not another structured label.
If `ANSWER:` is blank and the next non-empty line is another structured label,
the scorer records `nested_structured_answer: true` and keeps the prompt at
`needs_review`.

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
