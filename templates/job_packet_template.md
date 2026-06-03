# Job Packet: <title>

## Status
- Status: draft
- Created:
- Source context:
- Owner:
- Assigned agent:
- Priority:
- Risk:

Keep this metadata current before assigning the packet.

## Routing Decision

- Route:
- Rationale:
- Requires human approval before activation:
- Safe to batch:
- Blocking dependencies:

Allowed route values: Human Review, Codex / CLI Agent, Aider, Context Distiller, Human Terminal.

Decide routing before moving the packet from `job_queue/` to `active_jobs/`.

## Objective

State one narrow outcome the agent should achieve.

## Background / Context

Include only the context needed to perform the job without rediscovering the project.

## Scope

Define the boundaries of the work. Avoid broad rewrites or opportunistic refactors.

### In Scope

- List the specific behaviors, files, or checks included in this packet.

### Out of Scope

- List nearby work the agent must not perform.

## Files Allowed To Edit

- Provide an explicit file allowlist. The agent should not edit outside this list.

## Files Explicitly Off Limits

- List canonical files, generated outputs, unrelated modules, or other protected files.

## Required Steps

- Give ordered, concrete steps. The agent should stop and report if repo state contradicts these instructions.

## Verification Commands

- List commands that must pass before review. Verify before any commit.

## Expected Outputs

- Describe the files, behavior, or terminal results expected from the job.

## Failure / Stop Conditions

- Define conditions that require stopping instead of guessing, expanding scope, or rewriting broadly.

## Review Notes

- Capture risks, assumptions, or reviewer focus areas.

## Acceptance Criteria

- Define the exact conditions for accepting the job as complete.

## Commit Guidance

- Do not commit until verification passes and the diff has been reviewed. Commit only the intended files.
