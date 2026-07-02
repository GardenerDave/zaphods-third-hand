# LARQL Direct Edit Scale Ladder Closeout

This report parks the LARQL direct-edit path as bounded research evidence.
The direct-edit pipeline worked end to end mechanically: failure evidence was
converted into a continuation direction packet, then into a rank-1 delta
design, then into a safetensors delta artifact, then into a patched HF model
copy, and then into supervised reaudition.

What it did not do is change behavior in a useful way for the tested file-scope
task. The semantic reaudition stayed flat:

- target improvement count: 0
- target regression count: 0
- control regression count: 0
- no behavior-level improvement

## Scale ladder

| Scale label | Scale | Diff norm | Changed fraction |
| --- | ---: | ---: | ---: |
| scale1e2 | 1e-2 | 0.005207756534218788 | 0.01282795270284017 |
| scale3e2 | 3e-2 | 0.022328760474920273 | 0.03791888554890951 |
| scale1e1 | 1e-1 | 0.09307212382555008 | 0.11683901151021321 |
| scale3e1 | 3e-1 | 0.30268949270248413 | 0.2798132101694743 |

## Evidence summary

The tested layer-0 continuation rank-1 edit produced real tensor movement as
scale increased, but the reaudition did not translate that movement into
behavior-causal improvement on the file-scope task.

The strongest observed change was post-cast diffusion from 0.0052 at 1e-2 to
0.3027 at 3e-1, while generation-level behavior remained flat.

## B7 semantic result summary

- target improvement: 0
- target regression: 0
- control regression: 0
- no behavior-level improvement

## Bounded conclusion

The direct-edit pipeline mechanically works end-to-end, but the tested
layer-0 continuation rank-1 edit was not behavior-causal for the file-scope
task.

## Explicit non-claims

- no general LARQL success claim
- no behavior improvement claim
- no deployment or promotion claim
- no automatic failure-to-curriculum capture

## Recommended next status

LARQL is research-only unless and until causal module selection improves.

Prompt/scaffold steering remains the mainline product direction.
