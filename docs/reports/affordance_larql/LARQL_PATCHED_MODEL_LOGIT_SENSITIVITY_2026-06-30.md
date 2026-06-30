# LARQL Patched Model Logit Sensitivity

This report adds a diagnostic stage after unchanged patched-model behavioral reauditions.

What this stage does:

- reads a reviewed patched-model materialization record;
- reuses the same bounded LARQL probe set as the patched-model reaudition runner;
- runs forward-pass logits comparison on the base model and the patched model;
- compares the final prompt-position logits without relying on generation;
- records per-probe and aggregate logit-difference evidence in a reviewable packet.

What this stage does not do:

- it does not train;
- it does not perform another weight edit;
- it does not write another delta artifact;
- it does not materialize another patched model;
- it does not promote or deploy anything;
- it does not mutate registries or authorize install.

This stage is evidence, not authority. It is intended to answer whether the patched copy changes model distributions at all, even when greedy decoded outputs stay unchanged.
