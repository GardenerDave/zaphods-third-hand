# Report Title

- Date: `<YYYY-MM-DD>`
- Report status: `draft|reviewed|superseded`
- Human reviewer: `<NAME_OR_ROLE>`

## Purpose

State the question this report addresses and why the evidence is worth keeping.

## Source / Evidence Inputs

- Source files, manifests, capability cards, run folders, or report inputs:
- Source hashes or stable identifiers, when available:
- Private evidence retained outside the repository:

Use sanitized, package-relative paths or placeholders. Do not include secrets
or private source text.

## Workflow Used

- Workflow or script:
- Configuration/profile:
- Endpoint/model, if applicable and sanitized:
- Output contract or schema version, if applicable:

## Validation Performed

List commands, tests, contract checks, manual inspections, and their outcomes.

```text
<COMMAND>
<RESULT>
```

## Findings

Record factual observations, including useful failures and unexpected results.
Separate observed evidence from interpretation.

## Limitations

State what was not tested, unavailable, private, inferred, or outside scope.
Do not claim production readiness, model suitability, or generality beyond the
evidence.

## Human Decision / Follow-Up

- Decision: `accept evidence|rework|reject|no decision`
- Approved follow-up:
- Separate packet or owner, if any:

This report records the decision; it does not grant authority, move lifecycle
state, accept generated context, or promote or assign a model.

## Sanitization Checklist

- [ ] Removed credentials, tokens, private contacts, and account identifiers.
- [ ] Replaced operator usernames and absolute paths with safe placeholders.
- [ ] Replaced real endpoint hosts/RFC1918 addresses with `<LAN_HOST>`.
- [ ] Reviewed commands, metadata, filenames, excerpts, tables, and links.
- [ ] Preserved factual findings, hashes, scores, and failure modes.
- [ ] Confirmed private `.work/`, `outputs/`, `sources/`, and raw evidence were
      not copied unintentionally.
- [ ] Ran tracked-file sanitization and repository-health checks.
- [ ] Reviewed the final diff manually.
