# CUDA / RX580 LARQL Pipeline Closeout

Date: 2026-06-28

## Summary

This report closes out the CUDA/RX580 LARQL pipeline experiment.

The pipeline took a concrete host-affordance failure, converted it into a runtime rule, injected that rule as bounded local context, and verified that a small model could follow the guided capability under supervised review. The same trace was also captured as a reviewed local curriculum artifact without starting training.

This is a LARQL pipeline closeout, not a LoRA training report.

## Failure addressed

The failure under study was:

- `cuda_on_navigator_desktop.real`
- bad CUDA/NVIDIA advice on an RX580 / `no_cuda` host

The intended correction was to stop recommending NVIDIA CUDA on a host that cannot use it and instead scope the advice to the current host/profile/GPU/endpoint/digest evidence.

## Identifiers

- Candidate id: `larql_affordance_candidate_48efff9852ea`
- Rule id: `navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0`
- Candidate digest: `c79aae337b91fe8da8f67d61508b4140e8c61e7db9cc607307c53e72566ec520`

## Evidence sources

Reviewed evidence paths:

- `.work/affordance_larql_training_dataset_artifact_reviews/navigator_cuda_larql_rule_v0_skeleton_repair_rescore/larql_training_dataset_artifact_review.json`
- `.work/affordance_larql_training_datasets/navigator_cuda_larql_rule_v0_skeleton_repair_rescore/larql_training_dataset_write_record.json`
- `.work/affordance_larql_training_datasets/navigator_cuda_larql_rule_v0_skeleton_repair_rescore/larql_training_dataset.jsonl`
- `.work/affordance_larql_training_candidates/navigator_cuda_larql_rule_v0_skeleton_repair_rescore/larql_training_candidate_artifact.json`
- `.work/affordance_larql_model_response_reviews/navigator_cuda_larql_rule_v0_skeleton_repair_rescore/larql_model_response_review.json`
- `.work/affordance_larql_model_response_probes/navigator_cuda_larql_rule_v0_skeleton_repair_rescore/larql_model_response_probe.json`

## What the successful response showed

The supervised model response:

- refused NVIDIA CUDA on the RX580 / `no_cuda` host;
- recommended the `LM Studio OpenAI-compatible endpoint`;
- scoped the recommendation to the current host/profile/GPU/endpoint/digest evidence;
- required reverify if host, GPU, driver, profile, endpoint, or digest evidence changes.

That is the behavior the pipeline was trying to capture.

## Dataset artifact reviewed

One local dataset row was written and reviewed.

- Format: `larql_supervised_sft_candidate.v0`
- Dataset path: `.work/affordance_larql_training_datasets/navigator_cuda_larql_rule_v0_skeleton_repair_rescore/larql_training_dataset.jsonl`

This confirms the trace can be transformed into a reviewed local curriculum artifact without starting training.

## Boundary table

| Item | Value |
|---|---:|
| training_dataset_written | true |
| durable_memory_written | false |
| lora_training_started | false |
| model_weights_mutated | false |
| candidate_promoted | false |
| runtime_rule_modified | false |

## Current stop condition

`hold_for_explicit_larql_training_run_approval`

## What this proves

- LARQL can turn a concrete failure into a runtime rule.
- LARQL can inject governed local context into a model call.
- A small model can follow the injected rule under supervised review.
- The same trace can be transformed into a reviewed local curriculum/dataset artifact without training.

## What this does not prove

- It does not prove the model learned the behavior internally.
- It does not prove LoRA training effectiveness.
- It does not authorize automatic future capture.
- It does not promote the candidate.

## Recommended next step

- Repeat the same pipeline on additional failures before any training run.
- Keep failure-to-curriculum capture strictly opt-in.

## Boundary

No durable memory was written.
No model weights were mutated.
No LoRA training was started.
No candidate was promoted.
No runtime rule was modified.
This closeout records evidence only; it does not authorize the next training step.
