# Coding Delegation Dogfood

This report documents a blocked coding-delegation experiment.

The goal was to have Codex act as operator/reviewer only while a local 1.7B
model produced the actual implementation patch for a tiny bounded safety check.
The intended tiny task was to tighten
`local_harness/validate_correction_aware_model_output.py` by requiring a
non-empty `reason` in correction-aware model outputs, with a matching test in
`tests/test_validate_correction_aware_model_output.py`.

## What was attempted

I inspected the repo state, identified a small bounded validator change, and
checked the local model endpoint path documented for this project.

## Blocker

The local 1.7B model attempt could not be run in this environment:

- `curl http://127.0.0.1:1234/v1/models` could not connect to a local server;
- `~/ai/src/llama.cpp/build/bin/llama-server` was not present.

Because the delegated model could not be reached, no model-authored patch was
available to parse, verify, or apply.

## Result

`result: blocked_before_model_attempt`

## What Codex did

- inspected repo state;
- selected a tiny bounded validator task;
- verified that the expected local 1.7B endpoint/server was unavailable;
- recorded the experiment as blocked evidence.

## What Codex did not do

- did not write the implementation;
- did not repair or substitute a patch;
- did not apply a model-generated diff;
- did not run a local 1.7B model attempt;
- did not train, tune, write deltas, materialize models, or capture failures
  into curriculum;
- did not promote anything.

## Authority boundary

- model inference occurred: no
- Codex-authored implementation occurred: no
- promotion occurred: no
- training occurred: no
- delta writing occurred: no
- model materialization occurred: no
- automatic failure-to-curriculum capture occurred: no

## Why this matters

The experiment shows the boundary clearly: ZTH can describe a delegable coding
task, but the local 1.7B execution path must actually be available for the
delegation pattern to work.
