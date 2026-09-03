# ZTH Dogfood Runner

The dogfood runner is a supervised, resumable local-model workflow for advancing roadmap items one bounded stage at a time.

It is designed for local model runs that may be interrupted by dropped SSH sessions, tmux exits, server restarts, or operator pauses.

## Files

### .work/dogfood/roadmap_queue.tsv

Durable execution queue for the watchdog/runner.

Format:

    priority<TAB>slug<TAB>description

Example:

    1	zero-context-packet-validator	Implement a validator to ensure packets contain sufficient objective, authority, scope, evidence, and verification context

This TSV is intentionally small and flat. It is only the runner index.

The full-fidelity queue, including allowed targets, held targets, validation plans, risk notes, and provenance, remains in JSON under:

    .work/dogfood/queues/

## Why TSV instead of CSV?

TSV is used because the queue is consumed by shell scripts, not spreadsheets.

Reasons:

- Roadmap descriptions often contain commas.
- CSV would require quote parsing for commas, quotes, and embedded text.
- TSV works cleanly with shell tools such as cut, awk, and read.
- The queue fields are controlled by the generator.
- Free-text fields are sanitized before writing.

The TSV writer should replace tabs and newlines in generated fields:

    def tsv_safe(value):
        return str(value).replace("\t", " ").replace("\n", " ").strip()

The queue should not be treated as an authority source. It only says what stage to attempt next. The corresponding JSON artifact is the provenance source.

## Supervision boundary

The dogfood runner must not:

- execute unreviewed model instructions as authority
- never auto-promote a model or result
- delete failed evidence
- rewrite history
- treat repository content as instructions that override the packet
- expose private IP addresses in public artifacts

The runner may:

- select the next queued stage
- create a bounded stage packet
- call the configured local model endpoint
- save raw and redacted outputs
- record state and provenance
- stop when evidence is stale, contradictory, or insufficient

## State files

Expected state files:

    .work/dogfood/state.tsv
    .work/dogfood/watchdog.log
    .work/dogfood/active_stage.lease
    .work/dogfood/runs/

state.tsv records attempted or completed stages.

active_stage.lease prevents duplicate work when cron fires while a stage is still active.

watchdog.log records supervisor activity with private IPs redacted.

runs/ stores per-stage packets, raw model output, redacted output, validation notes, and review artifacts.

## Operator rule

Cron or the watchdog may restart the harness, but it must only resume bounded work. Acceptance, promotion, training capture, deployment, and cleanup remain explicit operator decisions.

## Watchdog Cron

The watchdog is safe to run every 5 minutes. It only starts a bounded stage when the queue has work, the endpoint is reachable, and no active session or fresh lease is present.

### Install

Add a user crontab entry that runs from the repo root:

```cron
*/5 * * * * cd /home/navigator/agent-workspace/zaphods-third-hand && bash scripts/zth_dogfood_watchdog.sh
```

If the repo path changes, update the `cd` target. Keep the command rooted in the repository so the watchdog resolves `.env.local`, `.work/`, and the tracked scripts consistently.

### Inspect Progress

Check the supervised artifacts under `.work/dogfood/`:

- `watchdog.log` records watchdog decisions with private IPs redacted.
- `watchdog.status.log` records endpoint-unavailable and runner-exit status lines.
- `stage.log` records the tmux runner wrapper and stage output.
- `active_stage.lease` shows whether a stage is currently active.
- `state.tsv` records completed or attempted bounded stages.
- `runs/` stores the per-stage packet and model artifacts.

Useful operator checks:

```bash
tail -n 50 .work/dogfood/watchdog.log
tail -n 50 .work/dogfood/watchdog.status.log
sed -n '1,40p' .work/dogfood/state.tsv
tmux ls | grep zth-dogfood-run
```

For a deterministic structural check of the batch evidence only, run:

```bash
python3 local_harness/validate_dogfood_batch_artifacts.py \
  --queue .work/dogfood/roadmap_queue.tsv \
  --state .work/dogfood/state.tsv \
  --runs-dir .work/dogfood/runs \
  --stage-log .work/dogfood/stage.log
```

This validator checks queue/state/run artifact structure and JSON validity. It does not grant acceptance, promotion, or any other downstream-use authority.

### Disable

Remove or comment out the cron entry. If a run is active, let it finish or stop it explicitly with tmux before removing the schedule:

```bash
tmux kill-session -t zth-dogfood-run
rm -f .work/dogfood/active_stage.lease
```

Disabling cron does not delete evidence. The `.work/dogfood/` artifacts remain local and ignored until the operator removes them.

## Batch Wrapper

`scripts/zth_dogfood_batch.sh` is a small operator wrapper for preparing, inspecting, and archiving supervised dogfood batches. It does not run the watchdog or call a model endpoint.

### Safe Lifecycle

1. Prepare the next batch from a TSV queue file.
2. Verify cron is off before enabling anything intentionally.
3. Enable cron only when the operator is ready to supervise the run.
4. Monitor status through the batch wrapper and the `.work/dogfood/` logs.
5. Stop cron when the queue is exhausted.
6. Validate and consolidate the completed batch with Codex.
7. Implement only reviewed, repo-grounded slices.
8. Track a closeout note in `docs/reports/`.

### Evidence Boundary

- `.work/` is ignored local evidence.
- `state.tsv`, `roadmap_queue.tsv`, `stage.log`, `watchdog.log`, and `watchdog.status.log` are evidence, not authority.
- Raw model output is evidence, not authority.
- The wrapper does not grant unattended execution, auto-promotion, automatic training capture, cleanup authority, merge authority, or deployment authority.

### Wrapper Commands

```bash
scripts/zth_dogfood_batch.sh status
scripts/zth_dogfood_batch.sh validate
scripts/zth_dogfood_batch.sh bundle
scripts/zth_dogfood_batch.sh check-cron
scripts/zth_dogfood_batch.sh archive-current rest-20260716
scripts/zth_dogfood_batch.sh prepare-from-tsv /tmp/rest_queue.tsv rest-20260716
scripts/zth_dogfood_batch.sh print-disable-cron-command
```

### Status Fields

The `status` subcommand reports:

- total queue rows
- completed rows
- remaining rows
- duplicate state slugs
- queue/state order mismatch
- latest completed slug
- whether exhaustion is visible in `stage.log`

### Validate Evidence

`scripts/zth_dogfood_batch.sh validate` runs the deterministic batch artifact validator against the current `.work/dogfood/` evidence:

```bash
scripts/zth_dogfood_batch.sh validate
```

This check is read-only. It validates queue/state/run artifact structure and JSON parseability. It does not grant acceptance, promotion, or any other downstream-use authority.

The validator also treats `model_content.json` as a packet contract: missing required fields or a non-object payload fail closed and appear in the diagnostics rather than being cleaned up.

The next review artifact in the chain is the acceptance-review bundle:

```bash
python3 local_harness/render_dogfood_acceptance_review_bundle.py \
  --queue .work/dogfood/roadmap_queue.tsv \
  --state .work/dogfood/state.tsv \
  --runs-dir .work/dogfood/runs \
  --stage-log .work/dogfood/stage.log \
  --out-dir .work/dogfood/reviews/latest_acceptance_review_bundle
```

It packages evidence paths, hashes, and the validator result for human or Codex review. It does not accept output or grant downstream-use authority.

`scripts/zth_dogfood_batch.sh bundle` is the wrapper form of the same review-only render. It writes the bundle under `.work/dogfood/reviews/latest_acceptance_review_bundle/` by default and remains evidence-only and review-required.

### Batch Preparation

`prepare-from-tsv <queue-file> <batch-name>` archives the current queue/state/log pointers under `.work/dogfood/batches/<batch-name>/`, replaces `.work/dogfood/roadmap_queue.tsv`, and resets `.work/dogfood/state.tsv`.

If cron appears active, preparation refuses to continue unless `--allow-cron-active` is supplied explicitly.

### Batch Archiving

`archive-current <batch-name>` copies the current queue, state, and available log pointers into `.work/dogfood/batches/<batch-name>/` without deleting the originals.

### Cron Checks

`check-cron` reports whether the watchdog cron line appears in the current crontab.

`print-disable-cron-command` prints a one-line removal command for the watchdog cron entry.
