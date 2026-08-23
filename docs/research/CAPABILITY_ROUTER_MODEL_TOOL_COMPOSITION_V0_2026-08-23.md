# First bounded MODEL -> TOOL -> OBSERVATION -> REPLAN closeout

This fresh exploratory slice preserves the prior tool-loop evidence and does
not modify or rescore historical artifacts.

## Preserved prior milestone

```text
BOUNDED_READ_ONLY_TOOL_SUPPLIER_DEMONSTRATED=true
SINGLE_OBSERVATION_REPLAN_LOOP_DEMONSTRATED=true
REQUEST_GROUNDED_TOOL_REQUIREMENT_DERIVATION_DEMONSTRATED=true
FIRST_BOUNDED_ADAPTIVE_AGENT_LOOP=true
```

Prior additive boundaries remain:

```text
SUCCESS_CONTRACT_ARTIFACTS_GENERATED=true
SUCCESS_CONTRACT_RUNTIME_ENFORCEMENT_DEMONSTRATED=false
TOOL_AUTHORITY_ENFORCEMENT_DEMONSTRATED=true
TOOL_PLAN_AUTHORITY_PROVENANCE_LABEL_MISMATCH=true
```

The fresh driver corrected authority provenance to
`ENVIRONMENT_AUTHORITY_RECORD` and used executable success-contract
evaluation for terminal decisions.

## Fresh result

| Metric | Result |
|---|---:|
| Tasks correct under evaluator | 5/6 |
| Plan-0 requirements correct | 6/6 |
| Plan-1 requirements correct | 5/5 applicable |
| Plan-2 requirements correct | 5/5 applicable |
| Model outputs parse-valid | 4/4 |
| Model outputs contract-valid | 4/4 |
| Semantic outputs safely bound | 2/4 |
| MODEL -> TOOL transitions | 2/3 expected successful routes |
| Authorized tool calls | 2/2 planned |
| Valid observations | 2/2 tool calls |
| TOOL -> deterministic transitions | 2/2 |
| Full MODEL -> TOOL -> deterministic chains | 2 |
| Success contracts evaluated | 6/6 |
| Predicate-failing contracts | 2 |
| Terminal success | 3/6 |
| Ready for review | 3/6 |
| Semantic binding failures | 2 |
| Tool authority denials reached | 0 |
| Unsafe downstream tool calls prevented | 2/2 |
| REPLAN_STALLED | 0 |
| Duplicate model/tool calls | 0/0 |
| Unnecessary model/tool calls | 0/0 |
| 30B/V100 calls | 0 |
| External calls | 0 |
| Runtime expected-field reads | 0 |
| Model output granted authority | 0 |

The two successful chains observed existing repository targets and then
replanned to deterministic existence policy. The deterministic control also
succeeded without model or tool use. The unsupported service request failed
closed before inference.

## Failure containment

The absent-target task returned a contract-valid object expression but selected
`exists` as its action. Because `exists` was not in the frozen observation
operation vocabulary, the router stopped after the model step and made zero
tool calls. This is a preserved semantic binding failure, not a repaired
absence observation. The unauthorized-target task also failed before tool
execution because its semantic output did not satisfy the frozen action/object
contract. No model output granted authority.

The run therefore demonstrates the MODEL→TOOL→OBSERVE→REPLAN control path for
two existing-target tasks, but does not demonstrate a valid absent-file tool
observation in this fresh slice.

## Runtime architecture

```text
MODEL: action + object_expression
CODE: capability derivation, exact equality, authority membership,
      tool validation, observation policy, success-contract evaluation
TOOL: exact-authorized repository-relative metadata only
```

No contents, writes, shell, network, process control, or V100/30B execution
were used.

## Provenance

- authoritative prior closeout: `c53396addf97a50ec92d1c63b930703a725648bd`;
- fresh freeze commit: `51c9cb2`;
- fresh run: `.work/model_size_supplier_floor/capability_router_model_tool_composition_v0/run_20260823T052541Z/`;
- model: Qwen3 1.7B-labeled / 2,031,739,904 operative parameters;
- model calls: 4 distinct tasks;
- tool calls: 2;
- teacher/retry/escalation calls: 0.

For the preserved prior tool run, the execution-driver hash and later
closeout-driver hash remain distinct:

```text
EXECUTION_DRIVER_SHA256=4165ab93df9a9439a8002cef72c6d8de5b8b296124d31beec6a69ecdd57b15b4
CLOSEOUT_DRIVER_SHA256=72a52e0f3445fe6d5c0fd1c7ea4f4d51ff2f426da998f6006e62fff43b585245
```

Those hashes do not describe this fresh wrapper's execution identity and no
prior calls were replayed.

The reused engine's run-local aggregate contains a task-ID-specific
`unauthorized_tool_calls_prevented` counter from the earlier experiment. The
metrics above are the additive corrected closeout computed from this run's
preserved scorecards and runtime traces; raw responses and run artifacts were
not changed.

## Resource description

Level-2 GTX1650 `gpu_device_only` model telemetry: median latency 1952.930 ms,
mean 2348.808 ms, p95 3678.144 ms; total gross device energy 262.520 J across
four model calls. Tool execution was local bounded Python and had no GPU
energy sample. These are descriptive measurements only.

## Markers

```text
MODEL_TO_TOOL_CAPABILITY_TRANSITION_DEMONSTRATED=true
TOOL_TO_DETERMINISTIC_REPLAN_DEMONSTRATED=true
SUCCESS_CONTRACT_RUNTIME_ENFORCEMENT_DEMONSTRATED=true
FIRST_MODEL_TOOL_ADAPTIVE_COMPOSITION_LOOP=true
NEXT_DECISION=ADD_FAILURE_DIAGNOSIS_AND_BOUNDED_TEACHING_INTERVENTION
```

These markers describe bounded control flow, not general autonomy, production
readiness, generalized tool use, self-training, or automatic promotion.
