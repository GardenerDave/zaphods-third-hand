# 30B First Handoff Postmortem

Status: inspection-only postmortem

This report preserves the first controlled local 30B consumption experiment for
the transaction-aware supervised handoff context.

## Experiment Summary

- Experiment ID: `30b_first_handoff_20260830`
- Source transaction ID: `orch_manual_20260707t112634z`
- First-worker identity: `manual_operator_provided_model_output`
- Second-worker identity: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- Verified live endpoint: `http://192.168.1.16:8080/v1`
- Request URL: `http://192.168.1.16:8080/v1/chat/completions`
- Acquisition status: completed
- Final verdict: not yet a successful practical ZTH model-to-model handoff

## Preservation Notes

The experiment was copied into `.work/operator_handoffs/30b_first_handoff_20260830/`
to avoid mutating the historical source run. The preserved bytes and hashes are
recorded here so this result is not dependent only on transient `.work` state.
The durable archive for the preserved bytes lives at
[`docs/reports/evidence/30b_first_handoff_20260830/`](./evidence/30b_first_handoff_20260830/).

## Frozen Hashes

- `preregistration.json`
  - `8a6901fbd6076190375163f1609df6334c78b03c8ec56a81144d12b26d7c7f8c`
- `transaction_manifest.json`
  - `faae2b912e11191c4b21f09e213f4b720d67cf00c16caf1297b797474737918e`
- `next_worker_context.json`
  - `097dfe4dd9b6b2127bfa74e00e0d4703a9bf5de3969e93a5384c787632c99d41`
- `next_worker_context.md`
  - `aeed44caa09b98df8b804c5e22455d1b5013e47f4281928bde7f17301d77b994`
- `request_metadata.json`
  - `27415c77ddc98b38fb98f9a985957a0383f8af7a3dded9bf8d124526a75ccaec`
- `raw_response.txt`
  - `fe2caf58ca3723318c565c7e1d465c4979574fd706d3c92208311dc0b02c31f5`
- `closeout.json`
  - `f168972e733b210a00a07eaca2771f40bdc57d266900ed890c2b18c9b38daa59`

## Source Artifact Hashes

- `model_prompt_packet.md`
  - `3e4c6d2cb9ab3393502769d3aaa8ce027bd8334ad6b54974c65bd21deae7d007`
- `raw_model_output.txt`
  - `adbbf7c43a9436426596e2ebd8911c4ed41d4bf7958c164f4f21469192c7f064`
- `review_decision.json`
  - `aab640710bf974ccb5cf533ff53244c447f54571800b75ed84a4091061cc966d`
- `downstream_use_gate.json`
  - `ff85584b88d981c07159cc9881bfb060ac8fce13a3cbdcce5384e0867b76c6c5`
- `handoff_packet.json`
  - `c5cffeb8efbbba96ac9530cf3cac7940021ee60b56ac0187909767c6d3fcc25b`

## Integrity Sequence

The integrity question separates three stages:

1. Historical source run at `.work/manual_supervised_attempts/20260707T112634Z`
2. Copied experiment workspace under `.work/operator_handoffs/30b_first_handoff_20260830/source_run`
3. Durable tracked archive under `docs/reports/evidence/30b_first_handoff_20260830/`

What was proven:

- The original historical source run was not modified.
- Several files were copied unchanged into the experiment workspace.
- Some copied artifacts were intentionally regenerated during experiment ingest.
- The durable archive copies match the experiment bytes by SHA-256.

Classification by file:

- `run_manifest.json`
  - ORIGINAL SOURCE BYTE-PRESERVED
- `triage_packet.json`
  - ORIGINAL SOURCE BYTE-PRESERVED
- `orchestration_packet.json`
  - ORIGINAL SOURCE BYTE-PRESERVED
- `model_prompt_packet.md`
  - ORIGINAL SOURCE BYTE-PRESERVED
- `prompt_to_paste.md`
  - ORIGINAL SOURCE BYTE-PRESERVED
- `messy_input.txt`
  - ORIGINAL SOURCE BYTE-PRESERVED
- `operator_instructions.txt`
  - ORIGINAL SOURCE BYTE-PRESERVED
- `output_contract.json`
  - ORIGINAL SOURCE BYTE-PRESERVED
- `raw_model_output.txt`
  - ORIGINAL SOURCE BYTE-PRESERVED
- `supervised_model_attempt.json`
  - COPIED THEN REGENERATED FOR EXPERIMENT
- `output_validation.json`
  - COPIED THEN REGENERATED FOR EXPERIMENT
- `output_validation_report.txt`
  - COPIED THEN REGENERATED FOR EXPERIMENT
- `review_decision.json`
  - COPIED THEN REGENERATED FOR EXPERIMENT
- `downstream_use_gate.json`
  - COPIED THEN REGENERATED FOR EXPERIMENT
- `handoff_packet.json`
  - COPIED THEN REGENERATED FOR EXPERIMENT
- `transaction_manifest.json`
  - NEW EXPERIMENT ARTIFACT
- `next_worker_context.json`
  - NEW EXPERIMENT ARTIFACT
- `next_worker_context.md`
  - NEW EXPERIMENT ARTIFACT
- `preregistration.json`
  - NEW EXPERIMENT ARTIFACT
- `request_metadata.json`
  - NEW EXPERIMENT ARTIFACT
- `raw_response.txt`
  - NEW EXPERIMENT ARTIFACT
- `closeout.json`
  - NEW EXPERIMENT ARTIFACT

The archived durable copies in `docs/reports/evidence/30b_first_handoff_20260830/`
match the copied experiment bytes by SHA-256 for every archived file recorded in
`archive_manifest.json`.

## Prompt Hierarchy Seen by the 30B

- Transport/system wrapper:
  - OpenAI-chat system prompt from `icm_call.py`
  - `You are a concise local AI worker. Follow the user's instructions exactly.`
- Next-worker instructions:
  - `next_worker_context.md` rendered bundle
- Original first-worker prompt/instructions:
  - present as `task_state.task_request`
- Bounded task:
  - present as `task_state.bounded_task_request`
- Previous-worker result:
  - available as a local path reference to `raw_model_output.txt`
- Validation state:
  - present in `validation`
- Review/gate state:
  - present in `review` and `downstream_use_gate`
- Handoff scope:
  - present in `handoff` and `constraints`
- Authority constraints:
  - present in `authority_boundaries`, `constraints`, and the generated handoff record

## Result Summary

The 30B received the generated context and produced a valid JSON response.
It preserved the allowed / held target envelope and did not violate the authority
boundary language, but it did not continue the downstream task. The response
repeated the original bounded task content rather than behaving like a second
worker continuation.

## Provenance Findings

- The raw previous result body was not embedded as text in the prompt.
- The previous result was visible only as a local path reference and provenance
  metadata.
- The prompt therefore preserved provenance but did not supply a model-visible
  prior-result body for direct continuation.
- The instruction hierarchy gave the original task contract strong placement
  inside the generated context, which likely made repetition more attractive
  than continuation.

## What This Demonstrated

- The generated ZTH handoff context can be transported to a second local model.
- The request preserves authority boundaries and provenance.
- The transport succeeded without operator-added manual reconstruction.
- The experiment proved the generated context is a model-visible evidentiary
  dossier, not yet a sufficient executable continuation prompt.

## What It Did Not Demonstrate

- True 1.7B -> 30B continuation behavior.
- A downstream result that clearly advances the task.
- Transaction completion.
- Automatic routing.

## Acquisition Count Wording

The evidence supports one captured successful acquisition, with no evidence of
retry, fallback, replay, or a second successful acquisition artifact.
Read-only local artifacts do not strictly prove the server-side request count
beyond that, so the claim is intentionally phrased conservatively.

## Durable Archive

Tracked durable evidence copies live under:

`docs/reports/evidence/30b_first_handoff_20260830/`

The archive manifest at
[`docs/reports/evidence/30b_first_handoff_20260830/archive_manifest.json`](./evidence/30b_first_handoff_20260830/archive_manifest.json)
records source path, archive path, SHA-256, and size for every archived file.
