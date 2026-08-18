# Supervised capability batch preparation

Status: `ready_for_review`. The first unattended run is prepared but has not
been started.

## Reviewed fixture pack

The reviewed pack is
`local_harness/fixtures/capability_loop/reviewed_v1/`. It contains 24 bounded
tasks adapted from existing ZTH logic probes, prompt-patch cases, front-door
chain cases, and queue-handoff review cases. Each task records source
provenance and selects the existing `zth_output_contract` validator.

## Codex adapter decision

The installed Codex CLI supports the documented noninteractive `codex exec`
stdin path with ephemeral, read-only execution and a final-message output
file. The machine-local wrapper is `~/bin/zth-codex-teacher` and is configured
through the ignored local environment only.

A generic strict output schema is intentionally not used. The teacher envelope
is stable, but `corrected_reference_output` is task-specific and may have
different shapes; a universal schema would either reject valid task-specific
references or silently under-specify them. The wrapper therefore relies on the
teacher packet's JSON-only instruction and the existing downstream parser,
which fails closed on malformed or unavailable output. Deterministic worker
validation remains authoritative.

## Planned command

```bash
set -a
source .env.local
set +a
PYTHONPATH=. python3 scripts/zth_capability_batch.py \
  local_harness/fixtures/capability_loop/reviewed_v1 \
  --out-dir .work/capability_batch_reviewed_v1 \
  --max-worker-attempts 2 \
  --max-teacher-passes 2
```

The command processes only this reviewed fixture directory, emits trajectory
and scorecard evidence, and does not insert queue work, promote patches, train,
or accept model output.
