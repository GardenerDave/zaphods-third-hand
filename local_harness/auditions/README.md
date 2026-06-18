# ZTH Model Auditions

The model audition harness is a generic, file-driven way to probe local or remote OpenAI-compatible models.

It is not a production role assignment system. A suite score may suggest potential fit signals, but role eligibility belongs to later ZTH or MTNG policy layers.

Core shape:

    model + suite + prompt_file + fixtures_file + scorer_profile = audition_run

## Run an explicit endpoint

    python3 local_harness/run_model_audition.py \
      --model-id "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M" \
      --base-url "http://192.168.1.13:8082/v1" \
      --api-key "not-needed-for-local" \
      --suite "local_harness/auditions/suites/baseline_micro_v0.json" \
      --out-dir ".work/model_auditions/qwen25_3b_baseline_micro"

## Run a model registry file

    python3 local_harness/run_model_audition.py \
      --model local_harness/auditions/models/qwen25_3b_q4_local.json \
      --suite local_harness/auditions/suites/baseline_micro_v0.json \
      --out-dir .work/model_auditions/qwen25_3b_baseline_micro

The model file may provide model_id, base_url, api_key_env, and api_key_default.

Explicit CLI arguments override the model registry file.

## Override prompt, fixture, or scorer files

    python3 local_harness/run_model_audition.py \
      --model local_harness/auditions/models/qwen25_3b_q4_local.json \
      --suite local_harness/auditions/suites/baseline_micro_v0.json \
      --prompt-file local_harness/auditions/prompts/routing_v0.md \
      --fixtures-file local_harness/auditions/fixtures/routing_micro_v0.jsonl \
      --scorer-profile local_harness/auditions/scorers/routing_basic_v0.json \
      --out-dir .work/model_auditions/qwen25_3b_override_probe

Suite-relative paths are resolved relative to the suite file. CLI-provided paths are resolved relative to the current working directory.

## Outputs

Each run writes run_metadata.json, case_manifest.jsonl, raw_outputs/, rendered_prompts/, scores/, capability_card.json, and capability_card.md.

raw_outputs/ preserves model responses. scores/ stores deterministic per-case scoring. capability_card.json aggregates case-level results into a stable machine-readable summary.

## Interpreting capability cards

Important fields include overall, case_count, completed_count, failed_count, metric_averages, failure_modes, and runtime.

These scores are probes. They are useful for comparison, regression tracking, and choosing what to inspect next. They are not final deployment decisions.

## Offline dry run

    python3 local_harness/run_model_audition.py \
      --model local_harness/auditions/models/qwen25_3b_q4_local.json \
      --suite local_harness/auditions/suites/baseline_micro_v0.json \
      --out-dir .work/model_auditions/dry_run_baseline_micro \
      --dry-run

## Available micro suites

baseline_micro_v0: mixed small probes
coding_micro_v0: deterministic code patch planning probes
routing_micro_v0: label classification probes
extraction_micro_v0: grounded extraction probes

The files are intentionally small so 1B to 3B local models can run them quickly.
