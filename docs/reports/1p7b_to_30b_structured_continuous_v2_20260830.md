# Structured Continuous Handoff V2

Experiment: `1p7b_to_30b_structured_continuous_v2_20260830`

Implementation HEAD: `0d9c91d42b84d2e73c1d1707a63dac3c820018a9`

This run used the frozen structured Worker-A configuration from `1p7b_worker_a_structured_v2_20260830` and the hardened Worker-B one-shot provenance path.

## Worker A

Endpoint: `http://192.168.1.16:8081/v1`

Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`

Observed context: `32768`

Worker-A patch selection:

1. `scope_boundary_v1`
2. `unsupported_certainty_v1`
3. `output_contract_v1`
4. `allowed_held_mapping_v1`
5. `required_fields_boolean_v1`

Structured schema SHA: `8a0eefccc8738cb56dbd83b9a908ed459f865149cd6482c5db767e81c3e65b59`

Worker-A prompt SHA: `078ef3964f5abae4a04446c9c088658312456d3e5fbdbd20f085092a9465f730`

Worker-A request-body SHA: `a5616709c305425ba8430026732efd967cb469ffafb09a410ba0e66292962117`

Worker-A raw-response SHA: `58f62a2f81dfcf90b8cb385b8cf09501e25f4d49fa8f2fec6915accea60f2a5b`

Captured provenance: `PASS`

Validation checks:

- `parse_json`: passed
- `required_fields`: passed
- `required_field_types`: passed
- `allowed_held_target_separation`: passed
- `held_target_preservation`: passed
- `target_authority`: passed
- `requires_reason`: passed

Complete Worker-A contract: `PASS`

## Review, gate, handoff

Explicit review: `accepted`

Gate: `allowed`

Handoff: `prepared`

Transaction lifecycle: `HANDOFF`

Next worker: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`

Worker-A result bound into continuation: `PASS`

## Worker B

Offline preflight: `PASS`

Frozen continuation SHA: `681a4c72c25fb91e22b536919c9d5fa30c282a7ad85f9e350878e67f59308664`

Frozen continuation byte length: `5965`

Offline rendered request SHA: `2391defa3ea8971528aebb53e9c7c395bea18c7edce05d05113a93a672bccec9`

Offline rendered request byte length: `6492`

Immutable intent SHA: `88e350efa2fe12eecd05b6e0f7250f4d75d24ebf64b35d59eaf73a67f223a3d5`

Transport event log:

1. `transport_started`
2. `response_received`
3. `completed`

Worker-B request-body SHA: `2391defa3ea8971528aebb53e9c7c395bea18c7edce05d05113a93a672bccec9`

Worker-B metadata SHA: `207a3036cdf26503f554565ad1e2e87f7591ec02cae1bd79e961b6548099bc84`

Worker-B raw-response SHA from transport log: `4fb74ffb95eebf30cd204454415c1f95a07ebb1a581fa0d910c93ceb82e2cca3`

Worker-B downstream production: `PASS`

The 30B response produced the downstream cleanup plan directly, with:

- ordered concrete actions
- affected files/components
- validation criteria
- held work preserved as inactive

Authority preservation across handoff: `PASS`

Continuous lineage: `PASS`

Complete experiment: `PASS`

## Evidence preservation

Tracked evidence mirror:

- `docs/reports/evidence/1p7b_to_30b_structured_continuous_v2_20260830/source_run/`
- `docs/reports/evidence/1p7b_to_30b_structured_continuous_v2_20260830/archive_manifest.json`
- `docs/reports/evidence/1p7b_to_30b_structured_continuous_v2_20260830/worker_b_rendered_request.json`

The preserved `.work` source run remains unchanged.

## Conservative milestone statement

Successful supervised continuous-lineage structured 1.7B -> ZTH -> 30B production handoff.
