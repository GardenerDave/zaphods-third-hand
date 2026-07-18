# Front Door Chain Review Command 2026-07-17

This report records the read-only wrapper that validates and scores the full
front-door chain in one command.

## Source Report

- `docs/reports/model_auditions/FRONT_DOOR_CHAIN_SCORECARD_2026-07-17.md`

## Command Path

- `local_harness/review_front_door_chain.py`

## What It Wraps

- `local_harness/validate_front_door_chain.py`
- `local_harness/score_front_door_chain.py`

## Tests Run

- `python3 -m pytest tests/test_review_front_door_chain.py`
- `python3 -m pytest tests/test_validate_front_door_chain.py tests/test_score_front_door_chain.py tests/test_review_front_door_chain.py`

## Interpretation

The wrapper is a convenience command only. It validates the triage, bounded
task, and review packets, then scores review readiness without queue handoff,
repo mutation, fixture import, training capture, promotion, deployment, or
downstream-use authority.

## Authority Boundary

The wrapper is read-only and review-only. It does not grant router automation,
automatic queue handoff, repo mutation authority, fixture import authority,
training capture authority, promotion authority, deployment authority, or
downstream-use authority.

## Next Recommended Supervised Step

Use the wrapper only as a human-review aid. Future work, if any, should stay
focused on scoring calibration and supervised queue-handoff review.
