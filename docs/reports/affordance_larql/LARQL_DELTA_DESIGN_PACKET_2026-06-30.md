# LARQL Delta Design Packet

This report adds the first packet-only delta design stage after the reviewable prompt activation direction packet.

Current state before this stage:

- the direction packet is reviewable;
- the selected vector source is a prompt-side correction direction;
- output-space direction alone is still not enough to design a weight delta.

What this stage adds:

- module-input compact vectors alongside the existing prompt output vectors;
- a packet-only rank-1 delta design review artifact;
- a proposed delta shape derived from output direction length and input basis length.

Why input-side vectors are needed:

For a linear projection with `output = input @ W.T`, a rank-1 design needs both:

- an output correction direction;
- an input basis vector.

This stage computes design metadata only. It does not write a safetensors delta, mutate weights, materialize a patched model, or authorize promotion.

Target provenance is resolved deterministically from the strongest available reviewed source:

- direction packet;
- source activation capture record;
- compact vector rows;
- otherwise fail closed.

The packet does not silently continue with `unknown` target metadata.

The design packet may describe a future rank-1 formula:

`delta_W = scale * normalize(output_direction) outer normalize(input_basis)`

That formula remains text only in this stage. Any scale choice, delta artifact, patched model materialization, or reaudition run remains separately authorized work.
