# ZTH Reports

Reports are durable, human-reviewed evidence snapshots.

They preserve selected findings from local runs, model auditions, comparisons,
audits, regressions, and review passes so another person can understand what
was observed without rerunning the original workflow.

Reports do not accept generated context, promote or assign models, authorize
lifecycle movement, approve code changes, or establish production readiness.

## What Belongs in a Durable Report

Commit a report when the evidence has lasting review value, such as:

- a model audition comparison or selected capability card;
- a preflight regression finding;
- a reproducible failure analysis;
- a review or audit summary;
- a meaningful regression snapshot;
- a sanitized summary of an important local run;
- a human decision that needs a traceable evidence record.

A useful report answers:

- What workflow was used?
- What source evidence or configuration was reviewed?
- What validation was performed?
- What was observed?
- What failed or remained uncertain?
- What did a human decide?
- What follow-up, if any, was approved?

Use [`REPORT_TEMPLATE.md`](REPORT_TEMPLATE.md) for new reports unless a
workflow-specific report format already captures the same information.

## What Stays Disposable or Private

Keep routine or sensitive run material outside `docs/reports/`:

| Location | Typical contents | Default treatment |
|---|---|---|
| `.work/` | audition runs, comparisons, temporary extraction data, scratch evidence | Disposable local evidence; inspect before deletion. |
| `outputs/` | sessions, review patches, run records, agent/Aider artifacts | Local review evidence; not canonical and normally not committed. |
| `sources/`, transcripts, exports | private source material and ChatGPT exports | Private input; do not commit without separate publication approval. |
| Private local files | endpoint configs, credentials, logs, model paths, full raw responses | Keep local unless explicitly selected and sanitized. |

Do not commit every raw run, large logs, caches, secrets, credentials, private
source text, or unreviewed model output. Preserve only the minimum evidence
needed to support the report’s findings.

Raw evidence may remain private while a sanitized report records hashes,
normalized source labels, commands, counts, and factual observations.

## Sanitize Before Committing

Before adding a report:

1. Replace operator-specific usernames and absolute home/workspace paths with
   package-relative paths or placeholders such as `<REPO_ROOT>` and
   `<MODEL_ROOT>`.
2. Replace real endpoint hosts and RFC1918 addresses with `<LAN_HOST>` while
   preserving the fact that a LAN endpoint was used.
3. Remove credentials, tokens, email addresses, private account names, machine
   names, and private source text.
4. Check copied commands, metadata, raw excerpts, filenames, tables, and
   Markdown links—not only prose.
5. Preserve factual behavior, scores, failure modes, source hashes, and
   validation results. Sanitization must not turn evidence into an approval.
6. Run the tracked-file-safe checks in
   [`SANITIZATION_NOTES.md`](../SANITIZATION_NOTES.md) and the practical
   pre-share checks in [`REPO_HEALTH.md`](../REPO_HEALTH.md).
7. Review the final diff manually before publication.

Do not use a broad recursive grep as the routine sanitization command. It can
scan ignored `.work/`, `outputs/`, `sources/`, or other private material and
print it into terminal logs. Use `git grep` for tracked-file checks; inspect
private/generated evidence separately only when it is intentionally being
published.

## Evidence and Decision Boundaries

A report may record a human decision, but the report itself grants no
authority. In particular:

- a report does not make generated context canonical;
- an audition or preflight report does not promote, approve, rank into a role,
  or assign a model;
- a successful endpoint or server run does not establish production readiness;
- a role-run report does not activate packets or move lifecycle state;
- publication remains a human decision.

When no decision has been made, say so explicitly. Prefer “evidence for human
review” over language that implies approval.

## Report Organization

Use a dated file or folder when the report represents a specific run or
comparison. Keep workflow-specific artifacts together and avoid mixing
incompatible schemas in one run folder.

Current report areas:

- [`model_auditions/`](model_auditions/README.md) — board/capability-card and
  exploratory small-model evidence.

Add another report area only when several durable reports need shared guidance.
