# LARQL Patched Model Materializer

This report adds the first separately authorized patched-copy stage in the LARQL direct-layer pipeline.

What this stage does:

- reads a reviewed rank-1 delta artifact record;
- verifies the artifact hash before use;
- validates target resolution and shape before copying;
- copies the base model directory into a patched model directory;
- applies the reviewed delta to exactly one target tensor in the copied model only;
- writes a materialization record and review packet.

What this stage does not do:

- it does not overwrite the base model;
- it does not run inference or reaudition;
- it does not promote or deploy anything;
- it does not mutate registries or authorize install.

Patched model materialization is a separate gate from delta artifact writing. Reaudition remains the next gate after this stage.

The hardened materializer validates before copying so failure paths do not leave a partial patched model directory behind. In the safetensors path, the patched target tensor is written back using the original target dtype rather than silently widening it.
