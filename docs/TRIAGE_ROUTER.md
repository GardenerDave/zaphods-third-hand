# Triage / Router Packet Layer

The triage/router layer turns messy user input into a bounded, inspectable
triage packet. The packet is a recommendation record, not an authority grant.
Everything downstream (prompt patch selection, prompt packet assembly,
validation, review) consumes the packet under human supervision.

Pipeline position:

```
messy input
  -> deterministic router (local_harness/triage_router_rules.py)
  -> triage packet (validated by local_harness/triage_packet_schema.py)
  -> selected prompt patches (docs/PROMPT_PATCH_LIBRARY.md)
  -> bounded prompt packet / output contract
  -> validator hooks
  -> guided output artifact + provenance
```

No live model calls are made anywhere in this layer.

## Triage packet schema

Validated by `local_harness/triage_packet_schema.py`
(`validate_triage_packet`). Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `triage_id` | str | Non-empty identifier. |
| `messy_input` | str | The original, unmodified user input. |
| `normalized_intent` | str | One-line restatement of what the input appears to ask for. |
| `task_type` | str | e.g. `repo_patch`, `docs_update`, `presentation_outline`, `training_design`, `prompt_patch_workflow`, `triage_router_workflow`, `design_packet`. |
| `recommended_workflow` | str | Recommendation only. Must not contain execution/autonomy terms. |
| `confidence` | str | `low`, `medium`, or `high`. |
| `requires_clarification` | bool | True whenever the router is unsure or input is broad. |
| `bounded_outputs` | list[str] | The concrete artifacts the workflow is allowed to produce. |
| `allowed_targets` | list[str] | Paths/areas the workflow may touch. |
| `held_targets` | list[str] | Paths/areas explicitly withheld. May be empty, but must not overlap `allowed_targets`. |
| `risk_flags` | list[str] | Conservative risk labels (see below). |
| `recommended_prompt_patches` | list[str] | Patch IDs from the prompt patch library. Recommendations only. |
| `output_contract` | dict | Requires non-empty `format` (str) and boolean `requires_reason`. |
| `validation_hooks` | list[str] | Validator names that must run before the output is accepted. |
| `provenance` | dict | Requires non-empty `source`. Router-produced packets also record `router_rule_id` and `matched_keywords`. |

### Authority rejections

The validator rejects any packet that attempts to smuggle in authority:

* Forbidden keys anywhere in the packet: `execution_authority`,
  `auto_promote`, `auto_train`, `auto_curriculum_capture`,
  `lifecycle_authority`.
* Forbidden substrings in `recommended_workflow`: `execute`,
  `auto_execute`, `autonomous`, `auto_promote`, `auto_train`,
  `training_execution`, `auto_curriculum`.
* `allowed_targets` and `held_targets` overlap.

### Risk-flag requirements

`required_risk_flags_for_input(messy_input)` computes the minimum risk flags
a packet must carry for its input. Validation fails if any are missing:

| Input contains | Required flag |
| --- | --- |
| `training`, `fine-tune`, `finetune`, `lora`, `adapter` | `training_pipeline_ambiguity` |
| `prompt injection` | `prompt_injection_surface` |
| `orchestrat...` | `orchestration_scope_risk` |
| `everything`, `all of it`, `entire repo`, `whole repo` | `scope_creep` |

### Model-facing packets

`validate_triage_packet(packet, model_facing=True)` additionally requires
`output_contract.requires_reason == True`. Any packet intended to shape model
output must demand a reason and carry provenance. The deterministic router
always validates its own output in model-facing mode.

## Deterministic router

`local_harness/triage_router_rules.py` routes by keyword only. No model, no
heuristics beyond substring matching. Rules:

| Rule | Keywords | Recommended workflow | Task type |
| --- | --- | --- | --- |
| `route_training_design` | `lora`, `fine-tune`, `fine tune`, `training` | `training_design_packet_workflow` (design only, never execution) | `training_design` |
| `route_prompt_patch_library` | `prompt injection`, `prompt patch`, `failure mode` | `prompt_patch_library_workflow` | `prompt_patch_workflow` |
| `route_triage_router` | `router`, `triage`, `messy input`, `orchestration` | `triage_router_workflow` | `triage_router_workflow` |
| `route_presentation_outline` | `presentation`, `demo`, `talk` | `presentation_outline_workflow` | `presentation_outline` |
| `route_repo_patch` | `bug`, `fix`, `code`, `test` | `repo_patch_packet_workflow` | `repo_patch` |
| `route_docs_update` | `docs`, `readme`, `roadmap` | `documentation_planning_workflow` | `docs_update` |
| fallback `route_design_packet_fallback` | (none matched) | `design_packet_workflow` | `design_packet` |

### Downgrade behavior

The router is deliberately conservative:

* **Multiple rules match** (multi-domain input): downgrade to the fallback
  `design_packet` route, set `requires_clarification: true`, and merge the
  risk flags required for the input.
* **Broad/ambiguous markers** (`everything`, `all of it`, `entire repo`,
  `whole repo`, `tie it back together`, `got messy`, `somehow`): downgrade to
  the fallback route, set `requires_clarification: true`, force
  `confidence: "low"`, and add `scope_creep`.

Every packet carries baseline held targets (`production automation`,
`automatic curriculum capture`, `automatic promotion`) and baseline
validation hooks (`allowed_held_target_separation`, `required_reason`,
`no_execution_authority`).

### Forbidden router outputs

The router refuses to emit a packet whose rendered JSON contains any of:
`execute this command`, `modify arbitrary files`, `train an adapter`,
`auto-add failure to curriculum`, `promote a patch automatically`, or
repo-wide certainty claims. This is enforced at render time in addition to
schema validation.

## CLI usage

Validate a packet:

```bash
python3 local_harness/triage_packet_schema.py \
  --packet examples/triage_packets/triage_example_001.json \
  --model-facing
```

Route a messy input:

```bash
python3 local_harness/triage_router_rules.py \
  --messy-input "Prepare a demo talk about the harness." \
  --triage-id triage_demo_001 \
  --out /tmp/triage_demo_001.json
```

## Examples

* `examples/triage_packets/triage_example_001.json` — broad multi-domain
  LoRA / prompt-injection input, downgraded to `design_packet` with
  clarification required.
* `examples/triage_packets/triage_example_002.json` — narrow repo patch
  request with bounded targets.

## What this layer may produce

* Triage packets (recommendations, risk flags, bounded outputs).
* Recommended prompt patch IDs (see `docs/PROMPT_PATCH_LIBRARY.md`).
* Output contracts and validation hook lists.

## What this layer must never produce

* Execution commands or execution authority.
* Authority to modify arbitrary files.
* Training or adapter execution (only *design* packets).
* Automatic curriculum capture from failures.
* Automatic patch promotion.
* Repo-wide certainty claims.

## Non-goals

* No live model calls.
* No autonomous execution or scheduling.
* No automatic promotion, training, or failure-to-curriculum capture.
* No replacement for human review; the packet is an input to supervision,
  not a substitute for it.
