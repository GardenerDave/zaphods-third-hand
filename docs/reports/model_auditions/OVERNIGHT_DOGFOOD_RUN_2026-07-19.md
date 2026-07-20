# Overnight Dogfood Run 2026-07-19

This report preserves the July 19 overnight launch history and records the July 20 hardening pass that corrected the run-state semantics.

## Branch And Commits

- Branch: `dogfood/overnight-20260718`
- Starting commit: `78529329eaf905b62e89bf50991edab3fa366f93`
- Launch controller commit: `34948414f6c05a095c1bd448b987f9d92edba6eb`
- Closeout report commit: `b29d2202b02cb55a674717f89695fb2a438f966e`

## Time Window

- Run start: `2026-07-19T00:10:12-04:00`
- Run closeout: `2026-07-19T03:45:18-04:00`
- Deadline: `2026-07-19T08:00:00-04:00`

## What Happened

The overnight controller ran with bounded local authority and preserved evidence across the whole window.

The first three stages were blocked because the local model path failed:

- `worker-loop-001-roadmap-grounding-01`
- `worker-loop-002-roadmap-grounding-02`
- `worker-loop-003-roadmap-grounding-03`

After endpoint recovery, the controller progressed through the 120 queued worker stages and then repeatedly selected the synthetic closeout stage `Create overnight status and evidence manifest.` instead of treating queue exhaustion as terminal.

That repeated closeout stage was the failure mechanism:

- it was re-enqueued as ordinary work;
- it produced duplicate run directories and duplicate `ready_for_review` records;
- it inflated the durable event stream to 564 rows;
- it left the run without a durable terminal marker that prevented further ticks from starting another closeout.

## Final Run Facts

- 120 queued worker stages were queued
- 117 worker stages produced model outputs under the old lifecycle semantics
- 3 worker stages remained blocked
- 54 repeated synthetic closeout executions occurred after queue exhaustion
- 171 model outputs = 117 worker outputs + 54 closeout outputs
- 174 run directories = 120 worker directories + 54 closeout directories
- 68 deadline mentions in the preserved evidence set
- Final authoritative stage distribution:
  - `ready_for_review`: 118
  - `review`: 3
- Final queue state: exhausted, but not terminal in the preserved launch artifact
- Final recorded transition: `2026-07-19T07:55:37-04:00`
- Final lifecycle weakness: semantic review was still being treated as successfully reviewed output even when the content was only structurally acceptable

The historical `118 ready_for_review` unique-stage count is therefore `117` worker stages plus the synthetic closeout stage under the old coarse semantics.

## Schema Drift And Changed-Path Findings

- The launch artifact did not distinguish between:
  - captured model output;
  - structure-valid output;
  - semantic review success;
  - ready-for-review staging;
  - queue exhaustion / terminal closeout.
- Changed-path claims were not being checked as tightly as the launch packet required.
- Procedural placeholder content could still land in the same lifecycle bucket as completed review output.
- Deadline handling was not controller-owned in the way the hardened pipeline now requires.

## Repairs Implemented In This Hardening Pass

- Added durable queue-exhaustion terminal state handling.
- Added idempotent closeout markers so repeated ticks do not create duplicate closeout work.
- Moved deadline evaluation into the controller.
- Added a frozen overnight review schema validator.
- Preserved raw model output and repair diagnostics separately from validation state.
- Made status derive from durable state and report fresh counts.
- Added tests for:
  - one-shot terminal closeout;
  - repeated tick idempotence;
  - controller-owned deadline evaluation;
  - schema drift rejection;
  - changed-path allowlist enforcement;
  - evidence requirements;
  - actionable model-call diagnostics.

## Verification Performed

- `bash -n scripts/zth_overnight_dogfood_controller.sh`
- `bash -n scripts/zth_overnight_dogfood_status.sh`
- `bash -n scripts/zth_install_overnight_dogfood_cron.sh`
- `bash -n scripts/zth_uninstall_overnight_dogfood_cron.sh`
- `python3 -m py_compile scripts/zth_overnight_dogfood_controller.py scripts/zth_validate_overnight_review_output.py`
- `python3 -m pytest tests/test_long_duration_dogfood_scripts.py -q`
- Focused overnight semantics slice:
  - queue exhaustion idempotence
  - status reporting
  - schema validation
  - dry-run preservation

## Conclusion

The run proved sustained orchestration, evidence preservation, retry recovery, and bounded repository authority. It did not prove reliable semantic review.

The repeated closeout defect is now treated as a terminal-state bug rather than ordinary queue work.

## Inspection Evidence

- `.work/dogfood/overnight/state.tsv`
- `.work/dogfood/overnight/status.json`
- `.work/dogfood/overnight/manifests/overnight_run_manifest.json`
- `.work/dogfood/overnight/runs/20260719_001012-worker-loop-001-roadmap-grounding-01/`
- `.work/dogfood/overnight/runs/20260719_001018-worker-loop-002-roadmap-grounding-02/`
- `.work/dogfood/overnight/runs/20260719_001034-worker-loop-003-roadmap-grounding-03/`
