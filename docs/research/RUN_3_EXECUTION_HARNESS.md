# Run 3 execution harness

Run 3's first execution attempt is preserved as an invalid, incomplete pilot
under `.work/capability_batch_reviewed_v3/`. It is not scored and is not a
resume source for Run 3B.

The tracked harness is
[`scripts/zth_run3_routing_experiment.py`](../../scripts/zth_run3_routing_experiment.py).
It uses the frozen Run 3 policy and fixtures, reuses the supervised capability
loop, and fails closed when an arm has incomplete durable state. A baseline is
written once per arm; restart recovery requires a complete attempt-1 artifact
set and never overwrites it. A terminal transition without its summary is also
treated as unsafe to resume.

The preregistered SHA256 arm ordering uses the first bit of
`sha256("20260818:" + task_id)`: control-first for zero and treatment-first for
one. Supported-negative deterministic-retry evidence is translated from the
router's `alternatives` into `avoid_deterministic_patch_retry`; the router
itself is unchanged.

The external-teacher adapter remains machine-local and review-only. The
machine wrapper uses `codex exec --ephemeral --sandbox read-only`, accepts the
packet on stdin, and returns the last message through a temporary file. The
pilot emitted `Failed to create stream fd: Operation not permitted` while an
external call was in flight. The durable evidence establishes a stall after
`external_teacher_started`, but does not establish that the wrapper or Codex
installation is intrinsically broken. The tracked harness adds a bounded
external subprocess timeout (120 seconds by default), preserving the failure
as infrastructure evidence rather than converting it into a capability
verdict.

No Run 3B fixtures or model calls are created by this repair. Run 3B should use
a fresh execution directory and the unchanged preregistered fixture set unless
review determines that the incomplete pilot contaminated any fixture-level
state; the pilot's partial trajectories must never be used as Run 3B metrics.
