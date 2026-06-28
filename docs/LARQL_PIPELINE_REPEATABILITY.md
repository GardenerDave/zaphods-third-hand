# LARQL Pipeline Repeatability

This document describes the repeatable LARQL pipeline that was proven by the
CUDA/RX580 closeout.

The important distinction is simple:

- LARQL prompt/context injection was proven.
- LARQL curriculum/dataset artifact creation was proven.
- model-internal learning or training was not performed.
- LoRA is a blocked downstream action, not part of this pipeline run.

The result is evidence of a repeatable, supervised, guided-capability workflow.
It is not evidence that the model internally learned the behavior.

## Repeatability ladder

1. failure evidence
2. candidate/rule
3. runtime install
4. runtime consultation
5. model context packet
6. model response probe
7. model response review
8. pass record
9. training/curriculum candidate packet
10. candidate review
11. explicit opt-in boundary
12. local candidate artifact
13. artifact review
14. explicit opt-in boundary
15. local dataset artifact
16. dataset artifact review
17. stop at training-run approval boundary

The ladder is repeatable because each stage produces reviewable evidence and
stops at a held approval boundary unless an explicit next step is approved.

## What this proves

- LARQL can turn a concrete failure into a runtime rule.
- LARQL can inject governed local context into a model call.
- A small model can follow the injected rule under supervised review.
- The same trace can be transformed into a reviewed local curriculum/dataset
  artifact without training.

## What this does not prove

- It does not prove the model learned the behavior internally.
- It does not prove LoRA training effectiveness.
- It does not authorize automatic future capture.
- It does not promote the candidate.

## Final stop condition

`hold_for_explicit_larql_training_run_approval`

## Boundary

- No durable memory unless explicitly approved.
- No automatic failure-to-curriculum capture.
- No LoRA training unless explicitly approved.
- No model weight mutation unless explicitly approved.
- No candidate promotion unless explicitly approved.

## Notes

The reviewed CUDA/RX580 pipeline showed that the system can:

- capture the failure as supervised evidence;
- express the correction as a runtime rule;
- consult that rule in a bounded local context;
- score the model response without treating the injected rule as automatic
  authority; and
- write a reviewed local dataset artifact while still stopping before any
  training-run approval.

That is the repeatable pipeline this project currently treats as proven.
