# Overnight Dogfood Run 2026-07-19

This report records the one-night aggressive dogfood launch for
`dogfood/overnight-20260718`.

## Branch And Commit

- Branch: `dogfood/overnight-20260718`
- Starting commit: `78529329eaf905b62e89bf50991edab3fa366f93`
- Code commit: `34948414f6c05a095c1bd448b987f9d92edba6eb`

## Window

- Start time: `2026-07-19T00:10:12-04:00`
- Stop time: `2026-07-19T00:10:34-04:00`
- Deadline: `2026-07-19T08:00:00-04:00`

## Objective

Implement a bounded overnight controller that can run from cron every five
minutes, source `.env.local`, preserve evidence, stop starting new work after
the deadline, and expose a status command and removal command.

## Implementation Summary

- Added `scripts/zth_overnight_dogfood_controller.sh`
- Added `scripts/zth_overnight_dogfood_status.sh`
- Added `scripts/zth_install_overnight_dogfood_cron.sh`
- Added `scripts/zth_uninstall_overnight_dogfood_cron.sh`
- Extended `tests/test_long_duration_dogfood_scripts.py`

## Verification

- `bash -n` for all overnight scripts
- `python3 -m pytest tests/test_long_duration_dogfood_scripts.py -q`
- Foreground dry run: `./scripts/zth_overnight_dogfood_controller.sh --dry-run`
- Live invocation: `source .env.local; bash -x ./scripts/zth_overnight_dogfood_controller.sh --tick`
- Status check: `./scripts/zth_overnight_dogfood_status.sh`

## Launch Result

The live invocation reached the configured model path, attempted three
bounded stages, and preserved the failure evidence. Each stage was marked
blocked because the local model call failed repeatedly.

Attempted stages:

- `worker-loop-001-roadmap-grounding-01`
- `worker-loop-002-roadmap-grounding-02`
- `worker-loop-003-roadmap-grounding-03`

## Cron

Installed cron entry:

```cron
*/5 * * * * /bin/bash -lc 'cd "/home/navigator/agent-workspace/zaphods-third-hand" && exec "/home/navigator/agent-workspace/zaphods-third-hand/scripts/zth_overnight_dogfood_controller.sh" --tick' # ZTH_OVERNIGHT_DOGFOOD_20260718
```

Removal command:

```bash
/home/navigator/agent-workspace/zaphods-third-hand/scripts/zth_uninstall_overnight_dogfood_cron.sh
```

## Changed Paths

- `scripts/zth_overnight_dogfood_controller.sh`
- `scripts/zth_overnight_dogfood_status.sh`
- `scripts/zth_install_overnight_dogfood_cron.sh`
- `scripts/zth_uninstall_overnight_dogfood_cron.sh`
- `tests/test_long_duration_dogfood_scripts.py`

## Evidence Locations

- `.work/dogfood/overnight/state.tsv`
- `.work/dogfood/overnight/status.json`
- `.work/dogfood/overnight/runs/20260719_001012-worker-loop-001-roadmap-grounding-01/`
- `.work/dogfood/overnight/runs/20260719_001018-worker-loop-002-roadmap-grounding-02/`
- `.work/dogfood/overnight/runs/20260719_001034-worker-loop-003-roadmap-grounding-03/`

## Final State

- Working tree: clean after the code commit and cron install
- Review state: blocked on local model call failure
- Next supervised action: inspect the endpoint availability and decide whether
  to rerun the overnight window with a working local model server
