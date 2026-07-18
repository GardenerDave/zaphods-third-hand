# Long Duration Dogfood Cron 2026-07-18

This report records the supervised long-duration dogfood cron loop added for
repeatable review artifact generation.

## Purpose

Run bounded long-duration dogfood ticks on a schedule so ZTH can keep
inspecting the repository, running safe checks, and producing review artifacts
for later supervised action.

## Scripts Added

- `scripts/zth_long_duration_dogfood_tick.sh`
- `scripts/zth_install_long_duration_cron.sh`
- `scripts/zth_uninstall_long_duration_cron.sh`

## Cron Cadence

- Default cadence: every 20 minutes

## Max Duration

- Default max duration: 8 hours from install time
- Duration metadata is stored under `.work/long_duration_dogfood/control/`

## What It May Do

- Inspect the current branch, HEAD, and recent commits
- Record `git status --short`
- Run bounded safe checks and tests
- Write tick outputs and prompts under `.work/long_duration_dogfood/`
- Recommend the next bounded implementation-oriented task for later review

## What It Must Not Do

- Auto-commit
- Auto-push
- Auto-merge
- Queue-write
- Run automatic queue handoff
- Mutate `main` unattended
- Train
- Promote
- Deploy
- Grant downstream-use authority
- Loosen validators

## Run Artifact Location

Tick artifacts are written under:

`.work/long_duration_dogfood/runs/<timestamp>/`

## How to Inspect the Latest Output

Look for the most recent tick directory under:

`.work/long_duration_dogfood/runs/`

Then inspect:

- `tick_summary.json`
- `implementation_prompt.md`
- `git_status_short.txt`
- `git_log_oneline_20.txt`
- `roadmap_snippets.txt`
- command exit codes and stdout/stderr files

## How to Stop or Uninstall

- Remove the cron entry with `scripts/zth_uninstall_long_duration_cron.sh`
- The uninstall helper only removes lines tagged `ZTH_LONG_DURATION_DOGFOOD`

## Authority Boundary

This cron loop is supervised and review-oriented. It does not authorize queue
writing, automatic queue handoff, router automation, unattended execution,
repo mutation without review, fixture import, training capture, promotion,
deployment, or downstream use.
