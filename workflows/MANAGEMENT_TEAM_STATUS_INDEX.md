# Management-Team Status Index

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](../docs/FIRST_SUCCESS.md).

## Purpose

Provide a concise reference for the management-team system state. This index is descriptive only; it does not automate routing, lifecycle movement, role execution, unattended execution, or batched execution.

## Current Approval Level

- Approved usage mode: supervised routed use only.
- All five management-team role prompts are included.
- Human approval is required before each routed role use, activation, lifecycle movement, and future packet creation.
- Role output is advisory unless accepted through human lifecycle review.
- Unattended execution is not approved.
- Batched execution is not approved unless a later approved packet explicitly validates and authorizes it.
- Routing automation and lifecycle automation are not approved.

## Role Prompt Status

- Manager: available for supervised scoping and decomposition.
- Tech Lead: available for supervised planning and verification design.
- Implementer: available for supervised allowlisted edits only.
- Reviewer: available for supervised evidence and diff review.
- Integrator: available for supervised handoff/readiness assessment.

## Supporting Workflow Documents

- Manual routing workflow exists.
- Review-patch acceptance workflow exists.
- Supervised usage rules exist.
- Supervised role-run evidence note format exists.

## Lifecycle State

Use this section to summarize active, queued, completed, failed, blocked, or superseded work in your project.

## Not Approved

- Unattended role execution.
- Batched role execution.
- Routing automation.
- Lifecycle automation.
- Direct packet creation by role output.
- Lifecycle movement by role output.
- File edits by role output unless an active packet explicitly allowlists the file and authorizes the edit.
- Agent triggering by role output.
- Execution authorization by role output.
- Automatic canonical context updates.
- Automatic review-patch acceptance.
- Role-prompt self-modification.
- Broad scaffold creation.

## Recommended Next Steps

- Create a narrow queued packet for the next supervised role use.
- Record role-run evidence inside the active packet.
- Review generated context patches before accepting them.
- Keep unattended and batched execution off until separately validated.

## Stop Conditions

- A role output attempts to expand scope beyond the active packet.
- A role output suggests unattended or batched execution.
- A role output attempts lifecycle movement, packet creation, file edits, canonical context updates, scripts, or automation without explicit active-packet authorization.
- A role output attempts to trigger other agents or authorize execution.
- A role output treats generated outputs or review patches as canonical automatically.
- Repo state contradicts the active packet.
