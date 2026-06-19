# Supervised Role-Run Evidence Note Format

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](../docs/FIRST_SUCCESS.md).

## Purpose

Define the standard evidence note format for supervised management-team role
runs. Role output is advisory unless an active packet explicitly grants
authority. The evidence note records authority already granted; it does not
create, expand, or transfer authority.

## Recording Location

- Normally record role-run evidence inside the active job packet.
- Use a separate note file only when the active packet explicitly allows that path.
- Do not treat a role-run note as authorization for lifecycle movement, file edits, canonical updates, batching, or unattended execution.
- An authorized Implementer may record allowlisted edits in the note, but the authority comes from the active packet, not the note.

## Evidence Note Template

```markdown
## Supervised Role-Run Evidence Note

- Role used:
- Source prompt file:
- Active job packet:
- Human supervisor:
- Date:
- Purpose of role run:
- Authority source:
- Authority granted by active packet:
- Authorized file allowlist:
- Inputs reviewed:
- Output summary:
- Recommendations:
- Explicit non-authorizations:
- Actions performed under granted authority:
- Files changed:
- Stop conditions encountered:
- Follow-up packet candidates:
- Human decision:
```

## Advisory Limits

Role output must not:

- Claim or infer authority not explicitly granted by the active packet.
- Move lifecycle packets.
- Approve or activate packets.
- Turn Manager draft content into a queued or active packet.
- Approve unattended execution.
- Approve batched execution.
- Canonicalize context.
- Trigger other agents.

Manager, Tech Lead, Reviewer, and Integrator outputs are advisory and do not
edit files. A Manager may draft packet content for human review but may not
activate, approve, move, or authorize lifecycle transitions.

An Implementer may edit only when the active packet explicitly grants
implementation authority, and then only inside its file allowlist.

Any recommended next action requires separate human approval and, when it is
new work, a separate lifecycle packet.

## Required Non-Authorizations

Each evidence note should identify the active packet authority and state when
applicable that the role output did not authorize:

- File edits beyond the active packet's explicit Implementer authority.
- Lifecycle movement.
- Packet approval or activation.
- Canonical context updates beyond explicit Implementer authority.
- Generated output or review patch edits beyond explicit Implementer authority.
- Scripts or automation.
- Unattended execution.
- Batched execution.

## Do Not

- Do not use an evidence note to grant authority retroactively.
- Do not describe a Manager draft as an approved, queued, or active packet.
- Do not describe advisory recommendations as execution authorization.
- Do not omit the active packet and allowlist when an Implementer changed files.
- Do not treat advisory role output as approval.
