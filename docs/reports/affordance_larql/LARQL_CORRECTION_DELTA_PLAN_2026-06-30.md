# LARQL Correction Delta Plan

Date: 2026-06-30

This report records the first packet-only transition from a mechanically proven
direct layer-edit pipeline to behavior-derived direct delta planning.

Baseline from `_006`:

- reaudition completed successfully;
- raw strict JSON remained `0/4` for base and patched outputs;
- normalized strict JSON reached `4/4` for base and patched outputs;
- diagnostic extraction reached `4/4` for base and patched outputs;
- raw outputs were equal across all probes;
- normalized outputs were equal across all probes;
- patched normalized improvement count remained `0`;
- patched normalized regression count remained `0`.

Interpretation:

- the direct tensor delta pipeline is mechanically clean enough for the next
  planning step;
- the patched copy exists and can be compared;
- this deterministic direct delta did not prove a behavioral correction.

Selected first candidate method:

- `activation_difference_direction`

Why this method is first:

- it is the smallest next behavior-derived experiment after the `_006`
  baseline;
- it can compare failure-shaped and correction-shaped prompts at one selected
  layer or module;
- it can remain packet-bounded before any new delta artifact is written.

What this planning packet does:

- defines candidate methods for behavior-derived direct delta computation;
- defines activation contrast probe pairs for file-scope and regression checks;
- selects a bounded first method for supervised review;
- records risks and required follow-up gates.

What this planning packet does not do:

- it does not implement LoRA;
- it does not use PEFT;
- it does not train;
- it does not modify model weights;
- it does not write safetensors deltas;
- it does not materialize another patched model;
- it does not promote a model;
- it does not authorize install, deployment, registry mutation, or automatic
  failure-to-curriculum capture.

Authority boundary:

- planning is authorized only as a packet-only review scaffold;
- model inference remains a separate authorization gate;
- weight editing remains a separate authorization gate;
- patched model materialization remains a separate authorization gate;
- reaudition remains a separate authorization gate.

Next supervised step:

`implement_authorized_activation_capture_probe`
