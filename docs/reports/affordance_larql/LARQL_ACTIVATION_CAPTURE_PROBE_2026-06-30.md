# LARQL Activation Capture Probe

Date: 2026-06-30

This report records the first authorized LARQL activation capture probe packet
for correction-derived delta research.

Why activation capture follows the correction delta plan:

- the direct layer-edit pipeline is mechanically proven;
- the patched model copy and reaudition harness are proven;
- the deterministic direct delta did not create a behavioral change on the
  current probe set;
- the next bounded step is to capture failure-versus-correction activation
  evidence at the selected module and layer.

What this stage captures:

- a packet describing the selected capture method;
- the probe ids and prompt-pair count;
- the intended capture point for the selected module family;
- the review boundary and the follow-up authorization gate;
- when separately authorized outside this Codex task, compact activation
  summary statistics rather than full tensors.

What this stage is not:

- not a weight edit;
- not a safetensors delta writer;
- not a patched model materialization step;
- not training;
- not LoRA;
- not PEFT;
- not model promotion.

Authority boundaries:

- packet-only mode requires explicit planning authorization;
- model inference requires a separate explicit authorization flag;
- weight mutation remains unauthorized;
- delta artifact writing remains unauthorized;
- patched model materialization remains unauthorized;
- promotion, install, deployment, registry mutation, and automatic
  failure-to-curriculum capture remain unauthorized.

Expected next review step:

`supervised_activation_capture_review`
