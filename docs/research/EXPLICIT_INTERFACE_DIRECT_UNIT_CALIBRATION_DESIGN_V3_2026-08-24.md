# Explicit-Interface Direct Unit Calibration V3

Status: frozen and unexecuted.

This is a new calibration lineage for the explicit supplier-facing interface.
It preserves the 16 preregistered semantic cases from V2 while assigning new
V3 artifact and interface identities. No V2 response or score is transferred.

## Purpose and claim boundary

The experiment compares direct local and external supplier responses on
identical, explicit-interface messages. It is calibration evidence only. It
does not select a routing policy, qualify a supplier, or claim that either
supplier has been measured on the failed V2 transport path.

V2 remains characterized as
`LOCAL_AND_EXTERNAL_CAPABILITY_NOT_MEASURED_DUE_TO_TRANSPORT_FAILURES`.

The direct unit is supplier × capability family × V3 interface × direct
responsibility × validated direct artifact. There is no teacher/worker rescue,
retry, replay, or downstream repair.

## Frozen cohort and arms

The cohort contains eight `triage-routing` and eight
`unsupported-certainty` cases. The exact V2 semantic case content is preserved
as the preregistered case set; V3 changes only execution lineage and the
transport-aware protocol dimension. Each case has `local_teacher` and
`external_teacher` arms. The materialized supplier message UTF-8 bytes and
their SHA256 are identical across arms.

The fixed budget is 16 local and 16 external opportunities, 32 total. There
are no conditional extensions, retries, replays, resume operations, or
replacement calls.

## Qualified transport bindings

Local transport was qualified at
`http://192.168.1.16:8080/v1` with model
`Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`. External transport was qualified
with `/home/navigator/bin/zth-codex-teacher` at the frozen SHA, Codex CLI
`codex-cli 0.146.0`, authenticated isolated `CODEX_HOME=/tmp/zth_v3_codex_home`,
and cwd `/tmp`. These are preflight bindings, not supplier calls during
preflight. Tools are not claimed to be mechanically disabled; tool and
repository observations remain best-available observations.

## Validation dimensions

The V3 evaluator is frozen before outcomes. It reports transport, parsing,
required fields/types, explicit-interface validity, task semantics,
review-status validity, and `PROHIBITED_ACTIONS_NOT_OBSERVED` separately. V3
defines:

`PROTOCOL_VALID = TRANSPORT_VALID AND PROHIBITED_ACTIONS_NOT_OBSERVED`.

A transport/request error is a terminal transport disposition, not a captured
supplier response and not an imputed semantic failure.

## Acquisition firewall and lifecycle

The acquisition process consumes only the V3 acquisition projection and exact
supplier messages. It does not import or open evaluator semantics. Hashes for
scoring artifacts may be checked in preflight only. Raw evidence is sealed
only after all terminal arm artifact coverage and hashes validate, the raw
manifest is written, and lifecycle metadata is written. The final seal marker
is written last.

Execution is one-shot: PREPARED, atomically claim the experiment guard,
RUNNING, then calls. A second execution is rejected before RUNNING and before
supplier-opportunity artifacts. Every started opportunity has CALL_STARTED and
a terminal artifact, including transport failure evidence.

## Future closeout

After raw seal only, a separate closeout may load the frozen V3 evaluator and
evaluator cases. It will report family-specific direct rates and the two
descriptive views `MICRO_AGGREGATE_DIRECT_EXPLICIT_V3` and
`FAMILY_MACRO_AGGREGATE_DIRECT_EXPLICIT_V3`. No routing-policy winner is
computed by this calibration.

## Provenance

The source explicit-interface V2 freeze is preserved. Transport qualification
provenance is commit `46638a5ce8b461cd57676a1317a4a57d129c7d02`. V3 artifact
hashes, the pure evaluator hash, projection hash, and acquisition harness hash
are bound in the accompanying machine-readable freeze artifacts.

`NEXT_DECISION=EXECUTE_EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V3`
