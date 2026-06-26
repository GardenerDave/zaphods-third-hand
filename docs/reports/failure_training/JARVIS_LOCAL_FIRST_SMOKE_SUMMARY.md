# Jarvis Local-First Failure Curriculum Smoke

Status: completed

## Environment

Host: jarvis
Model: /home/navigator/ai/models/small-auditions/qwen3-1.7b/Qwen_Qwen3-1.7B-Q4_K_M.gguf
Runtime: llama.cpp
Training status: not launched

## Results

- Failure curriculum test suite passed: 118 tests.
- run_cycle completed with 2 failures and 2 candidates.
- Explicit review accepted 1 candidate and left 1 as needs_revision.
- Finalization produced 1 train row and 1 SFT train row.
- Adapter plan was written with launch_policy: manual_only.
- Baseline Qwen3 1.7B strict-JSON inference failed the target contract.
- Placeholder adapted evaluation produced verdict no_change, baseline 0.0, adapted 0.0, delta 0.0.

## Boundary

This smoke proves the local-first evidence loop and training/evaluation seams. It does not claim adapter training or model improvement.
