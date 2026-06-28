# Affordance LARQL Apply Packet v0

Status: experimental model-free apply-packet draft

Affordance LARQL Apply Packet v0 drafts an inert LARQL apply packet from a
validated dry-run packet and an approved dry-run review.

This is packet only. It does not apply LARQL, mutate durable memory, train
LoRA, or promote the candidate.

## Purpose

The packet exists after a dry-run packet has been reviewed and approved for
later apply-packet drafting.

It records a proposed rule and the criteria a later reviewer would use before
any real LARQL application is authorized.

## Inputs

- `larql_dry_run_packet.json`
- `larql_dry_run_review.json`

Both inputs must be validated and approved as described in the packet
requirements.

## Outputs

The helper writes:

```text
larql_apply_packet.json
larql_apply_packet.md
```

## Packet verdicts

- `ready_for_larql_apply_review`
- `invalid_input`

The promotion verdict is always:

```text
hold_pending_explicit_experiment_approval
```

## Proposed rule

The packet includes an inert proposed rule payload copied from the dry-run
packet, renamed to show that it is proposed but not applied.

## Apply review criteria

The packet includes explicit criteria for later review before any LARQL
application would be authorized.

## Boundary

This is packet only. It is not an applied LARQL patch, not durable memory,
not LoRA training, and not candidate promotion.

It only permits later review of whether LARQL application should be authorized.

## Sample command

```bash
python3 local_harness/affordance_larql_apply_packet.py \
  --dry-run-packet .work/affordance_larql_dry_run_packets/navigator_cuda_larql_dry_run_v0/larql_dry_run_packet.json \
  --dry-run-review .work/affordance_larql_dry_run_reviews/navigator_cuda_larql_dry_run_v0/larql_dry_run_review.json \
  --out .work/affordance_larql_apply_packets/navigator_cuda_larql_apply_v0
```
