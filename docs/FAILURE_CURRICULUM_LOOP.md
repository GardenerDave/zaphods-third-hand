# Failure Curriculum Loop

The failure curriculum loop turns failed model audition/probe rows into supervised training artifacts.

It is intentionally conservative:

- failed rows become normalized `failure_event` records
- failures are classified by deterministic rules
- classified failures become curriculum candidates
- candidates must be reviewed before training
- only `accepted` rows may enter train/validation datasets
- `holdout_locked` rows are reserved for evaluation and must not be trained on

## Data flow

```text
raw probe rows
  -> failure_events.jsonl
  -> classified_failure_events.jsonl
  -> candidates.jsonl
  -> review split
  -> train / validation / holdout
  -> SFT chat-message exports

## Explicit review flow

Generated candidates are not training data until a reviewer explicitly promotes them.

A review decision file uses JSONL rows with this shape:

```json
{"candidate_id":"candidate_id_here","review_status":"accepted","reviewer":"dave","review_notes":"Gold answer checked."}

## Adapter planning

The current training layer can write an adapter training plan without launching training.

Command:

    python -m local_harness.failure_training.train_adapter \
      --cycle-id cycle_fixture \
      --base-model-id tiny-model \
      --dataset-dir .work/failure_training/cycles/cycle_fixture/finalized/datasets \
      --output-dir .work/failure_training/cycles/cycle_fixture/tuning/adapter_plan \
      --training-method lora \
      --trainer manual \
      --notes "Plan only. No training launched."

This writes:

    tuning/adapter_plan/
      adapter_manifest.json
      trainer_config.json

The generated trainer config uses `launch_policy: manual_only`. This command records intent and paths; it does not start a fine-tune.

## Evaluation reports

After a baseline run and adapted run have result summaries, compare them with:

    python -m local_harness.failure_training.evaluate_adapter \
      --baseline-summary .work/failure_training/cycles/cycle_fixture/evaluation/baseline_summary.json \
      --adapted-summary .work/failure_training/cycles/cycle_fixture/evaluation/adapted_summary.json \
      --output-dir .work/failure_training/cycles/cycle_fixture/evaluation/adapter_eval \
      --cycle-id cycle_fixture \
      --adapter-id adapter_id_here \
      --base-model-id tiny-model \
      --adapted-model-id tiny-model+lora \
      --target-capability strict_json_contract \
      --baseline-run-id baseline_fixture \
      --adapted-run-id adapted_fixture

This writes:

    evaluation/adapter_eval/
      evaluation_report.json
      evaluation_report.jsonl
      evaluation_report.md

The comparator is model-free. It reads recorded numeric summaries and reports improvement, regression, mixed results, no change, or unknown.

## Comparing evaluation reports

Multiple evaluation reports can be ranked with:

    python -m local_harness.failure_training.compare_cycles \
      --reports \
        .work/failure_training/cycles/cycle_a/evaluation/adapter_eval/evaluation_report.json \
        .work/failure_training/cycles/cycle_b/evaluation/adapter_eval/evaluation_report.json \
      --output-dir .work/failure_training/comparisons/example_comparison

This writes:

    comparisons/example_comparison/
      comparison_summary.jsonl
      comparison_rows.jsonl
      comparison_report.md

The comparison reporter ranks reports by verdict and score delta. It is evidence plumbing, not an authority layer.
