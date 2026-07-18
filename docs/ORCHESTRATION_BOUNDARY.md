# Orchestration Boundary Layer

The orchestration boundary sits directly after triage/router classification and
prompt patch selection. It assembles a bounded, reviewable orchestration packet
that can be consumed by a later model-facing prompt renderer.

Pipeline position:

```text
messy input
  -> deterministic triage/router packet
  -> selected prompt patch IDs
  -> orchestration packet assembly (this layer)
  -> plain-text orchestration review artifact
  -> later model-facing prompt packet rendering
```

This layer is deterministic and model-free.

## What the orchestration boundary does

The assembler in `local_harness/orchestration_packet.py` takes:

- a validated triage packet
- a loaded prompt patch library

and returns one orchestration packet with:

- triage linkage (`triage_id`, source summary, workflow, task type)
- copied scope (`allowed_targets`, `held_targets`, `risk_flags`)
- selected patch IDs (from triage recommendations)
- rendered patch deltas (via prompt patch library rendering)
- output contract and validation hooks
- explicit authority boundaries
- provenance back to triage + patch IDs
- mandatory `review_required: true`

## Packet guarantees and validation

`validate_orchestration_packet(...)` enforces:

- required fields are present
- `review_required` is always `true`
- `allowed_targets` and `held_targets` do not overlap
- every selected patch ID exists in the loaded library
- deprecated selected patches are rejected by default
- deprecated selected patches are only allowed when explicitly enabled
- `output_contract` is present and non-empty
- `validation_hooks` is present and non-empty
- authority boundaries include all required denials:
  - `no_execution_authority`
  - `no_automatic_patch_promotion`
  - `no_automatic_training`
  - `no_default_failure_to_curriculum_capture`
  - `no_direct_file_modification_authority`
- command execution instruction terms are rejected
- packet-level execution / auto-training / auto-promotion / default
  failure-to-curriculum-capture authority language is rejected

## Renderer behavior

`local_harness/render_orchestration_packet.py` renders a plain-text artifact with
review sections:

- Source / Triage
- Workflow
- Allowed Targets
- Held Targets
- Risk Flags
- Prompt Patches
- Output Contract
- Validation Hooks
- Authority Boundaries
- Review Requirement
- Provenance

The renderer validates the packet first and does not invent new authority,
targets, or patch selections.

## Explicit non-goals

This layer does not:

- call live models
- execute commands
- modify files directly
- train adapters or run automatic training
- promote patches automatically
- perform default failure-to-curriculum capture
- bypass supervised review

## Relationship to prior layers

- Triage/router (`docs/TRIAGE_ROUTER.md`) normalizes messy input into a bounded
  triage packet.
- Prompt patch library (`docs/PROMPT_PATCH_LIBRARY.md`) provides validated patch
  records and deterministic patch-delta rendering.
- This orchestration boundary combines both into one inspectable packet that is
  review-ready and provenance-preserving.

## Bounded Task Packet Drafts

`local_harness/validate_bounded_task_packet_draft.py` validates the manual
bridge artifact used after a validated messy-input triage packet. The draft is a
review-required handoff shape, not a router, queue inserter, or authority
grant.

Required fields include:

- `packet_schema: "bounded_task_packet_draft_v1"`
- `source_packet_schema: "messy_input_triage_packet_v1"`
- `source_packet_path`
- `task_summary`
- `allowed_targets`
- `held_targets`
- `evidence_needed`
- `proposed_action`
- `validation_plan`
- `stop_conditions`
- `authority_boundary`
- `review_required: true`
- `downstream_use_status: "prohibited_until_review"`
- `automation_status: "not_automated"`
- `queue_handoff_status: "not_inserted"`

The authority boundary must include:

- `no_unattended_execution`
- `no_repo_mutation_without_review`
- `no_training_capture`
- `no_promotion`
- `no_deployment`
- `no_downstream_use_authority`

Example validation command:

```bash
python3 local_harness/validate_bounded_task_packet_draft.py \
  --packet .work/messy_input_triage_bridge/20260717_triage_to_bounded_task_001/bounded_task_packet_draft.json
```

This validator is deterministic and model-free. It checks packet shape and
authority boundaries only; it does not authorize execution, repo mutation,
queue insertion, fixture import, training capture, promotion, deployment, or
downstream use.

The deterministic bridge fixture suite at
`local_harness/fixtures/triage_to_bounded_task_bridge/` exercises this draft
shape against both passing and fail-closed cases.

## Bounded Task Review Packet Drafts

`local_harness/validate_bounded_task_review_packet.py` validates the review
packet that follows a validated bounded task draft. This review packet is
review-required evidence only; it does not authorize queue insertion, repo
mutation, fixture import, training capture, promotion, deployment, or
downstream use.

Required fields include:

- `packet_schema: "bounded_task_review_packet_v1"`
- `source_packet_schema: "bounded_task_packet_draft_v1"`
- `source_packet_path`
- `source_validation_status: "passed"`
- `review_status: "review_required"`
- `downstream_use_status: "prohibited_until_review"`
- `automation_status: "not_automated"`
- `queue_handoff_status: "not_inserted"`
- `repo_mutation_status: "not_authorized"`
- `task_summary`
- `reviewed_artifacts`
- `required_checks`
- `authority_boundary`
- `diagnostics`
- `recommended_next_step`

The authority boundary must include:

- `no_unattended_execution`
- `no_repo_mutation_without_review`
- `no_training_capture`
- `no_promotion`
- `no_deployment`
- `no_downstream_use_authority`

Example validation command:

```bash
python3 local_harness/validate_bounded_task_review_packet.py \
  --packet local_harness/fixtures/bounded_task_review_packet/valid_review_packet_001.json
```

The deterministic bridge fixture suite at
`local_harness/fixtures/bounded_task_review_packet/` exercises this review
shape against pass and fail-closed cases.
