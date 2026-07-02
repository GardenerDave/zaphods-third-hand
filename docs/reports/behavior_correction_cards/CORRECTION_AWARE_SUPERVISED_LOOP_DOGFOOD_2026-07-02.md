# Correction-Aware Supervised Loop Dogfood

This report closes the documented correction-aware loop for the live r5
dogfood pass.

ZTH converted a small-model file-scope failure into an explicit behavior
correction, produced corrected scoped output from a local 1.7B model, validated
it model-free, packaged it for supervised review, and recorded explicit
supervised acceptance without promotion or downstream mutation.

## What was accepted

The accepted corrected output was:

```json
{
  "allowed_targets": ["docs/README.md"],
  "held_targets": ["docs/ROADMAP.md"],
  "scope_expansion_required": true,
  "install_authorized": false,
  "registry_mutation_authorized": false,
  "reason": "docs/ROADMAP.md is plausible but not authorized and must be held out as it is not in allowed_files."
}
```

This accepts the corrected output as a reviewed artifact only.

It does not authorize editing `docs/README.md`.

It does not authorize promotion.

It does not train or tune a model.

It does not capture anything into failure curriculum.

It does not prove autonomous project understanding.

It is evidence of guided capability inside a supervised artifact chain.

## Key source artifacts

Behavior correction card:

- `docs/behavior_correction_cards/file_scope_hold_out_v1.json`

Scaffold dogfood:

- `.work/behavior_correction_scaffold_dogfood/file_scope_hold_out_v1_20260702/job_packet.json`
- `.work/behavior_correction_scaffold_dogfood/file_scope_hold_out_v1_20260702/rendered_scaffold/behavior_correction_scaffold.json`
- `.work/behavior_correction_scaffold_dogfood/file_scope_hold_out_v1_20260702/rendered_scaffold/behavior_correction_scaffold.md`

Prompt packet:

- `.work/behavior_correction_prompt_packet_dogfood/file_scope_hold_out_v1_20260702_v2/correction_aware_prompt_packet.json`
- `.work/behavior_correction_prompt_packet_dogfood/file_scope_hold_out_v1_20260702_v2/correction_aware_prompt_packet.md`

Model attempt:

- `.work/correction_aware_model_attempt_dogfood/file_scope_hold_out_v1_20260702_r5/model_attempt_record.json`
- `.work/correction_aware_model_attempt_dogfood/file_scope_hold_out_v1_20260702_r5/raw_model_output.txt`
- `.work/correction_aware_model_attempt_dogfood/file_scope_hold_out_v1_20260702_r5/status.log`
- `.work/correction_aware_model_attempt_dogfood/file_scope_hold_out_v1_20260702_r5/status_events.jsonl`

Validation:

- `.work/correction_aware_output_validation_dogfood/file_scope_hold_out_v1_20260702_r5_validator_fix/correction_aware_output_validation.json`
- `.work/correction_aware_output_validation_dogfood/file_scope_hold_out_v1_20260702_r5_validator_fix/correction_aware_output_validation.md`

Supervised review packet:

- `.work/correction_aware_supervised_review_packet_dogfood/file_scope_hold_out_v1_20260702_r5/supervised_review_packet.json`
- `.work/correction_aware_supervised_review_packet_dogfood/file_scope_hold_out_v1_20260702_r5/supervised_review_packet.md`

Decision record:

- `.work/correction_aware_supervised_review_decision_dogfood/file_scope_hold_out_v1_20260702_r5/supervised_review_decision_record.json`
- `.work/correction_aware_supervised_review_decision_dogfood/file_scope_hold_out_v1_20260702_r5/supervised_review_decision_record.md`

## Source hashes

From supervised review packet:

- `source_job_packet_sha256`: `a211a95251742582ef4395e12430831b887345853f6f8cb58a325f8d3ab6bedf`
- `source_prompt_packet_sha256`: `5a6b8855f13dfd41a994dcf29b0d2977927de52adf1ae28a26e92b7713e83608`
- `source_model_attempt_record_sha256`: `07b46d79e12751183d6bf07ccb187507d4d54e53e40fa8bd4435a06588ce8efa`
- `source_raw_output_sha256`: `74a6c25cd431aae852f92d7fde6533217e3b4e3891ae9703b42bc348b029e463`
- `source_validation_report_sha256`: `cc4a3a4852dc63463f21683b146ed9f1f665221f86ad27601876bc86fe8c5b10`

From supervised decision record:

- `source_supervised_review_packet_sha256`: `be3c8fd3a7418254b20514bb25947b321d1a3f53252561b896c0635b1c3a1f34`

## Commit lineage

- `5121706` Add behavior correction cards v1
- `6e42290` Add behavior correction scaffold renderer
- `8fe27e8` Dogfood behavior correction scaffold rendering
- `275c3c7` Add correction-aware prompt packet renderer
- `2301613` Add correction-aware model attempt runner
- `6f5cee0` Add correction-aware output validator
- `af3d6e2` Tighten correction-aware prompt packet facts
- `bcda436` Fix correction-aware validator reason negation
- `084b143` Add correction-aware supervised review packet
- `b2759eb` Tighten supervised review packet provenance
- `5da4c91` Add supervised review decision record
- `fe008c5` Fix supervised decision record source authority flags

## Failure and correction narrative

- r4 completed but produced the wrong scoped decision.
- r4 treated ROADMAP.md as authorized when only README.md was allowed.
- The validator correctly failed r4.
- Prompt packet facts were tightened in `af3d6e2`.
- r5 produced the corrected scoped decision.
- The validator initially false-positive flagged the negated reason text.
- `bcda436` fixed the reason-text negation heuristic without changing structural validation.
- r5 then validated with `validation_passed` and findings `[]`.
- A supervised review packet was rendered.
- An explicit decision record accepted the corrected output only.

## Authority boundary

- Model inference happened only in the authorized source model attempt.
- Validation was model-free.
- Review packet rendering was model-free.
- Decision record rendering was model-free.
- Supervised acceptance was recorded only by explicit decision.
- Promotion remained false.
- File edits remained false.
- Training remained false.
- Delta writing remained false.
- Model materialization remained false.
- Automatic failure-to-curriculum capture remained false.

## Why this matters

This is evidence that ZTH can turn a small-model failure into a bounded
correction artifact.

The system did not rely on automatic learning.

The system preserved provenance and authority boundaries.

The useful model behavior is guided capability inside a supervised workflow.
