# Model Prompt Packet Renderer

The model prompt packet renderer sits after the orchestration boundary. It takes
a validated orchestration packet and renders a bounded, reviewable prompt
artifact for later supervised model-facing use.

Pipeline position:

```text
messy input
  -> triage/router packet
  -> prompt patch selection
  -> orchestration packet assembly + validation
  -> model prompt packet rendering (this layer)
  -> later supervised model call (future PR)
```

This layer is deterministic and model-free.

## What this renderer does

`local_harness/render_model_prompt_packet.py`:

- validates orchestration packets before rendering
- preserves packet identity (`orchestration_id`, `triage_id`)
- preserves allowed targets exactly
- preserves held targets exactly
- preserves selected prompt patch IDs
- includes rendered patch deltas
- includes output contract
- includes validation hooks
- includes authority boundaries
- includes an explicit review-required section
- includes a required response shape section

For JSON contracts, the required response shape is explicit and conservative:

- return only JSON matching the output contract
- include a reason field when required
- do not include prose outside the JSON object

## Safety and authority boundaries

The renderer does not invent new targets, new authority, or expanded workflow
scope. It rejects forbidden terms in rendered output, including:

- `execute this command`
- `modify files directly`
- `train the adapter`
- `promote this patch`
- `auto-add failure to curriculum`
- `default curriculum capture`

## What this layer does not do

This layer does not:

- call models
- execute commands
- modify files
- train adapters
- promote patches
- perform default failure-to-curriculum capture

It preserves review requirement, provenance linkage via packet IDs, target
boundaries, patch selection, validation hooks, and authority boundaries.

## Relationship to prior layers

- Triage/router (`docs/TRIAGE_ROUTER.md`) produces bounded triage packets.
- Prompt patch library (`docs/PROMPT_PATCH_LIBRARY.md`) defines validated patch
  records and patch deltas.
- Orchestration boundary (`docs/ORCHESTRATION_BOUNDARY.md`) assembles and
  validates orchestration packets.
- This renderer is the final model-free step before a supervised model call can
  be introduced in a later PR.
