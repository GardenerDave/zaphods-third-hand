# Change Closeout Report: <change name>

```yaml
change_name: "<change name>"
status: draft
requires_human_review: true
docs_pass_status: "incomplete"
validation_status: "not_run"
promotion_recommendation: "not_ready"
safety_boundary_changed: "unknown"
lifecycle_candidate: "unknown"
```

This report is draft review evidence. It does not merge, promote, accept,
delete, execute, clean up, or authorize lifecycle movement.

A change can pass tests and still be incomplete when documentation, prompt or
template contracts, safety boundaries, limitations, or human-review guidance
are missing.

## Summary

<What changed, why, and what remains unresolved?>

## Files / Areas Changed

- <File or area and its purpose>

## Behavior Changes

- <User-visible, operator-visible, contract, or internal behavior change>

## Validation Performed

- <Command or review performed, result, and limitation>

## Docs Pass

- User-facing docs:
- Operator docs:
- README and documentation-index links:
- Prompt contracts and templates:
- Examples and known limitations:
- Validation instructions:

## Safety / Authority Boundary Check

- <Whether execution, promotion, acceptance, deletion, assignment, or
  lifecycle authority changed or became ambiguous>

## Things We Are Proud Of

- <Strength, decision, validation, abstraction, or safety boundary worth
  repeating>

## Things We Are Not Proud Of

- <Brittle shortcut, lucky pass, hidden manual step, missing validation,
  confusing handoff, risky cleanup, or undocumented assumption>

## Simplification / Essential Complexity

- Accidental: <Complexity that can probably be removed>
- Unresolved: <Complexity that needs evidence or human judgment>
- Design-critical: <Complexity that protects safety, provenance,
  reversibility, auditability, or human supervision>

## Lifecycle Knowledge Captured

- <Reusable workflow knowledge that should or should not feed Tool Maker>

## Promotion Readiness

- <Recommendation and evidence still required>

This recommendation grants no merge, promotion, acceptance, or lifecycle
authority.

## Follow-Up Tasks

- <Separate task requiring human review and routing>

## Open Questions

- <Unresolved fact or decision>
