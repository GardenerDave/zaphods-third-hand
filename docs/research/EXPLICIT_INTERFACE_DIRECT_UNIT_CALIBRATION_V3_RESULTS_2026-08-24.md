# Explicit-Interface Direct Unit Calibration V3 Results

Status: closed model-free from sealed acquisition evidence.

## Provenance and transport

- Execution-boundary commit: `442ff0a875bc09135aeaf57193fa97f753c68115`
- Run: `.work/model_size_supplier_floor/explicit_interface_direct_unit_calibration_v3/run_20260824T225000Z`
- Schedule SHA256: `25d5107fdf23948a7419336e50386233be824a8d47574254c428699b5d2bbe61`
- Execution harness SHA256: `b51bb6458f2a1708928a3f9e657213ed622ed2e8332a652a5db54ea74e36299d`
- Evaluator SHA256: `3922879d7c740531d65c0af06b1d9fb0a667357867736783d0ccd6ccd20d5eda`
- Evaluator-case SHA256: `91454cc877dcb27805fdc6288d1b7753bd079273babc7663cb334a79fe114698`

Acquisition was `TERMINAL_COMPLETE`: 32/32 responses were captured, with 16
local and 16 external responses, zero infrastructure failures, zero retries,
zero replays, and raw seal/hash coverage 32/32. Thus semantic capability was
observable for both suppliers in this V3 cohort. V2 remains independently
characterized as `LOCAL_AND_EXTERNAL_CAPABILITY_NOT_MEASURED_DUE_TO_TRANSPORT_FAILURES`.

## Frozen evaluator dimensions

`PROTOCOL_VALID = TRANSPORT_VALID AND PROHIBITED_ACTIONS_NOT_OBSERVED`.

| Family / supplier | Transport | Parse | Required fields | Field types | Interface | Task semantics | Review status | Prohibited actions not observed | Protocol | Direct capability |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| triage / local | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 3/8 | 8/8 | 8/8 | 8/8 | 3/8 |
| triage / external | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| unsupported-certainty / local | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| unsupported-certainty / external | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |

Supplier totals:

- local: 11/16 direct capability valid (68.75%);
- external: 16/16 direct capability valid (100%).

Descriptive aggregates:

- `MICRO_AGGREGATE_DIRECT_EXPLICIT_V3`: local 11/16 (68.75%), external 16/16 (100%);
- `FAMILY_MACRO_AGGREGATE_DIRECT_EXPLICIT_V3`: local 68.75% (triage 37.5%, unsupported-certainty 100%), external 100% (both families 100%).

## Matched-pair summary

Across 16 byte-matched cases: both pass 11, local only 0, external only 5,
both fail 0. Triage has both pass 3 and external only 5; unsupported-certainty
has both pass 8.

The five local failures were all `TASK_SEMANTICS_VALID` failures in triage;
no transport, parsing, structural contract, review-status, or protocol
dimension failed.

## Interpretation boundary

V3 directly measures the local supplier’s and external supplier’s ability to
produce valid direct artifacts under this explicit interface and frozen case
cohort. External direct capability was observable on all 16 cases; local
direct capability was observable on all 16, with five triage semantic failures.
The descriptive matched comparison is 16/16 external versus 11/16 local.

This is calibration-cohort evidence only. It does not establish general coding
ability, population-level superiority, routing-policy superiority, or supplier
qualification.

Evaluation calls: supplier 0, model 0, external inference 0.
