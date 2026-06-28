# LARQL Model Response Probe v0

This experiment scaffold runs one explicit model call against a bounded LARQL
model-context packet and then scores the response locally. It is a probe only
and does not write durable memory, train LoRA, mutate weights, or promote the
candidate.

Inputs:

- `larql_model_context_packet.json`
- `ZTH_ENDPOINT_URL`
- `ZTH_MODEL_ID`

Outputs:

- `larql_model_response_probe.json`
- `larql_model_response_probe.md`
- `model_response.txt`

Purpose:

- call the configured OpenAI-compatible endpoint once with the supplied
  instruction and user input
- score the response with local deterministic checks
- preserve the same no-mutation / no-promotion boundary

Boundary:

- model call is explicit and bounded to the configured endpoint
- no durable memory is written
- no candidate promotion is granted
- no LoRA training is authorized
- no model weights are mutated
