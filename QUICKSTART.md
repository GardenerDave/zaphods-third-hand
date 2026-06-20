# Quickstart

Run [`docs/FIRST_SUCCESS.md`](docs/FIRST_SUCCESS.md) first. This guide covers
the normal operator workflow after the model-free and optional endpoint smoke
checks succeed.

## Boundaries

- ZTH is human-supervised and file-based.
- Generated summaries, patches, scores, and role outputs remain evidence until
  reviewed.
- No workflow automatically promotes a model, accepts generated context, moves
  lifecycle state, or establishes production readiness.
- Core model-backed workflows use an existing OpenAI-compatible endpoint. The
  optional small-model exploratory harness is the only workflow that can
  manage temporary local llama.cpp servers.

Before use, confirm that your activity complies with [`LICENSE.md`](LICENSE.md)
and [`COMMERCIAL_USE.md`](COMMERCIAL_USE.md).

## Prerequisites

For the Context Distiller path below:

- Bash
- Python 3
- a working directory where generated files can be reviewed
- an existing OpenAI-compatible endpoint
- a model ID accepted by that endpoint
- a source transcript or log safe for your environment

See the dependency matrix in [`README.md`](README.md#dependency-matrix) for
optional workflows and test dependencies.

## 1. Configure and Verify the Endpoint

From the repository root:

```bash
cp config.example.env config.env
# Edit config.env with the real endpoint and model before loading it.
set -a
source config.env
set +a
```

If required by the endpoint, set `OPENAI_API_KEY` in your private shell or
`config.env`.

Verify connectivity:

```bash
python3 local_harness/icm_call.py handoff \
  --api openai-chat \
  --base-url "$ZTH_BASE_URL" \
  --model "$ZTH_MODEL" \
  --max-tokens 16 \
  --timeout 60 \
  --final-only \
  "Reply with exactly: ok"
```

Do not continue until the endpoint, model ID, and authentication are correct.
See [`docs/OPENAI_COMPATIBLE_ENDPOINTS.md`](docs/OPENAI_COMPATIBLE_ENDPOINTS.md)
for local, LAN, and remote patterns.

Advanced role-specific endpoint routing uses the `ICM_DEEP_*`, `ICM_CODER_*`,
and `ICM_ROUTER_*` variables documented there and in
[`config.example.env`](config.example.env). The normal Context Distiller path
uses the single `ZTH_BASE_URL` / `ZTH_MODEL` pair.

## 2. Choose a Private Source

Keep private transcripts and logs outside tracked documentation. Record a
stable source ID and short title:

```bash
export SOURCE_ID="<SOURCE_ID>"
export SOURCE_FILE="<SOURCE_FILE>"
export SHORT_TITLE="<SHORT_TITLE>"
```

For example, if the private source is `/tmp/zth-team-handoff.txt`:

```bash
export SOURCE_ID="team-handoff-2026-06-20"
export SOURCE_FILE="/tmp/zth-team-handoff.txt"
export SHORT_TITLE="team-handoff"
```

Do not commit source material unless it has been explicitly reviewed for
sharing.

## 3. Run Context Distiller

Start with compact mode:

```bash
export ZTH_DISTILLER_SESSION_MAX_TOKENS="700"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="280"
export ZTH_DISTILLER_TIMEOUT="900"
export ZTH_DISTILLER_RUN_PROFILE="normal"
export ZTH_DISTILLER_RUN_PURPOSE="handoff"

./scripts/run_context_distiller_head.sh \
  "$SOURCE_ID" \
  "$SOURCE_FILE" \
  "$SHORT_TITLE" \
  --compact
```

Use chunked mode for a source that is too long for one reliable request:

```bash
export ZTH_DISTILLER_CHUNK_LINES="200"
export ZTH_DISTILLER_CHUNK_MAX_TOKENS="600"

./scripts/run_context_distiller_head.sh \
  "$SOURCE_ID" \
  "$SOURCE_FILE" \
  "$SHORT_TITLE" \
  --chunked
```

If a reasoning-capable endpoint returns empty final content, try:

```bash
export ZTH_DISTILLER_FINAL_ONLY="1"
```

Detailed smoke, compact, chunked, timeout, advisor, threshold, ledger,
calibration, and role-critique options are maintained in
[`docs/CONTEXT_DISTILLER_WORKFLOW.md`](docs/CONTEXT_DISTILLER_WORKFLOW.md).

## 4. Review the Evidence

Inspect:

```text
outputs/context/
outputs/indexes/
outputs/sessions/
outputs/review_patches/
outputs/run_records/
```

The current head script creates `outputs/context/` and `outputs/indexes/` as
reserved locations but does not populate them. Review the session, review
patch, and run-record directories for the active outputs from this workflow.

Print a concise recent-run summary:

```bash
python3 local_harness/report_distiller_metrics.py \
  --runs-dir outputs/run_records \
  --limit 6
```

For compact mode, verify the session follows the documented structure,
including `Executive Summary`, `Durable Facts`, `Decisions Made`, `Open
Questions`, and `Next Actions`; see
[`Compact Mode`](docs/CONTEXT_DISTILLER_WORKFLOW.md#compact-mode).

For advisory filters, ledger/calibration options, role critiques, and the
chunked recommendation threshold—including `--advisor-only`, `--write-ledger`,
`--calibration-window`, `--role-critiques-file`,
`--role-critiques-strict`, `--profile`, `--purpose`, `--exclude-purpose`, and
`--min-recent-runs-for-chunked`—see
[`Metrics Advisor and Filters`](docs/CONTEXT_DISTILLER_WORKFLOW.md#metrics-advisor-and-filters).

Check the generated session against the source. Review the proposed patch and
run metrics. Keep source paths, endpoint names, and model names private unless
they have been sanitized for sharing.

The review patch is not canonical and must not be applied automatically.

## 5. Route Any Follow-Up Work

If review identifies an accepted follow-up:

1. Create a narrow packet from `templates/job_packet_template.md`.
2. Record the objective, allowed files, off-limits files, verification, and
   stop conditions.
3. Have a human review and activate the packet.
4. Use one supervised route, such as an authorized Implementer, Aider, or a
   human terminal session.
5. Record the result and human acceptance, rework, or rejection decision.

Use:

- [`docs/MANAGEMENT_TEAM_OVERVIEW.md`](docs/MANAGEMENT_TEAM_OVERVIEW.md)
- [`workflows/MANUAL_JOB_ROUTING_WORKFLOW.md`](workflows/MANUAL_JOB_ROUTING_WORKFLOW.md)
- [`workflows/REVIEW_PATCH_ACCEPTANCE_WORKFLOW.md`](workflows/REVIEW_PATCH_ACCEPTANCE_WORKFLOW.md)
- [`workflows/SUPERVISED_ROLE_RUN_EVIDENCE_NOTE_FORMAT.md`](workflows/SUPERVISED_ROLE_RUN_EVIDENCE_NOTE_FORMAT.md)

Role output does not activate packets, authorize lifecycle movement, or expand
an active packet’s file allowlist.

## Troubleshooting

- Placeholder endpoint or model:
  - Edit and reload `config.env`.
- Endpoint connectivity failure:
  - Verify `ZTH_BASE_URL`, `ZTH_MODEL`, and `OPENAI_API_KEY` if required.
  - For HTTP error codes, authentication failures, and endpoint diagnostics,
    see
    [`OpenAI-Compatible Endpoint Troubleshooting`](docs/OPENAI_COMPATIBLE_ENDPOINTS.md#troubleshooting).
- Source file not found:
  - Run from the repository root or use an absolute private source path.
- Distiller timeout:
  - This guide uses 900 seconds as the normal compact-run starting point; the
    detailed workflow uses 240 seconds only for a tiny smoke profile.
  - If 900 seconds still expires, reduce source size or output budgets before
    increasing `ZTH_DISTILLER_TIMEOUT`, then inspect endpoint latency.
- Chunked run is too slow:
  - Reduce `ZTH_DISTILLER_CHUNK_LINES` and
    `ZTH_DISTILLER_CHUNK_MAX_TOKENS`.
- Generated evidence is weak or incorrect:
  - Do not accept it. Record rework or create a narrower follow-up packet.

For the complete documentation map, see [`docs/README.md`](docs/README.md).
