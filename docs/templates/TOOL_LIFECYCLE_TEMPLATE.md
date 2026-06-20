# Tool Lifecycle Draft: <name>

```yaml
lifecycle_name: "<name>"
status: draft
source_material:
  - "<source file, transcript, log, or evidence note>"
intended_operator: "<human or supervised agent>"
risk_level: "<low|medium|high|unknown>"
requires_human_review: true
replayable_steps: []
validation_checks: []
known_failure_modes: []
promotion_recommendation: "not_ready"
```

This is a draft evidence artifact. It does not authorize execution, lifecycle
movement, cleanup, or promotion.

## Purpose

<What outcome does this lifecycle help produce?>

## When to Use

<When is this workflow appropriate, and when is it not?>

## Inputs Required

- <Input>

## Preconditions

- <Condition that must be true before starting>

## Human Decisions Required

- <Decision that must remain with the human operator>

## Workflow Steps

1. <Step>

## Useful Commands

```text
<Command copied from reviewed evidence>
```

## Validation Checks

- <Check and expected evidence>

## Failure Modes

- <Failure, signal, and likely cause>

## Failed-but-Important Attempts

- <Attempt that failed but exposed a useful constraint or diagnostic>

## Things We Are Proud Of

- <Strength, decision, pattern, validation, or safety boundary worth preserving>

## Things We Are Not Proud Of

- <Brittle shortcut, hidden manual step, missing validation, risky assumption,
  or lucky outcome that should not be normalized>

## Simplification / Essential Complexity

- Simplify: <Complexity that can probably be reduced>
- Keep: <Complexity that appears design-critical>
- Decide: <Complexity that needs human judgment before promotion>

Simplification must not remove safety, provenance, reversibility, auditability,
or human supervision.

## Recovery / Rollback

- <Safe recovery, rollback, or cleanup step requiring review>

## Artifacts Produced

- <Output file, report, log, or other evidence>

## Promotion Criteria

- <Evidence required before a human may promote this draft into a reusable,
  canonical lifecycle>

## Open Questions

- <Unresolved fact or decision>
