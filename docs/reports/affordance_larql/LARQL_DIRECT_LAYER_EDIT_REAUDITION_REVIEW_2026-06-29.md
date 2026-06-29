# LARQL Direct Layer Edit Reaudition Review

Date: 2026-06-29

This review records the first completed base-vs-patched reaudition as evidence
only.

What the first comparison established:

- the first base-vs-patched reaudition executed successfully;
- the direct edit was behaviorally visible;
- this is not a behavioral success claim;
- the first observed comparison did not prove the desired LARQL correction.

Why cleanup was required:

- the earlier output hygiene was weak because prompt text was decoded together
  with generated text;
- file-scope prompts were too loose and allowed rambling instead of bounded JSON
  decisions;
- greedy decoding still passed `temperature=0.0`, which produced an avoidable
  transformers warning.

What the driver now does:

- decodes only newly generated tokens;
- requests stricter JSON in the file-scope and regression probes;
- writes a rule-based scoring report after inference;
- keeps scoring as evidence only.

Boundaries preserved:

- a pass does not promote the patched model;
- a failure does not automatically become curriculum;
- no LoRA, PEFT, training, base overwrite, install, deployment, registry
  mutation, or automatic failure-to-curriculum capture is authorized.
