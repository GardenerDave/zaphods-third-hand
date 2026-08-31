# Semantic Claim Discipline Patch Audit 2026-08-31

This report preserves two related evidence sets:

1. the Historian-vs-direct evidence-supplier pilot, and
2. the follow-on semantic claim-discipline experiment using the existing `unsupported_certainty_v1` prompt patch.

The raw `.work/` run directories remain unchanged.

## 1. Historian pilot preservation

### Pilot status

The Historian evidence-supplier pilot remains a pilot, not a definitive qualification.

Preserved limitations:

- equal downstream context ceiling, but not identical actual prompt-token usage
- SOURCE-EQUIVALENT rather than byte-identical evidence corpora
- custom comparison runner rather than the full canonical ZTH transaction lifecycle
- Historian improved provenance richness and record-level traceability, but did not show a detectable semantic-quality advantage over direct projection in the three-task pilot

### Runtime recovery

- Historian repo: `/home/navigator/agent-workspace/project-historian-v1`
- Historian HEAD: `cc3e2d4aa0ecc3cdd8e7f25d3ce8e6fdbdb56a85`
- pinned embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- pinned embedding revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
- pinned reranker model: `cross-encoder/ms-marco-MiniLM-L6-v2`
- pinned reranker revision: `233902d25c440f23af6f7d6e94d2946bac0bee0a`
- disposable cache source: `/home/navigator/.cache/project-historian/huggingface`
- restored disposable cache: `/tmp/historian-hf-cache`
- recovery mechanism: local cache copy only; no Historian source mutation

### Historian evidence service

- startup command: `interfaces/khoj/runtime/py312-cpu/bin/python -m historian.cli serve --host 127.0.0.1 --port 8765`
- service mode: read-only
- `/v1/evidence`: works and returns retrieval provenance
- `/v1/query`: present, but not used as the evidence-supplier arm in the pilot

### Pilot evidence locations

- preserved comparison workspace: `.work/historian_direct_vs_historian_round`
- preserved pilot report: `docs/reports/round3_preservation_and_historian_readiness_2026-08-31.md`

### Pilot normalization

The saved pilot outputs can be normalized through the canonical observation validator only when the downstream evidence set is translated to the canonical projected paths.

Direct-arm outputs are directly grounded against filesystem paths.
Historian-arm outputs carry record-level provenance and retrieval locators; they are not byte-identical to the direct-arm evidence packets.

## 2. Prompt-patch audit

### Available patches

The prompt patch library includes `unsupported_certainty_v1` in `docs/PROMPT_PATCH_LIBRARY.md`.

The patch library also exposes:

- `scope_boundary_v1`
- `absence_of_evidence_v1`
- `placeholder_leakage_v1`
- `output_contract_v1`
- `reason_required_v1`
- `stop_condition_quality_v1`

### Observation-lane wiring

The observation runner (`local_harness/run_manual_supervised_attempt.py`) can project prompt patches into the model packet.

This round used that existing mechanism:

- baseline arm: no extra semantic-caution patch projected
- patched arm: `unsupported_certainty_v1` projected

So the observation lane did not bypass patch infrastructure for this experiment.

## 3. Canonical validation normalization

Validator behavior:

- JSON parse
- required fields
- required field types
- observation findings shape
- observation grounding against projected evidence paths
- `reason` requirement
- review remains separate from validation

### Saved Historian pilot outputs

The six pilot outputs remained:

- D1: passed
- H1: passed
- D2: passed
- H2: passed
- D3: failed on grounding
- H3: failed on grounding

The pilot still supports the narrow conclusion that Historian improved provenance richness but did not clearly improve semantic quality.

## 4. Semantic-discipline experiment

### Design

Independent variable:

- `unsupported_certainty_v1` OFF vs ON

Controlled:

- same worker model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- same local endpoint scope
- same evidence supplier: direct bounded projection
- same observation schema
- same grounding validator
- same review/gate boundaries
- same temperature and completion limits

### Tasks

- Task A: transport qualification versus model capability
- Task B: raw-response preservation versus semantic acceptance
- Task C: mechanical validation versus downstream approval

### Task A

Result:

- baseline: `Transport qualification proves model capability.`
- patched: `Transport qualification proves model capability.`

Interpretation:

- patch had no effect on the over-strong conclusion
- the response was mechanically valid in both arms

### Task B

Result:

- baseline: `Preserving exact worker output establishes evidence integrity without implying correctness or acceptance.`
- patched: same claim

Interpretation:

- patch had no effect on this already-disciplined response
- the response was mechanically valid in both arms

### Task C

Result:

- baseline: failed JSON parsing
- patched: failed JSON parsing

Interpretation:

- the patch did not repair malformed output
- the failure was preserved exactly in both arms

### Aggregate effect

The existing semantic-caution patch did not materially reduce unsupported conclusions from the same worker on the same evidence in this small experiment.

It also did not improve malformed-output behavior.

## 5. Narrow conclusions

### Historian pilot

In this three-task SOURCE-EQUIVALENT pilot, Historian retrieval improved provenance richness but produced no detectable semantic-quality advantage over direct projection.

### Semantic discipline

The failure on Task A persisted with and without `unsupported_certainty_v1`, which suggests the current bottleneck is not evidence supplier selection alone.

## 6. Artifact hashes

Representative hashes for the preserved experiment artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `task_a/baseline/20260831T120000Z/raw_model_output.txt` | `0f22fdfdb5eadb4f366cdcaf34480a2bbb62d2c2be81282050d071bb3282b695` |
| `task_a/patched/20260831T120000Z/raw_model_output.txt` | `0f22fdfdb5eadb4f366cdcaf34480a2bbb62d2c2be81282050d071bb3282b695` |
| `task_b/baseline/20260831T120000Z/raw_model_output.txt` | `2ed249da85fbe6f96bfc2ce89adf5f26091bf4894fe27ada9f551f3e1d1ac28c` |
| `task_b/patched/20260831T120000Z/raw_model_output.txt` | `2ed249da85fbe6f96bfc2ce89adf5f26091bf4894fe27ada9f551f3e1d1ac28c` |
| `task_c/baseline/retry_120001Z/20260831T120001Z/raw_model_output.txt` | `756d81d226c4c3634036d94a33d133c88adbeedcbc9af14e19a5945c53e9a434` |
| `task_c/patched/retry_120001Z/20260831T120001Z/raw_model_output.txt` | `40be211cd2dc963f13deaa7b9f47f495e257f7f6e5870782867da2e5cf91ce67` |

For the full artifact set, use the saved run directories under:

- `.work/historian_direct_vs_historian_round`
- `.work/semantic_claim_discipline_20260831`
