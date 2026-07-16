# Prompt Patch A/B Harness

This harness is a deterministic, fixture-based v0 comparison tool for prompt patches.

It does not call models, endpoints, or live services. It evaluates stored baseline and patched outputs against a simple expected contract and reports whether the patch improved a known failure fixture.

## What it checks

Supported contract checks are limited to:

- required allowed targets
- forbidden allowed targets
- required held targets
- required JSON fields
- forbidden completion claims
- requires scope-expansion flag

The harness reports whether the patched output improved, stayed unchanged, or regressed relative to the baseline output on the same fixture.

## What it does not do

- No live model A/B execution.
- No automatic training or failure-to-curriculum capture.
- No automatic patch promotion.
- No acceptance decision.
- No merge, deployment, or downstream-use authority.
- No claim about universal prompt quality.

## Usage

```bash
python3 local_harness/run_prompt_patch_ab_harness.py --cases path/to/cases.json
python3 local_harness/run_prompt_patch_ab_harness.py --cases path/to/cases.json --output path/to/result.json
python3 local_harness/run_prompt_patch_ab_harness.py --cases local_harness/fixtures/prompt_patch_ab/scope_boundary_example.json
python3 local_harness/run_prompt_patch_ab_harness.py --cases local_harness/fixtures/prompt_patch_ab/known_failure_modes_v1.json
```

The case file must contain:

- `harness_schema: "prompt_patch_ab_cases_v1"`
- `cases`: a list of case objects with `case_id`, `failure_mode`, `prompt_patch_id`, `task_summary`, `expected_contract`, `baseline_output`, and `patched_output`

The tracked `scope_boundary_example.json` fixture is illustrative and model-free. A pass on this fixture shows the stored patched output fits the expected contract better than the baseline output. It is not a prompt-patch promotion decision.

The tracked `known_failure_modes_v1.json` fixture pack is a small deterministic regression suite for known failure modes. It exercises multiple stored baseline/patched pairs and confirms the harness can score expected improvements without calling a model. Passing the pack is still not a prompt-patch promotion decision and does not authorize downstream use.

## Relationship to the library

Prompt patches are still defined in [`docs/PROMPT_PATCH_LIBRARY.md`](PROMPT_PATCH_LIBRARY.md). This harness only compares stored outputs against a simple deterministic contract. It does not select patches, render prompts, or call models.
