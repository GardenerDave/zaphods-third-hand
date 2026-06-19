# Small Model Audition Notes — 2026-06-19

This note records the observed setup issues and model behavior from the first small-model audition batch. It is intentionally operational: keep the raw evidence separate from any later promotion decision.

The reusable harness and current local/LAN operator workflow are documented in
[`local_harness/model_auditions/README.md`](../../../local_harness/model_auditions/README.md).

## Setup findings

- Ubuntu/Debian Python rejected a global `pip install` with `externally-managed-environment` / PEP 668. The safe path was a dedicated venv under `~/ai/tools/hf-venv`.
- The current Hugging Face CLI installed by `huggingface_hub[cli]` is available as `hf`; relying on a global `huggingface-cli` failed.
- Hand-typed GGUF filenames were fragile. The corrected downloader lists repo files and selects by glob pattern.
- SmolLM3 downloaded immediately. The other models failed until filename matching was made repo-driven.
- Qwen/SmolLM-style reasoning models produced empty `content` while consuming the token budget in `reasoning_content`. Adding `/no_think` to system/user prompts fixed this for the first pass.

## Files that landed on the server

```text
/home/navigator/ai/models/small-auditions/granite-3.3-2b/ibm-granite_granite-3.3-2b-instruct-Q4_K_M.gguf
/home/navigator/ai/models/small-auditions/ministral-3b/mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf
/home/navigator/ai/models/small-auditions/qwen3-1.7b/Qwen_Qwen3-1.7B-Q4_K_M.gguf
/home/navigator/ai/models/small-auditions/qwen3-4b/Qwen_Qwen3-4B-Q4_K_M.gguf
/home/navigator/ai/models/small-auditions/smollm3-3b/SmolLM3-Q4_K_M.gguf
```

## First concept prompt

Prompt: explain what a context distiller does in Zaphod's Third Hand, requiring token reduction, agent handoff, decision trace preservation, failure handling, and reuse.

Observed behavior:

- `qwen3_1_7b`: fastest usable model, but used labeled lines instead of exact bullets.
- `qwen3_4b`: best normal assistant-style answer among the Qwen models, but much slower.
- `smollm3_3b`: concise and obeyed five-bullet shape, but thinner content.
- `granite_2b`: structured, but generic and slightly semantically loose.
- `ministral_3b`: polished prose, but slower and more verbose.

## Router prompt

Prompt: classify a note about README/docs flow into one of `bug_report`, `build_spec`, `context_distill`, `docs_update`, `model_audition`, `cleanup`, `unknown`, returning strict JSON.

Observed behavior:

- `qwen3_4b`: correct route, raw JSON, numeric confidence. Current router winner.
- `granite_2b`: correct route and raw JSON, but schema drifted with `confidence: "high"` instead of a number.
- `qwen3_1_7b`: raw JSON and fast, but wrong route: chose `context_distill` instead of `docs_update`.
- `smollm3_3b`: correct route but wrapped JSON in markdown fences.
- `ministral_3b`: correct route but wrapped JSON in markdown fences.

## Provisional role read

Do not promote automatically. This is a starting hypothesis for the next audition run.

```text
qwen3_4b    -> current final-router candidate despite speed cost
qwen3_1_7b  -> cheap prefilter / wake-a-bigger-model gate, not final router yet
smollm3_3b  -> concise summarizer / format-following candidate, but needs fence pressure
solid granite_2b -> schema/report candidate after numeric confidence pressure
ministral_3b -> polished summary/control model, probably not strict controller without cleanup
```

## Failure modes the harness must score

- Empty `content` because the model used `reasoning_content`.
- Markdown fence leakage around JSON.
- Schema type drift such as `confidence: "high"`.
- Correct JSON with the wrong route.
- Exact-count failures such as five labeled lines instead of five bullets.
- Generic ML context-distillation answers instead of ZTH workflow-specific answers.
- Invented file paths in developer handoff reports.

## Boundary

Audition is not promotion. The harness records raw responses, mechanical scores, and summary notes. A human still decides whether a model gets a ZTH role.

## Strict schema and defined-route follow-up

A later strict-schema router probe targeted `model_audition` with this note:

```text
The model loaded and answered, but it put the answer inside reasoning_content until I added /no_think. Now I need to record which models obey JSON, which ones use markdown fences, and which are fast enough for router work.
```

Without route definitions, only `ministral_3b` selected `model_audition`; it still wrapped the JSON in markdown fences. `qwen3_1_7b`, `qwen3_4b`, `smollm3_3b`, and `granite_2b` all returned `unknown` despite valid or mostly valid JSON structure.

Adding explicit route definitions did not rescue the Qwen/SmolLM/Granite side:

- `qwen3_1_7b`: raw JSON, numeric confidence, but still `unknown` with high confidence. This is dangerous for final routing because it is confidently wrong.
- `qwen3_4b`: raw JSON, numeric confidence, but still `unknown`. Earlier docs-routing success did not generalize to model-audition classification.
- `smollm3_3b`: recoverable raw JSON after leading newline, but still `unknown`.
- `granite_2b`: raw JSON, numeric confidence, but still `unknown`.
- `ministral_3b`: semantically correct `model_audition`, but again returned fenced JSON.

Conclusion: route definitions alone are not enough for several small models when the route label is conceptually new or workflow-specific. The harness must score semantic route correctness separately from raw controller discipline.

Operational read after this probe:

```text
Best semantic classifier for model-audition notes:
- Ministral 3B, but requires markdown-fence cleanup.

Best raw JSON discipline:
- Granite 2B and Qwen3 1.7B, but both were semantically wrong here.

Highest-risk failure:
- Qwen3 1.7B returning unknown with 0.95 confidence.
```

Recommended router guardrail:

```text
Escalate if:
- route == unknown
- confidence < 0.75
- invalid raw JSON
- markdown fence leakage appears
- content is empty
- reasoning_content is present
- schema type mismatch appears
- a high-confidence unknown appears on a note containing known workflow terms such as model, JSON, audition, scoring, route, or benchmark
```

This follow-up is included in `prompts.example.json` as `router_model_audition_defined_routes`.
