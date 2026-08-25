# Explicit-Interface V3 Transport Qualification

This is infrastructure qualification only. V2 remains immutable at
`9145c17da7ce694bd55ba2c612a58029e75aa768` and retains the characterization
`LOCAL_AND_EXTERNAL_CAPABILITY_NOT_MEASURED_DUE_TO_TRANSPORT_FAILURES`.

## Results

- Local transport: `false`.
- External transport: `false`.
- Qualification invocations: one external invocation; zero local completion calls.
- V2/V3 experiment calls: zero.
- Repository mutation from the qualification: none.

### Local

The V2 divergence is in the Dev-side capture path. Preflight resolved and
validated a concrete endpoint, but the acquisition path passed the optional
`ZTH_CAPABILITY_TEACHER_BASE_URL` directly to `resolve_worker_spec()`. When that
override was absent, `icm_spec.py` fell back to its default
`http://<LAN_HOST>:8083/v1`, producing the sealed unresolved request URL.

The qualification harness now constructs the worker spec with the resolved
base URL and includes a model-free regression through `call_worker()` proving
that the completion URL is derived from that same URL. No configured endpoint
currently exposes the authoritative
`Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`: `config.env` exposes the 7B handoff
model at `http://192.168.1.13:8083/v1`, and the documented host/port probes did
not return `/v1/models`. Therefore no local completion was attempted.

The actual V2 placeholder request was:
`http://<LAN_HOST>:8083/v1/chat/completions`.
The regression's concrete non-placeholder construction is:
`http://192.168.1.13:8083/v1/chat/completions`.

### External

V2 failed before supplier response generation because the preserved wrapper used
Codex with a read-only sandbox and Codex could not initialize its local state.
For the single qualification invocation, the preserved wrapper was run from
`/tmp` with isolated writable `HOME`/`CODEX_HOME` runtime state. The state
initialization failure did not recur. The invocation reached the Codex service,
but returned exit code 1 with empty stdout and complete stderr showing repeated
`401 Unauthorized` responses and `Missing bearer or basic authentication`.
This is an authentication/configuration transport failure, not a semantic
supplier result. No model-produced response was preserved.

The wrapper still uses `--sandbox read-only`; that does not mechanically disable
tools. Tool and repository observations remain `BEST_AVAILABLE_OBSERVATION`.
The working directory was `/tmp`, outside the repository, and no repository
mutation was observed.

## V3 evaluator design note

The frozen V2 evaluator's `PROTOCOL_VALID` dimension can be true for a transport
failure because it only checks for prohibited-action markers. V3 should either
make `PROTOCOL_VALID` require `TRANSPORT_VALID`, or rename the independent
dimension to `PROHIBITED_ACTIONS_NOT_OBSERVED`. Local request errors should also
use an explicit transport-failure terminal disposition rather than being called
`RESPONSE_CAPTURED`.

## Evidence

Raw qualification evidence is preserved under:
`.work/model_size_supplier_floor/explicit_interface_v3_transport_qualification_2026-08-24/run_20260824T000000Z/`.

- External stdout SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- External stderr SHA256: `082fd9aa9fb027337dc870862e89a6df4119e105be956f7d8f1c965998123383`.
- Preserved wrapper SHA256: `2c5fcaf0727bdf466e21d660c927e63d23ecb67857949b2ef21e7e599297ceab`.
- Qualification harness SHA256: `c8c9b72cedf3ae4db2fe045518c94b85715aa68e0eb4d72b67b428247f08b9ea`.

`NEXT_DECISION=FIX_FAILED_TRANSPORT_BEFORE_V3`
