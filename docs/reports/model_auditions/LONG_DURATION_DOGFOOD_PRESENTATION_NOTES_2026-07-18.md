# Long Duration Dogfood Presentation Notes 2026-07-18

## Five-Minute Demo Title

ZTH v0.4.0: Evidence-Backed Dogfood Loop

## One-Sentence Pitch

ZTH turns repeated supervised dogfood work into durable evidence, then stops at
an operator review point instead of repeating stale recommendations.

## Problem

Local and small-model workflows drift unless bounded by evidence and review.

## What The Loop Did

- Ran safe checks.
- Recommended bounded next work.
- Detected completed milestones.
- Initially repeated stale recommendations.
- Got refactored into a declarative milestone map.
- Stopped at operator review.

## Demo Flow

- Show latest tick summary.
- Show closeout report.
- Show milestone map.
- Show tests.
- Show final stop target.

## Strongest Story Beat

The framework discovered its own missing abstraction.

## Exact Boundary

- No queue writing.
- No queue insertion.
- No automatic handoff.
- No downstream-use authority.

## Closing Line

ZTH did not just finish tasks; it forced the next decision back to the operator.
