# Aider First Success

Start here only after [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md) makes sense.

This is an optional advanced workflow. Aider can edit files, so keep the task tiny, explicitly scoped, and supervised.
Review every diff and generated artifact before accepting anything.

The workflow remains file-based:

- Human-supervised operation only.
- No unattended execution.
- No automatic lifecycle movement.
- No automatic canonicalization.
- No automatic review-patch acceptance.
- Generated outputs remain review material until a human accepts follow-up work.

## Prerequisites

Required:

- Python 3
- Bash
- Repo root as the current working directory
- Aider installed, or an explicit Python path for an Aider install

Required for model-backed Aider runs:

- A running OpenAI-compatible endpoint
- A model id accepted by that endpoint
- Environment variables or CLI flags for endpoint/model settings

Useful docs:

- [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md)
- [`docs/OPENAI_COMPATIBLE_ENDPOINTS.md`](OPENAI_COMPATIBLE_ENDPOINTS.md)
- [`local_harness/README.md`](../local_harness/README.md)

## Tiny Disposable Task

Create a disposable target file:

```bash
mkdir -p scratch
printf 'Aider smoke note.\n' > scratch/aider_smoke_note.txt
```

Create a small supervised run folder:

```bash
mkdir -p outputs/agent_runs/aider-first-success
cat > outputs/agent_runs/aider-first-success/TASK.md <<'EOF'
# Local Agent Task

Run a tiny supervised Aider smoke test against a disposable scratch file.
EOF
cat > outputs/agent_runs/aider-first-success/INPUT.md <<'EOF'
# Input Bundle

- Editable file: scratch/aider_smoke_note.txt
- Read-only context: README.md
EOF
cat > outputs/agent_runs/aider-first-success/MODEL_REQUEST.md <<'EOF'
# Model Request

In `scratch/aider_smoke_note.txt`, append `This line was added by a supervised Aider smoke test.\n`.

- Edit only the listed file.
EOF
```

## Preflight Only

Run preflight before allowing any edit:

```bash
python3 local_harness/run_aider_worker.py \
  outputs/agent_runs/aider-first-success \
  --preflight-only \
  --init-stubs \
  --read README.md \
  --read-head-lines 20 \
  --compact-request-max-chars 700 \
  scratch/aider_smoke_note.txt
```

Inspect:

- `outputs/agent_runs/aider-first-success/AIDER_PREFLIGHT.json`
- `outputs/agent_runs/aider-first-success/AIDER_MESSAGE.md`
- `outputs/agent_runs/aider-first-success/AIDER_READ_DIGEST.md`, if created

If preflight says the prompt or read payload is too large, stop and reduce scope.

## Real Supervised Run

Use your actual endpoint and model values. For Aider/litellm, the model usually needs an explicit
provider prefix such as `openai/<MODEL_ID>`.
Endpoint prewarm proves connectivity only. On slower local backends, Aider can still time out during
the real edit request even when prewarm returns `ok`.

```bash
python3 local_harness/run_aider_worker.py \
  outputs/agent_runs/aider-first-success \
  --init-stubs \
  --aider-python /path/to/aider/python \
  --openai-api-base "$ZTH_BASE_URL" \
  --model "openai/$ZTH_MODEL" \
  --timeout 360 \
  --read README.md \
  --read-head-lines 20 \
  --compact-request-max-chars 700 \
  scratch/aider_smoke_note.txt
```

If your Aider install is already the default for this repo, you may omit `--aider-python`.

## Expected Review Artifacts

After the run, inspect the run folder before accepting anything:

- `MODEL_REQUEST.md`
- `AIDER_MESSAGE.md`
- `AIDER_PREFLIGHT.json`
- `AIDER_REQUEST.json`
- `AIDER_EVENTS.jsonl`
- `OUTPUT.md`
- `METRICS.json`
- `REVIEW.md`
- `ACCEPTED.md`

Also inspect the Git diff:

```bash
git diff -- scratch/aider_smoke_note.txt
```

Do not promote or commit the result until a human decides the edit is acceptable.

## What Success Looks Like

- Preflight completes and shows a small prompt/read payload.
- Endpoint prewarm succeeds, if enabled.
- Aider edits only `scratch/aider_smoke_note.txt`.
- The diff is one harmless sentence or similarly tiny wording change.
- The run folder contains reviewable request, output, metrics, review, and acceptance artifacts.
- No lifecycle packets move automatically.
- No generated review patch is accepted automatically.

## Common Failure Modes

- Endpoint timeout:
  - Confirm the server is running, increase `--timeout`, or reduce the prompt/read payload.
  - Treat successful prewarm as a connectivity check, not a guarantee the full Aider edit will finish.
- Model alias mismatch:
  - Use the exact model id from the endpoint and include the provider prefix, for example `openai/<MODEL_ID>`.
- Prompt/read payload too large:
  - Lower `--read-head-lines` and `--compact-request-max-chars`.
- Aider executable/path missing:
  - Install Aider or pass the correct `--aider-python /path/to/aider/python`.
- Generated edit is low quality:
  - Reject it in review notes and keep the output as evidence. Do not broaden the task to compensate.
- `.gitignore` changes appear:
  - The wrapper passes `--no-gitignore` to Aider. If you run Aider manually, include that flag or review
    and revert any unintended `.gitignore` edits.

This guide is not a recommendation for broad autonomous coding. Use Aider only for tiny, supervised,
explicitly scoped edits until you have stronger local evidence.
