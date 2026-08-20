# Run 7 Escalation-Path Repair

Status: future-evaluation implementation repair; review-only; no production
routing authority.

## Confirmed defect

The Run 7 forensic analysis confirmed a lossy integration defect in the
external-recovery path. Direct external interventions used the shared
diagnostic/review teacher contract, whose parser preserves `teacher_diagnosis`,
`retry_guidance`, and `corrected_reference_output`. Run 7 escalation instead
sent a task-output-shaped request containing fields such as `allowed_targets`
and `held_targets`. The shared parser did not preserve those top-level fields,
so the escalation worker retry received only `{"teacher_parse_status":"passed"}`.

This was an implementation defect, not evidence that the frozen external
teacher lacked capability. The historical Run 7 raw artifacts and result remain
unchanged: control 20/20, final treatment 18/20, quality preservation false,
resource reduction true.

## Repair

`scripts/zth_run7_scope_escalation.py` now uses the proven shared
`_teacher_prompt` diagnostic/review-only contract for external escalation.
The local-first validation failure is represented as an additional failed
transition for diagnosis. The parsed teacher payload, including
`failure_classification`, `teacher_diagnosis`, `retry_guidance`, and
`corrected_reference_output`, is passed into the escalation worker retry.

The repair does not change the validator, authority boundary, escalation
trigger, intervention identity, model identities, thresholds, resource priors,
fixtures, or production routing. Teacher guidance remains advisory; the
deterministic validator remains the final capability check.

The escalation action now also writes `baseline_reference.json`, matching the
direct isolated-arm provenance contract. It is included in the existing
terminal artifact index and is therefore covered by binding and hash
verification on reuse.

The Run 7 preregistration driver binding was re-bound from the historical
driver implementation to the repaired future-evaluation implementation. The
historical execution directory remains immutable and is not reinterpreted or
re-executed.

## Model-free verification

Tests cover:

- semantic diagnostic guidance surviving parsing and escalation retry
  serialization;
- list-valued `allowed_targets` and `held_targets`, boolean
  `scope_expansion_required`, and string `review_status` remaining typed;
- regression against the former parse-status-only payload;
- semantic parity of direct and escalation guidance categories;
- indexed escalation `baseline_reference.json` provenance;
- existing local-pass, pre-escalation resume, post-escalation resume,
  artifact-corruption, binding-drift, infrastructure, and call-accounting
  behavior.

No model calls were made. No Run 7 raw evidence was changed.

## Future confirmation

The repair must be evaluated in a separately authorized future experiment.
Run 7 itself remains a failed quality-preservation result and is not
retroactively converted into evidence for the repaired path. No Run 8 is
designed or preregistered by this note.
