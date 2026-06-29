# LARQL Layer Edit Mechanism Selection

Date: 2026-06-29

This report records the first model-free mechanism-selection stage for the
LARQL-core direct layer-edit path.

What this stage does:

- validates the held direct layer-edit candidate;
- records an undecided or supervised concrete mechanism selection candidate;
- optionally inspects a local base-model directory by reading `config.json` and
  `model.safetensors.index.json` only;
- writes a held selection artifact, module inventory, reversible patch format
  proposal, boundary file, and reaudition plan.

What this stage does not do:

- it does not implement LoRA;
- it does not use PEFT, TRL, or SFTTrainer;
- it does not train;
- it does not mutate weights;
- it does not write a patched model;
- it does not merge adapters;
- it does not overwrite base model files;
- it does not deploy anything.

Main path status:

- LARQL-core direct layer edit remains the main path;
- adapter/LoRA remains preserved as fallback only;
- selecting a direct mechanism does not authorize a weight edit or model write.

Artifacts written:

- `larql_layer_edit_mechanism_selection.json`
- `module_inventory.json`
- `selected_mechanism_plan.md`
- `reversible_patch_format.md`
- `layer_edit_boundary.md`
- `reaudition_plan.md`

Selection semantics:

- `undecided_pending_review` keeps the mechanism held for review;
- a concrete selection is still a supervised candidate only;
- no concrete selection in this stage authorizes install, deploy, registry
  mutation, dataset release, or automatic failure-to-curriculum capture.

Next supervised step:

`supervised_direct_layer_edit_smoke`
