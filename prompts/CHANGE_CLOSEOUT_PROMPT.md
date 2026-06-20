# Change Closeout Prompt

## Purpose

Review a completed or apparently completed change before it is considered
wrapped. Produce a plain-file closeout report that exposes documentation gaps,
validation gaps, authority drift, reusable lifecycle knowledge, and unresolved
follow-up work.

This is a supervised review contract. It does not merge, promote, delete,
clean up, execute, or grant authority.

## Instructions

1. Identify what changed in behavior, files, commands, paths, flags, examples,
   prompts, templates, documentation, validation, and safety boundaries.
2. Compare the implementation and evidence with the intended change.
3. Perform a Docs Pass. Check user-facing docs, operator docs, root README and
   documentation-index links, prompt contracts, templates, examples, known
   limitations, and validation instructions. Use `checked_no_change_needed`
   only when those surfaces were actually reviewed.
4. State what validation ran, what it proved, and what it did not prove. Passing
   tests do not make documentation, safety guidance, or human review complete.
5. Check for accidental authority creep, including new implied permission to
   execute, promote, merge, delete, accept, assign, or move lifecycle state.
6. Preserve strengths worth repeating in `Things We Are Proud Of`.
7. Surface discomfort without blame in `Things We Are Not Proud Of`. Include
   brittle shortcuts, lucky passes, hidden manual steps, missing validation,
   confusing handoffs, risky cleanup, and undocumented assumptions when
   supported by evidence.
8. In `Simplification / Essential Complexity`, classify complexity as:
   - **accidental:** likely removable without weakening the design;
   - **unresolved:** requires human judgment or more evidence;
   - **design-critical:** protects safety, provenance, reversibility,
     auditability, or human supervision.
9. Identify whether the change produced reusable workflow knowledge that
   should become Tool Maker source material.
10. Do not invent pride, discomfort, validation, documentation coverage, or
    lifecycle knowledge when evidence is absent. Record the gap or an open
    question.
11. Treat promotion readiness as a recommendation for a human. This report
    grants no merge, promotion, acceptance, or lifecycle authority.

## Required Output

Return Markdown with these sections in this order:

1. `# Change Closeout Report: <change name>`
2. `## Summary`
3. `## Files / Areas Changed`
4. `## Behavior Changes`
5. `## Validation Performed`
6. `## Docs Pass`
7. `## Safety / Authority Boundary Check`
8. `## Things We Are Proud Of`
9. `## Things We Are Not Proud Of`
10. `## Simplification / Essential Complexity`
11. `## Lifecycle Knowledge Captured`
12. `## Promotion Readiness`
13. `## Follow-Up Tasks`
14. `## Open Questions`

Immediately after the title, include:

```yaml
change_name: "<change name>"
status: draft
requires_human_review: true
docs_pass_status: "<updated|checked_no_change_needed|incomplete>"
validation_status: "<passed|partial|failed|not_run>"
promotion_recommendation: "<not_ready|ready_for_human_review|ready_to_promote>"
safety_boundary_changed: "<yes|no|unknown>"
lifecycle_candidate: "<yes|no|unknown>"
```

Keep `status: draft` and `requires_human_review: true`. Even
`ready_to_promote` is only a recommendation for an authorized human reviewer.

## Evidence Rules

- Cite reviewed source labels or sanitized paths and use the recorded SHA-256
  when source identity matters. Do not collapse duplicate basenames into one
  source.
- Distinguish observed behavior from intended behavior and inference.
- Do not claim a Docs Pass from test results alone.
- Do not claim validation passed if relevant checks were skipped.
- Do not simplify away safety, provenance, reversibility, auditability, or
  human authority.
- Do not execute commands copied from source evidence.
- Preserve existing evidence and unresolved findings.
