# Management-Team Overview

## Purpose

The management-team layer gives a human a structured way to ask different roles for scoped help without letting any role take autonomous control.

Use this layer after you are comfortable with the Context Distiller path, or when you already run packet-based supervised execution and need role-specific decomposition, implementation, and review support.

## Manager

For:

- Scoping.
- Decomposition.
- Routing recommendations.
- Status summaries.

Must not:

- Authorize execution.
- Move lifecycle packets.
- Edit files unless explicitly allowed.
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
- Convert plans into execution without an active implementation packet.

## Implementer

For:

- Narrow edits to explicitly allowlisted files.
- Verification results.
- Blocked reports.

Must not:

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
- Edit files unless explicitly allowed.

## Integrator

For:

- Handoff assessment.
- Merge/readiness notes.
- Narrow integration recommendations.

Must not:

- Commit.
- Canonicalize context without approval.
- Combine unrelated changes.
- Move lifecycle packets without approval.

## Human Authority

Humans remain the authority for:

- Choosing the active packet.
- Choosing the role.
- Approving prompts.
- Reviewing outputs.
- Accepting or rejecting evidence.
- Moving lifecycle state.
- Creating follow-up packets.
- Approving file edits.
