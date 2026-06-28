# Affordance LARQL Dry-Run Review v0

Status: experimental model-free review record

Affordance LARQL Dry-Run Review v0 records operator review of an inert LARQL
dry-run packet.

This is review only. It does not apply LARQL, create an apply packet, mutate
durable memory, train LoRA, or promote the candidate.

## Purpose

The review exists after a dry-run packet has been drafted and an operator
decides whether it is ready for later LARQL apply-packet drafting.

## Inputs

- `larql_dry_run_packet.json`
- operator decision
- operator summary

The dry-run packet must already be a validated, inert packet with promotion
held.

## Outputs

The helper writes:

```text
larql_dry_run_review.json
larql_dry_run_review.md
```

## Review decisions

- `approved_for_larql_apply_packet_drafting_only`
- `rejected_larql_dry_run_packet`
- `invalid_input`

The promotion verdict is always:

```text
hold_pending_explicit_experiment_approval
```

## Boundary

This is review only. No LARQL patch is applied, no durable memory is written,
no LoRA training is authorized, and no candidate promotion is granted.

Approval only permits drafting a later apply packet.

## Sample command

```bash
python3 local_harness/affordance_larql_dry_run_review.py \
  --packet .work/affordance_larql_dry_run_packets/navigator_cuda_larql_dry_run_v0/larql_dry_run_packet.json \
  --decision approve_for_larql_apply_packet_drafting \
  --operator-summary "The dry-run LARQL rule is scoped to navigator_desktop or matching host evidence/profile constraints, blocks CUDA/NVIDIA troubleshooting on RX580/no_cuda, recommends the LM Studio OpenAI-compatible endpoint path, requires reverify for unknown/split/stale hosts or digest mismatch, and preserves held promotion. Approve for LARQL apply-packet drafting only." \
  --out .work/affordance_larql_dry_run_reviews/navigator_cuda_larql_dry_run_v0
```
