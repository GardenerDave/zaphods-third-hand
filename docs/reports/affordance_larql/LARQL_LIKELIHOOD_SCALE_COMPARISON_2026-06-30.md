# LARQL Likelihood Scale Comparison

This report adds a packet-only comparison stage across multiple teacher-forced likelihood runs.

What this stage does:

- reads multiple teacher-forced likelihood comparison JSON files across scales;
- compares per-probe correction-margin deltas by scale;
- aggregates target probes separately from control and regression probes;
- checks whether target improvement is monotonic;
- checks whether control regression is monotonic;
- writes a supervised comparison packet and recommended next step.

What this stage does not do:

- it does not run model inference;
- it does not train;
- it does not write a new patch or delta;
- it does not promote or deploy anything.

This stage is evidence, not authority. It is meant to prevent blind scaling decisions by separating target gains from control and regression movement.
