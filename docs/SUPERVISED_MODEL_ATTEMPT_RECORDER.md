# Supervised Model Attempt Recorder

The supervised model attempt recorder sits directly after the model prompt packet
renderer. It records model attempt artifacts in a deterministic, model-free,
review-oriented format.

Pipeline position:

```text
messy input
  -> triage/router packet
  -> orchestration packet assembly + validation
  -> model prompt packet rendering
  -> supervised model attempt recording (this layer)
  -> later output-contract validation layer (future PR)
```

## What this layer does

`local_harness/supervised_model_attempt.py` provides:

- `validate_supervised_model_attempt_record(record)`
- `build_supervised_model_attempt_record(...)`

The builder records one supervised attempt from:

- prompt packet identity (`prompt_packet_id` and/or `source_prompt_packet_path`)
- triage + orchestration IDs
- operator-provided model metadata
- operator metadata with `review_required: true`
- raw model output text
- provenance

The builder and validator enforce:

- required IDs (`attempt_id`, `triage_id`, `orchestration_id`)
- prompt packet linkage (`prompt_packet_id` or `source_prompt_packet_path`)
- required `model_metadata`
- required `operator_metadata`
- `operator_metadata.review_required` must be `true`
- required raw output preservation (`raw_model_output` is required string)
- `validation_status` starts as `not_validated`
- `acceptance_status` starts as `not_reviewed`
- explicit denial boundaries:
  - no command execution authority
  - no direct file modification authority
  - no automatic patch promotion authority
  - no automatic training authority
  - no default failure-to-curriculum capture authority
  - human review required before downstream use

The record is a supervised evidence artifact. It is not an acceptance decision.

## Renderer behavior

`local_harness/render_supervised_model_attempt.py` renders a plain-text review
artifact with sections:

- Attempt IDs
- Model Metadata
- Operator Metadata
- Source Prompt Packet
- Raw Model Output
- Validation Status
- Acceptance Status
- Authority Boundaries
- Provenance
- Review Requirement

The renderer validates the record before rendering and preserves
`raw_model_output` exactly as text.

## What this layer does not do

This layer does not:

- call models
- call network/model endpoints
- execute commands from model output
- modify files from model output
- validate semantic correctness of model output
- accept model output
- promote patches
- train adapters
- capture failures into curriculum by default

## Why this exists

This layer creates a deterministic handoff artifact for supervised review. It
preserves prompt provenance, model metadata, operator metadata, raw output, and
review requirements so a future layer can validate output contracts without
introducing autonomous authority.
