# Queue Handoff Review

This document defines the supervised queue-handoff review boundary before any
queue-writing implementation exists.

`ready_for_review` makes a task eligible for queue-handoff review only.

## Purpose

Define the supervised queue-handoff review boundary before any queue-writing
implementation exists.

A front-door review result may make a task eligible for queue-handoff review,
but it must never insert, schedule, execute, mutate, train, promote, deploy,
or grant downstream-use authority by itself.

## Core Rule

A front-door review result may make a task eligible for queue-handoff review,
but it must never insert, schedule, execute, mutate, train, promote, deploy,
or grant downstream-use authority by itself.

## Current Inputs

Queue-handoff review may consider:

- `front_door_chain_review_v1`
- `review_status: ready_for_review`
- chain validation result
- scorecard result
- source triage packet path
- bounded task packet path
- review packet path
- allowed targets
- held targets
- diagnostics
- validation plan
- repo state or commit reference if available
- reviewer note or explicit approval note

## Proposed Queue-Handoff Review Statuses

These are design-only statuses:

- `approved_for_queue_candidate`
- `rejected_for_queue`
- `needs_repair_before_queue_review`

`approved_for_queue_candidate` does not insert into a queue. It only means the
item may be considered for a later manual queue insertion step.

## Approval Criteria

A queue-handoff review may only approve a queue candidate if:

- front-door review status is `ready_for_review`
- scorecard is ready
- chain validation passed
- diagnostics are empty
- allowed targets are narrow enough
- held targets are explicit
- task summary is concrete
- validation plan is actionable
- authority boundary terms are present
- no queue insertion, repo mutation, training capture, promotion,
  deployment, or downstream use is implied

## Rejection Conditions

Reject if:

- status is `blocked` or `invalid`
- diagnostics are non-empty
- allowed targets are too broad
- held targets include likely actual work
- task summary is vague
- validation plan is weak
- evidence references `.work` in a non-portable way
- action language implies execution, mutation, cleanup, import, merge,
  training, promotion, deployment, or queue insertion
- downstream use is implied

## Repair Conditions

Use `needs_repair_before_queue_review` if:

- allowed targets are plausible but too broad
- evidence needed is vague
- validation plan is too shallow
- task summary is unclear
- held targets are incomplete
- source linkage is valid but not readable enough
- diagnostics are repairable without changing the authority model

## Required Explicit Approval Fields

This section defines a future review artifact shape, but does not implement it.

Suggested future schema name:

- `queue_handoff_review_v1`

Suggested fields:

- `review_schema`
- `source_review_schema: front_door_chain_review_v1`
- `source_review_path`
- `queue_handoff_review_status`
- `approval_scope`
- `reviewer_note`
- `required_checks`
- `authority_boundary`
- `automation_status: not_automated`
- `queue_handoff_status: not_inserted`
- `repo_mutation_status: not_authorized`
- `downstream_use_status: prohibited_until_review`
- `diagnostics`
- `recommended_next_step`

## Non-Goals

This spec does not implement:

- queue insertion
- queue writing
- router automation
- unattended execution
- repo mutation
- fixture import
- training capture
- prompt patch promotion
- deployment
- downstream-use authority

## Future Implementation Requirements

Before any implementation:

- add fail-closed validator for `queue_handoff_review_v1`
- add pass and blocked fixtures
- add tests proving no queue insertion occurs
- add docs/report
- require explicit approval for any future queue-writing command
- keep queue insertion manual until a separately reviewed implementation exists

## Authority Boundary

This spec is design-only and does not authorize routing, queue insertion, repo
mutation, fixture import, training capture, promotion, deployment, or
downstream use.
