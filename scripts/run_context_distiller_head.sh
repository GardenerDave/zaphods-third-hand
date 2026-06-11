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
CHUNK_MAX_TOKENS="${ZTH_DISTILLER_CHUNK_MAX_TOKENS:-1200}"
SESSION_MAX_TOKENS="${ZTH_DISTILLER_SESSION_MAX_TOKENS:-2200}"
PATCH_MAX_TOKENS="${ZTH_DISTILLER_PATCH_MAX_TOKENS:-1800}"
CALL_TIMEOUT="${ZTH_DISTILLER_TIMEOUT:-900}"
FINAL_ONLY="${ZTH_DISTILLER_FINAL_ONLY:-0}"

case "$FINAL_ONLY" in
  1|true|TRUE|yes|YES)
    FINAL_ONLY="1"
    ;;
  *)
    FINAL_ONLY="0"
    ;;
esac

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
RUN_STARTED_AT="$(date -u +%FT%TZ)"
RUN_START_EPOCH="$(date +%s)"
RUN_STATUS="running"
FAILURE_STAGE=""
CHUNK_SPLIT_STATUS="skipped"
CHUNK_SUMMARY_STATUS="skipped"
CHUNK_SPLIT_SECONDS="0"
CHUNK_SUMMARY_SECONDS="0"
CHUNK_ATTEMPTED="0"
CHUNK_SUCCEEDED="0"
CHUNK_FAILED="0"
CHUNK_RETRY_COUNT="0"
CHUNK_METRICS_FILE=""
SESSION_STATUS="pending"
SESSION_SECONDS="0"
SESSION_INPUT_PROMPT_FILE=""
PATCH_STATUS="pending"
PATCH_SECONDS="0"

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
METRICS_FILE="${RUN_DIR}/METRICS.json"
SESSION_METADATA_FILE="${RUN_DIR}/session_metadata.json"
PATCH_METADATA_FILE="${RUN_DIR}/patch_metadata.json"

now_epoch() {
  date +%s
}

elapsed_since() {
  local started_at="$1"
  echo "$(( $(now_epoch) - started_at ))"
}

file_bytes() {
  if [ -f "$1" ]; then
    wc -c < "$1" | tr -d ' '
  else
    echo "0"
  fi
}

file_lines() {
  if [ -f "$1" ]; then
    wc -l < "$1" | tr -d ' '
  else
    echo "0"
  fi
}

file_est_tokens() {
  local bytes
  bytes="$(file_bytes "$1")"
  echo "$(( (bytes + 3) / 4 ))"
}

json_number() {
  local file="$1"
  shift
  if [ ! -s "$file" ]; then
    echo "null"
    return
  fi

  python3 - "$file" "$@" <<'PY'
import json
import sys

path = sys.argv[1]
keys = sys.argv[2:]

try:
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    for key in keys:
        if not isinstance(value, dict):
            value = None
            break
        value = value.get(key)
    if isinstance(value, bool):
        value = None
    if isinstance(value, int):
        print(value)
    elif isinstance(value, float):
        print(int(value) if value.is_integer() else value)
    else:
        print("null")
except Exception:
    print("null")
PY
}

json_string() {
  local file="$1"
  shift
  if [ ! -s "$file" ]; then
    echo "null"
    return
  fi

  python3 - "$file" "$@" <<'PY'
import json
import sys

path = sys.argv[1]
keys = sys.argv[2:]

try:
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    for key in keys:
        if not isinstance(value, dict):
            value = None
            break
        value = value.get(key)
    if isinstance(value, str):
        print(json.dumps(value))
    else:
        print("null")
except Exception:
    print("null")
PY
}

write_metrics() {
  local status="${1:-$RUN_STATUS}"
  local completed_at
  local total_seconds
  local prompt_file

  completed_at="$(date -u +%FT%TZ)"
  total_seconds="$(elapsed_since "$RUN_START_EPOCH")"

  if [ -n "$SESSION_INPUT_PROMPT_FILE" ]; then
    prompt_file="$SESSION_INPUT_PROMPT_FILE"
  elif [ "$CHUNKED_MODE" = "1" ]; then
    prompt_file="${RUN_DIR}/synthesis_prompt.md"
  else
    prompt_file="${RUN_DIR}/session_prompt.md"
  fi

  cat > "$METRICS_FILE" <<EOF
{
  "source_id": "${SOURCE_ID}",
  "source_file": "${SOURCE_FILE}",
  "short_title": "${SHORT_TITLE}",
  "compact_mode": "${COMPACT_MODE}",
  "chunked_mode": "${CHUNKED_MODE}",
  "chunk_line_size": "${CHUNK_LINES}",
  "chunk_count": "${CHUNK_COUNT}",
  "chunk_max_tokens": "${CHUNK_MAX_TOKENS}",
  "session_max_tokens": "${SESSION_MAX_TOKENS}",
  "patch_max_tokens": "${PATCH_MAX_TOKENS}",
  "call_timeout_seconds": "${CALL_TIMEOUT}",
  "final_only": "${FINAL_ONLY}",
  "source": {
    "bytes": $(file_bytes "$SOURCE_FILE"),
    "lines": $(file_lines "$SOURCE_FILE"),
    "estimated_tokens": $(file_est_tokens "$SOURCE_FILE")
  },
  "prompts": {
    "session_prompt_file": "${prompt_file}",
    "session_prompt_bytes": $(file_bytes "$prompt_file"),
    "session_prompt_lines": $(file_lines "$prompt_file"),
    "session_prompt_estimated_tokens": $(file_est_tokens "$prompt_file"),
    "patch_prompt_file": "${RUN_DIR}/patch_prompt.md",
    "patch_prompt_bytes": $(file_bytes "${RUN_DIR}/patch_prompt.md"),
    "patch_prompt_lines": $(file_lines "${RUN_DIR}/patch_prompt.md"),
    "patch_prompt_estimated_tokens": $(file_est_tokens "${RUN_DIR}/patch_prompt.md")
  },
  "outputs": {
    "session_bytes": $(file_bytes "$SESSION_FILE"),
    "session_lines": $(file_lines "$SESSION_FILE"),
    "session_estimated_tokens": $(file_est_tokens "$SESSION_FILE"),
    "patch_bytes": $(file_bytes "$PATCH_FILE"),
    "patch_lines": $(file_lines "$PATCH_FILE"),
    "patch_estimated_tokens": $(file_est_tokens "$PATCH_FILE")
  },
  "model_usage": {
    "session_metadata_file": "${SESSION_METADATA_FILE}",
    "patch_metadata_file": "${PATCH_METADATA_FILE}",
    "session": {
      "finish_reason": $(json_string "$SESSION_METADATA_FILE" finish_reason),
      "prompt_tokens": $(json_number "$SESSION_METADATA_FILE" usage prompt_tokens),
      "completion_tokens": $(json_number "$SESSION_METADATA_FILE" usage completion_tokens),
      "total_tokens": $(json_number "$SESSION_METADATA_FILE" usage total_tokens),
      "timings": {
        "prompt_ms": $(json_number "$SESSION_METADATA_FILE" timings prompt_ms),
        "predicted_ms": $(json_number "$SESSION_METADATA_FILE" timings predicted_ms),
        "prompt_per_second": $(json_number "$SESSION_METADATA_FILE" timings prompt_per_second),
        "predicted_per_second": $(json_number "$SESSION_METADATA_FILE" timings predicted_per_second)
      }
    },
    "review_patch": {
      "finish_reason": $(json_string "$PATCH_METADATA_FILE" finish_reason),
      "prompt_tokens": $(json_number "$PATCH_METADATA_FILE" usage prompt_tokens),
      "completion_tokens": $(json_number "$PATCH_METADATA_FILE" usage completion_tokens),
      "total_tokens": $(json_number "$PATCH_METADATA_FILE" usage total_tokens),
      "timings": {
        "prompt_ms": $(json_number "$PATCH_METADATA_FILE" timings prompt_ms),
        "predicted_ms": $(json_number "$PATCH_METADATA_FILE" timings predicted_ms),
        "prompt_per_second": $(json_number "$PATCH_METADATA_FILE" timings prompt_per_second),
        "predicted_per_second": $(json_number "$PATCH_METADATA_FILE" timings predicted_per_second)
      }
    }
  },
  "stages": {
    "chunk_split": {
      "status": "${CHUNK_SPLIT_STATUS}",
      "elapsed_seconds": ${CHUNK_SPLIT_SECONDS}
    },
    "chunk_summary": {
      "status": "${CHUNK_SUMMARY_STATUS}",
      "elapsed_seconds": ${CHUNK_SUMMARY_SECONDS},
      "attempted": ${CHUNK_ATTEMPTED},
      "succeeded": ${CHUNK_SUCCEEDED},
      "failed": ${CHUNK_FAILED},
      "retry_count": ${CHUNK_RETRY_COUNT},
      "chunk_metrics_file": "${CHUNK_METRICS_FILE}"
    },
    "session": {
      "status": "${SESSION_STATUS}",
      "elapsed_seconds": ${SESSION_SECONDS}
    },
    "review_patch": {
      "status": "${PATCH_STATUS}",
      "elapsed_seconds": ${PATCH_SECONDS}
    }
  },
  "run_started_at": "${RUN_STARTED_AT}",
  "run_completed_at": "${completed_at}",
  "total_elapsed_seconds": ${total_seconds},
  "failure_stage": "${FAILURE_STAGE}",
  "session_file": "${SESSION_FILE}",
  "patch_file": "${PATCH_FILE}",
  "worker": "openai-compatible-model-endpoint",
  "base_url": "${BASE_URL}",
  "model": "${MODEL}",
  "status": "${status}"
}
EOF
}

on_exit() {
  local exit_code="$?"
  if [ "$exit_code" -ne 0 ] && [ -z "$FAILURE_STAGE" ]; then
    FAILURE_STAGE="script"
  fi
  if [ "$RUN_STATUS" != "completed" ]; then
    if [ "$exit_code" -ne 0 ]; then
      RUN_STATUS="failed"
    fi
    write_metrics "$RUN_STATUS"
  fi
}

trap on_exit EXIT

call_model() {
  if [ "$FINAL_ONLY" = "1" ]; then
    python3 "${PACKAGE_ROOT}/local_harness/icm_call.py" handoff --api openai-chat --base-url "$BASE_URL" --model "$MODEL" --timeout "$CALL_TIMEOUT" --final-only "$@"
  else
    python3 "${PACKAGE_ROOT}/local_harness/icm_call.py" handoff --api openai-chat --base-url "$BASE_URL" --model "$MODEL" --timeout "$CALL_TIMEOUT" "$@"
  fi
}

if [ "$CHUNKED_MODE" = "1" ]; then
  CHUNK_SPLIT_STATUS="running"
  CHUNK_SPLIT_START="$(now_epoch)"
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

  CHUNK_SPLIT_SECONDS="$(elapsed_since "$CHUNK_SPLIT_START")"
  CHUNK_SPLIT_STATUS="completed"
  CHUNK_SUMMARY_STATUS="running"
  CHUNK_SUMMARY_START="$(now_epoch)"
  CHUNK_METRICS_FILE="${RUN_DIR}/chunk_metrics.tsv"
  printf 'chunk_prompt\tchunk_summary\tstatus\tattempts\telapsed_seconds\tprompt_estimated_tokens\toutput_estimated_tokens\tprompt_bytes\toutput_bytes\terror_log\tmetadata_file\n' > "$CHUNK_METRICS_FILE"

  for CHUNK_PROMPT in "$RUN_DIR"/chunks/chunk_[0-9][0-9][0-9]_prompt.md; do
    [ -f "$CHUNK_PROMPT" ] || continue
    CHUNK_SUMMARY="${CHUNK_PROMPT%_prompt.md}_summary.md"
    CHUNK_ERROR="${CHUNK_PROMPT%_prompt.md}_error.log"
    CHUNK_METADATA="${CHUNK_PROMPT%_prompt.md}_metadata.json"
    CHUNK_METADATA_PATH="$CHUNK_METADATA"
    CHUNK_OK="0"
    CHUNK_STATUS="failed"
    CHUNK_ATTEMPTS="1"
    CHUNK_STAGE_START="$(now_epoch)"
    CHUNK_ATTEMPTED="$((CHUNK_ATTEMPTED + 1))"
    : > "$CHUNK_ERROR"

    if call_model --metadata-out "$CHUNK_METADATA" --max-tokens "$CHUNK_MAX_TOKENS" < "$CHUNK_PROMPT" > "$CHUNK_SUMMARY" 2>> "$CHUNK_ERROR"; then
      CHUNK_OK="1"
    else
      {
        echo
        echo "--- retry 1 ---"
      } >> "$CHUNK_ERROR"
      CHUNK_ATTEMPTS="2"
      CHUNK_RETRY_COUNT="$((CHUNK_RETRY_COUNT + 1))"
      CHUNK_METADATA="${CHUNK_PROMPT%_prompt.md}_retry1_metadata.json"
      CHUNK_METADATA_PATH="$CHUNK_METADATA"

      if call_model --metadata-out "$CHUNK_METADATA" --max-tokens "$CHUNK_MAX_TOKENS" < "$CHUNK_PROMPT" > "$CHUNK_SUMMARY" 2>> "$CHUNK_ERROR"; then
        CHUNK_OK="1"
      fi
    fi

    if [ "$CHUNK_OK" = "1" ]; then
      CHUNK_STATUS="completed"
      CHUNK_SUCCEEDED="$((CHUNK_SUCCEEDED + 1))"
      if [ ! -s "$CHUNK_ERROR" ]; then
        rm -f "$CHUNK_ERROR"
      fi
    else
      CHUNK_FAILED="$((CHUNK_FAILED + 1))"
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

    if [ -f "$CHUNK_ERROR" ]; then
      CHUNK_ERROR_PATH="$CHUNK_ERROR"
    else
      CHUNK_ERROR_PATH=""
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$CHUNK_PROMPT" \
      "$CHUNK_SUMMARY" \
      "$CHUNK_STATUS" \
      "$CHUNK_ATTEMPTS" \
      "$(elapsed_since "$CHUNK_STAGE_START")" \
      "$(file_est_tokens "$CHUNK_PROMPT")" \
      "$(file_est_tokens "$CHUNK_SUMMARY")" \
      "$(file_bytes "$CHUNK_PROMPT")" \
      "$(file_bytes "$CHUNK_SUMMARY")" \
      "$CHUNK_ERROR_PATH" \
      "$CHUNK_METADATA_PATH" >> "$CHUNK_METRICS_FILE"
  done

  CHUNK_SUMMARY_SECONDS="$(elapsed_since "$CHUNK_SUMMARY_START")"
  if [ "$CHUNK_ATTEMPTED" -eq 0 ]; then
    CHUNK_SUMMARY_STATUS="skipped"
  elif [ "$CHUNK_FAILED" -eq 0 ]; then
    CHUNK_SUMMARY_STATUS="completed"
  elif [ "$CHUNK_SUCCEEDED" -eq 0 ]; then
    CHUNK_SUMMARY_STATUS="failed"
  else
    CHUNK_SUMMARY_STATUS="partial"
  fi

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
Chunk max tokens: ${CHUNK_MAX_TOKENS}
Session max tokens: ${SESSION_MAX_TOKENS}
Patch max tokens: ${PATCH_MAX_TOKENS}
Call timeout seconds: ${CALL_TIMEOUT}
Final-only/no-think mode: ${FINAL_ONLY}
Session metadata file: ${SESSION_METADATA_FILE}
Patch metadata file: ${PATCH_METADATA_FILE}
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
  SESSION_INPUT_PROMPT_FILE="${RUN_DIR}/synthesis_prompt.md"
else
  SESSION_INPUT_PROMPT_FILE="${RUN_DIR}/session_prompt.md"
fi

SESSION_STATUS="running"
SESSION_STAGE_START="$(now_epoch)"
if call_model --metadata-out "$SESSION_METADATA_FILE" --max-tokens "$SESSION_MAX_TOKENS" < "$SESSION_INPUT_PROMPT_FILE" > "$SESSION_FILE"; then
  SESSION_SECONDS="$(elapsed_since "$SESSION_STAGE_START")"
  SESSION_STATUS="completed"
else
  SESSION_SECONDS="$(elapsed_since "$SESSION_STAGE_START")"
  SESSION_STATUS="failed"
  FAILURE_STAGE="session"
  RUN_STATUS="failed"
  exit 1
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

PATCH_STATUS="running"
PATCH_STAGE_START="$(now_epoch)"
if call_model --metadata-out "$PATCH_METADATA_FILE" --max-tokens "$PATCH_MAX_TOKENS" < "$RUN_DIR/patch_prompt.md" > "$PATCH_FILE"; then
  PATCH_SECONDS="$(elapsed_since "$PATCH_STAGE_START")"
  PATCH_STATUS="completed"
else
  PATCH_SECONDS="$(elapsed_since "$PATCH_STAGE_START")"
  PATCH_STATUS="failed"
  FAILURE_STAGE="review_patch"
  RUN_STATUS="failed"
  exit 1
fi

cp "$SESSION_FILE" "$RUN_DIR/OUTPUT.md"

cat > "$RUN_DIR/REVIEW.md" <<EOF
# Review

Status: pending human review

Session summary:
- ${SESSION_FILE}

Context review patch:
- ${PATCH_FILE}
EOF

RUN_STATUS="completed"
write_metrics "$RUN_STATUS"

cat > "$RUN_DIR/ACCEPTED.md" <<EOF
# Accepted

Status: pending

Human review required before canonical merge.
EOF

echo "Wrote session: ${SESSION_FILE}"
echo "Wrote patch:   ${PATCH_FILE}"
echo "Run folder:    ${RUN_DIR}"
