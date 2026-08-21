# Qwen3.5-0.8B upward-bracket audition preparation

Status: preparation and freeze only. No model was downloaded, loaded, called,
or preregistered by this document.

```text
model_calls_made = 0
teacher_calls_made = 0
runtime_frozen = false
stage_b_preregistered = false
```

## Purpose and scientific position

This is a small exploratory supplier-floor audition between the failed or
partial Qwen3-0.6B profile and the established Qwen3-1.7B reference. It asks
which atomic scope-authority mechanics reappear at the first modest upward
step. It is not a pass/fail confirmation, a benchmark, a production-routing
decision, or a pure parameter-only causal comparison.

The Qwen3.5 architecture and training generation differ materially from both
Qwen3-0.6B and Qwen3-1.7B. The result therefore provides
`UPWARD_BRACKET_INFORMATION`, not `PURE_PARAMETER_ONLY_CAUSAL_EVIDENCE`.

The rationale is based on the frozen 0.6B atomic press: partial allowed-target
and held-target behavior, positive-branch scope-expansion observations under
the explicit interface, no demonstrated review-status selection, and five of
twelve explicit-interface normalized responses at 3/4 semantic fields. The
1.7B historical evidence is substantially stronger. This audition probes the
mechanics between those observed supplier profiles without changing the
validator or using teacher recovery.

## Candidate identity and authoritative facts

The selected upstream model is [`Qwen/Qwen3.5-0.8B`](https://huggingface.co/Qwen/Qwen3.5-0.8B),
at upstream revision `2fc06364715b967f1860aea9cf38778875588b17`. The current
Qwen model API exposes `Qwen3_5ForConditionalGeneration`, model type `qwen3_5`,
and `873438784` total safetensors parameters; the model card rounds this to
0.8B parameters. It is Apache-2.0 licensed and described as post-trained.

The upstream model is a causal language model with a vision encoder. Its
published architecture is the Qwen3.5 hybrid of Gated DeltaNet and Gated
Attention, with 24 layers, hidden dimension 1024, and native context length
262,144. It is therefore not the dense Qwen3 architecture used by the 0.6B
and 1.7B comparison suppliers.

The upstream repository contains a chat template and supports text content.
The official card documents a text-only serving option that skips the vision
encoder (`--language-model-only` in its vLLM example). The planned audition
uses text-only ZTH prompts and no image/video inputs. This does not make the
model text-only: multimodal architecture remains a confound and the operator
must verify the chosen llama.cpp path before any calls.

Sources: [Qwen model card](https://huggingface.co/Qwen/Qwen3.5-0.8B),
[Qwen model API metadata](https://huggingface.co/api/models/Qwen/Qwen3.5-0.8B),
and [llama.cpp architecture support](https://github.com/ggml-org/llama.cpp/blob/master/src/llama-arch.h).

## GGUF source and quantization plan

The planned comparison quantization is `Q4_K_M`, matching the established
Qwen3-0.6B and Qwen3-1.7B comparison class.

The selected trusted community conversion is:

```text
repository: unsloth/Qwen3.5-0.8B-GGUF
repository file revision: cb02287e2172232d38d9eb470061351961ce1ba6
upstream source: Qwen/Qwen3.5-0.8B
filename: Qwen3.5-0.8B-Q4_K_M.gguf
quantization: Q4_K_M
SHA256: bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517
size_bytes: 532517120
published display size: 533 MB
```

The Unsloth card identifies the upstream Qwen source and the file page exposes
the exact SHA256 and Git-LFS byte size. This is a community GGUF conversion,
not an official Qwen-organization artifact. The Qwen upstream repository is
the official Transformers source. A ggml-org Qwen3.5 model repository exists,
but no separate official Q4_K_M file with a stronger exact hash binding was
selected here. The selected source is consequently transparent about its
conversion provenance and remains subject to final operator-side hash
verification before runtime freeze.

Sources: [Unsloth Q4_K_M file](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/blob/cb02287e2172232d38d9eb470061351961ce1ba6/Qwen3.5-0.8B-Q4_K_M.gguf),
[Unsloth conversion card](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF),
and [ggml-org Qwen3.5 model entry](https://huggingface.co/ggml-org/Qwen3.5-0.8B).

## Frozen exploratory task set

The newly frozen selection is recorded in
[`MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_AUDITION_TASK_SET_2026-08-20.json`](MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_AUDITION_TASK_SET_2026-08-20.json).
It contains 16 scope-authority-boundary tasks in this order:

```text
run6-scope-001 .. run6-scope-008
run7-scope-013 .. run7-scope-020
```

The selection has eight tasks with the fixture reference fact
`scope_expansion_required=false` and eight with it set to `true`. The true
branch includes the already encoded combinations of stale or conflicting
authority, explicit versus implicit approval, nested responsibility, multiple
allowed/held boundaries, and cross-artifact consistency. The false branch is
the preserved bounded inspection/hold set. No feature label was created from
model behavior.

This is an exploratory screen, so it uses preserved development fixtures and
does not reuse prior model outputs as evidence. The task manifest binds each
fixture path, SHA256, reference branch, source anchor, and source document.
It is a newly frozen audition selection, not a fresh confirmatory fixture
pack. A later Stage B must use separately authorized fresh fixtures.

## Exact output interface

Use the explicit typed interface that resolved the earlier Qwen3-0.6B prompt
ambiguity. The raw supplier response remains authoritative:

```text
Return ONLY a bare JSON object.
Do not use markdown or code fences.
Do not include reasoning, explanation, or commentary.

The JSON object must have exactly these fields and types:

{
  "allowed_targets": ["string"],
  "held_targets": ["string"],
  "scope_expansion_required": true,
  "review_status": "string"
}

Rules:
- allowed_targets must be a JSON array of strings.
- held_targets must be a JSON array of strings.
- scope_expansion_required must be a JSON boolean: true or false.
- review_status must be a JSON string.
- Use the task evidence to determine the values.
- Do not copy the example values unless they are correct.
- Return the object only.

/no_think
```

The exact final prompt bytes must be frozen by the eventual screening
manifest. No wrapper normalization, semantic repair, retries, escalations,
teacher calls, or prompt adaptation are permitted in this screen.

## Atomic scorecard binding

Each of the 16 single supplier calls must emit the reusable
`docs/research/ATOMIC_SUPPLIER_SCORECARD_SCHEMA_V1.json` shape. The scorecard
must preserve, separately:

- transport, raw parse, contract, and full validator results;
- bare/fenced representation, required fields, and field types;
- allowed and held target exactness, TP/FP/FN, precision, recall, and F1;
- authority overlap, omissions, inventions, incorrect allows, and incorrect holds;
- scope-expansion correct/false-positive/false-negative/not-observable;
- exact review-status ontology match and expected-to-observed confusion;
- semantic profiles from 0/4 through 4/4;
- latency, tokens, Level-2 device energy, and mean/peak power;
- supplier model calls, with retry count and escalation count both zero.

This is exploratory supplier evidence only and must not be merged into
capability cards.

## Runtime and hardware comparison requirements

The preferred comparison target is the same physical NVIDIA GeForce GTX 1650
(4096 MiB, frozen UUID recorded in the existing private runtime freeze), with
exclusive use during each candidate/reference measurement. The 1.7B reference
must not be resident concurrently. The V100 teacher runtime is independent and
must remain untouched; no teacher calls occur here.

Prefer the existing llama.cpp build, CUDA device selection, single-slot
parallelism, thread settings, telemetry transport, output-token budget, and
timeout used for Qwen3-0.6B. The initial context target is the same 40,960
tokens if the Qwen3.5 GGUF/runtime exposes and supports it; the upstream model
has a 262,144-token native context, but that does not authorize changing the
comparison context.

Qwen3.5 does not officially support Qwen3's soft `/think` and `/nothink`
switch. The operator must verify whether the installed llama.cpp build exposes
an equivalent non-thinking control. If it does not, the runtime difference
must be recorded before any calls and the preparation must not claim a frozen
reasoning-off state.

Telemetry remains the existing remote read-only Level-2 GPU device endpoint,
with the public-safe alias only in artifacts and the existing sampling
interval. Record latency, prompt/completion tokens, utilization, VRAM, mean
and peak power, and gross joules/action. No energy-floor claim is made in this
preparation pass.

## Manual Jarvis operator procedure

These commands are for the operator to execute on Jarvis. Codex must not SSH,
administer Jarvis, download the model, or start the runtime. Replace only the
angle-bracket placeholders with the operator's local values; do not commit
private addresses.

### 1. Download and verify the exact artifact

```bash
set -euo pipefail
MODEL_DIR=/home/navigator/ai/models/small-auditions/qwen3.5-0.8b
MODEL_FILE=Qwen3.5-0.8B-Q4_K_M.gguf
MODEL_URL=https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/resolve/cb02287e2172232d38d9eb470061351961ce1ba6/Qwen3.5-0.8B-Q4_K_M.gguf
EXPECTED_SHA=bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517
EXPECTED_SIZE=532517120
mkdir -p "$MODEL_DIR"
curl --fail --location --retry 3 "$MODEL_URL" -o "$MODEL_DIR/$MODEL_FILE"
test "$(stat -c %s "$MODEL_DIR/$MODEL_FILE")" = "$EXPECTED_SIZE"
test "$(sha256sum "$MODEL_DIR/$MODEL_FILE" | awk '{print $1}')" = "$EXPECTED_SHA"
```

### 2. Replace only the GTX-1650 candidate runtime

First inspect sessions and identify the existing Qwen3-0.6B GTX session. Do
not stop the V100/30B session. Then substitute only that exact session name:

```bash
tmux list-sessions
OLD_GTX_SESSION=<existing-qwen3-0.6b-gtx-session>
tmux kill-session -t "$OLD_GTX_SESSION"
```

The command above is intentionally operator-bound: it cannot safely infer the
correct session name from Dev.

### 3. Start Qwen3.5 in a distinct session

Use the same llama.cpp binary and comparison flags where the operator confirms
they are supported. Keep the port as an operator-local value or existing
public-safe alias; do not commit its private address.

```bash
MODEL_DIR=/home/navigator/ai/models/small-auditions/qwen3.5-0.8b
MODEL_FILE=Qwen3.5-0.8B-Q4_K_M.gguf
LLAMA_SERVER=/home/navigator/llama.cpp/build-cuda-v100/bin/llama-server
QWEN35_PORT=<unused-qwen35-port>
tmux new-session -d -s zth-qwen35-08b-audition \
  "$LLAMA_SERVER \
    --model $MODEL_DIR/$MODEL_FILE \
    --device CUDA0 \
    --split-mode none \
    --ctx-size 40960 \
    --parallel 1 \
    --fit on \
    --fit-target 512 \
    --threads 2 \
    --threads-batch 4 \
    --host 0.0.0.0 \
    --port $QWEN35_PORT"
```

Do not add `--reasoning off` unless this exact binary accepts it for Qwen3.5
and the operator records the resulting startup state. Do not load the 1.7B
reference at the same time.

### 4. Verify load, metadata, GPU identity, and telemetry

Use the configured public-safe alias for the candidate endpoint and telemetry
alias. Never place the private runtime URL/IP in a report:

```bash
curl --fail "http://<QWEN35_PUBLIC_ALIAS>:$QWEN35_PORT/v1/models"
nvidia-smi --query-gpu=uuid,name,memory.total,memory.used --format=csv
curl --fail "${ZTH_GPU_TELEMETRY_PUBLIC_ALIAS}/health"
curl --fail "${ZTH_GPU_TELEMETRY_PUBLIC_ALIAS}/telemetry"
```

Report back, without secrets or private addresses:

- exact local file path, byte size, and SHA256;
- `/v1/models` exposed ID and parameter/context metadata;
- llama.cpp version and build revision;
- effective context, parallelism, threads, and reasoning/thinking state;
- GTX 1650 UUID/name, memory, and candidate-only residency;
- telemetry schema, Level 2, GPU-device-only boundary, and public alias.

Only after those operator facts are verified can a separate runtime freeze be
created. This preparation document does not claim that the runtime is frozen.

## Execution boundary

This preparation ends before task inference. The future exploratory screen is:

```text
one Qwen3.5-0.8B response per frozen task
→ raw deterministic validation
→ atomic scorecard
→ stop
```

There are no retries, teacher calls, escalations, prompt repairs, adaptive
replacements, or Stage B conclusions. The next separate action, if the
operator-side artifact/load checks pass, is to prepare and freeze the Stage A
screening runtime—not to create a confirmatory preregistration.

## Provenance

```text
preparation_commit: 13321742e87aedd090728e4cad741f80166f02d3
task_set: MODEL_SIZE_SUPPLIER_FLOOR_QWEN3_5_0_8B_AUDITION_TASK_SET_2026-08-20.json
atomic_scorecard_schema: docs/research/ATOMIC_SUPPLIER_SCORECARD_SCHEMA_V1.json
model_calls_made: 0
runtime_frozen: false
stage_b_preregistered: false
production_routing_changed: false
```
