# LARQL Direct Layer Edit Candidate

Date: 2026-06-29

This report records the direction change from the adapter baseline toward the
intended LARQL-core mechanism.

What this artifact does:

- preserves the earlier adapter/LoRA path as a baseline or fallback only;
- creates a reviewable LARQL-core direct layer-edit candidate;
- keeps the model-modification method as `LARQL`;
- leaves the persistence mechanism under review as
  `direct_layer_weight_edit_candidate`;
- stops before any decomposition choice, weight edit, model artifact write, or
  recompile step.

What this artifact does not do:

- it does not implement LoRA training;
- it does not use PEFT, TRL, or SFTTrainer;
- it does not mutate model weights;
- it does not write a patched model;
- it does not merge adapters;
- it does not overwrite base model files;
- it does not deploy anything.

Why this direction change matters:

- the adapter/weight-delta smoke provided a fallback baseline path;
- the intended LARQL-core path is direct layer decomposition, bounded
  information injection, and later re-materialization/recompile;
- this candidate makes that distinction explicit before any irreversible or
  authority-expanding step.

Generated review artifacts:

- `larql_direct_layer_edit_candidate.json`
- `layer_edit_mechanism_plan.md`
- `decomposition_options.json`
- `injection_boundary.md`
- `reaudition_plan.md`

Key preserved boundaries:

- no model call;
- no weight edit;
- no model artifact write;
- no base model overwrite;
- no adapter merge;
- no production deployment;
- no runtime-rule install;
- no registry mutation;
- no install authorization;
- no dataset release;
- no automatic failure-to-curriculum capture.

Next supervised step:

`supervised_layer_edit_mechanism_selection`
