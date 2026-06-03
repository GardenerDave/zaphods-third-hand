#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SOURCE_ID="${1:-}"
SOURCE_FILE="${2:-}"
SHORT_TITLE="${3:-}"
MODE_ARG="${4:-}"
MODE_ARG_2="${5:-}"

# Configure before use:
#   export ZTH_BASE_URL="http://<LLAMA_CPP_BASE_URL>/v1"
#   export ZTH_MODEL="<MODEL_NAME>"
BASE_URL="${ZTH_BASE_URL:-http://<LLAMA_CPP_BASE_URL>/v1}"
MODEL="${ZTH_MODEL:-<MODEL_NAME>}"
CHUNK_LINES="${ZTH_DISTILLER_CHUNK_LINES:-350}"

if [[ "$BASE_URL" == *"<LLAMA_CPP_BASE_URL>"* ]] || [[ "$MODEL" == "<MODEL_NAME>" ]]; then
  echo "Configure ZTH_BASE_URL and ZTH_MODEL before running. See config.example.env."
  exit 1
fi

COMPACT_MODE="0"
if [ "$MODE_ARG" = "--compact" ] || [ "${ZTH_DISTILLER_COMPACT:-}" = "1" ]; then
  COMPACT_MODE="1"
fi

CHUNKED_MODE="0"
if [ "$MODE_ARG" = "--chunked" ] || [ "$MODE_ARG_2" = "--chunked" ] || [ "${ZTH_DISTILLER_CHUNKED:-}" = "1" ]; then
  CHUNKED_MODE="1"
fi
CHUNK_COUNT="0"

if [ -z "$SOURCE_ID" ] || [ -z "$SOURCE_FILE" ] || [ -z "$SHORT_TITLE" ]; then
  echo "Usage: ./scripts/run_context_distiller_head.sh <SOURCE_ID> <SOURCE_FILE> <SHORT_TITLE> [--compact] [--chunked]"
  exit 1
fi

if [ ! -f "$SOURCE_FILE" ]; then
  echo "Source file not found: $SOURCE_FILE"
  exit 1
fi

OUTPUT_DIR="${PACKAGE_ROOT}/outputs"
SESSION_DIR="${OUTPUT_DIR}/sessions"
PATCH_DIR="${OUTPUT_DIR}/review_patches"
RUNS_DIR="${OUTPUT_DIR}/run_records"
CONTEXT_DIR="${OUTPUT_DIR}/context"
INDEX_DIR="${OUTPUT_DIR}/indexes"

mkdir -p "$CONTEXT_DIR" "$SESSION_DIR" "$PATCH_DIR" "$INDEX_DIR" "$RUNS_DIR"

DATE="$(date +%F)"
SESSION_FILE="${SESSION_DIR}/${DATE}_${SHORT_TITLE}.md"
PATCH_FILE="${PATCH_DIR}/context_patch_${SOURCE_ID}.md"
RUN_DIR="${RUNS_DIR}/${SOURCE_ID}_${SHORT_TITLE}"

mkdir -p "$RUN_DIR"

call_model() {
  python3 "${PACKAGE_ROOT}/local_harness/icm_call.py" deep "$@"
}

if [ "$CHUNKED_MODE" = "1" ]; then
  mkdir -p "$RUN_DIR/chunks"

  awk \
    -v chunk_lines="$CHUNK_LINES" \
    -v outdir="$RUN_DIR/chunks" \
    -v source_id="$SOURCE_ID" \
    -v source_file="$SOURCE_FILE" \
    '
      function start_chunk() {
        if (outfile != "") {
          close(outfile)
        }
        chunk += 1
        lines_in_chunk = 0
        outfile = sprintf("%s/chunk_%03d.md", outdir, chunk)
        print "# Source Chunk " chunk > outfile
        print "" >> outfile
        print "Source ID: " source_id >> outfile
        print "Source file: " source_file >> outfile
        print "Chunk: " chunk >> outfile
        print "" >> outfile
        print "## Text" >> outfile
        print "" >> outfile
      }

      {
        if (chunk == 0 || lines_in_chunk >= chunk_lines) {
          start_chunk()
        }
        print $0 >> outfile
        lines_in_chunk += 1
      }

      END {
        if (outfile != "") {
          close(outfile)
        }
      }
    ' "$SOURCE_FILE"

  CHUNK_FILES=( "$RUN_DIR"/chunks/chunk_[0-9][0-9][0-9].md )
  if [ -f "${CHUNK_FILES[0]}" ]; then
    CHUNK_COUNT="${#CHUNK_FILES[@]}"
  fi

  for CHUNK_FILE in "$RUN_DIR"/chunks/chunk_[0-9][0-9][0-9].md; do
    CHUNK_PROMPT="${CHUNK_FILE%.md}_prompt.md"
    cat > "$CHUNK_PROMPT" <<EOF
You are the Zaphod's Third Hand Context Distiller.

Extract durable context from this chunk only.

Produce only this compact structure:

# Chunk Context Summary

## Chunk Source
- Source ID: ${SOURCE_ID}
- Source file: ${SOURCE_FILE}
- Chunk file: ${CHUNK_FILE}

## Durable Facts

## Decisions Made

## Open Questions

## Bugs / Issues Identified

## Rules Added

## User Preferences

## Files / Artifacts Mentioned

## Next Actions

## Compression Notes

CHUNK TEXT:
EOF

    cat "$CHUNK_FILE" >> "$CHUNK_PROMPT"
  done

  for CHUNK_PROMPT in "$RUN_DIR"/chunks/chunk_[0-9][0-9][0-9]_prompt.md; do
    [ -f "$CHUNK_PROMPT" ] || continue
    CHUNK_SUMMARY="${CHUNK_PROMPT%_prompt.md}_summary.md"
    CHUNK_ERROR="${CHUNK_PROMPT%_prompt.md}_error.log"
    CHUNK_OK="0"
    : > "$CHUNK_ERROR"

    if call_model --max-tokens 1200 < "$CHUNK_PROMPT" > "$CHUNK_SUMMARY" 2>> "$CHUNK_ERROR"; then
      CHUNK_OK="1"
    else
      {
        echo
        echo "--- retry 1 ---"
      } >> "$CHUNK_ERROR"

      if call_model --max-tokens 1200 < "$CHUNK_PROMPT" > "$CHUNK_SUMMARY" 2>> "$CHUNK_ERROR"; then
        CHUNK_OK="1"
      fi
    fi

    if [ "$CHUNK_OK" = "1" ]; then
      if [ ! -s "$CHUNK_ERROR" ]; then
        rm -f "$CHUNK_ERROR"
      fi
    else
      cat > "$CHUNK_SUMMARY" <<EOF
# Chunk Context Summary

## Chunk Source
- Chunk prompt: ${CHUNK_PROMPT}
- Status: failed

## Error
See: ${CHUNK_ERROR}

## Compression Notes
Chunk distillation failed; human review required.
EOF
    fi
  done

  CHUNK_SUMMARIES=( "$RUN_DIR"/chunks/chunk_[0-9][0-9][0-9]_summary.md )
  if [ ! -f "${CHUNK_SUMMARIES[0]}" ]; then
    echo "No chunk summary files found: $RUN_DIR/chunks/chunk_[0-9][0-9][0-9]_summary.md"
    exit 1
  fi

  cat > "$RUN_DIR/synthesis_prompt.md" <<EOF
You are the Zaphod's Third Hand Context Distiller.

Synthesize a single final Context File from the chunk summaries below.

Produce only this structure:

# Conversation Context File

## Source
- Source ID: ${SOURCE_ID}
- Source type:
- Source file or link: ${SOURCE_FILE}
- Conversation title: ${SHORT_TITLE}
- Approximate date range:
- Project:
- Confidence:

## Executive Summary

## Durable Facts

## Decisions Made

## Open Questions

## Bugs / Issues Identified

## Rules Added

## Version / Release Notes

## User Preferences

## Files / Artifacts Mentioned

## Next Actions

## Suggested Destination

## Compression Notes

CHUNK SUMMARIES:
EOF

  for CHUNK_SUMMARY in "${CHUNK_SUMMARIES[@]}"; do
    cat >> "$RUN_DIR/synthesis_prompt.md" <<EOF

---
Chunk summary file: ${CHUNK_SUMMARY}
---

EOF
    cat "$CHUNK_SUMMARY" >> "$RUN_DIR/synthesis_prompt.md"
  done
fi

cat > "$RUN_DIR/TASK.md" <<EOF
Run the Zaphod's Third Hand Context Distiller on source ${SOURCE_ID}.

Create:
- ${SESSION_FILE}
- ${PATCH_FILE}
EOF

cp "$SOURCE_FILE" "$RUN_DIR/INPUT.md"

cat > "$RUN_DIR/MODEL_REQUEST.md" <<EOF
Worker: OpenAI-compatible model endpoint
Base URL: ${BASE_URL}
Model: ${MODEL}
Task: Create session summary and context review patch.
Source ID: ${SOURCE_ID}
Source file: ${SOURCE_FILE}
Short title: ${SHORT_TITLE}
Compact mode: ${COMPACT_MODE}
Chunked mode: ${CHUNKED_MODE}
Chunk line size: ${CHUNK_LINES}
EOF

if [ "$COMPACT_MODE" = "1" ]; then
  cat > "$RUN_DIR/session_prompt.md" <<EOF
You are the Zaphod's Third Hand Context Distiller.

Summarize the provided source into this exact markdown structure and nothing else:

# Conversation Context File

## Source
- Source ID: ${SOURCE_ID}
- Source type:
- Source file or link: ${SOURCE_FILE}
- Conversation title: ${SHORT_TITLE}
- Approximate date range:
- Project:
- Confidence:

## Executive Summary

## Durable Facts

## Decisions Made

## Open Questions

## Bugs / Issues Identified

## Rules Added

## Version / Release Notes

## User Preferences

## Files / Artifacts Mentioned

## Next Actions

## Suggested Destination

## Compression Notes

Source text follows:
EOF

  cat "$SOURCE_FILE" >> "$RUN_DIR/session_prompt.md"
else
  cat > "$RUN_DIR/session_prompt.md" <<EOF
You are the Zaphod's Third Hand Context Distiller.

Read the source text below and produce only a Conversation Context File using this exact structure:

# Conversation Context File

## Source
- Source ID: ${SOURCE_ID}
- Source type:
- Source file or link: ${SOURCE_FILE}
- Conversation title: ${SHORT_TITLE}
- Approximate date range:
- Project:
- Confidence:

## Executive Summary

## Durable Facts

## Decisions Made

## Open Questions

## Bugs / Issues Identified

## Rules Added

## Version / Release Notes

## User Preferences

## Files / Artifacts Mentioned

## Next Actions

## Suggested Destination

## Compression Notes

Do not produce a separate report.
Do not update canonical files.
Do not include raw transcript text unless needed as evidence.

SOURCE TEXT:
EOF

  cat "$SOURCE_FILE" >> "$RUN_DIR/session_prompt.md"
fi

if [ "$CHUNKED_MODE" = "1" ]; then
  call_model --max-tokens 2200 < "$RUN_DIR/synthesis_prompt.md" > "$SESSION_FILE"
else
  call_model --max-tokens 2200 < "$RUN_DIR/session_prompt.md" > "$SESSION_FILE"
fi

cat > "$RUN_DIR/patch_prompt.md" <<EOF
You are creating a review patch for source ${SOURCE_ID}.

Read the session summary below and produce only this structure:

# Context Review Patch ${SOURCE_ID}

## Proposed Durable Facts

## Proposed Decisions

## Proposed Rules

## Proposed Risks / Bugs

## Proposed Next Actions

## Proposed Workflow Updates

## Unmerged / Needs Human Review

Only include concrete, durable updates. Use "- No update proposed." where no update is needed.
Review patches are not canonical until a human accepts them.

SESSION SUMMARY:
EOF

cat "$SESSION_FILE" >> "$RUN_DIR/patch_prompt.md"

call_model --max-tokens 1800 < "$RUN_DIR/patch_prompt.md" > "$PATCH_FILE"

cp "$SESSION_FILE" "$RUN_DIR/OUTPUT.md"

cat > "$RUN_DIR/REVIEW.md" <<EOF
# Review

Status: pending human review

Session summary:
- ${SESSION_FILE}

Context review patch:
- ${PATCH_FILE}
EOF

cat > "$RUN_DIR/METRICS.json" <<EOF
{
  "source_id": "${SOURCE_ID}",
  "source_file": "${SOURCE_FILE}",
  "short_title": "${SHORT_TITLE}",
  "compact_mode": "${COMPACT_MODE}",
  "chunked_mode": "${CHUNKED_MODE}",
  "chunk_line_size": "${CHUNK_LINES}",
  "chunk_count": "${CHUNK_COUNT}",
  "session_file": "${SESSION_FILE}",
  "patch_file": "${PATCH_FILE}",
  "worker": "openai-compatible-model-endpoint",
  "base_url": "${BASE_URL}",
  "model": "${MODEL}",
  "status": "completed"
}
EOF

cat > "$RUN_DIR/ACCEPTED.md" <<EOF
# Accepted

Status: pending

Human review required before canonical merge.
EOF

echo "Wrote session: ${SESSION_FILE}"
echo "Wrote patch:   ${PATCH_FILE}"
echo "Run folder:    ${RUN_DIR}"
