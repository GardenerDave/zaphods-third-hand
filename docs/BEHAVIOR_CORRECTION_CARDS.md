# Behavior Correction Cards v1

Behavior correction cards are small, explicit, packet-level guidance artifacts
for supervised ZTH workflows.

They describe a known failure pattern, the bounded correction to inject into a
packet scaffold, how a validator can check the result, and what the card does
not authorize.

The intent is practical: replace ad hoc prompt injection with a named,
auditable, reusable correction step that can be assigned only when a packet
explicitly requests it.

## Core properties

- explicit: the card must be assigned in a packet;
- auditable: the card is a plain-file artifact with provenance and status
  metadata;
- supervised: humans still decide when a card is relevant;
- bounded: the card names a failure pattern and the corrective instruction
  without becoming a hidden global behavior;
- non-authoritative: the card does not change model weights, install a rule,
  or authorize promotion.

## How a correction card differs from related mechanisms

- Prompt injection is ad hoc and often ephemeral.
- LoRA and other adapter methods mutate model behavior through training or
  weight-side mechanisms.
- LARQL direct edits work at the model-weight level and are parked as research
  evidence, not as the product path.
- A behavior correction card is none of those things. It is a packet-level
  scaffold directive that helps a supervised workflow ask for the right
  correction in the right place.

## How a card is assigned

A packet can opt into a correction by naming the card explicitly:

```yaml
behavior_corrections:
  - file_scope_hold_out_v1
```

That assignment is explicit packet-level guidance only. It does not imply
default use, automatic reuse, or unattended authority.

## Rendering assigned corrections

Assigned corrections can be rendered into a bounded scaffold section by a
model-free local harness script.

Example:

```text
python3 local_harness/render_behavior_correction_scaffold.py \
  --packet .work/example_job_packet.json \
  --out-dir .work/example_behavior_correction_scaffold
```

The renderer reads the packet, validates each referenced card, and writes a
scaffold artifact such as:

- `behavior_correction_scaffold.json`
- `behavior_correction_scaffold.md`

The rendered scaffold remains explicit and bounded. It records the assigned
corrections, the correction instructions, validator expectations, known
failure modes, non-authorities, and provenance notes. It does not auto-assign
corrections and it does not authorize model calls, edits, or promotion.

## Composing correction-aware prompt packets

After a scaffold has been rendered, a separate model-free composer can turn a
job packet plus the scaffold into a model-facing prompt packet.

Example:

```text
python3 local_harness/render_correction_aware_prompt_packet.py \
  --job-packet .work/example_job_packet.json \
  --correction-scaffold .work/example_behavior_correction_scaffold/behavior_correction_scaffold.json \
  --out-dir .work/example_correction_aware_prompt_packet
```

Expected output artifacts:

- `correction_aware_prompt_packet.json`
- `correction_aware_prompt_packet.md`

The composer is model-free. It only packages the explicit assignment, task
boundary, correction guidance, and authority boundary into a prompt-ready
artifact. It does not auto-assign corrections and it does not call a model.

## Validator role

Validators can check whether a packet or response followed the card by looking
for the expected bounded shape:

- did the output preserve a scoped allowed/held split?
- did it avoid empty schema-shaped JSON when a decision was required?
- did it avoid claiming authority beyond the packet boundary?

Validators can compare the packet, the correction card, and the model output.
They do not accept the output as truth; they only report whether the observed
shape matches the expected correction pattern.

## Failure-to-curriculum boundary

Failure-to-curriculum capture remains strictly opt-in. A correction card does
not make failed outputs training data by default, and it does not authorize any
automatic capture path.

## Example cards

- [`file_scope_hold_out_v1`](behavior_correction_cards/file_scope_hold_out_v1.json)
