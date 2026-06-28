# LARQL Model Context Packet v0

This experiment scaffold drafts a bounded model-context packet from a
validated LARQL runtime consultation probe. It is model-free and does not
apply a rule, train LoRA, write durable memory, mutate weights, or promote the
candidate.

Inputs:

- `larql_runtime_consultation_probe.json`
- runtime rule JSON
- messy user input text

Outputs:

- `larql_model_context_packet.json`
- `larql_model_context_packet.md`

Purpose:

- package the consultation result into an inert packet for later model-response
  probing
- keep the runtime rule scoped to `navigator_desktop` and `no_cuda`
- preserve the bounded consultation boundary

The packet includes:

- the runtime rule context
- the user input
- a bounded model instruction
- authorization flags that remain false

Boundary:

- packet only
- no model is called
- no durable memory is written
- no candidate promotion is granted
- no LoRA training is authorized
- no model weights are mutated
