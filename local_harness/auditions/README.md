# ZTH Model Auditions

Model auditions are a repeatable way to test local or remote OpenAI-compatible models without turning the result into an automatic deployment decision.

A model audition asks:

> If several models receive the same prompts, fixtures, scorer rules, and board, how do their outputs compare?

The answer is saved as plain files so a human can inspect the evidence.

## Choose an Audition Workflow

This directory is the board/capability-card audition workflow. Use it for
suites, fixtures, scorer profiles, multi-suite boards, capability cards,
capability-card comparisons, and optional preflight gates.

For exploratory small-model work that downloads GGUFs, manages temporary local
llama.cpp servers in tmux, calls existing local/LAN endpoints, preserves raw
prompt responses, and applies mechanical exploratory scoring, use
[`local_harness/model_auditions/`](../model_auditions/README.md).

Of the two audition workflows, only this board/capability-card workflow
consumes preflight manifests. The small-model exploratory harness does not
currently consume preflight gates. The two workflows write different schemas;
prefer
`.work/model_auditions/board_runs/` here and
`.work/model_auditions/exploratory_runs/` for the small-model harness.

Neither workflow promotes, approves, assigns, or production-certifies a model.

## In Plain English

A model audition is a structured interview for an AI model.

Instead of asking, "Is this model good?", ZTH asks smaller questions:

- Can it return valid JSON?
- Can it follow a small schema?
- Can it classify a task into the expected label?
- Can it extract grounded facts without inventing details?
- Can it produce a small code patch plan?
- How long did it take?
- What failure modes appeared?

The result is not a production role assignment. It is a candidate fit signal.

## Core Shape

Single-suite audition:

    model + suite + prompt_file + fixtures_file + scorer_profile = audition_run

Multi-suite board run:

    model + board = board_run

Comparison report:

    board_capability_card + board_capability_card = comparison_report

## Key Terms

| Term | Meaning |
|---|---|
| Model | The local or remote OpenAI-compatible endpoint being tested. |
| Prompt file | The instruction template sent to the model. |
| Fixture file | The JSONL test cases used by a suite. |
| Scorer profile | Deterministic scoring rules and weights. |
| Suite | One group of related test cases, such as routing or extraction. |
| Board | A group of suites run against the same model. |
| Capability card | The summary of one model run. |
| Comparison report | A side-by-side comparison of existing capability cards. |
| Failure mode | A named signal describing what went wrong. |

## What This Does Not Do

Model auditions do not:

- assign production roles;
- decide that a model is "the router" or "the coder";
- call a judge model;
- modify your repository;
- start, stop, or download models for this board/capability-card workflow;
- automatically accept generated outputs.

A human reviews the evidence and decides what to do next.
For optional exploratory GGUF download and temporary local llama.cpp lifecycle
support, use the separate
[`local_harness/model_auditions/`](../model_auditions/README.md) harness. That
support is not production model-server management or model promotion.

## Run an Explicit Endpoint

Use this when you know the model id and endpoint URL.

    python3 local_harness/run_model_audition.py \
      --model-id "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M" \
      --base-url "http://<LAN_HOST>:8082/v1" \
      --api-key "not-needed-for-local" \
      --suite "local_harness/auditions/suites/baseline_micro_v0.json" \
      --out-dir ".work/model_auditions/board_runs/qwen25_3b_baseline_micro"

Replace `<LAN_HOST>` with an authorized host from private configuration. Do not
commit a real internal address.

## Run a Model Registry File

Use this when a model config file already records the model id, endpoint, and API-key behavior.

    python3 local_harness/run_model_audition.py \
      --model local_harness/auditions/models/qwen25_3b_q4_local.json \
      --suite local_harness/auditions/suites/baseline_micro_v0.json \
      --out-dir .work/model_auditions/board_runs/qwen25_3b_baseline_micro

The model file may provide:

- `model_id`
- `base_url`
- `api_key_env`
- `api_key_default`

Explicit CLI arguments override the model registry file.
Bundled LAN-oriented model files use `<LAN_HOST>` and must be edited privately
before use.

## Optional Preflight Gate

`run_model_audition.py` can optionally check a completed LLM-probe preflight
capability manifest before creating audition output or calling a model:

    python3 local_harness/run_model_audition.py \
      --model local_harness/auditions/models/qwen25_3b_q4_local.json \
      --suite local_harness/auditions/suites/baseline_micro_v0.json \
      --preflight-manifest .work/llm_probe_preflight/example/preflight_capability_manifest.json \
      --out-dir .work/model_auditions/board_runs/qwen25_3b_baseline_micro

Preflight gating is optional. Without `--preflight-manifest`, existing audition
behavior is unchanged.

The gate reads `preflight_capability_manifest.json` directly. It does not read
the optional OKF export and does not run LLM-probe.

Gate rules:

- `pass`: the model may enter the audition;
- `intermittent`: blocked unless `--allow-intermittent-preflight` or a waiver is provided;
- `unknown`: blocked unless `--allow-unknown-preflight` or a waiver is provided;
- `fail`: blocked unless `--waive-preflight "human-readable reason"` is provided;
- missing or malformed manifests: fail closed.

Any override is recorded under `preflight_gate` in `run_metadata.json`.
A preflight pass means only that the audition may run. It does not promote,
approve, assign, or rank the model. A waiver also does not promote the model.

## Run a Board

Use a board when you want to test one model across several suites.

    python3 local_harness/run_model_audition_board.py \
      --model local_harness/auditions/models/qwen25_3b_q4_local.json \
      --board local_harness/auditions/boards/local_baseline_board_v0.json \
      --out-dir .work/model_auditions/board_runs/qwen25_3b_board

Board runs can optionally select the model's preflight manifest from a JSON map:

    python3 local_harness/run_model_audition_board.py \
      --model local_harness/auditions/models/qwen25_3b_q4_local.json \
      --board local_harness/auditions/boards/local_baseline_board_v0.json \
      --preflight-manifest-map .work/llm_probe_preflight/preflight_manifest_map.json \
      --out-dir .work/model_auditions/board_runs/qwen25_3b_board

Manifest-map shape:

```json
{
  "schema_version": "zth.preflight_manifest_map.v0.1",
  "models": {
    "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M": "qwen25_3b/preflight_capability_manifest.json"
  }
}
```

Map paths are resolved relative to the map file. The board matches the current
model by model ID, model registry `model_ref`, or model-config filename stem.
The selected manifest and the same direct-audition overrides are passed to
every suite. Each suite records the decision in its own `run_metadata.json`.

When a map is supplied, a missing model entry fails closed unless
`--allow-missing-preflight-manifest` is explicit. Intermittent, unknown, and
failed statuses follow the same override and waiver rules as direct auditions.

The board gate uses `preflight_capability_manifest.json`, not OKF output.
Gating decides whether the board audition may run; preflight status is not
included in suite scores, board scores, comparisons, or rankings. Passing or
waiving the gate never promotes the model.

The board writes one board-level capability card:

    .work/model_auditions/board_runs/qwen25_3b_board/board_capability_card.json

## Compare Existing Board Cards

Use comparison reporting after you have two or more board capability cards.

    python3 local_harness/compare_model_auditions.py \
      --cards \
        .work/model_auditions/board_runs/qwen25_3b_board/board_capability_card.json \
        .work/model_auditions/board_runs/qwen25_coder7b_board/board_capability_card.json \
      --out-dir .work/model_audition_comparisons/qwen3b_vs_coder7b

The comparison script does not rerun models. It only reads existing cards and writes:

- `comparison.json`
- `comparison.md`

## Override Prompt, Fixture, or Scorer Files

Use overrides when you want to test a different prompt, fixture set, or scoring profile without changing the suite file.

    python3 local_harness/run_model_audition.py \
      --model local_harness/auditions/models/qwen25_3b_q4_local.json \
      --suite local_harness/auditions/suites/baseline_micro_v0.json \
      --prompt-file local_harness/auditions/prompts/routing_v0.md \
      --fixtures-file local_harness/auditions/fixtures/routing_micro_v0.jsonl \
      --scorer-profile local_harness/auditions/scorers/routing_basic_v0.json \
      --out-dir .work/model_auditions/board_runs/qwen25_3b_override_probe

Path rules:

- Suite-relative paths are resolved relative to the suite file.
- Board-relative suite paths are resolved relative to the board file.
- CLI-provided paths are resolved relative to the current working directory.

## Outputs

A single-suite audition writes:

    out_dir/
    ├── run_metadata.json
    ├── case_manifest.jsonl
    ├── raw_outputs/
    ├── rendered_prompts/
    ├── scores/
    ├── capability_card.json
    └── capability_card.md

A board audition writes:

    out_dir/
    ├── board_metadata.json
    ├── board_manifest.jsonl
    ├── suites/
    ├── board_capability_card.json
    └── board_capability_card.md

Important files:

| File | Why it matters |
|---|---|
| `raw_outputs/` | Preserves the model/API response. Inspect this before deleting run evidence. |
| `scores/` | Shows deterministic per-case scoring. |
| `case_manifest.jsonl` | Shows which cases completed, failed, or were skipped. |
| `capability_card.json` | Machine-readable summary for one suite. |
| `board_capability_card.json` | Machine-readable summary for one model across a board. |
| `comparison.md` | Human-readable side-by-side report. |

## Interpreting Capability Cards

Important fields include:

- `overall`
- `case_count`
- `completed_count`
- `failed_count`
- `metric_averages`
- `failure_modes`
- `runtime`
- `suite_scores`

A high score means the model did well on the tested probes. It does not prove the model is ready for production use.

A failure mode is a clue, not a verdict. For example:

- `json_parse_failed` may mean the prompt needs stricter JSON instructions.
- `expected_field_mismatch` may mean the model chose the wrong label.
- `expected_contains_missing` may mean the answer omitted a required term.
- `runtime_over_target` may mean the model is too slow for the current profile.
- `empty_output` may mean the endpoint returned no final answer content.

## How to Use ChatGPT With Audition Results

Paste a capability card, score file, raw output, or comparison report into ChatGPT and ask:

- What failed?
- Is this a model problem, prompt problem, scorer problem, or runtime problem?
- What should I inspect before deleting `.work`?
- Should this be committed as a report?
- What is the smallest safe next test?

This works especially well when a model looks bad at first glance. Sometimes the real issue is a prompt, timeout, output-channel, or server-template mismatch.

## Offline Dry Run

Use `--dry-run` to test file resolution and output layout without calling a live model endpoint.

    python3 local_harness/run_model_audition.py \
      --model local_harness/auditions/models/qwen25_3b_q4_local.json \
      --suite local_harness/auditions/suites/baseline_micro_v0.json \
      --out-dir .work/model_auditions/board_runs/dry_run_baseline_micro \
      --dry-run

## Available Micro Suites

| Suite | Purpose |
|---|---|
| `baseline_micro_v0` | Mixed small probes. |
| `coding_micro_v0` | Deterministic code patch planning probes. |
| `routing_micro_v0` | Label classification probes. |
| `extraction_micro_v0` | Grounded extraction probes. |

The files are intentionally small so 1B to 3B local models can run them quickly.

## Preserving Useful Results

`.work/` is local run evidence and is normally disposable.

Before deleting it, inspect useful failures or comparison results. If a run is worth preserving, copy the important cards and reports under:

    docs/reports/

Committed reports are evidence snapshots. They are useful for future comparison, but they are still not production role assignments.
