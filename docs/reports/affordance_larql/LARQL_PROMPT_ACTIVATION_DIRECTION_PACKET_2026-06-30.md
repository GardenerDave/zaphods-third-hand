# LARQL Prompt Activation Direction Packet

This report adds the first packet-only direction candidate stage on top of proven prompt-forward activation capture.

What this adds:

- gated compact prompt vector output from the activation capture probe;
- a packet-only direction analyzer that compares correction-minus-failure vectors;
- file-scope coherence checks separated from an unrelated regression guard.

What the compact vectors mean:

- they are evidence artifacts derived from prompt-side activations;
- they are not a model modification;
- they do not write a weight delta;
- they do not authorize promotion, install, deployment, or registry mutation.

What the direction packet evaluates:

- whether the three file-scope probes point in a coherent direction;
- whether the unrelated regression guard is too aligned with that direction;
- whether a later supervised review should treat the direction as reviewable, unclear, or rejected.

What remains out of scope:

- no LoRA;
- no PEFT;
- no training;
- no safetensors delta artifact;
- no patched model materialization;
- no model promotion;
- no automatic failure-to-curriculum capture.

The code keeps `delta_artifact_recommended` false. Any later direct delta experiment still requires a separate supervised review step.
