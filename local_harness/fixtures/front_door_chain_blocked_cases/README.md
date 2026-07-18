# Front Door Chain Blocked Cases

This fixture pack provides blocked and invalid front-door cases for
calibration.

## Purpose

Exercise the review wrapper against packets that should not be treated as
ready for human review.

## Case List

- `triage_missing_review_required_001` - triage packet missing `review_required`.
- `bounded_task_queue_inserted_001` - bounded task packet with queue handoff already inserted.
- `review_repo_mutation_authorized_001` - review packet with repo mutation authorized.
- `missing_authority_boundary_term_001` - packet missing `no_downstream_use_authority`.
- `malformed_review_packet_001` - malformed review packet.

## Expected Behavior

The cases are expected to return `blocked` or `invalid` and nonzero exit codes.
They must not be ready for human review.

## Command Example

```bash
python3 local_harness/review_front_door_chain.py \
  --triage-packet local_harness/fixtures/front_door_chain_blocked_cases/triage_missing_review_required_001.triage_packet.json \
  --bounded-task-packet local_harness/fixtures/front_door_chain_blocked_cases/triage_missing_review_required_001.bounded_task_packet_draft.json \
  --review-packet local_harness/fixtures/front_door_chain_blocked_cases/triage_missing_review_required_001.review_packet.json
```

## Authority Boundary

The fixture cases are evidence only. They do not authorize queue insertion,
repo mutation, fixture import, training capture, promotion, deployment, or
downstream use.
