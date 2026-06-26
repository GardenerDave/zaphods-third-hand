# Failure-Curriculum Training

This guide explains the supervised ZTH failure-curriculum adapter-training
workflow at a practical operator level. It is not an automatic training system
and does not grant deployment, promotion, routing, or lifecycle authority.

## Purpose

Failure-curriculum training turns reviewed model failures into a small,
inspectable training and evaluation loop:

```text
failure evidence
→ reviewed training rows
→ JSONL curriculum
→ QLoRA adapter training
→ base-vs-adapter evaluation
→ miss review
→ next precision curriculum
→ measured behavior comparison
```

The goal is guided capability improvement on bounded structured-output
behavior, not broad autonomous capability.

## What this workflow is for

- Preparing compact failure examples from reviewed evidence.
- Training or evaluating an adapter against a narrow output contract.
- Comparing base-vs-adapter behavior on held-out validation cases.
- Preserving measured results for operator review.

## What this workflow is not for

- Unattended model training or deployment.
- Automatic model promotion, routing, or role assignment.
- Claims of general intelligence or independent project judgment.
- Publishing private logs, endpoint details, secrets, or raw local paths.

## Hardware/software prerequisites

The proven local milestone used:

- Qwen3-1.7B;
- a 4-bit base model plus LoRA rank-8 adapter;
- non-thinking mode;
- masked prompt loss with assistant-target-only training;
- FP32 trainable LoRA weights;
- NaN/nonfinite loss and gradient guards;
- NVIDIA GTX 1650 4GB hardware class.

Useful local inspection commands:

```bash
nvidia-smi
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Package categories used by this workflow include CUDA-enabled `torch`,
`transformers`, `datasets`, `accelerate`, `peft`, `trl`, `bitsandbytes`,
`sentencepiece`, `protobuf`, and `numpy`.

CUDA version numbers printed by the driver and the PyTorch package do not need
to match exactly. The useful smoke check is that PyTorch sees CUDA and can run a
CUDA tensor operation:

```bash
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device:", torch.cuda.get_device_name(0))
    x = torch.randn((512, 512), device="cuda")
    y = x @ x
    print("matmul ok:", y.shape)
PY
```

## Expected directory layout

Use a private local workspace for raw training data, run logs, and adapters.
This example uses a placeholder-style home directory; public docs and reports
should not expose operator usernames, hostnames, LAN IPs, secrets, or absolute
private paths.

```text
~/zth-lora/
  .venv/
  train_zth_masked_qlora_v4_rank8.py
  train_zth_masked_qlora_v5_structured_precision.py
  train_zth_masked_qlora_v6_exact_key_no_extra.py
  eval_base_vs_adapter.py
  eval_base_vs_v5_structured_precision.py
  eval_base_vs_v6_exact_key_no_extra.py
  data/
    v5_precision/
    v5_structured_mixed/
    v6_exact_key_no_extra/
    v6_mixed/
  reports/
    v5_structured_precision_train.log
    v5_structured_precision_eval.log
    v6_exact_key_no_extra_train.log
    v6_exact_key_no_extra_eval.log
    v4_v5_v6_failure_curriculum_comparison.md
```

Generated run outputs should normally stay local. Commit only compact,
sanitized summaries when they are useful project evidence.

## Dataset format

Use JSONL: one JSON object per line. For structured-output training, the
assistant target is text but should itself parse as JSON.

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Return only valid JSON. Preserve the requested keys exactly."
    },
    {
      "role": "user",
      "content": "Return JSON with exactly one key named accepted. The value is false."
    },
    {
      "role": "assistant",
      "content": "{\"accepted\":false}"
    }
  ],
  "metadata": {
    "curriculum": "v6_exact_key_no_extra",
    "failure_mode": "generic_key_substitution"
  }
}
```

Rules:

- Keep train and validation splits separate.
- Metadata should explain the failure mode being targeted.
- Never train on raw private logs without review and sanitization.
- Do not mix plain-text assistant targets into a JSON-only curriculum unless
  the training goal is broader than JSON contract fidelity.

Quick validation:

```bash
python - <<'PY'
import json
from pathlib import Path

paths = [
    Path("data/v6_mixed/v6_mixed_train.jsonl"),
    Path("data/v6_mixed/v6_mixed_validation.jsonl"),
]

for p in paths:
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    print(p, "rows:", len(rows))
    for i, r in enumerate(rows, 1):
        assert "messages" in r, (p, i)
        assert r["messages"][-1]["role"] == "assistant", (p, i)
        json.loads(r["messages"][-1]["content"])
    print("strict JSON assistant targets: ok")
PY
```

## Dataset mixing recipe

The successful pattern was additive. Do not replace the previous curriculum;
add small weighted precision examples on top of the previous structured
curriculum.

- v5 pattern: original JSON-assistant rows plus v5 precision rows repeated 3x.
- v6 pattern: v5 structured-mixed rows plus v6 exact-key/no-extra rows repeated
  3x.

Template:

```bash
python - <<'PY'
import json
from pathlib import Path

base_train = Path("data/v5_structured_mixed/v5_structured_mixed_train.jsonl")
base_val = Path("data/v5_structured_mixed/v5_structured_mixed_validation.jsonl")
new_train = Path("data/v6_exact_key_no_extra/v6_train.jsonl")
new_val = Path("data/v6_exact_key_no_extra/v6_validation.jsonl")

out_train = Path("data/v6_mixed/v6_mixed_train.jsonl")
out_val = Path("data/v6_mixed/v6_mixed_validation.jsonl")

def load_jsonl(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

mixed_train = load_jsonl(base_train) + load_jsonl(new_train) * 3
mixed_val = load_jsonl(base_val) + load_jsonl(new_val)

out_train.parent.mkdir(parents=True, exist_ok=True)
out_train.write_text(
    "\n".join(json.dumps(r, ensure_ascii=False) for r in mixed_train) + "\n"
)
out_val.write_text(
    "\n".join(json.dumps(r, ensure_ascii=False) for r in mixed_val) + "\n"
)

print("mixed train rows:", len(mixed_train))
print("mixed validation rows:", len(mixed_val))
PY
```

## Training recipe summary

Training scripts should:

- load Qwen3-1.7B in 4-bit;
- apply LoRA rank 8, alpha 16;
- use non-thinking chat template behavior;
- mask prompt tokens and train only assistant target tokens;
- keep trainable LoRA weights in FP32;
- use conservative learning rate;
- include nonfinite loss and gradient checks;
- save adapter weights only.

Known-good parameters:

```text
MAX_LENGTH=384
LR=2e-5
EPOCHS=2
GRAD_ACCUM=16
LoRA rank=8
LoRA alpha=16
optimizer AdamW eps=1e-6 weight_decay=0.0
```

Example launch:

```bash
tmux new-session -d -s zth-v6-exact-key '
cd ~/zth-lora
source .venv/bin/activate
python train_zth_masked_qlora_v6_exact_key_no_extra.py 2>&1 | tee reports/v6_exact_key_no_extra_train.log
'
```

Watch training:

```bash
tail -f ~/zth-lora/reports/v6_exact_key_no_extra_train.log
```

`Ctrl-C` stops `tail` or `watch`. It does not stop training running inside
tmux. Detach from tmux with `Ctrl-b` then `d`, check sessions with `tmux ls`,
and watch the GPU with:

```bash
watch -n 2 nvidia-smi
```

## Evaluation command

Evaluation scripts should:

- load the same base model;
- run the base model on the validation set;
- load the adapter on the same base model;
- run the adapter on the same validation set;
- use non-thinking mode;
- decode only newly generated tokens after the prompt;
- preserve raw base and adapter outputs locally;
- save JSONL with `target`, `base_output`, `adapter_output`, and validity flags.

Use absolute adapter paths when possible. Some PEFT paths can be mistaken for
Hugging Face Hub model IDs when provided as relative paths.

Example:

```bash
python eval_base_vs_v6_exact_key_no_extra.py 2>&1 | tee reports/v6_exact_key_no_extra_eval.log
```

Expected evaluation output pattern:

```text
base_vs_adapter_eval_<run_label>_full.jsonl
```

## How to read metrics

Current strict metrics:

- JSON validity;
- top-level key match;
- exact match;
- extra fields present;
- value type match;
- array count match.

Behavior evaluation is the win condition. Lower eval loss by itself does not
prove the adapter improved the target behavior.

## How to classify misses

Turn non-exact rows and extra-field rows into review Markdown before creating
the next curriculum. Useful labels include:

- generic placeholder schema substitution;
- generic key substitution;
- prefixed-key substitution;
- source-content leakage after correct answer;
- runaway list expansion or invented extra items;
- array cardinality error or merged list items;
- type/value mismatch;
- semantic substitution or unsupported paraphrase;
- over-normalized phrasing or non-exact semantic rewrite;
- target ambiguity or brittle expected answer.

The persistent failures after v6 were:

- `count` becoming `key1`/`key2`/`key3`;
- `blocked` becoming `key_blocked`;
- `accepted` becoming `key`;
- `files_changed` plus source code prompting `file1` leakage.

## When to stop

Pause when another small weighted dataset is unlikely to target the remaining
failure mode. The v4, v5, and v6 sequence proved the supervised loop. v6
improved general contract fidelity, but it did not fix the five persistent
extra-field/key-substitution attractors. That is a good stopping point before
trying a different tactic.

## Safety boundaries

- Adapters are evidence, not authorities.
- Metrics are evidence, not deployment permission.
- No adapter gets production status automatically.
- Do not publish raw local paths, hostnames, LAN IPs, secrets, tokens, or
  private logs.
- Do not claim broad intelligence or independent project judgment.
- Do not claim a model can approve its own output.
- Do not imply the training loop is unattended.

Public-safe phrasing:

```text
This demonstrates supervised guided capability improvement on bounded structured-output behavior.
```

## Current proven milestone

Observed progression:

- v4: validity breakthrough.
- v5: structured precision improvement.
- v6: further exact-match and contract-fidelity improvement.

Measured behavior:

| Run | Validation set | JSON validity | Top-level key match | Exact match | Extra fields | Value type match | Array count match |
|---|---:|---:|---:|---:|---:|---:|---:|
| v4 | 36 rows | 36/36 | 31/36 | 10/36 | not recorded | not recorded | not recorded |
| v5 | 42 rows | 42/42 | 37/42 | 17/42 | 5/42 | 37/42 | 37/42 |
| v6 | 48 rows | 48/48 | 43/48 | 23/48 | 5/48 | 43/48 | 43/48 |

This demonstrates a repeatable supervised loop for turning small-model failure
evidence into measurable adapter improvement on bounded structured-output
behavior. It does not demonstrate independent project judgment, deployment
readiness, or unsupervised model improvement.

## Next recommended iteration

Do not immediately add another small weighted dataset. Recommended next
operator improvements are small model-free scripts:

- validate a curriculum JSONL dataset;
- mix curriculum rows with explicit weighting;
- score an evaluation JSONL file;
- produce non-exact miss-review Markdown;
- produce extra-field review Markdown;
- write a compact round report.

Avoid building an automatic training launcher, adapter promoter, Git committer,
or report publisher.
