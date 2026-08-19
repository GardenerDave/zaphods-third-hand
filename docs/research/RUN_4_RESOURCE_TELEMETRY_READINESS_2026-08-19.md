# Run 4 Resource-Telemetry Readiness

This note records the telemetry hardening needed before a future weighted-cost
Run 4. It does not create Run 4 fixtures, alter Run 3C evidence, or select any
resource weights.

## What Run 3C measured

Run 3C durably measured worker and teacher call counts, task counts, retries,
model identities, and start-to-response transition intervals. Worker and local
teacher artifacts also preserved usage and server timing metadata. The external
Codex adapter preserved identity and response text, but its structured artifact
did not contain token usage or server timing metadata.

The Run 3C preregistered teacher-call result remains unchanged: control used 35
teacher calls and treatment used 33. That is an intervention-count result, not
a weighted economic result.

## Telemetry contract now available

`local_harness/resource_telemetry.py` defines
`zth_resource_telemetry_v1`. Future worker, local-teacher, and external-teacher
calls can record the same fields:

- role, model identity, adapter/server identity;
- request-start and response-capture monotonic timestamps;
- elapsed milliseconds;
- prompt, completion, total, and cached tokens;
- server prompt and generation milliseconds;
- timeout, transport classification, and optional hardware/device identity.

Missing values are explicit JSON `null`; they are not estimated or converted to
zero. Elapsed time is measured from the local monotonic clock. Existing worker
and local-teacher response metadata is copied without changing its semantics.
External successful responses currently receive the common record with usage
and server timing fields null because the adapter does not expose those values.

Optional descriptive configuration labels are available in `config.example.env`:

- `ZTH_CAPABILITY_WORKER_HARDWARE`
- `ZTH_CAPABILITY_TEACHER_HARDWARE`
- `ZTH_EXTERNAL_TEACHER_SERVICE_CLASS`

These labels are operator-supplied only. Hardware is never inferred from a
model name.

## Resource-weight manifest

`docs/research/RUN_4_RESOURCE_WEIGHTS_TEMPLATE.json` is a schema/template for
future weights covering worker, local-teacher, and external-teacher call,
token, and time units. It is deliberately draft, unfrozen, and unapproved.
`load_approved_resource_weights()` rejects any manifest that is not explicitly
both frozen and approved, so no weighted routing can use the template.

## Remaining gaps

Stable hardware identity, GPU/device utilization, energy/power, monetary/API
prices, and external-teacher token/server timing telemetry remain unavailable.
The external adapter path must be extended only if its supported structured
output actually exposes usage; prose must not be scraped and missing values
must remain null.

The current instrumentation does not retroactively rewrite Run 3C artifacts.
Old artifacts remain valid without the new optional field. New execution
artifacts will carry the common record at the worker/local/external call
boundaries.

## Explicit Run 4 decision modes

Run 4 has two scientifically distinct options:

**A. Count-based replication.** Report worker, deterministic-retry,
local-teacher, and external-teacher resource counts separately. This mode does
not require a resource-weight manifest and is the currently available mode.

**B. Weighted-cost experiment.** Use weighted scoring or routing only after an
approved, frozen resource-weight manifest has a canonical digest, explicit
units and source/basis for every non-null weight, rationale, reviewer,
approval time, and approval basis. No default weights exist.

## Requirement before a weighted-cost Run 4

Before preregistering weighted cost, obtain complete external usage telemetry or
explicitly accept a count/time-only metric, establish stable operator-reviewed
resource identities, and freeze an approved weight manifest with units,
rationale, sources, and approval state. Until then, the defensible primary
cost metric remains separate direct counts—especially
`local_teacher_calls + external_teacher_calls`—with telemetry reported as
secondary evidence.

Telemetry collection readiness must not be described as weighted-cost
readiness. Count-based Run 4 is ready from an instrumentation perspective;
weighted-cost Run 4 remains gated on the approved manifest and complete enough
external resource evidence.

No model calls were made for this readiness work.
