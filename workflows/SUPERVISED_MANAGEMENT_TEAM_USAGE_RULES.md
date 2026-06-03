# Supervised Management-Team Usage Rules

## Purpose

Define how management-team role prompts may be used safely in supervised routed development without approving unattended execution, batching, automation, or broad scaffold creation.

## Current Approval Level

- Management-team role prompts are accepted for supervised routed use.
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
- No scripts or automation unless a separate approved packet allows them.

## Required Human Supervision

- Human selects the active packet.
- Human selects the role.
- Human submits or approves the role prompt.
- Human reviews role output before any file changes.
- Human decides whether outputs become job notes, follow-up packets, or rejected material.

## Packet Routing Requirements

- Every role use must reference an active job packet.
- The packet must name route, objective, allowed files, off-limits files, verification commands, and stop conditions.
- Role output cannot expand scope.
- Role output cannot override packet restrictions.
- Any new work must become a separate queued packet.

## Role Invocation Rules

- Manager: may triage, scope, and decompose work; must not authorize execution or edit files.
- Tech Lead: may plan architecture and implementation strategy; must not edit files or broaden scope.
- Implementer: may propose or apply changes only inside the active packet allowlist and only when explicitly routed to do so.
- Reviewer: may review evidence, diffs, and outputs; must not modify files unless a packet explicitly allows it.
- Integrator: may propose merge sequencing and handoff notes; must not merge canonical context or lifecycle packets without approval.

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

- Do not edit role prompts without a packet that explicitly allows it.
- Do not create scripts.
- Do not create automation.
- Do not edit canonical context.
- Do not edit generated outputs or review patches.
- Do not move lifecycle packets unless the active packet allows it.
- Do not create broad scaffold.
