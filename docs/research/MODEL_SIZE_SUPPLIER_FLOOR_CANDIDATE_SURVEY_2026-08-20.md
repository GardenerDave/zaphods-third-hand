# Model-Size Supplier-Floor Candidate Survey

Status: model-free survey and selection pass. No model was downloaded,
installed, started, or called. This document selects a Stage A screening
candidate only; it is not a scientific experiment preregistration and its
facts are not capability evidence.

Survey basis: [model-size supplier-floor research design](MODEL_SIZE_SUPPLIER_FLOOR_RESEARCH_DESIGN_2026-08-20.md),
authoritative commit `92a861d2d272a4e141998c9a50c3e151ebdc3c4c` and design
SHA256 `642dfe6b0edb051e8e6e9ee680b07da7a50308e5f160f167ca99d722fb2a9158`.

## Survey decision

**Disposition: `SELECT_QWEN3_0_6B_FOR_SCREENING`**

First candidate:

```text
model identity: Qwen/Qwen3-0.6B
proposed screening artifact: Qwen_Qwen3-0.6B-Q4_K_M.gguf
proposed quantized source: bartowski/Qwen_Qwen3-0.6B-GGUF
```

This is the strongest first screening choice because it reduces parameter
count substantially while retaining Qwen3 family continuity, an official
post-trained model identity, an available GGUF path, and a llama.cpp-compatible
deployment route. It provides a cleaner size-reduction test than Qwen3.5-0.8B,
whose newer hybrid multimodal architecture changes more than size.

The exact artifact is not downloaded or frozen as a scientific input here. The
Stage A preparation task must re-check its immutable revision, file hash,
license, chat template, and runtime behavior before use.

## Candidate comparison

| Candidate | Size / family | Runtime and format position | Scientific role |
|---|---|---|---|
| `Qwen/Qwen3-0.6B` | 0.6B; same Qwen3 family as the 1.7B reference | Official Qwen GGUF distribution exists; the inspected official GGUF tree exposes Q8_0. Q4_K_M is available from reproducible community GGUF distributions. | **Selected first screening candidate** |
| `Qwen/Qwen3.5-0.8B` | 0.8B; newer Qwen3.5 hybrid multimodal family | Official Transformers artifact; Qwen documents vLLM/SGLang/Transformers serving. GGUF availability exists through `ggml-org`, but this is not the same architecture/runtime control. | Alternate-family control; defer |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | 1.1B; Llama 2 architecture/tokenizer | Official Transformers chat artifact; community quantizations are available. | Alternate-family control; defer |
| `HuggingFaceTB/SmolLM2-360M-Instruct` | 360M; SmolLM2 compact family | Official Transformers artifact; the card documents Transformers, Transformers.js, vLLM, and SGLang. Quantized descendants exist, but no exact GGUF artifact is selected here. | Next-down candidate |
| `HuggingFaceTB/SmolLM2-135M-Instruct` | 135M; SmolLM2 compact family | Official Transformers artifact; quantized descendants exist. | Lower-band future option |

The survey found no additional candidate that materially improved the first
choice on family control, current local format availability, same-runtime
comparability, and size information value. The shortlist remains sequential;
it is not a five-model benchmark.

## Candidate facts and sources

### Qwen3-0.6B — selected

Authoritative model identity: [`Qwen/Qwen3-0.6B`](https://huggingface.co/Qwen/Qwen3-0.6B).
The Qwen model card reports a causal language model with 0.6B parameters,
0.44B non-embedding parameters, 28 layers, and 32,768-token context. It is a
post-trained Qwen3 model with a chat template and supports thinking and
non-thinking modes; the card documents `/no_think` and an API-level
`enable_thinking` control. The screening runtime must freeze non-thinking
behavior if that is the intended ZTH configuration.

The official Qwen GGUF family is [`Qwen/Qwen3-0.6B-GGUF`](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF).
The inspected main tree currently shows `Qwen3-0.6B-Q8_0.gguf` at 639 MB;
the official Qwen llama.cpp instructions document GGUF and Q4_K_M usage for
the Qwen3 family. For a directly comparable Q4_K_M artifact, the inspected
[`bartowski/Qwen_Qwen3-0.6B-GGUF` file](https://huggingface.co/bartowski/Qwen_Qwen3-0.6B-GGUF/blob/main/Qwen_Qwen3-0.6B-Q4_K_M.gguf)
reports:

```text
filename: Qwen_Qwen3-0.6B-Q4_K_M.gguf
published size: 484 MB
published SHA256: 9acfc1e001311f34b4252001b626f2e466d592a42065f66571bff3790d4e1b14
source revision shown by the file page: 7bcae0b
license shown by the source family/model metadata: Apache-2.0
```

This proposed artifact is a community conversion of the official Qwen model,
not an official Qwen-organization Q4_K_M file. That provenance distinction
must remain explicit. If Stage A uses it, the exact downloaded bytes and
revision must be frozen before any screening call. The file page documents
llama.cpp usage and the Q4_K_M filename. The official Qwen card documents
OpenAI-compatible local serving through a custom endpoint, while Qwen's
llama.cpp documentation documents official GGUF distribution and Q4_K_M
quantization. These facts make same-runtime comparison plausible, but do not
replace local load validation.

Compatibility assessment:

- **Model-family control:** high; it is the same Qwen3 family as the
  established Qwen3 1.7B Q4_K_M reference.
- **Runtime control:** high in principle; GGUF and llama.cpp are available.
- **Hardware control:** high in principle; its proposed Q4_K_M file is far
  below the reference model's size and should fit on the reference hardware;
  actual fit remains a preparation check.
- **Quantization control:** high if Q4_K_M is frozen for both suppliers;
  artifact provenance differs and must be recorded.
- **Task suitability:** promising from official post-training and chat
  support, but structured scope-authority performance is unknown until
  screening.
- **Size information value:** high; approximately one third of 1.7B by
  parameter count.
- **Energy-measurement value:** high; same-hardware inference and the same
  Q4_K_M class are feasible in principle.

Known risks are small-model structured-output reliability, Qwen3 thinking-mode
configuration, community-conversion provenance for Q4_K_M, and any tokenizer,
chat-template, or llama.cpp version interaction. None is evidence of failure;
all are preparation checks.

### Qwen3.5-0.8B — alternate-family control

Authoritative identity: [`Qwen/Qwen3.5-0.8B`](https://huggingface.co/Qwen/Qwen3.5-0.8B).
The card reports 0.8B language-model parameters, a vision encoder, a causal
language model with a hybrid Gated DeltaNet/Gated Attention layout, and a
262,144-token native context. It is Apache-2.0 and post-trained. Qwen documents
Transformers, vLLM, and SGLang serving, including a text-only mode; the card
also states that current/main framework versions are required for Qwen3.5.

The Qwen3.5 page's model type is multimodal and its hybrid architecture is
materially different from Qwen3. It therefore has weaker model-family control
and a larger runtime/architecture confound than Qwen3-0.6B. The
[`ggml-org/Qwen3.5-0.8B` repository](https://huggingface.co/ggml-org/Qwen3.5-0.8B)
indicates a GGUF path, but no exact file, quantization, or hash is selected in
this survey.

Role: defer as an alternate-family control if the research later asks whether
the result generalizes across architecture generations. It is not the first
size-isolation candidate.

### TinyLlama-1.1B-Chat-v1.0 — alternate-family control

Authoritative identity: [`TinyLlama/TinyLlama-1.1B-Chat-v1.0`](https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0).
The card reports approximately 1.1B parameters, Apache-2.0 licensing, and a
chat model based on the Llama 2 architecture and tokenizer. It describes
Supervised Fine-Tuning followed by DPO, and documents the Transformers chat
template and vLLM/SGLang serving paths. The model card's displayed base file
is approximately 2.2 GB in BF16; community quantizations are listed but no
exact GGUF file is selected here.

TinyLlama is instruction/chat suitable enough for a future alternate-family
comparison, but it reduces size only modestly from 1.7B and changes family,
tokenizer, training recipe, and likely prompt behavior. It is therefore lower
information value for the first supplier-floor step.

Role: defer as an alternate-family control, not a next-down size candidate.

### SmolLM2-360M-Instruct — next-down candidate

Authoritative identity: [`HuggingFaceTB/SmolLM2-360M-Instruct`](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct).
The card describes SmolLM2 as a compact family with 135M, 360M, and 1.7B
variants. The 360M instruct model is Apache-2.0, a Transformer decoder, and
post-trained with SFT and DPO. The card documents chat-template use and
Transformers, Transformers.js, vLLM, and SGLang paths. Its displayed model
size is 0.4B parameters; exact non-embedding count, context configuration,
and a confirmation GGUF artifact are not frozen here.

It is a stronger lower-band candidate than the 135M option for a subsequent
step because it retains a meaningful instruction-following target while
providing a much larger reduction than 1.7B. It is a different family and
uses a different tokenizer/training lineage, so it should follow Qwen3-0.6B
rather than replace it.

Role: next-down candidate after the first screening disposition, subject to a
separate model survey/preparation check.

### SmolLM2-135M-Instruct — lower-band future option

Authoritative identity: [`HuggingFaceTB/SmolLM2-135M-Instruct`](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct).
The card reports approximately 0.1B parameters, Apache-2.0, Transformer
decoder architecture, post-training, and a chat template. It documents
Transformers, Transformers.js, vLLM, and SGLang usage. Quantized descendants
exist, but no exact GGUF artifact, file size, or hash is selected here.

Its size reduction is informative, but its risk of near-zero structured
scope-authority capability and format/runtime mismatch is higher. It should be
considered only after a higher lower-band candidate provides evidence that the
search can move down.

Role: defer as a lower-band option.

## Scientific comparability assessment

The first screening should eventually use the same hardware as the established
Qwen3 1.7B supplier, the same llama.cpp/OpenAI-compatible path where practical,
the same Q4_K_M quantization class, the same context/output constraints, and a
frozen non-thinking configuration. Hardware identity, runtime version, model
revision, tokenizer/chat template, and exact file hash must be recorded before
screening.

The eventual screening measurement plan should include wall-clock latency,
prompt and generation tokens, GPU utilization, VRAM, average and peak power
where telemetry permits, joules per action, and joules per validated task.
This survey does not measure any of them.

The same-family Qwen3 choice offers the cleanest first comparison. Qwen3.5's
vision/hybrid design, TinyLlama's Llama 2 lineage, and SmolLM2's separate
training/tokenizer lineage are meaningful scientific confounds. If a future
candidate cannot run on the reference hardware, the design must retain raw
native measurements and use the research-design bridge-calibration method
before making normalized cross-hardware claims.

## Role in the search ladder

```text
Qwen3 1.7B: established reference; not re-proved here
    ↓
Qwen3 0.6B: selected first Stage A screening candidate
    ↓ if viable
SmolLM2 360M: next-down candidate
    ↓ if still viable and justified
SmolLM2 135M: lower-band option
```

Qwen3.5-0.8B and TinyLlama-1.1B remain alternate-family controls, not
additional first-screening arms. This preserves the sequential/logarithmic
search strategy rather than turning Stage A into a benchmark.

## Next step

The next separate task is to prepare, download/install, and freeze the Stage A
screening runtime for the selected Qwen3-0.6B candidate. That task must verify
the exact artifact and bytes before any screening call. Screening results will
be labeled Stage A and will not be treated as confirmatory scientific evidence.
No Stage B confirmation preregistration is created by this survey.

## Selection record

```text
disposition: SELECT_QWEN3_0_6B_FOR_SCREENING
first_candidate: Qwen/Qwen3-0.6B
proposed_quantization: Q4_K_M
proposed_artifact: bartowski/Qwen_Qwen3-0.6B-GGUF/Qwen_Qwen3-0.6B-Q4_K_M.gguf
downloaded: false
installed: false
model_calls: 0
screening_started: false
scientific_preregistration_created: false
```
