# LARQL Model Response Review v0

This review tool inspects a completed model response probe without calling a
model. It classifies the response as a model semantic failure, scorer false
positive/negative, endpoint failure, or pass.

Inputs:

- `larql_model_response_probe.json`
- `model_response.txt`

Outputs:

- `larql_model_response_review.json`
- `larql_model_response_review.md`

Boundary:

- review only
- no model is called
- no durable memory is written
- no candidate promotion is granted
- no LoRA training is authorized
- no model weights are mutated
