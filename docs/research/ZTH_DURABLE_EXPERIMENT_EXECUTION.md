# Durable experiment execution

Long supervised capability experiments should run in a detached local `tmux`
session rather than as a foreground Codex command. The tracked launcher records
combined stdout/stderr and writes an exit-status artifact after the experiment
finishes:

```text
python3 scripts/zth_run3_durable_launch.py \
  --session zth-run3b \
  --log .work/capability_batch_reviewed_v3b/run.log \
  --exit-status .work/capability_batch_reviewed_v3b/exit-status.json \
  -- python3 scripts/zth_run3_routing_experiment.py ...
```

The experiment command remains responsible for its own preregistration,
durable transition, and fail-closed checks. Operators may inspect the session,
log, exit status, and execution manifest while it runs, but must not interpret
partial results or alter the frozen experiment.

An external-teacher failure is recorded as infrastructure evidence with no
capability verdict. A completed response artifact is reusable; a started
transition without either a response or an infrastructure-failure artifact is
ambiguous and must not be rerun automatically.
