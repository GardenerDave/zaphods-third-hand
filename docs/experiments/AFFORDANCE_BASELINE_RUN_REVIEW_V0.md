# Affordance Baseline Run Review v0

Status: experimental model-free review record

Affordance Baseline Run Review v0 records operator review/adjudication of a
completed baseline prompt-context run.

This is review only. It does not call a model, rerun the baseline, modify the
original run report, apply LARQL, train LoRA, mutate model weights, write
durable memory, run a comparison lane, or promote the candidate.

## Purpose

The review exists after a baseline run has produced:

```text
baseline_lane_result_report.json
post_run_audit_report.md
```

It preserves the original run verdict and classifies review flags into
mechanical scorer false negatives, model weaknesses, true failures, passes, or
not-reviewed items.

## Inputs

- `baseline_lane_result_report.json`
- `post_run_audit_report.md`
- operator summary

The run report must preserve held promotion, verified candidate digest,
verified prompt-suite digest, and baseline selected lane.

## Outputs

The helper writes:

```text
baseline_run_review.json
baseline_run_review.md
```

## Review verdicts

- `baseline_review_accepts_needs_review_evidence`
- `baseline_review_requires_scorer_repair`
- `baseline_review_requires_prompt_repair`
- `baseline_review_rejects_run`
- `invalid_input`

The promotion verdict is always:

```text
hold_pending_explicit_experiment_approval
```

## Prompt adjudication labels

- `scorer_false_negative`
- `model_weakness`
- `true_failure`
- `pass`
- `not_reviewed`

The v0 heuristics are intentionally narrow. They are designed to preserve a
review record for known baseline run shapes, not to replace operator judgment.

For the structured split-workflow prompt, a response can be a scorer false
negative when it fills the exact labels and uses active-host applicability
language such as `Candidate applies only if: active host is ... and
constraints (...) are met.` That is still review-only evidence, not a formal
pass.

## Recommended next steps

- true failure: `repair_baseline_packet_or_candidate_before_rerun`
- model weakness: `draft_baseline_prompt_or_scorer_repair`
- scorer false negatives only: `draft_scorer_repair`

No review verdict recommends promotion.

## Boundary

The review does not modify the original run report. It does not convert a
failed run into a pass, run a model, apply LARQL, train LoRA, mutate a model,
write durable memory, execute a comparison lane, or promote the candidate.

## Sample command

```bash
python3 local_harness/affordance_baseline_run_review.py \
  --run-report .work/affordance_baseline_runs/navigator_cuda_baseline_v1/baseline_lane_result_report.json \
  --post-run-audit .work/affordance_baseline_runs/navigator_cuda_baseline_v1/post_run_audit_report.md \
  --out .work/affordance_baseline_run_reviews/navigator_cuda_baseline_v1 \
  --operator-summary "Baseline run completed with all model calls OK and boundaries preserved. Most review flags are scorer wording false negatives; split workflow active-host answer remains a real weak answer requiring prompt/scorer follow-up."
```
