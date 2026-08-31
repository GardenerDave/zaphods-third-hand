# Semantic Property Classification Frozen Measurement

## Frozen Experiment

- Preregistration commit: `dc4c4a2a5010ebcc291978edb4a2a06195790de9`
- Endpoint: `http://192.168.1.16:8080/v1`
- Model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- Temperature: `0`
- Max completion tokens: `64`
- Probe: `local_harness/semantic_property_classification_probe.py`
- Output directory: `.work/semantic_property_classification_20260831_frozen_v1`
- Model calls: `11`

## Frozen Cases

Synthetic:

- `p1_semantic_capability_established`
- `p2_transport_not_asserted`
- `p3_semantic_capability_not_established`
- `p4_transport_established`
- `p5_semantic_capability_not_asserted`
- `p6_transport_established`
- `p6_semantic_not_established`

Natural:

- `a1_semantic_capability`
- `a2_semantic_capability`
- `a3_raw_response_integrity`
- `a3_semantic_acceptance`

## Hashes

### Schema

- Template schema SHA256: `857f5463aa2166a624f90c750262f26cf76c52534edcdf98971acd82455ce435`
- Effective schema SHA256 for semantic-capability query: `925691d574e35a3afec02029fb3971bea12597eef1a69f35a713f4a0e765312f`
- Effective schema SHA256 for transport query: `cb152b2803d75d9f68164e3d6d6dee5cac08daff428ba21b0b0c12434dc8a54d`
- Effective schema SHA256 for raw-response-integrity query: `95dc0a8787a811c80c8ec1abe427f2d8018125fe8a96361446b56079e2d15aea`
- Effective schema SHA256 for semantic-acceptance query: `07483553294dfc4c207011a220a760d456197f7269627c6b7e0267d9de369462`

### Gold

- `p1_semantic_capability_established`: `87bad675bbed57ae743327b731af4222074e17d588b427a475662c3361e9e005`
- `p2_transport_not_asserted`: `bb064debd39c9461f98db9e978a8c770abc8ad3b8436974f4b982c0035bfbde0`
- `p3_semantic_capability_not_established`: `93b29798566b07f9c192ee552009fe446095d35099d43f922c5609f3942731b2`
- `p4_transport_established`: `715bb4abc41f853966a843526ff68310be6aa45f90c78e30133ceb7a23f9e3d2`
- `p5_semantic_capability_not_asserted`: `59a2085ce80890a9923f28e50cfdaf946d8bdfd5299982c28c51674c456e24b3`
- `p6_transport_established`: `b4262ab5485959fa7deab1cda022d906fa45e305d575ca2cd0d4ea733011dc86`
- `p6_semantic_not_established`: `1f356689906cdd96447119aa4578f4eb81c8f048634e04b206f4199102b345d0`
- `a1_semantic_capability`: `b9ad985a158a10757b7264d96de296ab02e54a7c780c016bf6d543aab436aa5e`
- `a2_semantic_capability`: `e9500e40ee48ae21b6657b9a15d7c7c34cc2d219408433abba4bdb7fb7636d20`
- `a3_raw_response_integrity`: `f3cd7c9a6c468e98442fb133cfd00b314038250422c9ac1bd4265602df80c0bf`
- `a3_semantic_acceptance`: `80ca79759e30a305b0157843e5e27a4d57063e090a30f9dff717dba4fb33da4b`

### Request / Response

- Prompt/request/response hashes are preserved per-case in each `model_call.json`.

## Mechanical Results

- Mechanically scored: `11 / 11`
- Mechanically failed: `0 / 11`
- All cases had `finish_reason: stop`
- All cases passed JSON/schema/queried-property validation

## Semantic Matrix

| Case | Expected | Observed | Mechanical | Semantic match |
| --- | --- | --- | --- | --- |
| `p1_semantic_capability_established` | `established` | `established` | passed | true |
| `p2_transport_not_asserted` | `not_asserted` | `not_asserted` | passed | true |
| `p3_semantic_capability_not_established` | `not_established` | `not_established` | passed | true |
| `p4_transport_established` | `established` | `established` | passed | true |
| `p5_semantic_capability_not_asserted` | `not_asserted` | `not_asserted` | passed | true |
| `p6_transport_established` | `established` | `established` | passed | true |
| `p6_semantic_not_established` | `not_established` | `not_established` | passed | true |
| `a1_semantic_capability` | `established` | `established` | passed | true |
| `a2_semantic_capability` | `established` | `established` | passed | true |
| `a3_raw_response_integrity` | `established` | `established` | passed | true |
| `a3_semantic_acceptance` | `not_established` | `not_established` | passed | true |

### Synthetic

- Exact: `7 / 7`

### Natural

- Exact: `4 / 4`

### Overall

- Exact: `11 / 11`

## A1 / A2 Comparison With Multi-Label Extraction

The earlier multi-label contract was mixed/negative on the natural A1/A2 cases.
Under the per-property contract, both A1 and A2 classified `semantic_capability = established` exactly.

## Causal Answer

When proposition selection is removed and one semantic property is queried at a time, the current 30B correctly classifies what the frozen natural candidate prose asserts about that property on this frozen corpus.

This is same-model decomposition-induced recovery, not model-size floor displacement.

## Decomposition Implication

The result is consistent with the documented:

- Bifurcation
- Atomization
- Generalization
- Recomposition

heuristic.

## Capability-Floor Implication

This experiment does not establish any cross-model capability-floor displacement.
It only shows that the same model recovered on the isolated per-property task relative to the earlier multi-label proposition-set extraction contract.

## Limitations

- No evidence-side typing was tested here.
- No trust mechanism was tested here.
- No production routing or deterministic checker changes were made.
- No smaller-model comparison was run in this turn.

