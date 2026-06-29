# LARQL Weight Persistence Smoke

Date: 2026-06-29

This is the first weight-persistence smoke bridge from a completed LARQL model-modification candidate.

What was prepared:

- a bounded `training_input.jsonl` derived from the opt-in LARQL behavior example preview;
- a local training stack preflight using Python imports and filesystem inspection only;
- a weight-persistence handoff;
- a reaudition plan.

Why this is the first weight-persistence smoke bridge:

- the earlier chain proved bounded behavior capture and live temporary-context replay;
- this step is the first explicit bridge from that evidence into a weight-level persistence smoke path.

Why adapter/weight-delta is selected only for the smoke:

- the smoke needs one concrete persistence mechanism to prepare a reauditionable training path;
- that choice is limited to this smoke only;
- it does not authorize any broader persistence or production decision.

What was not authorized:

- package installation;
- model download;
- base-model overwrite;
- adapter merge;
- deployment;
- runtime-rule install;
- registry mutation;
- dataset release;
- automatic failure-to-curriculum capture.

Training stack preflight outcome:

- recorded in `training_stack_preflight.json`;
- if imports or base model path are missing, the smoke remains a preparation artifact and the training run is blocked.

Next command if a valid base model path and training stack are available:

`python3 local_harness/larql_weight_persistence_smoke.py --candidate <candidate.json> --behavior-jsonl <larql_behavior_example_preview.jsonl> --run-id <run_id> --out-root .work/larql_weight_persistence_smokes --base-model-path <base_model_dir> --authorize-larql-weight-persistence-smoke --run-training`

Next step:

`supervised_weight_persistence_reaudition`
