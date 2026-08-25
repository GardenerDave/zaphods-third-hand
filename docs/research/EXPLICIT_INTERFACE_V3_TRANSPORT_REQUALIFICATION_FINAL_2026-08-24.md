# Explicit-Interface V3 Transport Requalification — Final

This final additive qualification preserves all earlier failed and partial
qualification evidence. V2 remains immutable and no V2/V3 experiment cases
were used.

## Final status

- `LOCAL_TRANSPORT_QUALIFIED=true`
- `EXTERNAL_TRANSPORT_QUALIFIED=true`
- New local qualification calls in the full requalification program: 1
- New external qualification calls in this final attempt: 1
- V2/V3 experiment calls: 0
- Repository mutation by supplier invocation: none

## Authentication and runtime precheck

`CODEX_HOME=/tmp/zth_v3_codex_home codex login status` reported
`Logged in using ChatGPT`. Redacted runtime metadata reported authenticated
file-backed ChatGPT-token state. No credential values, token hashes, or auth
file contents were recorded.

The external process ran with cwd `/tmp`, isolated temporary runtime state, the
preserved wrapper, `--sandbox read-only`, and no V2/V3 artifacts or task
context. Codex doctor reported unrelated model-refresh/network warnings, but
authentication was configured and the transport control completed successfully.

## External qualification

Exactly one invocation used:
`Return exactly: TRANSPORT_OK`.

- return code: `0`
- stdout: exactly `TRANSPORT_OK`
- model-produced response: observed
- Codex CLI: `0.146.0`
- wrapper SHA256: `2c5fcaf0727bdf466e21d660c927e63d23ecb67857949b2ef21e7e599297ceab`
- stdout SHA256: `52c39f2b1f4fa8585552879bc993f277904438f439a300241bf0d895a634139a`
- stderr SHA256: `3aec8674d33f25fbfe0486a4009e60f3e6ff8a6a025262ab13b2d641fe78a9b1`
- authentication mechanism type: file-backed ChatGPT tokens
- tools: not mechanically disabled; observations retained as best available

The stderr includes Codex model-refresh timeout diagnostics, but the direct
transport control returned successfully and no repository mutation occurred.

## Local qualification

The previous local result remains unchanged: endpoint
`http://192.168.1.16:8080/v1`, exact 30B identity from `/v1/models`, and one
successful `TRANSPORT_OK` response.

## Evidence locations

- Local requalification:
  `.work/model_size_supplier_floor/explicit_interface_v3_transport_requalification_2026-08-24/run_20260824T211500Z/`
- Final external requalification:
  `.work/model_size_supplier_floor/explicit_interface_v3_transport_requalification_2026-08-24/external_run_20260824T212000Z/`

`NEXT_DECISION=FREEZE_EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V3`
