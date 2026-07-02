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
Prompt packets should render concrete decision facts, packet notes, and a
required output contract rather than copyable empty-example outputs.

## Running a correction-aware model attempt

After a prompt packet exists, an explicit authorization can trigger one model
attempt against an OpenAI-compatible endpoint.

Example:

```text
python3 local_harness/run_correction_aware_model_attempt.py \
  --prompt-packet .work/example_correction_aware_prompt_packet/correction_aware_prompt_packet.md \
  --out-dir .work/example_model_attempt \
  --endpoint-url http://127.0.0.1:1234/v1 \
  --model qwen3-1.7b-gpu-40k \
  --authorize-model-attempt
```

Expected output artifacts:

- `model_attempt_record.json`
- `raw_model_output.txt`
- `model_attempt_summary.json`
- `status.log`
- `status_events.jsonl`

This runner performs one model attempt only. It does not validate correctness,
accept outputs, promote artifacts, train, write deltas, materialize models, or
capture failures for curriculum.

## Validating correction-aware model outputs

After a model attempt, a separate model-free validator can inspect the raw
output and compare it against the packet expectations.

Example:

```text
python3 local_harness/validate_correction_aware_model_output.py \
  --model-attempt-dir .work/example_model_attempt \
  --job-packet .work/example_job_packet.json \
  --prompt-packet .work/example_correction_aware_prompt_packet.json \
  --out-dir .work/example_output_validation
```

Expected output artifacts:

- `correction_aware_output_validation.json`
- `correction_aware_output_validation.md`

Validation is model-free. It does not accept, promote, train, write deltas, or
perform supervised acceptance. It only records whether the observed output
matches the explicit correction-card expectations.

## Rendering correction-aware supervised review packets

After validation, a separate model-free renderer can package the attempt,
validation report, and source packets into a reviewer-facing packet.

Example:

```text
python3 local_harness/render_supervised_review_packet.py \
  --model-attempt-dir .work/example_model_attempt \
  --job-packet .work/example_job_packet.json \
  --prompt-packet .work/example_correction_aware_prompt_packet.json \
  --validation-report .work/example_output_validation/correction_aware_output_validation.json \
  --out-dir .work/example_supervised_review_packet
```

Expected output artifacts:

- `supervised_review_packet.json`
- `supervised_review_packet.md`

The review packet is model-free and does not accept, promote, train, write
deltas, materialize models, or capture failures for curriculum. It is a
review artifact only.
Use the JSON prompt packet path, not the Markdown packet, so the provenance
fields and authority split remain explicit and machine-checkable.

## Rendering supervised review decision records

After a supervised review packet exists, a separate model-free renderer can
record an explicit supervised decision without promoting anything:

```text
python3 local_harness/render_supervised_review_decision_record.py \
  --review-packet .work/example_supervised_review_packet/supervised_review_packet.json \
  --decision accept_as_corrected_output \
  --reviewer-id david \
  --rationale "Validated r5 corrected output and confirmed ROADMAP.md is held out." \
  --out-dir .work/example_supervised_review_decision
```

Expected output artifacts:

- `supervised_review_decision_record.json`
- `supervised_review_decision_record.md`

This is a model-free decision record only. It does not promote, edit files,
train, write deltas, materialize models, or capture failures for curriculum.

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
