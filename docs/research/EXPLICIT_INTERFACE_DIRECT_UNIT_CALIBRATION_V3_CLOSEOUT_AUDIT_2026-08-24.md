# Explicit-Interface Direct Unit Calibration V3 Closeout Audit

The sealed acquisition was verified before evaluator loading. All 32
`CALL_STARTED` artifacts had durable terminal evidence; all 32 terminal-arm
artifact manifests and 160 stored file hashes recomputed successfully. The
raw seal marker was true, the lifecycle was `TERMINAL_COMPLETE`, and the
schedule recomputed to
`25d5107fdf23948a7419336e50386233be824a8d47574254c428699b5d2bbe61`.

The frozen evaluator and evaluator-case hashes matched their pre-execution
bindings. Evaluation imported the frozen V3 implementation only after the raw
integrity gate. No supplier, model, external inference, retry, or replay call
occurred during closeout.

The V3 transport correction succeeded: local and external transport each
produced 16/16 captured responses, with zero infrastructure failures. The only
failed direct-capability dimensions were five local triage
`TASK_SEMANTICS_VALID` checks. No routing-policy winner was computed.

V3 therefore provides observable explicit-interface direct-capability
calibration evidence for both suppliers in this 16-case cohort, subject to the
cohort and claim boundaries in the results artifact.
