# Management Team Role Contract

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](../docs/FIRST_SUCCESS.md).

## Introduction

This document defines the minimal role contract for the management-team layer. It outlines the purpose, allowed outputs, handoff expectations, and must-not-do rules for each role. This contract is not automation, and routing still happens through job packets.

Role output is advisory unless an active packet explicitly grants authority. A
role-run evidence note records authority already granted and grants no new
authority. Only an explicitly authorized Implementer may edit allowlisted
files. Humans retain packet activation, approval, lifecycle movement, and
acceptance authority.

## Roles

The following roles are defined:

- Manager
- Tech Lead
- Implementer
- Reviewer
- Integrator

## Role Definitions

### Manager

- Purpose: converts goals into scoped, sequenced work.
- Allowed outputs: project plans, status summaries, routing recommendations, packet decomposition, and draft packet content.
- Handoff expectations: provides draft packet content to a human for review and lifecycle placement.
- Must not do: edit files, activate or approve packets, move lifecycle state, authorize execution, or represent draft content as queued or active work.

### Tech Lead

- Purpose: protects technical integrity and turns scoped work into a safe plan.
- Allowed outputs: technical plans, dependencies, risks, verification design, and implementation guidance.
- Handoff expectations: provides narrow plans and checks to Implementer and Reviewer.
- Must not do: manage project resources, implement code, edit files, broaden scope, or authorize off-limits edits.

### Implementer

- Purpose: applies narrow changes exactly as allowed by an active packet.
- Allowed outputs: explicitly authorized edits to active-packet allowlisted files, verification results, and blocked reports.
- Handoff expectations: provides changed files and verification evidence to Reviewer and Integrator.
- Must not do: infer edit authority, review patches, broaden scope, edit off-limits files, move lifecycle state, or create scripts/automation unless explicitly authorized.

### Reviewer

- Purpose: reviews outputs, diffs, evidence, and review patches.
- Allowed outputs: findings, outcome classifications, proposed acceptance-note content, and rework recommendations.
- Handoff expectations: provides review decisions to Implementer, Integrator, and the human reviewer.
- Must not do: silently fix issues, canonicalize review material, or edit files; accepted fixes are routed to an authorized Implementer.

### Integrator

- Purpose: assesses handoff and integration readiness and proposes canonical updates.
- Allowed outputs: integration summaries, draft follow-up packet content, and narrow canonical-update recommendations.
- Handoff expectations: preserves the source-to-review-to-update trail.
- Must not do: edit files, commit, merge broad context, combine unrelated changes, or move lifecycle state; accepted integration work is routed to an authorized Implementer.

## Interactions With Other Workflows

- Job packets: roles receive work, constraints, and verification from packets.
- Manual routing workflow: humans decide routing and activation.
- Review-patch acceptance workflow: humans decide whether generated review patches influence canonical context.
- Context distiller outputs: generated outputs are evidence, not canonical material until accepted.
