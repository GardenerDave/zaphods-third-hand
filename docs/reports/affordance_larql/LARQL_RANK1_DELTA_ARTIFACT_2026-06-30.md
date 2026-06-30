# LARQL Rank-1 Delta Artifact

This report adds the first separately authorized tensor artifact stage in the LARQL direct-layer pipeline.

What this stage does:

- reads the reviewed delta design packet;
- recomputes the reviewed output direction and input basis from compact vectors;
- writes one standalone rank-1 delta artifact;
- records provenance, shape, scale, norm, and artifact hash.

What this stage does not do:

- it does not apply the delta to a model;
- it does not overwrite base weights;
- it does not materialize a patched model;
- it does not run inference or reaudition;
- it does not promote or deploy anything.

This stage is separately gated because a tensor artifact is materially different from a planning packet. Patched model materialization and reaudition remain separate authorization boundaries.
