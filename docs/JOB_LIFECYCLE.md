# Job Lifecycle

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md).

## Purpose

The job lifecycle turns vague work into small, reviewable, auditable steps.

## Lifecycle States

Recommended folders:

```text
job_queue/
active_jobs/
completed_jobs/
failed_jobs/
blocked_jobs/
```

## Queue

Queued packets define work before it starts. They should include:

- Route.
- Objective.
- Scope.
- File allowlist.
- Off-limits files.
- Verification commands.
- Stop conditions.
- Acceptance criteria.

## Activate

Activation is manual. Move a queued packet to active only after human approval. Update the packet status and review notes.

## Execute

Execution must follow the active packet. The agent should stop if:

- Repo state contradicts the packet.
- Required files are missing.
- The task needs files outside the allowlist.
- Verification fails and fixing it would exceed scope.
- The work drifts into automation or scaffold creation.

## Complete

Completion is a separate lifecycle action. Move the active packet to completed, update status, record notes, and mark acceptance criteria as met.

## Fail Or Block

Use failed or blocked states when the packet cannot proceed safely. Record why and what evidence was checked.

## Superseded Work

Superseded work should preserve audit evidence. Do not silently delete stale packets. Mark them clearly and create a packet if lifecycle cleanup needs review.
