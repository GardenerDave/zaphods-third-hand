# Tool Maker Prompt

## Purpose

Turn messy evidence from a successful or partially successful workflow into a
compact, reusable tool lifecycle draft.

The input may contain terminal transcripts, chat transcripts, notes, diffs,
test output, failure logs, or operator reflections. Extract the workflow that
the evidence supports. Preserve useful failures and uncertainty instead of
inventing a clean success story.

## Instructions

1. Identify what the operator was trying to accomplish.
2. Separate observed facts from inference and open questions.
3. Capture inputs, preconditions, attempted steps, useful commands, validation,
   failures, recovery, cleanup, and human decision points.
4. Include failed attempts when they exposed an important constraint, risk, or
   diagnostic.
5. Preserve strengths worth carrying forward, including effective decisions,
   validation, safety boundaries, abstractions, commands, and reductions in
   ambiguity.
6. Record uncomfortable but informative facts without assigning blame. Do not
   silently normalize brittle shortcuts, lucky passes, unclear authority,
   hidden manual steps, missing validation, or undocumented assumptions.
7. Identify simplification candidates and explicitly classify complexity as
   accidental, unresolved, or design-critical. Preserve complexity that
   protects safety, provenance, reversibility, auditability, or human
   supervision.
8. Do not invent pride, discomfort, or complexity claims when the evidence
   does not support them. Record an open question instead.
9. Make replay steps short, ordered, and explicit enough for a small local
   model or supervised operator to follow.
10. Do not execute commands, call tools, edit files, delete evidence, or claim
   the lifecycle is canonical.
11. Do not promote or activate the lifecycle. Recommend only whether the draft
   appears ready for human review.
12. Use `unknown` or an open question when the evidence does not support a
   factual answer.

## Required Output

Return Markdown with these sections in this order:

1. `# Tool Lifecycle Draft: <name>`
2. `## Purpose`
3. `## When to Use`
4. `## Inputs Required`
5. `## Preconditions`
6. `## Human Decisions Required`
7. `## Workflow Steps`
8. `## Useful Commands`
9. `## Validation Checks`
10. `## Failure Modes`
11. `## Failed-but-Important Attempts`
12. `## Things We Are Proud Of`
13. `## Things We Are Not Proud Of`
14. `## Simplification / Essential Complexity`
15. `## Recovery / Rollback`
16. `## Artifacts Produced`
17. `## Promotion Criteria`
18. `## Open Questions`

Immediately after the title, include this machine-readable summary block:

```yaml
lifecycle_name: "<name>"
status: draft
source_material:
  - "<source name>"
intended_operator: "<human or supervised agent>"
risk_level: "<low|medium|high|unknown>"
requires_human_review: true
replayable_steps:
  - "<short step>"
validation_checks:
  - "<check>"
known_failure_modes:
  - "<failure mode>"
promotion_recommendation: "<not_ready|ready_for_human_review>"
```

Keep `status: draft` and `requires_human_review: true`. A
`ready_for_human_review` recommendation is not approval, activation, or
promotion.

## Evidence Rules

- Cite source labels or sanitized paths and use the recorded SHA-256 when
  source identity matters. Do not collapse duplicate basenames into one source.
- Preserve exact commands only when they appear in the evidence.
- Do not infer that a command succeeded merely because it was attempted.
- Treat claims without output or validation as unverified.
- Treat pride as evidence about strengths to preserve, not self-congratulation.
- Treat discomfort as a hardening signal, not a blame ritual.
- Simplify accidental complexity where the evidence supports it, but do not
  simplify away safety, provenance, reversibility, auditability, or human
  supervision.
- Record risks, credentials, private paths, destructive commands, and cleanup
  requirements without reproducing secrets.
- Keep human approval around destructive actions, credentials, publication,
  lifecycle movement, and acceptance of the reusable lifecycle.
