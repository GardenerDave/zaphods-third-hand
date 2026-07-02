# Correction-Aware Prompt Packet Dogfood

This report records a model-free dogfood pass of the correction-aware prompt
packet composer.

## What was tested

An explicit job packet and an explicitly rendered behavior-correction scaffold
were composed into a model-facing prompt packet.

## Local evidence path

- `.work/behavior_correction_prompt_packet_dogfood/file_scope_hold_out_v1_20260702/`

## Job packet path

- `.work/behavior_correction_scaffold_dogfood/file_scope_hold_out_v1_20260702/job_packet.json`

## Scaffold path

- `.work/behavior_correction_scaffold_dogfood/file_scope_hold_out_v1_20260702/rendered_scaffold/behavior_correction_scaffold.json`

## Composer command

```text
python3 local_harness/render_correction_aware_prompt_packet.py \
  --job-packet .work/behavior_correction_scaffold_dogfood/file_scope_hold_out_v1_20260702/job_packet.json \
  --correction-scaffold .work/behavior_correction_scaffold_dogfood/file_scope_hold_out_v1_20260702/rendered_scaffold/behavior_correction_scaffold.json \
  --out-dir .work/behavior_correction_prompt_packet_dogfood/file_scope_hold_out_v1_20260702
```

## Rendered artifacts

- `.work/behavior_correction_prompt_packet_dogfood/file_scope_hold_out_v1_20260702/correction_aware_prompt_packet.json`
- `.work/behavior_correction_prompt_packet_dogfood/file_scope_hold_out_v1_20260702/correction_aware_prompt_packet.md`

## Assigned correction

- `file_scope_hold_out_v1`

## Outcome

Explicit correction-aware prompt packet composition rendered successfully.

## Boundary

- model inference: false
- generation: false
- training: false
- delta writing: false
- patched-model materialization: false
- promotion: false
- automatic failure-to-curriculum capture: false

## Non-claims

- no model inference was run
- no correction effectiveness claim
- no auto-assignment claim
- no promotion claim
