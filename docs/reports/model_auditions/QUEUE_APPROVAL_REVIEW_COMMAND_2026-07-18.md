# Queue Approval Review Command

## Purpose

Record the addition of a read-only queue approval review command that wraps
`queue_approval_path_v1` validation and emits an explicit review artifact only.

## Command Path

- `local_harness/review_queue_approval_path.py`

## Input Schema

- `queue_approval_path_v1`

## Output Schema

- `queue_approval_path_review_v1`

## Review Status Mapping

- `approved_for_manual_queue_insertion_candidate` →
  `ready_for_manual_queue_insertion_review`
- `rejected_before_queue_insertion` →
  `rejected_before_queue_insertion`
- `needs_repair_before_queue_insertion_review` →
  `needs_repair_before_queue_insertion_review`
- validation failure →
  `blocked_needs_repair`

## Output Path Safety

The command refuses output paths that:

- are the same as the input path
- are existing directories
- live under `queue/` or `queues/`
- live under `.work/queues/`
- live under `local_harness/fixtures/`

The command may write an explicit review artifact to a manually supplied
review path such as a temp file or report path, but it does not write queues,
insert queue items, or use queue-like paths.

## Validation Commands

- `python3 local_harness/review_queue_approval_path.py <input> <output>`
- `python3 -m pytest tests/test_review_queue_approval_path.py`

## What Remains Unimplemented

- queue insertion
- queue writing
- queue running
- automatic queue handoff
- router automation
- repo mutation
- fixture import
- training capture
- promotion
- deployment
- downstream-use authority

## Authority Boundary

This command is evidence-only and review-only. It does not authorize queue
insertion, queue writing, queue running, automatic handoff, router automation,
repo mutation, fixture import, training capture, promotion, deployment, or
downstream use.
