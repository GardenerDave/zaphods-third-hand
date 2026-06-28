# Affordance LARQL Apply Review v0

Status: experimental model-free review record

Affordance LARQL Apply Review v0 records operator review of an inert LARQL
apply packet.

This is review only. It does not apply LARQL, create or modify a real rule
file, mutate durable memory, train LoRA, or promote the candidate.

## Purpose

The review exists after an apply packet has been drafted and an operator decides
whether actual LARQL application would be authorized later.

## Inputs

- `larql_apply_packet.json`
- operator decision
- operator summary

The apply packet must already be a validated inert packet.

## Outputs

The helper writes:

```text
larql_apply_review.json
larql_apply_review.md
```

## Review decisions

- `approved_for_larql_application_only`
- `rejected_larql_application`
- `invalid_input`

The promotion verdict is always:

```text
hold_pending_explicit_experiment_approval
```

## Boundary

This is review only. No LARQL patch is applied by this review, no durable
memory is written, no LoRA training is authorized, and no candidate promotion
is granted.

Approval only authorizes a later apply step.

## Sample command

```bash
python3 local_harness/affordance_larql_apply_review.py \
  --apply-packet .work/affordance_larql_apply_packets/navigator_cuda_larql_apply_v0/larql_apply_packet.json \
  --decision approve_larql_application \
  --operator-summary "The proposed rule is scoped to navigator_desktop or matching host evidence/profile constraints, blocks CUDA/NVIDIA troubleshooting on RX580/no_cuda, recommends the LM Studio OpenAI-compatible endpoint path only under matching evidence, requires reverify for unknown/split/stale hosts or digest mismatch, and does not authorize promotion or durable memory. Approve LARQL application only." \
  --out .work/affordance_larql_apply_reviews/navigator_cuda_larql_apply_v0
```
