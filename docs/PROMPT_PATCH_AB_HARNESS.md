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
python3 local_harness/render_prompt_patch_ab_review_bundle.py \
  --cases local_harness/fixtures/prompt_patch_ab/known_failure_modes_v1.json \
  --out /tmp/prompt_patch_ab_review_bundle.json
```

The case file must contain:

- `harness_schema: "prompt_patch_ab_cases_v1"`
- `cases`: a list of case objects with `case_id`, `failure_mode`, `prompt_patch_id`, `task_summary`, `expected_contract`, `baseline_output`, and `patched_output`

The tracked `scope_boundary_example.json` fixture is illustrative and model-free. A pass on this fixture shows the stored patched output fits the expected contract better than the baseline output. It is not a prompt-patch promotion decision.

The tracked `known_failure_modes_v1.json` fixture pack is a small deterministic regression suite for known failure modes. It exercises multiple stored baseline/patched pairs and confirms the harness can score expected improvements without calling a model. Passing the pack is still not a prompt-patch promotion decision and does not authorize downstream use.
The tracked pack also includes a combined scope-boundary/output-contract case derived from supervised live evidence. Passing it still is not promotion and does not authorize downstream use.
The tracked pack also includes a messy-input triage packet case derived from supervised local-worker audition attempt 002. It keeps the triage packet validator authoritative: the baseline output is missing required fields, the contract output has the wrong `authority_boundary` type, and the patched output is a valid `messy_input_triage_packet_v1`. Passing it is still not promotion and does not authorize downstream use.

`render_prompt_patch_ab_review_bundle.py` packages a fixture run into a review artifact with hashes and explicit authority boundaries. It is review-only evidence, not a patch promotion mechanism and not downstream-use authorization.

## Live supervised A/B evidence producer

`run_prompt_patch_ab_live.py` is the operator-invoked live evidence producer for this branch. It makes one baseline call and one patched call under identical runtime settings, writes a harness-compatible case file, and leaves scoring to the deterministic harness.
It performs an explicit endpoint preflight first and fails closed before the A/B calls when the endpoint is unreachable.

Example usage:

```bash
python3 local_harness/run_prompt_patch_ab_live.py \
  --case-id case_001 \
  --failure-mode scope_boundary \
  --prompt-patch-id scope_boundary_v1 \
  --task-summary "Keep allowed and held targets separated." \
  --expected-contract path/to/expected_contract.json \
  --baseline-prompt path/to/baseline_prompt.txt \
  --patched-prompt path/to/patched_prompt.txt \
  --base-url http://127.0.0.1:8080/v1 \
  --model test-model \
  --out-dir /tmp/prompt_patch_ab_live_case
```

The live producer is evidence-only and review-required. It does not promote patches, does not authorize downstream use, and does not replace the deterministic harness for scoring.

## Fixture candidate exporter

`export_prompt_patch_ab_fixture_candidate.py` converts supervised live run evidence into a reviewable fixture candidate draft. It does not import the candidate, does not promote patches, and does not authorize downstream use. A reviewer must still manually copy or accept any candidate into the tracked fixture pack.

## Fixture candidate review

`review_prompt_patch_ab_fixture_candidate.py` validates a candidate draft and renders a checklist for human review. It does not import candidates, does not promote patches, and does not authorize downstream use. Accepted candidates still require manual tracked fixture, test, and docs edits.

## Fixture candidate wrapper

`scripts/zth_prompt_patch_candidate.sh` runs the export and review steps for a supervised live run and prints the resulting candidate and review paths. It writes reviewable candidate artifacts only, does not import fixtures, does not promote patches, and does not authorize downstream use.

## Relationship to the library

Prompt patches are still defined in [`docs/PROMPT_PATCH_LIBRARY.md`](PROMPT_PATCH_LIBRARY.md). This harness only compares stored outputs against a simple deterministic contract. It does not select patches, render prompts, or call models.
