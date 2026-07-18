# Queue Approval Path

This document defines the review-only queue approval path that sits after
`queue_handoff_review_v1`.

`queue_approval_path_v1` is a design-only review artifact. It can describe a
manual queue-insertion candidate, but it does not insert queues, write queues,
run queues, automate handoff, mutate repositories, train, promote, deploy, or
grant downstream-use authority.

## Purpose

Define the boundary for a future approval step that may consider a
queue-handoff review result and decide whether the item is a candidate for
manual queue insertion review.

The approval artifact remains evidence only. It does not perform queue
writing, queue insertion, queue running, or routing.

## Where It Sits

The intended sequence is:

1. `messy_input_triage_packet_v1`
2. `bounded_task_packet_draft_v1`
3. `bounded_task_review_packet_v1`
4. `front_door_chain_review_v1`
5. `queue_handoff_review_v1`
6. `queue_approval_path_v1`

The queue approval path is only meaningful when the source queue-handoff
review is already `approved_for_queue_candidate`.

## Schema

Suggested schema fields:

- `approval_schema`
- `source_review_schema`
- `source_review_path`
- `source_queue_handoff_review_status`
- `queue_approval_status`
- `approval_scope`
- `reviewer_note`
- `required_checks`
- `authority_boundary`
- `automation_status`
- `queue_insertion_status`
- `queue_writing_status`
- `repo_mutation_status`
- `downstream_use_status`
- `diagnostics`
- `recommended_next_step`

## Statuses

Design-only queue approval statuses:

- `approved_for_manual_queue_insertion_candidate`
- `rejected_before_queue_insertion`
- `needs_repair_before_queue_insertion_review`

Required non-authoritative lifecycle statuses:

- `automation_status: not_automated`
- `queue_insertion_status: not_inserted`
- `queue_writing_status: not_implemented`
- `repo_mutation_status: not_authorized`
- `downstream_use_status: prohibited_until_review`

## What Approval Does Not Do

Queue approval does not:

- insert a queue item
- write to a queue file
- run a queue
- automate handoff
- mutate a repository
- import fixtures
- capture training
- promote a patch or model
- deploy anything
- grant downstream-use authority

## Manual Candidate Approval

The only approved form is a manual queue-insertion candidate review artifact.
It can say the item is a candidate for later human handling, but it still
cannot write to a queue or authorize automation.

## Authority Boundary

The queue approval path is review-only evidence. It does not authorize
routing, queue insertion, queue writing, queue running, automatic queue
handoff, repo mutation, fixture import, training capture, promotion,
deployment, or downstream use.

## Validator

The fail-closed validator is
[`local_harness/validate_queue_approval_path.py`](../local_harness/validate_queue_approval_path.py).
It validates the review artifact shape and authority boundary without writing
a queue.
