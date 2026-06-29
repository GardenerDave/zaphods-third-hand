# LARQL Direct Layer Edit Smoke

Date: 2026-06-29

This is the first LARQL-core direct layer-edit smoke path.

It is not LoRA.
It is not training.
It is not an adapter.

What this stage does:

- validates a concrete LARQL layer-edit mechanism selection;
- checks that a requested target tensor key matches the selected module family;
- prepares a reversible direct tensor-delta artifact when the local tensor stack
  and base model path are available;
- optionally materializes a patched model copy only with separate explicit
  authorization;
- automatically verifies whether a materialized patched model copy actually
  differs from the base tensor at the target key.

What this stage does not do:

- it does not overwrite the base model;
- it does not train;
- it does not merge adapters;
- it does not deploy anything;
- it does not install runtime rules;
- it does not mutate completed registries.

Key boundary conditions:

- base model overwrite is never authorized;
- delta artifact creation is reversible;
- patched model copy requires separate explicit authorization;
- patched model copy verification records whether the effective patch was
  actually applied;
- behavioral success requires later re-audition;
- the first delta smoke is not, by itself, a behavioral success claim.

Outputs:

- `larql_direct_layer_edit_smoke.json`
- `direct_delta_manifest.json`
- `reversible_patch_bundle.json`
- `target_tensor_report.json`
- `reaudition_plan.md`
- `direct_delta.safetensors` when delta creation succeeds
- `patched_model/` only when separately authorized
- `patch_verification.json` when patched model materialization is attempted

Next step:

`supervised_direct_layer_edit_reaudition`
