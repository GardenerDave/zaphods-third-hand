# Messy Input Triage Packet Worker Audition Attempt 002

This report records a supervised local-worker audition for `messy_input_triage_packet_v1` after the local endpoint environment was made available.

## Purpose

Test whether a local worker can produce a valid messy-input triage packet under a schema-constrained prompt while keeping the deterministic validator authoritative and the result review-required.

## Local Evidence Directory

- `.work/messy_input_triage_worker_auditions/20260717_triage_packet_worker_attempt_002/`

## Endpoint Status

- `reachable`
- model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`

## Messy Input Summary

The request asked ZTH to identify the next bounded supervised follow-up after the validated front-door packet sample, the supervised local-worker loop, the 120-task dogfood run, validation hardening, and docs hygiene, while keeping router automation, repo mutation, training capture, promotion, deployment, and downstream-use authority out of scope.

## Prompt Pattern

- baseline prompt: ask for a JSON messy-input triage packet
- contract prompt: same task plus the exact schema and authority boundary terms required by the validator

## Validation Command

```bash
python3 local_harness/validate_messy_input_triage_packet.py \
  --packet .work/messy_input_triage_worker_auditions/20260717_triage_packet_worker_attempt_002/baseline_packet.json
```

```bash
python3 local_harness/validate_messy_input_triage_packet.py \
  --packet .work/messy_input_triage_worker_auditions/20260717_triage_packet_worker_attempt_002/contract_packet.json
```

## Result

- baseline parse status: `passed`
- baseline validation status: `failed`
- contract parse status: `passed`
- contract validation status: `failed`
- contract prompt improved reliability: `no`

## Validator Diagnostics

- baseline: missing required fields for the messy-input triage schema; the response was not shaped as a triage packet.
- contract: `authority_boundary` was not a list of strings.

## Packet Counts

- baseline packet counts: not meaningful for the validator because the required packet fields were missing.
- contract packet counts from validation result: allowed targets `3`, held targets `6`, evidence needed `3`, stop conditions `4`.

## Key Allowed Targets

The intended schema-constrained prompt kept the follow-up bounded to reviewable roadmap and validator work:

- `docs/ROADMAP.md`
- `docs/TRIAGE_ROUTER.md`
- `docs/reports/model_auditions/`
- `local_harness/validate_messy_input_triage_packet.py`
- `tests/test_validate_messy_input_triage_packet.py`

## Key Held Targets

- `training/`
- `deployment`
- `fixture import`
- `prompt patch promotion`
- `unattended execution`

## Authority Boundary

The audition kept the local worker in the evidence-producer role only. It did not grant unattended execution, repo mutation without review, training capture, promotion, deployment, or downstream-use authority.

## Interpretation

The contract prompt did not improve reliability enough to pass the validator. The local worker produced parseable JSON, but the baseline output did not shape into the triage schema and the contract output still violated the expected authority-boundary type. This is still useful evidence: the front-door contract is necessary, but the prompt needs further tightening or fixture-based prompt-patching before any router automation is even a discussion.
