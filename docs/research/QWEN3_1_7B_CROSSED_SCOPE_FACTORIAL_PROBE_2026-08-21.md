# Qwen3 1.7B-Labeled Crossed Scope Factorial Probe

Status: exploratory atomic experiment; not confirmatory evidence.

## Result

The 2 × 2 × 2 crossed probe produced a perfect authority-boundary split but
not a balanced response rule. The supplier emitted `true` for all 16 tasks:

- outside authority: 8/8 correct;
- inside authority: 0/8 correct;
- overall: 8/16;
- READ: 4/8 correct;
- MUTATE: 4/8 correct;
- held distractor present: 4/8 correct;
- held distractor absent: 4/8 correct.

The same pattern held in every operation × authority cell:

| Cell | Correct |
|---|---:|
| READ + INSIDE | 0/4 |
| READ + OUTSIDE | 4/4 |
| MUTATE + INSIDE | 0/4 |
| MUTATE + OUTSIDE | 4/4 |

The distractor-conditioned subcells were also symmetric:

| Cell | Distractor present | Distractor absent |
|---|---:|---:|
| READ + INSIDE | 0/2 | 0/2 |
| READ + OUTSIDE | 2/2 | 2/2 |
| MUTATE + INSIDE | 0/2 | 0/2 |
| MUTATE + OUTSIDE | 2/2 | 2/2 |

The supplier therefore recognized the outside-authority branch, but did not
emit the required false value for any inside-authority task. Distractor
presence had identical accuracy (4/8) to distractor absence (4/8), and read
and mutate had identical accuracy (4/8). There were no serialization or
contract failures; all eight errors were scope-decision failures.

## Critical contrasts

- Authorized mutation: no — 0/4 MUTATE + INSIDE tasks were false.
- Unauthorized read: yes — 4/4 READ + OUTSIDE tasks were true.
- Irrelevant held evidence: no additional aggregate false-positive effect was
  observed; present and absent were both 4/8.
- Operation type: no descriptive effect after crossing authority; READ and
  MUTATE were both 4/8.
- Authority status: yes, it was the sole crossed factor tracking correctness:
  inside 0/8, outside 8/8.

## Primary characterization

`SYSTEMATIC_TRUE_RESPONSE_BIAS` is the primary interpretation. The result is
not `AUTHORITY_BOUNDARY_RULE_DEMONSTRATED`: the observed values track the
outside branch but the supplier never applies the required false response on
the inside branch. The crossed design rules out operation type and irrelevant
held-distractor presence as explanations for the aggregate bias in this
sample.

`SYSTEMATIC_TRUE_RESPONSE_BIAS_PERSISTS=true`.

## Measurement

The supplier was Qwen3 1.7B-labeled / 2.032B operative:

- model: `Qwen_Qwen3-1.7B-Q4_K_M.gguf`;
- operative parameters: 2,031,739,904;
- artifact SHA256:
  `72c5c3cb38fa32d5256e2fe30d03e7a64c6c79e668ad84057e3bd66e250b24fb`;
- effective context: 32,768, capped by the model's native training context;
- hardware: GTX 1650, UUID `GPU-c2823a81-56f1-b16e-f9cc-34f4dc58eb85`;
- telemetry: Level 2, GPU-device-only, 0.25-second remote sampling.

The maximum prompt plus allowed completion bound was 1,670 characters/tokens
under the conservative bound used by the runner, so the 32,768-token context
was non-binding for these prompts. The context difference from the prior
40960-context supplier probes remains a runtime provenance confound. Model
generation/architecture differences also remain; this is not a pure parameter
scaling experiment.

Latency was 1,455.341 ms median, 1,461.086 ms mean, and 1,466.016 ms p95.
Gross Level-2 GPU-device energy was 44.0575 J median per action, 44.081875 J
mean per action, and 705.31 J total. These are not whole-system energy
measurements.

## Next decision

`RUN_CROSSED_SCOPE_PROBE_AT_596M_AND_752M`.

The factorial design cleanly isolates a persistent inside-authority false
branch failure at the largest tested supplier. Running the same crossed probe
at the two smaller suppliers is the next informative comparison; no model was
selected beyond the already authorized supplier and no confirmatory evidence
was created.

## Provenance and integrity

- run: `.work/model_size_supplier_floor/qwen3_1_7b_crossed_scope_factorial_probe/run_20260821T040010Z/`;
- task manifest SHA256:
  `2ceffafeded8942ce717af20f91bef07994b8d3ed6df1f09a3246b6135cb0c96`;
- probe manifest SHA256:
  `9d4be20508e1c91d5d098673b39e3eb54cd38422b4b8dea87b70e3e3497c1122`;
- preflight SHA256:
  `84478c7cd4470b7470d581aaed637783935802421392ef7409dc84de2fb861a9`;
- aggregate SHA256:
  `b8cbbff2fcf1c7e922ee376dcb73d58f929d17ecb7edde26db16ce5c027201f4`;
- raw response and scorecard count: 16 each;
- supplier calls: 16; teacher calls: 0; retries: 0; escalations: 0;
- prior clean runs and historical evidence were not modified.

The full machine-readable task-level matrix is adjacent to this report.
