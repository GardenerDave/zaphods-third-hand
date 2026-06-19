# Management-Team Overview

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md).

## Purpose

The management-team layer gives a human a structured way to ask different roles for scoped help without letting any role take autonomous control.

Use this layer after you are comfortable with the Context Distiller path, or when you already run packet-based supervised execution and need role-specific decomposition, implementation, and review support.

## Authority Model

- Role output is advisory unless an active packet explicitly grants execution authority.
- A role-run evidence note records authority already granted by the active packet; the note grants no new authority.
- Only an explicitly authorized Implementer may edit files, and only files named in the active packet allowlist.
- Manager, Tech Lead, Reviewer, and Integrator outputs remain advisory and do not edit files.
- Humans approve activation, lifecycle movement, acceptance, and follow-up work.

## Manager

For:

- Scoping.
- Decomposition.
- Draft packet content for human review.
- Routing recommendations.
- Status summaries.

Must not:

- Authorize execution.
- Approve or activate packet content.
- Move lifecycle packets.
- Represent draft packet content as queued or active work.
- Edit files.
- Trigger other agents.

## Tech Lead

For:

- Planning.
- Dependencies.
- Risks.
- Verification design.
- Stop conditions.

Must not:

- Implement changes.
- Broaden scope.
- Authorize off-limits edits.
- Edit files.
- Convert plans into execution without an active implementation packet.

## Implementer

For:

- Narrow edits explicitly authorized by the active packet.
- Verification results.
- Blocked reports.

Must not:

- Edit unless the active packet explicitly grants implementation authority.
- Edit outside the active allowlist.
- Invent work.
- Create scripts or automation unless explicitly allowed.
- Move lifecycle packets.

## Reviewer

For:

- Reviewing diffs, evidence, generated outputs, and acceptance criteria.
- Classifying outcomes.
- Identifying risks and test gaps.

Must not:

- Silently fix issues.
- Treat review patches as canonical automatically.
- Edit files; accepted fixes must be routed to an authorized Implementer.

## Integrator

For:

- Handoff assessment.
- Merge/readiness notes.
- Narrow integration recommendations.

Must not:

- Commit.
- Canonicalize context directly; accepted work must be routed to an authorized Implementer.
- Combine unrelated changes.
- Edit files; accepted integration work must be routed to an authorized Implementer.
- Move lifecycle packets.

## Human Authority

Humans remain the authority for:

- Choosing the active packet.
- Choosing the role.
- Approving prompts.
- Granting execution authority through an active packet.
- Reviewing outputs.
- Accepting or rejecting evidence.
- Moving lifecycle state.
- Reviewing and creating lifecycle packet records from draft content.
- Approving file edits.
