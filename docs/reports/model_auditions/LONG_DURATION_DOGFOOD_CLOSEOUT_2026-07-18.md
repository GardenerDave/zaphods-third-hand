# Long Duration Dogfood Closeout 2026-07-18

## Purpose

Record the supervised long-duration dogfood run as a completed evidence trail
and mark the point where the recommender should stop for operator review
instead of continuing to suggest more implementation work automatically.

## Supervised Run Boundary

- The cron/tick loop is supervised.
- The loop produces review artifacts only.
- Safe checks gate useful recommendations.
- The loop does not have unattended execution authority.

## Completed Evidence-Backed Milestones

- Long-duration dogfood cron and script tests
- Queue approval path validator scaffold
- Queue approval path calibration synthesis
- Read-only queue approval review command
- Queue approval review command calibration synthesis
- Declarative long-duration milestone map
- Declarative milestone map calibration synthesis
- Long-duration dogfood closeout report

## Stale-Recommendation Fixes

- Long-duration script tests stale guard
- Queue approval scaffold stale guard
- Queue approval path calibration stale guard
- Queue approval review command stale guard
- Queue approval review command calibration stale guard
- Declarative milestone map replacement for nested one-off guards

## Declarative Milestone Map

The recommender uses an ordered milestone map with these fields:

- category
- title
- required evidence files
- prompt

The map is encoded as tab-separated milestone rows, and each row uses a
comma-separated evidence list. The recommender selects the first incomplete
milestone, requires all evidence files for multi-file milestones, and skips
completed milestones automatically.

## Validation Coverage

- Long-duration script tests
- Review queue approval path tests
- Queue approval validator and fixture tests
- Queue handoff validator and fixture tests
- Front-door review, score, and validation tests
- Shell syntax checks
- `git diff --check`

## What Remains Unimplemented

- Queue insertion
- Queue writing
- Queue running
- Queue runner
- Queue processor
- Automatic queue handoff
- Router automation
- Unattended execution
- Repo mutation beyond explicit reviewed changes
- Fixture import
- Training capture
- Prompt patch promotion
- Deployment
- Downstream-use authority

## Recommended Stop / Next Decision Point

- Stop expanding queue-approval scaffolding for now.
- Review the long-duration dogfood evidence as a completed bounded run.
- Decide whether the next lane should be:
  - closeout polish / presentation notes
  - broader triage-router integration
  - model audition improvements
  - queue-writing design review
- Queue-writing design must require explicit operator approval and a separate
  authority review.

## Authority Boundary

This closeout is evidence-only, recommendation-only, and review-only. It does
not authorize queue writing, queue insertion, queue running, automatic
handoff, or downstream-use authority.
