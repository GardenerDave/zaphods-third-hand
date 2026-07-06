# Prompt Patch Library

The prompt patch library is a model-free catalog of reusable prompt
corrections. Each patch connects a known failure mode to a conservative
prompt correction and the validator behavior that makes the correction
checkable.

```text
failure mode -> prompt correction -> expected validator behavior
```

The library is bounded infrastructure. It does not call models, train
adapters, capture failures into curricula, or promote patches automatically.

## What a prompt patch is

A prompt patch is a small JSON record:

```json
{
  "patch_id": "scope_boundary_v1",
  "title": "Scope boundary enforcement",
  "status": "candidate",
  "failure_signature": [
    "model includes plausible but unauthorized targets",
    "model treats related files as allowed files"
  ],
  "applies_to": {
    "stage": ["target_selection"],
    "task_type": ["repo_patch", "docs_update", "triage"],
    "model_size": ["small", "mid", "any"]
  },
  "prompt_delta": "Only include targets explicitly listed in allowed_targets. Related or plausible files must go in held_targets.",
  "required_output_fields": [
    "allowed_targets",
    "held_targets",
    "scope_expansion_required",
    "reason"
  ],
  "validator_expectations": [
    "no held target may appear in allowed_targets",
    "scope_expansion_required must be true when requested work requires held targets"
  ]
}
```

Field notes:

- `patch_id` is stable and unique within a library.
- `status` is one of `candidate`, `active`, or `deprecated`. Status changes
  are supervised decisions, not automatic behavior.
- `failure_signature` describes the observed failure in plain language and is
  keyword-searchable.
- `applies_to.stage` values are limited to: `intake`, `triage`,
  `target_selection`, `prompt_assembly`, `output_contract`, `validation`,
  `review`.
- `applies_to.task_type` may include `any` as a wildcard.
- `prompt_delta` is the text block that gets rendered into a prompt packet.
- `required_output_fields` and `validator_expectations` are what downstream
  model-free validators check.

Patches must not carry authority fields. `auto_train`, `auto_promote`,
`auto_curriculum`, and `execution_authority` are rejected at validation time.

## Seed patch families

Seed examples live in [`examples/prompt_patches/`](../examples/prompt_patches/):

| Patch | Failure family |
| --- | --- |
| `scope_boundary_v1` | Plausible-but-unauthorized target inclusion |
| `absence_of_evidence_v1` | Failed search treated as proof of absence |
| `unsupported_certainty_v1` | Repo-wide certainty without evidence |
| `placeholder_leakage_v1` | Template placeholders leaking into output |
| `output_contract_v1` | Structured-output contract violations |
| `reason_required_v1` | Recommendations without justification |
| `stop_condition_quality_v1` | Continuing past the requested scope |

All seed patches start as `candidate`. Promotion to `active` is a supervised
review decision recorded outside the library.

## Using the library

```bash
python3 local_harness/prompt_patch_library.py \
  --patch-dir examples/prompt_patches \
  --task-type triage \
  --render
```

Programmatic use:

```python
from local_harness.prompt_patch_library import PromptPatchLibrary, render_prompt_deltas

library = PromptPatchLibrary()
library.load_dir(Path("examples/prompt_patches"))
selected = library.filter_by_stage("target_selection")
prompt_block = render_prompt_deltas(selected)
```

Selection behavior:

- Filter by stage, task type, or failure-signature keyword.
- `deprecated` patches are excluded from selection unless
  `include_deprecated=True` is passed explicitly.
- Rendering preserves patch IDs so provenance survives into the prompt packet.
- Rendered blocks state explicitly that patches grant no execution,
  promotion, training, or curriculum-capture authority.

## Relationship to triage routing

The triage router ([`docs/TRIAGE_ROUTER.md`](TRIAGE_ROUTER.md)) recommends
patch IDs in its `recommended_prompt_patches` field. The recommendation is
reviewable metadata. An operator or supervised workflow resolves those IDs
against this library when assembling a prompt packet.

## Non-goals

- No live model calls.
- No automatic training or failure-to-curriculum capture.
- No automatic patch promotion or deprecation.
- No claim that a patch fixes a failure; validators and supervised review
  decide that per run.
