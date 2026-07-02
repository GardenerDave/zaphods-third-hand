# Correction-Aware Prompt Packet Facts Tightening

This report records a model-free tightening pass for the correction-aware
prompt packet composer.

## Why the prompt packet was tightened

A live correction-aware model attempt produced an empty schema-shaped response:

- `allowed_targets: []`
- `held_targets: []`
- `scope_expansion_required: false`

That output treated `docs/ROADMAP.md` as if it were already authorized even
though the packet only authorized `docs/README.md`. The prompt packet was
tightened so the model-facing artifact states the concrete file-scope facts and
output contract explicitly instead of presenting an empty example shape.

## What changed

- Added concrete decision facts for allowed vs held files.
- Included packet notes in the rendered prompt packet.
- Rendered the expected output as a contract rather than a copyable empty
  example.
- Preserved explicit correction assignment and all authority boundaries.

## Local evidence path

- `.work/behavior_correction_prompt_packet_dogfood/file_scope_hold_out_v1_20260702_v2/`

## Boundary

- model-free
- no inference
- no acceptance
- no promotion
- no training
- no delta or materialization

## Non-claim

This report does not claim improved model behavior yet. It records a prompt
packet tightening step only.
