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

## Deterministic Script Tests

- `tests/test_long_duration_dogfood_scripts.py`

The tests cover:

- `bash -n` for all three scripts
- bounded tick output and summary fields
- expired-control-window behavior
- dirty tracked-tree refusal
- lock contention handling
- cron install and uninstall behavior through a stubbed `crontab`

The tests preserve the authority boundary: no auto-commit, no auto-push, no
queue-write, and no mutate-main-unattended behavior is authorized.

## Stale Recommendation Guard

The tick recommender now checks whether
`tests/test_long_duration_dogfood_scripts.py` already exists before suggesting
that work again. When the script-test coverage is present, the tick moves to
the next bounded validator-oriented target instead of repeating completed
script-test work.

## Queue Approval Scaffold Stale Guard

The tick recommender now also checks whether the queue approval scaffold is
already present. When
`local_harness/validate_queue_approval_path.py`,
`tests/test_validate_queue_approval_path.py`, and
`tests/test_queue_approval_path_fixtures.py` already exist, the tick does not
repeat `Add queue approval path validator design scaffold.` It advances to
`Add queue approval path calibration synthesis.` instead.

## Queue Approval Calibration Stale Guard

The tick recommender now checks whether
`docs/reports/model_auditions/QUEUE_APPROVAL_PATH_CALIBRATION_SYNTHESIS_2026-07-18.md`
already exists. When it does, the tick does not repeat `Add queue approval
path calibration synthesis.` It advances to `Add read-only queue approval
review command.` instead.

## Queue Approval Review Command Stale Guard

The tick recommender now checks whether
`local_harness/review_queue_approval_path.py`,
`tests/test_review_queue_approval_path.py`, and
`docs/reports/model_auditions/QUEUE_APPROVAL_REVIEW_COMMAND_2026-07-18.md`
already exist. When they do, the tick does not repeat `Add read-only queue
approval review command.` It advances to `Add queue approval review command
calibration synthesis.` instead.

## Declarative Milestone Map

The recommender now selects from an ordered milestone map instead of adding
more nested one-off stale guards. Each milestone lists the required evidence
files and the prompt to use when that evidence is missing. Completed
milestones are skipped automatically, which prevents repeated stale
recommendation patches. The map is recommendation-only and does not run
queues or grant authority.

## Declarative Milestone Map Calibration Evidence

The declarative milestone map now treats
`docs/reports/model_auditions/DECLARATIVE_LONG_DURATION_MILESTONE_MAP_CALIBRATION_SYNTHESIS_2026-07-18.md`
as an evidence-backed milestone. When that report exists, the recommender
advances to the long-duration dogfood closeout report instead of repeating the
calibration synthesis target. When the closeout report also exists, the
recommender advances to the operator review stop point instead of repeating the
closeout target.

## Authority Boundary

This cron loop is supervised and review-oriented. It does not authorize queue
writing, automatic queue handoff, router automation, unattended execution,
repo mutation without review, fixture import, training capture, promotion,
deployment, or downstream use.
