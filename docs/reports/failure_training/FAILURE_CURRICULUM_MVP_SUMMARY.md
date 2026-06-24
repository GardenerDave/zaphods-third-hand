# Failure Curriculum MVP Summary

## Status
MVP data loop complete. Full local suite passes: 118 tests.

## What this proves
The branch can turn failed model audition/probe rows into normalized failure events, classify them, build reviewable curriculum candidates, apply explicit review decisions, split accepted/holdout data safely, export chat-style SFT JSONL, write adapter training plans, compare baseline/adapted evaluation summaries, and rank evaluation reports.

## Safety boundary
No generated candidate is training data until explicitly accepted. Holdout-locked rows are evaluation-only. Adapter training is planned but not launched by this branch.

## Major modules
- collect_failures.py
- classify_failures.py
- build_curriculum.py
- apply_reviews.py
- finalize_review.py
- export_sft.py
- train_adapter.py
- evaluate_adapter.py
- compare_cycles.py
- run_cycle.py

## Evidence
pytest: 118 passed.
Branch: failure-curriculum-loop.
Latest doc fix: failure curriculum code fence corrected.
