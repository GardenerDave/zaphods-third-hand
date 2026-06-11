# Supervised Role-Run Evidence Note Format

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](../docs/FIRST_SUCCESS.md).

## Purpose

Define the standard evidence note format for supervised management-team role runs. Role runs remain supervised only, and role output is advisory unless a human accepts it through the job lifecycle.

## Recording Location

- Normally record role-run evidence inside the active job packet.
- Use a separate note file only when the active packet explicitly allows that path.
- Do not treat a role-run note as authorization for lifecycle movement, file edits, canonical updates, batching, or unattended execution.

## Evidence Note Template

```markdown
## Supervised Role-Run Evidence Note

- Role used:
- Source prompt file:
- Active job packet:
- Human supervisor:
- Date:
- Purpose of role run:
- Inputs reviewed:
- Output summary:
- Recommendations:
- Explicit non-authorizations:
- Files changed:
- Stop conditions encountered:
- Follow-up packet candidates:
- Human decision:
```

## Advisory Limits

Role output must not directly:

- Move lifecycle packets.
- Create packets.
- Edit files.
- Approve unattended execution.
- Approve batched execution.
- Canonicalize context.
- Trigger other agents.

Any recommended next action requires separate human approval and a separate lifecycle packet.

## Required Non-Authorizations

Each evidence note should state when applicable that the role output did not authorize:

- File edits.
- Lifecycle movement.
- New packet creation.
- Canonical context updates.
- Generated output or review patch edits.
- Scripts or automation.
- Unattended execution.
- Batched execution.

## Do Not

- Do not edit role prompts.
- Do not edit canonical context.
- Do not edit generated outputs or review patches.
- Do not modify distiller code.
- Do not create scripts or automation.
- Do not create lifecycle automation.
- Do not treat advisory role output as approval.
