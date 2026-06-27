# LARQL Affordance Patch Probe v0

Status: experimental scaffold only

This document sketches a model-free ZTH-side scaffold for evaluating whether
machine-specific “doesn’t work on this host” failures can be classified into
repair lanes before any LARQL, LoRA, or training work is attempted.

This is not a production LARQL integration. It does not install LARQL, vendor
LARQL, build vindexes, mutate model weights, train adapters, call models, call
external services, or promote any generated artifact.

## Central framing

LoRA teaches the model to ask which host/workflow context applies. LARQL may
help the model remember durable affordance associations. Host profiles remain
authority. ZTH decides whether the stack survived evidence.

## Problem targeted

Small models can produce plausible advice that fails on a specific machine:
CUDA commands on a non-CUDA GPU, AVX2 binaries on an older server, or paths that
exist on one host but not another. These failures are not only reasoning
failures. They are often affordance-map failures: the model does not have a
current, host-specific map of what this machine can safely do.

## Source of truth

Host profile files are the source of truth for mutable machine facts. They
record host-specific hardware, operating system, known-good paths, known-bad
paths, preferred roles, constraints, and staleness policy. If a host profile is
missing, stale, or ambiguous, the safe answer is to inspect and update the host
profile rather than encode the fact into a model.

## Repair lanes

The first-pass classifier assigns failures to one of these draft lanes:

- `host_profile_only`: the evidence suggests the host profile is missing,
  stale, or needs clarification.
- `larql_candidate`: the evidence suggests a durable host-affordance
  association may be a reversible LARQL-style patch candidate.
- `lora_candidate`: the evidence suggests procedural behavior should be taught
  or evaluated through LoRA/SFT-style training.
- `larql_plus_lora_candidate`: both host-specific affordance memory and
  procedural behavior may be involved.
- `review_only`: insufficient evidence, unknown host, or ambiguous failure.

LARQL is only a candidate affordance-memory patch layer. LoRA/SFT remains the
behavioral/procedural training lane. ZTH probes, validators, and operator
review remain the promotion authority.

## Evaluation variants

A later supervised evaluation may compare four variants:

1. Base model only.
2. Base + LoRA.
3. Base + LARQL.
4. Base + LARQL + LoRA.

The v0 scaffold does not run those variants. It prepares draft candidates,
probe prompts, regression prompts, and reports so an operator can review the
shape first.

## Sample run

```bash
python3 local_harness/larql_affordance_probe.py \
  --host-profile examples/host_profiles/navigator_desktop.example.json \
  --failure-note examples/failure_notes/cuda_on_rx580_failure.example.md \
  --out .work/larql_affordance_probe/sample_navigator_cuda
```

Then inspect the generated files:

```bash
find .work/larql_affordance_probe/sample_navigator_cuda -maxdepth 1 -type f -print | sort
```

Expected files:

```text
affordance_patch_candidate.json
classification_report.md
probe_plan.md
```

## Acceptance criteria for this scaffold

- Input host profile and failure note are plain files.
- Output is deterministic and human-reviewable.
- Output is marked draft and `needs_probe`.
- Output never marks a patch, adapter, or host fact as accepted.
- Output includes probe and regression prompts.
- Missing input files fail clearly.
- Path traversal in the output directory is refused.
- No model, network, LARQL, adapter, or training dependency is introduced.

## Stop conditions

Stop and fail before generating output if:

- the host profile is missing required keys;
- the failure note is missing;
- the output directory contains `..` path traversal;
- a generated candidate would need to claim a fact not present in the host
  profile or failure note.

Ambiguous or insufficient evidence is not a mechanical stop condition. In that
case the scaffold should emit a `review_only` candidate so the uncertainty is
preserved as reviewable evidence without pretending a LARQL or LoRA lane has
been proven.

## Known risks

- Stale host facts.
- Overgeneralizing one host’s constraint to all hosts.
- Confusing two hosts.
- Patch collateral damage.
- Mistaking a LARQL patch for proof.
- Baking mutable host facts into weights.

## Explicit non-goals

- No model download.
- No vindex build.
- No FFN mutation.
- No adapter training.
- No model calls.
- No network calls.
- No automated promotion.
- No production LARQL integration.

## Future work

Add a separate ZTH structure-affordance probe for repo/workflow ontology,
artifact placement, lifecycle authority, and promotion boundaries. This is
intentionally out of scope for LARQL Affordance Patch Probe v0, which is
limited to machine/host affordances.
