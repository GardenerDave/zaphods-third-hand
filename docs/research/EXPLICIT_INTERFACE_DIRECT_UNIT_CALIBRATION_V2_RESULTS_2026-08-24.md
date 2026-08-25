# Explicit-Interface Direct Unit Calibration V2 — Results

This closeout evaluates the sealed acquisition exactly once with the frozen V2
evaluator. No acquisition, retry, replay, repair, or supplier/model call was
performed during closeout.

## Provenance and integrity

- Run: `.work/model_size_supplier_floor/explicit_interface_direct_unit_calibration_v2/run_20260824T000000Z`
- Schedule SHA256: `6cd43015d5cdb40034c073bc6185ea70b24d77e75ad5623954ebbd8fe981e121`
- Evaluator SHA256: `db067b700711c91c8a22877a7b8170c517640b9f5e1723f8041d5b4a44f5d9fb`
- Evaluator-case artifact hash matched the authoritative V2 freeze.
- Acquisition: `TERMINAL_COMPLETE`, 32/32 terminal arms, raw seal true.
- Terminal per-arm artifact-hash coverage: 32/32, recomputed successfully.
- Retries/replays: 0/0.

## Frozen evaluator dimensions

The exact evaluator was applied to all 32 terminal arm records. Counts are
valid/total:

| Family | Supplier | Transport | Parse | Required fields | Field types | Interface | Task semantics | Review status | Protocol | Direct capability |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| triage-routing | local | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 8/8 | 0/8 |
| triage-routing | external | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 8/8 | 0/8 |
| unsupported-certainty | local | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 8/8 | 0/8 |
| unsupported-certainty | external | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 | 8/8 | 0/8 |

Micro aggregate direct capability:

- local: `0/16`
- external: `0/16`

Family-macro aggregate direct capability:

- local: `0.0%`
- external: `0.0%`

No routing-policy winner was computed.

## Transport distinction

The evaluator’s zero direct-capability counts must not be read as 32 semantic
task failures.

- Local: 16 response artifacts were captured, but every metadata status was
  `request_error`, with the same name-resolution error and preserved request
  URL `http://<LAN_HOST>:8083/v1/chat/completions`. No valid supplier response
  was observed.
- External: all 16 opportunities ended `EXTERNAL_NONZERO_EXIT`, return code 1,
  empty stdout, and no model-produced response. The normalized stderr signature
  was identical in all 16 cases: Codex CLI failed to initialize its in-process
  app-server client because the read-only filesystem prevented initialization.

Therefore:

`LOCAL_AND_EXTERNAL_CAPABILITY_NOT_MEASURED_DUE_TO_TRANSPORT_FAILURES`

V2 did not successfully test the intended local-versus-external capability
comparison. The result is transport/configuration evidence, not supplier
semantic incompetence evidence.

## Claim boundary and next decision

This run does not establish local or external semantic capability, supplier
superiority, interface competence, or any population-level result. The sealed
raw evidence remains unchanged and no response was repaired or imputed.

`NEXT_DECISION=DESIGN_EXPLICIT_INTERFACE_V3_TRANSPORT_CORRECTION`
