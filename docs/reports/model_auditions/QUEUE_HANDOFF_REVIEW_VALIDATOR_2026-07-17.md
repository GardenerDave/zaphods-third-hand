# Queue Handoff Review Validator 2026-07-17

This report records the fail-closed validator for the design-only queue
handoff review artifact.

## Source Spec

- `docs/QUEUE_HANDOFF_REVIEW.md`

## Validator Path

- `local_harness/validate_queue_handoff_review.py`

## Schema Name

- `queue_handoff_review_v1`

## Allowed Statuses

- `approved_for_queue_candidate`
- `rejected_for_queue`
- `needs_repair_before_queue_review`

## Non-Authoritative Lifecycle Statuses

The validator requires these exact non-authoritative lifecycle statuses:

- `automation_status: not_automated`
- `queue_handoff_status: not_inserted`
- `repo_mutation_status: not_authorized`
- `downstream_use_status: prohibited_until_review`

## Tests Run

- `python3 -m pytest tests/test_validate_queue_handoff_review.py`
- `python3 -m pytest tests/test_validate_queue_handoff_review.py tests/test_review_front_door_chain.py tests/test_score_front_door_chain.py`
- `python3 -m pytest tests/test_front_door_chain_diverse_fixtures.py tests/test_front_door_chain_blocked_fixtures.py tests/test_validate_front_door_chain.py tests/test_validate_queue_handoff_review.py`

## What This Proves

- A queue-handoff review artifact can be validated deterministically.
- The validator fails closed on malformed JSON, wrong schemas, unsafe
  lifecycle language, and missing authority terms.
- Approval, rejection, and repair statuses can be checked without queue
  writing.

## What Remains Unimplemented

- Queue insertion.
- Queue writing.
- Router automation.
- Automatic queue handoff.
- Unattended execution.
- Repo mutation.
- Fixture import.
- Training capture.
- Prompt patch promotion.
- Deployment.
- Downstream-use authority.

## Authority Boundary

This validator is evidence-only and review-only. It does not authorize
routing, queue insertion, repo mutation, fixture import, training capture,
promotion, deployment, or downstream use.
