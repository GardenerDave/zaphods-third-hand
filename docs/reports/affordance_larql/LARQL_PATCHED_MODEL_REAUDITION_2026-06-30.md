# LARQL Patched Model Reaudition

This report adds the first separately authorized inference comparison for the LARQL patched-copy path.

What this stage does:

- reads a reviewed patched-model materialization record;
- validates that the source path is a patched copy and not a base overwrite;
- runs the same bounded LARQL probes against the base model and the patched model;
- normalizes Qwen think tags consistently with earlier reaudition scoring;
- compares base vs patched outputs and scores movement toward the bounded correction target;
- writes a reaudition record, raw output files, a comparison file, and a review packet.

What this stage does not do:

- it does not train;
- it does not perform another weight edit;
- it does not write another delta artifact;
- it does not materialize another patched model;
- it does not promote or deploy anything;
- it does not mutate registries or authorize install.

The result of this stage is evidence, not authority. A patched model that looks better in this comparison is still subject to supervised review before any further decision.
