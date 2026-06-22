# Preflight-to-Audition Operator Planner

`local_harness/preflight_audition_plan.py` prepares a deterministic,
model-free command plan for the existing LLM-probe preflight and gated model
audition tools.

The planner inspects operator-supplied paths, validates the selected workflow
shape, and prints reviewable commands. It does not run those commands.

## Boundaries

The planner does not:

- call a model or run an audition;
- start or configure a model endpoint;
- delete `.work/` or other evidence;
- upload source material;
- promote, approve, rank, route, or assign a model;
- move lifecycle state;
- treat a passing check or preflight status as authority.

Printed commands are review material. An authorized operator must inspect the
inputs, endpoint configuration, generated manifest, gate result, output paths,
and commands before running anything manually.

## Source Choices

Choose exactly one preflight source:

- `--llm-probe-output` points to normalized LLM-probe JSON or verified YAML
  that still needs to be imported. The plan includes
  `llm_probe_preflight_ingest.py` and expects the resulting
  `preflight_capability_manifest.json` under
  `.work/llm_probe_preflight/<derived-name>/`.
- `--manifest` points to an existing canonical
  `preflight_capability_manifest.json`. The planner validates its contract and
  skips the ingest step.

The raw LLM-probe file is source evidence. The capability manifest, manifest
map, audition output, and operator plan are derived artifacts. The planner
keeps that distinction explicit.

Do not provide both source options. The planner fails closed rather than
choosing a source of truth implicitly.

## Audition Choices

Choose exactly one audition shape:

- `--suite` plans one gated run through `run_model_audition.py` using
  `--preflight-manifest`.
- `--board` plans one gated board run through
  `run_model_audition_board.py` using `--preflight-manifest-map`.

The board runner consumes a model-to-manifest map rather than a single direct
manifest flag. Board plans therefore print a small standard-library command
that would write the existing `zth.preflight_manifest_map.v0.1` shape. The
planner itself does not create that map. The printed sequence includes an
inspection command before the board audition command.

## Plan from Raw LLM-Probe Output

```bash
python3 local_harness/preflight_audition_plan.py \
  --llm-probe-output examples/llm_probe_preflight_fixture/results.json \
  --model local_harness/auditions/models/qwen25_3b_q4_local.json \
  --suite local_harness/auditions/suites/baseline_micro_v0.json \
  --out-dir .work/model_auditions/example_run \
  --print-commands
```

The printed sequence inspects the source, model, and suite; imports the
preflight evidence; inspects the generated capability manifest; prints the
gated audition command; and ends with focused and repository-health checks.

## Plan from an Existing Manifest

```bash
python3 local_harness/preflight_audition_plan.py \
  --manifest .work/llm_probe_preflight/example/preflight_capability_manifest.json \
  --model local_harness/auditions/models/qwen25_3b_q4_local.json \
  --suite local_harness/auditions/suites/baseline_micro_v0.json \
  --out-dir .work/model_auditions/example_run \
  --print-commands
```

This path skips import. It does not skip manifest inspection or gate
validation by the audition runner.

## Plan a Board Audition

```bash
python3 local_harness/preflight_audition_plan.py \
  --manifest .work/llm_probe_preflight/example/preflight_capability_manifest.json \
  --model local_harness/auditions/models/qwen25_3b_q4_local.json \
  --board local_harness/auditions/boards/local_baseline_board_v0.json \
  --out-dir .work/model_auditions/example_board_run \
  --print-commands
```

The printed plan includes the manifest-map preparation and inspection steps
required by the existing board gate. Preflight status is not added to board
scores, comparisons, or rankings.

## Write or Inspect a Plan

By default the planner writes nothing and prints a Markdown plan to standard
output. Use `--print-commands` for a shell-oriented rendering or `--json` for
a deterministic machine-readable rendering.

Write a local Markdown plan only when explicitly requested:

```bash
python3 local_harness/preflight_audition_plan.py \
  --manifest .work/llm_probe_preflight/example/preflight_capability_manifest.json \
  --model local_harness/auditions/models/qwen25_3b_q4_local.json \
  --suite local_harness/auditions/suites/baseline_micro_v0.json \
  --out-dir .work/model_auditions/example_run \
  --write-plan .work/preflight_audition_plans/example.md \
  --print-commands
```

The planner creates the plan file's parent directory but refuses to overwrite
an existing plan. Open the Markdown file, verify every source and derived
path, and review each command before copying any command into a shell.

Usual local evidence roots are:

- `.work/llm_probe_preflight/` for imported preflight evidence and board
  manifest maps;
- `.work/model_auditions/` for audition output;
- `.work/preflight_audition_plans/` for explicitly written local plans.

These ignored local artifacts are not automatically safe to publish. Review
and sanitize any evidence selected for a durable report.

## Validation

Run the focused planner tests:

```bash
python3 -m pytest local_harness/tests/test_preflight_audition_plan.py
```

Then run the repository health checks appropriate to the change:

```bash
python3 local_harness/repo_health_check.py
python3 local_harness/repo_health_check.py --all
```

Passing validation is evidence that the checked contracts behaved as tested.
It does not authorize an audition, promotion, publication, or lifecycle
decision.
