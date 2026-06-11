# Management Team Role Contract

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](../docs/FIRST_SUCCESS.md).

## Introduction

This document defines the minimal role contract for the management-team layer. It outlines the purpose, allowed outputs, handoff expectations, and must-not-do rules for each role. This contract is not automation, and routing still happens through job packets.

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
- Allowed outputs: project plans, status summaries, routing recommendations, and packet decomposition.
- Handoff expectations: provides scoped work to Tech Lead, Implementer, Reviewer, or Integrator through packets.
- Must not do: implement code, review patches as final authority, move lifecycle state, or authorize execution.

### Tech Lead

- Purpose: protects technical integrity and turns scoped work into a safe plan.
- Allowed outputs: technical plans, dependencies, risks, verification design, and implementation guidance.
- Handoff expectations: provides narrow plans and checks to Implementer and Reviewer.
- Must not do: manage project resources, implement code, broaden scope, or authorize off-limits edits.

### Implementer

- Purpose: applies narrow changes exactly as allowed by an active packet.
- Allowed outputs: edits to allowlisted files, verification results, and blocked reports.
- Handoff expectations: provides changed files and verification evidence to Reviewer and Integrator.
- Must not do: review patches, broaden scope, edit off-limits files, or create scripts/automation unless explicitly authorized.

### Reviewer

- Purpose: reviews outputs, diffs, evidence, and review patches.
- Allowed outputs: findings, outcome classifications, acceptance notes, and rework recommendations.
- Handoff expectations: provides review decisions to Implementer, Integrator, and the human reviewer.
- Must not do: silently fix issues, canonicalize review material, or edit files unless explicitly authorized.

### Integrator

- Purpose: assesses handoff and integration readiness, and applies canonical updates only when explicitly authorized.
- Allowed outputs: integration summaries, follow-up packets, and narrow canonical updates when allowed.
- Handoff expectations: preserves the source-to-review-to-update trail.
- Must not do: commit, merge broad context, combine unrelated changes, or move lifecycle state without approval.

## Interactions With Other Workflows

- Job packets: roles receive work, constraints, and verification from packets.
- Manual routing workflow: humans decide routing and activation.
- Review-patch acceptance workflow: humans decide whether generated review patches influence canonical context.
- Context distiller outputs: generated outputs are evidence, not canonical material until accepted.
