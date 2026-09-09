# Fleet Availability Handoff Dogfood 2026-09-09

## Scope

This dogfood run checked the explicit supplier-to-worker binding path and the
availability-aware transaction handoff projection. It did not add scheduling,
promotion, training, queue insertion, or autonomous authority.

## Identity Binding

- Capability supplier: `qwen3_1_7b_labeled_2_032b_minimal_atom`
- Explicit worker binding reference: `router`
- Mapping source observed in route evidence: `explicit_worker_binding_ref`
- Advertised model evidence: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Full live endpoint/preflight evidence remains in the ignored fleet snapshot
  artifact, referenced by hash from the transaction manifest and next-worker
  context.

## Dogfood Outcome

The first supervised worker attempt used the 1.7B worker and failed the
allowed/held target separation boundary by placing held targets in
`allowed_targets`. That failure was preserved as capability-boundary evidence
and justified escalation.

The 30B escalation produced a valid contract-shaped output preserving
`docs/reports/` as the only allowed target and holding production automation,
automatic curriculum capture, automatic promotion, and implementation packets.
The run was ingested with explicit accepted review.

## Durable Artifact Checks

The transaction handoff artifacts now include:

- `route_trace` evidence reference with sha256
- `capability_plan` evidence reference with sha256
- `fleet_snapshot` evidence reference with sha256
- `router_evidence.availability_summary.overall_execution_status`
- per-capability selected supplier, worker binding reference, worker identity,
  binding status, availability status/reason, advertised model identity, and
  execution-step creation status

## Source Run Hashes

Source run: `.work/manual_supervised_attempts/20260909T002000Z`

- 1.7B failed raw output:
  `9baa24170449d8a754fd63964c606f25cb721e2977afc879d815e3d5d260aea5`
- 1.7B failed call metadata:
  `bfdc9fd5c8a5695e4b59d81781f6b6133a05316138c6dc41910bb48d3f01942c`
- 30B accepted raw output:
  `70599cfa021e06966292371d8dc6753ac19698b43352b98601a191df96055aec`
- 30B call metadata:
  `f02fb67006a9851c9ce57fae76c3ea60b2f05c877bf2ffd81972518a24ecf9d7`
- fleet snapshot:
  `3b5ce9c3cd97717885fba149a018d646e59742d8fa7f09a038216f2d5f36c64d`
- capability plan:
  `bcba17d982a61c8d7709ad1f0751b54d55b28ef69bb08e2a067b4252c12bd175`
- route trace:
  `599cb7130ab6377714c41685c7f71dcfa6fe638a1b70cbd012b5b8971a7c7c57`
- transaction manifest:
  `d909b055ed6ecf5cb315ecd7ffa8d95cd64b761adedbb0c36a7bc390bf50d41d`
- next-worker context:
  `092fa454cd450238c65cd866a2cdaf2bc7bd19c9db95d21b32670c45ba366a18`

## Next Step

The next bounded architecture step is to make the supervised transaction
front-door write the availability-aware route trace and capability plan before
model dispatch, instead of requiring an operator-side attachment step.
