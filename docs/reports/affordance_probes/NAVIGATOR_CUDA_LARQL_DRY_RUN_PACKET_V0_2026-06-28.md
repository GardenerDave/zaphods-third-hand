# LARQL Dry-Run Packet v0

Candidate id: `larql_affordance_candidate_48efff9852ea`
Source failure id: `cuda_on_navigator_desktop.real`
Packet verdict: `ready_for_larql_dry_run_review`
Allowed next step: `review_larql_dry_run_packet`
Promotion verdict: `hold_pending_explicit_experiment_approval`

This is a dry-run packet only.
It is not an applied LARQL patch.
It is not durable memory.
It is not LoRA training.
It is not promotion.
It exists to let a reviewer decide whether a later LARQL apply packet should be drafted.

## Draft LARQL Rule

- Rule id: `navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0`
- Status: `draft_not_applied`
- Applies when:
  - active execution host matches navigator_desktop or matching host evidence/profile constraints
  - host constraint includes no_cuda
  - known-bad path includes CUDA-only setup on RX580
- Blocks or warns on:
  - CUDA-only setup
  - NVIDIA/CUDA troubleshooting path on RX580/no_cuda host
- Recommends:
  - LM Studio OpenAI-compatible endpoint for small-model GPU-backed workflow
- Requires reverify when:
  - active host is unknown
  - local host and remote host differ
  - hardware, GPU, driver, endpoint, or host profile may have changed
  - candidate digest or source digests do not match

## Boundary

This packet does not authorize LARQL application, LoRA training, durable memory, or candidate promotion.
