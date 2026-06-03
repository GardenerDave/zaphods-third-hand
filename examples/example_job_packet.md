# Job Packet: Example Tiny Documentation Update

## Status
- Status: draft
- Created:
- Source context: example packet
- Owner:
- Assigned agent:
- Priority: low
- Risk: low

## Routing Decision

- Route: Codex / CLI Agent
- Rationale: Narrow documentation edit with explicit file allowlist.
- Requires human approval before activation: yes
- Safe to batch: no
- Blocking dependencies: target file must exist.

## Objective

Add one sentence to a documentation file explaining a completed decision.

## Scope

### In Scope

- Edit one allowlisted documentation file.
- Run the verification commands.

### Out of Scope

- Editing role prompts.
- Editing generated outputs.
- Creating scripts or automation.
- Moving lifecycle packets.

## Files Allowed To Edit

- `<REPO_ROOT>/docs/example.md`

## Files Explicitly Off Limits

- source transcripts
- generated outputs
- review patches
- role prompts
- scripts

## Verification Commands

```bash
git status --short <REPO_ROOT>/docs/example.md
git diff -- <REPO_ROOT>/docs/example.md
```

## Failure / Stop Conditions

- Target file is missing.
- Required edit is ambiguous.
- The task requires more than one narrow documentation change.
