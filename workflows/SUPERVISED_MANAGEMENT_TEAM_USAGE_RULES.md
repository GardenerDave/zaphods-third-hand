# Supervised Management-Team Usage Rules

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](../docs/FIRST_SUCCESS.md).

## Purpose

Define how management-team role prompts may be used safely in supervised routed development without approving unattended execution, batching, automation, or broad scaffold creation.

## Current Approval Level

- Management-team role prompts are accepted for supervised routed use.
- Role output is advisory unless an active packet explicitly grants authority.
- A role-run evidence note records authority already granted and grants no new authority.
- Only an explicitly authorized Implementer may edit allowlisted files.
- They are not approved for unattended execution.
- They are not approved for batched execution.
- Human approval is required before each routed role use.

## Allowed Use

- Use roles only through an active job packet.
- Use roles for narrow, scoped planning, review, or implementation assistance.
- Use one role at a time unless a packet explicitly authorizes a sequence.
- Keep a human in the loop for prompt submission, output review, and acceptance.
- Preserve file allowlists, off-limits files, verification commands, and stop conditions from the active packet.

## Prohibited Use

- No unattended execution.
- No batched execution.
- No autonomous lifecycle movement.
- No automatic canonical context updates.
- No automatic review-patch acceptance.
- No broad scaffold creation.
- No role-prompt self-modification.
- No scripts or automation unless a separate active packet explicitly routes the work to an authorized Implementer.

## Required Human Supervision

- Human selects the active packet.
- Human selects the role.
- Human submits or approves the role prompt.
- Human grants any implementation authority through the active packet before file changes.
- Human reviews role output and any resulting Implementer changes.
- Human decides whether outputs become job notes, follow-up packets, or rejected material.
- Human approves activation and performs lifecycle movement.

## Packet Routing Requirements

- Every role use must reference an active job packet.
- The packet must name route, objective, allowed files, off-limits files, verification commands, and stop conditions.
- Any Implementer edit authority must be explicit in the active packet.
- Role output cannot expand scope.
- Role output cannot override packet restrictions.
- Manager output may draft packet content, but a human must create or update the lifecycle record.
- Any new work must become a separate human-reviewed packet.

## Role Invocation Rules

- Manager: may triage, scope, decompose work, and draft packet content; must not edit files, authorize execution, approve or activate packets, or move lifecycle state.
- Tech Lead: may plan architecture and implementation strategy; must not edit files or broaden scope.
- Implementer: may apply changes only when the active packet explicitly grants implementation authority and only inside its allowlist.
- Reviewer: may review evidence, diffs, and outputs; must not modify files.
- Integrator: may propose merge sequencing, canonical updates, and handoff notes; must not modify files or lifecycle packets.

## Evidence To Record

- Active packet path.
- Role used.
- Prompt/input summary.
- Output summary.
- Files changed, if any.
- Verification run, if any.
- Human decision.
- Follow-up packet needed, if any.

## Stop Conditions

- Role output asks to edit off-limits files.
- A non-Implementer role attempts to edit files.
- An Implementer attempts edits without explicit active-packet authority.
- Role output expands scope beyond packet.
- Role output suggests automation or batching.
- Role output attempts canonical context changes without an approved packet.
- Role output conflicts with source evidence or human correction.
- Verification fails.
- Repo state contradicts packet assumptions.

## Promotion Path

- Supervised-only usage remains the default.
- Batched use requires separate smoke tests and explicit approval.
- Unattended use requires separate design, risk review, validation, and human approval.
- Passing one smoke test does not authorize unattended or batched operation.

## Do Not

- Do not edit role prompts except through an explicitly authorized Implementer and active-packet allowlist.
- Do not create scripts or automation through advisory role output.
- Do not edit canonical context, generated outputs, or review patches except through an explicitly authorized Implementer and active-packet allowlist.
- Do not move lifecycle packets through role output.
- Do not create broad scaffold.
