# LARQL Apply Packet v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Rule id: `navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0`
Packet verdict: `ready_for_larql_apply_review`
Allowed next step: `review_larql_apply_packet`
Promotion verdict: `hold_pending_explicit_experiment_approval`

This is packet only.
It is not an applied LARQL patch.
It is not durable memory.
It is not LoRA training.
It is not candidate promotion.
This packet only permits later review of whether LARQL application should be authorized.

## Proposed Rule

- Rule id: `navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0`
- Status: `proposed_not_applied`

## Apply Review Criteria

- Rule remains scoped to navigator_desktop or matching host evidence/profile constraints.
- Rule blocks or warns on CUDA/NVIDIA troubleshooting for RX580/no_cuda hosts.
- Rule recommends the LM Studio OpenAI-compatible endpoint path only under matching evidence.
- Rule requires reverify when active host is unknown, split, stale, or digest evidence mismatches.
- Rule does not promote the candidate or write durable memory.

## Boundary

No LARQL patch is applied by this packet.
