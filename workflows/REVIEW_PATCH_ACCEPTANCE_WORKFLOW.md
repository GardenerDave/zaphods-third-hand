# Review Patch Acceptance Workflow

## Purpose

Review context patches, decide whether proposed updates should influence canonical context, and record outcomes manually.

Review patches are not canonical automatically. This workflow does not modify canonical context.

## Outcomes

- Accepted: patch is approved as valid source for future canonical context updates.
- Rejected: patch should not be used.
- Superseded: patch was replaced by a later or better patch.
- Needs Rework: patch contains useful signal but needs correction before acceptance.

## Review Checklist

- Does the patch match the source/session?
- Does it avoid invented facts?
- Are decisions, bugs, rules, preferences, and next actions correctly classified?
- Does it distinguish durable context from transient troubleshooting?
- Does it avoid treating failed or diagnostic runs as successful evidence?
- Does it preserve human corrections?

## Acceptance Note Format

```markdown
# Review Patch Acceptance Note

- Patch:
- Source ID:
- Outcome:
- Reviewed by:
- Review date:
- Evidence checked:
- Notes:
- Canonical files to update later:
- Follow-up job packet:
```

## Manual Process

1. Read the session file.
2. Read the review patch.
3. Compare against source/run evidence if needed.
4. Choose one outcome.
5. Record an acceptance note in an approved review location.
6. Only then create a separate job packet for canonical context updates, if needed.

## Do Not

- Do not treat a review patch as canonical automatically.
- Do not edit canonical context during review unless a separate approved job packet allows it.
- Do not delete rejected or superseded patches if they preserve useful audit evidence.
- Do not accept patches generated from failed or malformed distiller outputs without correction.
- Do not merge broad context updates without human review.
