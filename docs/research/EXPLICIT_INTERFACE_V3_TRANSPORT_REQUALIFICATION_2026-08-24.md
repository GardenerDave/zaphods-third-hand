# Explicit-Interface V3 Transport Requalification

This additive attempt preserves the failed qualification at commit
`8e9d567e2898fe11231dcd563a0b66845228213d` and does not alter V2.

## Results

- `LOCAL_TRANSPORT_QUALIFIED=true`
- `EXTERNAL_TRANSPORT_QUALIFIED=false`
- New local qualification completions: 1
- New external qualification invocations: 0
- V2/V3 experiment calls: 0
- V2 characterization remains `LOCAL_AND_EXTERNAL_CAPABILITY_NOT_MEASURED_DUE_TO_TRANSPORT_FAILURES`.

## Local transport

A narrow LAN scan of documented model ports discovered `192.168.1.16` with
ports 8080 and 8081 open. The non-inference request:

`GET http://192.168.1.16:8080/v1/models`

returned exactly:
`Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`.

The Dev-side configuration now uses the concrete base URL explicitly. The
request-construction regression proves that the same base URL produces:

`http://192.168.1.16:8080/v1/chat/completions`

The one authorized completion used `Return exactly: TRANSPORT_OK` and returned
`TRANSPORT_OK` with status `ok`. The response SHA256 is
`52c39f2b1f4fa8585552879bc993f277904438f439a300241bf0d895a634139a`.

## External transport

The normal Codex CLI reports `Logged in using ChatGPT`. Redacted `codex doctor`
metadata reports file-backed authentication with stored ChatGPT tokens and no
stored API key. No key or token values were read or emitted.

The isolated writable runtime reports `Not logged in`; redacted doctor metadata
reports no Codex credentials. Because the available authentication is
file-backed rather than OS-keyring-backed, no credential file was copied into
the isolated runtime and no external completion was attempted.

Operator action required before external requalification:

```text
mkdir -p /tmp/zth_v3_codex_home
CODEX_HOME=/tmp/zth_v3_codex_home codex login
```

The operator should then perform a non-inference `CODEX_HOME=/tmp/zth_v3_codex_home
codex login status` check. This interactive login was not automated.

## Recorder hardening

The qualification harness now writes a `CALL_STARTED` artifact before every
authorized completion and a terminal artifact in a `finally` path, preserves
failure evidence, refuses existing run directories, and has model-free tests
for success, failure, path binding, and run refusal.

## Evidence

New local run:
`.work/model_size_supplier_floor/explicit_interface_v3_transport_requalification_2026-08-24/run_20260824T211500Z/`

- `/v1/models` response SHA256: `56a4a28d039d1e378d561319b17ae0da276c2806231105c6bbadd21979fb20a7`
- local response SHA256: `52c39f2b1f4fa8585552879bc993f277904438f439a300241bf0d895a634139a`
- local request URL: `http://192.168.1.16:8080/v1/chat/completions`
- harness SHA256: `053b7b282f8773842657f60e179dacd61e323d7cf278469fa163437eed50ab72`
- regression-test SHA256: `1147739f844f61f1bf100d1d985ad1169bfb31d777bff9ca1f41c5be58fc798f`

The prior failed qualification run and its raw evidence remain unchanged.

`LOCAL_TRANSPORT_QUALIFIED=true`
`EXTERNAL_TRANSPORT_QUALIFIED=false`
`NEXT_DECISION=FIX_FAILED_TRANSPORT_BEFORE_V3`
