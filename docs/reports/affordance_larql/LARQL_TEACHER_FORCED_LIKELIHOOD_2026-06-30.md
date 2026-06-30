# LARQL Teacher-Forced Likelihood

This report adds a teacher-forced likelihood diagnostic after unchanged behavioral reaudition and template-token logit sensitivity.

What this stage does:

- reads a reviewed patched-model materialization record;
- reuses the same bounded LARQL probe prompts;
- scores corrected JSON continuations and failure-style JSON continuations by teacher-forced log likelihood;
- compares correction-vs-failure likelihood margins between the base model and the patched model;
- writes a reviewable diagnostic record and comparison packet.

What this stage does not do:

- it does not generate;
- it does not train;
- it does not perform another weight edit;
- it does not write another delta artifact;
- it does not materialize another patched model;
- it does not promote or deploy anything.

This stage is evidence, not authority. It is intended to measure whether the patched model moves probability mass toward corrected JSON decisions even when generated outputs remain unchanged.
