# LARQL Direct Layer Edit Reaudition

Date: 2026-06-29

This report records the first supervised reaudition driver for an effective
LARQL-core direct layer-edit smoke.

What this stage does:

- validates an effective patched-copy smoke artifact;
- prepares a deterministic probe set with strict JSON-oriented prompts;
- writes a rule-based scoring plan and scoring report path;
- writes a reaudition packet and boundary file;
- optionally runs local base-vs-patched inference only when separately
  authorized and the local model stack is available.

What this stage does not do:

- it does not implement LoRA;
- it does not use PEFT;
- it does not train;
- it does not mutate the base model;
- it does not mutate the patched model;
- it does not promote the patched model;
- it does not authorize install, deployment, registry mutation, dataset
  release, or automatic failure-to-curriculum capture.

Probe coverage:

- original LARQL behavior replay;
- adjacent-file anti-overfit;
- all-files-authorized control;
- unrelated task regression.

Important scoring boundary:

- scoring is evidence, not authority;
- a pass does not promote the patched model;
- a failure does not automatically become curriculum.

Inference cleanup:

- decode only newly generated tokens, not the input prompt;
- use greedy deterministic generation without invalid temperature warnings;
- use chat-template prompting when the tokenizer supports it;
- keep reaudition scoring as evidence only;
- strict JSON remains the real pass condition;
- diagnostic extraction is evidence only.

Next supervised step:

`supervised_reaudition_review`
