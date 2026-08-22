# Capability Router V1.1 grounding slice

Status: frozen exploratory design; not production routing.

## Question

Can the Router V1 control loop derive plans from actual packet/world facts and
validate supplier consequences using a runtime success contract, without any
runtime read of evaluator `expected_*` fields?

## Runtime/evaluator separation

Preparation writes separate files:

- `runtime_task.json`: request plus independently supplied world facts;
- `vogon_triage_packet.json` and `orchestration_packet.json`;
- `planner_facts.json`: packet-derived planning facts;
- `capability_plan.json`: plan and coverage only;
- `success_contract.json`: frozen predicates over runtime facts/observations;
- `evaluator.json`: expectations used only by post-run closeout.

The live executor reads the first five classes and never loads `evaluator.json`.
Closeout scoring is a separate model-free phase.

## Packet grounding

Planner facts include actual triage fields (task type, allowed/held targets,
risk flags, output contract, validation hooks), orchestration fields (review
requirement and authority boundaries), the raw request, and independently
supplied world facts. The adapter does not merely rename `packet_inputs` and
does not copy expected route annotations.

## Success contracts

Contracts contain no worked model answer. The semantic contract requires:

- exact two-string structured output;
- action membership in the packet/world allowed-operation set;
- normalized object-expression equality with the requested target.

The deterministic contract states the canonical operand computation to run.
The computed result is the runtime result; it is not compared to an expected
policy answer during execution.

## Dependency-aware composition

Each executable step has `step_id`, `capability_id`, supplier, required input
names, produced output names, and `depends_on`. The target-binding step depends
on the semantic step's `action` and `object_expression` outputs and on the
packet's requested target. Missing inputs fail closed.

## Fresh matrix

The 8-task matrix contains 2 deterministic-only tasks, 4 semantic plus
deterministic tasks, one unqualified reference-entity task, and one unknown
tool-needed task. The final two fail closed without model calls.

## Lazy backend

The executor loads model/runtime/telemetry only when a complete frozen plan has
model steps. Deterministic and incomplete/review workloads are testable with a
model initializer that raises immediately if touched.

## Boundaries

This is a bounded oracle-free grounding slice. It does not add live tool
execution, production routing, automatic qualification promotion, V100/30B
inference, external calls, destructive actions, or SSH/admin authority.
