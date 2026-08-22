# First end-to-end capability-router vertical slice V0

## Outcome

`FIRST_END_TO_END_CAPABILITY_ROUTER_LOOP=true`

This exploratory fixture-backed slice demonstrated all three required control
flow branches without modifying production routing, granting authority,
promoting a capability, touching the V100/30B runtime, or making an external
tool call:

1. deterministic code route with zero model calls;
2. bounded semantic extraction routed to the Qwen3 1.7B-labeled / 2.032B
   operative supplier and followed by deterministic validation;
3. unqualified capabilities routed fail-closed to `ready_for_review`.

## Reused components

The slice reused `route_messy_input` and the existing triage packet schema,
`assemble_orchestration_packet` and its validator, the existing
`examples/prompt_patches` library, the local structured-call harness, the
frozen Qwen3 1.7B runtime binding, and Level-2 GTX1650 device-only telemetry.
The new driver is an experimental adapter that adds capability decomposition,
registry lookup, route traces, and fixture scorecards; it is not a replacement
for the existing packet machinery.

## Metrics

| Metric | Result |
|---|---:|
| Tasks terminally correct | 8/8 |
| Router supplier choice correct | 8/8 |
| Deterministic/no-model opportunities avoided | 2/2 |
| Semantic 1.7B routes correct | 4/4 |
| Unsupported capabilities failed closed | 2/2 |
| Unnecessary model calls | 0 |
| Unnecessary escalations | 0 |
| Validator disagreements | 0 |
| Duplicate calls | 0 |
| Final review states | 2 |
| Total model calls | 4 |
| Model calls avoided | 4 |
| Qwen3 1.7B calls | 4 |
| 30B calls | 0 |
| External calls | 0 |

The two deterministic tasks used `DETERMINISTIC_CODE`. The four direct-entity
semantic tasks used the qualified exploratory minimal action/object supplier.
The two unsupported tasks selected `REVIEW_OR_ESCALATION` and did not call a
model.

## Model-path validation

All four semantic model responses were parse-valid and contract-valid. Action,
object-expression, and conservative normalized direct-target binding were
correct on 4/4 model routes. The model was given only the bounded semantic
atom; deterministic code retained equality and downstream validation.

## Route traces and provenance

Each task has plain-file `fixture.json`, `vogon_triage_packet.json`,
`orchestration_packet.json`, `router_packet.json`, `route_trace.json`, and
`scorecard.json` under:

`.work/capability_router_vertical_slice_v0/run_20260822T101000Z/`

Model tasks additionally preserve `semantic_prompt.txt`, `response.json`,
`validation.json`, and `power_samples.json`.

## Runtime and resources

- Model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`
- Operative parameters: `2031739904`
- Artifact SHA256: `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`
- Effective/training context: `32768/32768`
- GPU: GTX 1650, `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`
- Telemetry: Level 2, `gpu_device_only`, 0.25-second sampling
- Model-route latency mean/median/p95: 1968.584 / 1946.151 / 2136.724 ms
- Model-route gross energy: 233.5925 J total; 58.3981 J mean per call
- Idle baseline energy: 220.78 J over 30.0018 seconds

Energy and latency are descriptive measurements only; this slice does not
infer supplier causality from routing branch.

## Bounded interpretation

The demonstrated architecture is:

messy input -> existing bounded packet -> capability decomposition -> empirical
registry -> deterministic code or bounded model or review -> validation ->
scorecard/provenance -> terminal result.

This is `FIRST_END_TO_END_CAPABILITY_ROUTER_LOOP`, not a generalized-agent
capability claim. Registry statuses remain supervised evidence labels and are
not automatically changed by this run.

## Execution invariants

- Supplier model calls: 4
- Teacher calls: 0
- Retries: 0
- Escalations: 0
- Adaptations: 0
- 30B/V100 calls: 0
- External calls: 0
- Production routing changed: false
- Automatic qualification promotion: false

## Provenance hashes

- Authoritative prior closeout: `caa0c6ac8921b33708fe22c6837a5786139c5fe8`
- Freeze commit: `41b3d34b14cd7e1e5558444844a57a99bde8a875`
- Run manifest SHA256: `5521320326760b48ec289798ea700c9d29231126e06d0e9cb217a37f8657f4e1`
- Task manifest SHA256: `ee66fa6e7ddea303e498eaf6d48621e55a7c0339e8818bee3efb579f25b09a42`
- Registry SHA256: `f332d303b42de2c4cba3756210baf26c04dce1d33a724a2ebd59726914a5499f`
- Semantic schema SHA256: `485cfbe70878c4f33f08b7ed71ddade9b75c8d6f5b0e3258bb280b38b313f320`

## Next boundary

No next experiment or production integration is executed by this closeout.
The vertical slice establishes control-flow evidence only.
