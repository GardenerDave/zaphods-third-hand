# Decomposition Telemetry 2026-08-31

## Recorded observations

### semantic-router-per-property-recovery-20260831

- Parent task: multi-label proposition extraction
- Bifurcation signal: natural-case failures despite synthetic success
- Proposed decomposition: per-property classification
- Frozen variables: candidate prose, gold, endpoint, temperature
- Prediction: recover A1/A2 on the frozen natural corpus
- Observed outcome:
  - 30B: A1/A2 recovered; 4/4 natural exact
  - 1.7B: A1/A2 exact; 9/11 overall exact
- Capability note: smaller-model sufficiency observed after decomposition; pre-decomposition smaller-model requirement remained unmeasured
- Useful: yes

### transport-context-residual-20260831

- Parent task: per-property semantic classification
- Bifurcation signal: two transport-context misses remained on the 1.7B comparison
- Proposed decomposition: cross-property / distractor context isolation
- Frozen variables: queried property, candidate prose, gold, schema
- Observed outcome: P4 correct; P2 and P6 transport-context cases missed
- Capability note: candidate hidden variable may be cross-property / distractor context
- Useful: not yet determined

## Interpretation

Bifurcation is a signal to investigate decomposition, not proof that decomposition is required.

The telemetry is recorded as shadow evidence only. It does not grant production authority or route control.
