#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ZTH_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
WORK="$REPO/.work/dogfood"
BATCH_ROOT="$WORK/batches"
QUEUE="$WORK/roadmap_queue.tsv"
STATE="$WORK/state.tsv"
WATCHDOG_SCRIPT="$REPO/scripts/zth_dogfood_watchdog.sh"
SESSION="${ZTH_DOGFOOD_SESSION:-zth-dogfood-run}"

usage() {
  cat <<'EOF'
Usage:
  scripts/zth_dogfood_batch.sh status
  scripts/zth_dogfood_batch.sh validate
  scripts/zth_dogfood_batch.sh bundle [out-dir]
  scripts/zth_dogfood_batch.sh prepare-from-tsv <queue-file> <batch-name> [--allow-cron-active]
  scripts/zth_dogfood_batch.sh archive-current <batch-name>
  scripts/zth_dogfood_batch.sh check-cron
  scripts/zth_dogfood_batch.sh print-disable-cron-command

This wrapper is operator-only. It does not run the watchdog or call a model endpoint.
EOF
}

ensure_repo() {
  cd "$REPO"
  mkdir -p "$WORK" "$BATCH_ROOT"
}

queue_rows() {
  if [ ! -f "$QUEUE" ]; then
    return 0
  fi
  awk -F '\t' '!/^#/ && NF >= 3 { print }' "$QUEUE"
}

state_rows() {
  if [ ! -f "$STATE" ]; then
    return 0
  fi
  awk -F '\t' 'NF >= 4 { print }' "$STATE"
}

order_mismatch_report() {
  local queue_tmp state_tmp mismatch
  queue_tmp="$(mktemp)"
  state_tmp="$(mktemp)"
  trap 'rm -f "$queue_tmp" "$state_tmp"' RETURN

  queue_rows > "$queue_tmp"
  state_rows > "$state_tmp"

  if [ ! -s "$queue_tmp" ] || [ ! -s "$state_tmp" ]; then
    printf 'no\n'
    return 0
  fi

  mismatch="$(
    awk -F '\t' '
      NR==FNR { queue[++n] = $2; next }
      { if (queue[FNR] != $2) mismatch = 1 }
      END { print mismatch ? "yes" : "no" }
    ' "$queue_tmp" "$state_tmp"
  )"

  printf '%s\n' "$mismatch"
}

status_report() {
  local total completed remaining latest order_mismatch duplicate_count exhaustion_visible
  total="$(queue_rows | wc -l | tr -d ' ')"
  completed="$(state_rows | wc -l | tr -d ' ')"
  remaining="$((total - completed))"
  latest="$(state_rows | tail -n 1 | awk -F '\t' '{ print $2 }')"
  duplicate_count="$(state_rows | awk -F '\t' '{ count[$2]++ } END { d=0; for (k in count) if (count[k] > 1) d++; print d+0 }')"
  order_mismatch="$(order_mismatch_report)"
  exhaustion_visible="no"
  if [ -f "$WORK/stage.log" ] && grep -q "No remaining dogfood stages\." "$WORK/stage.log"; then
    exhaustion_visible="yes"
  fi

  cat <<EOF
Dogfood batch status
  queue_total: $total
  completed: $completed
  remaining: $remaining
  duplicate_state_slugs: $duplicate_count
  queue_state_order_mismatch: $order_mismatch
  latest_completed_slug: ${latest:-none}
  exhaustion_visible_in_stage_log: $exhaustion_visible
  queue_file: $QUEUE
  state_file: $STATE
EOF
}

cron_active() {
  local line=""
  if command -v crontab >/dev/null 2>&1; then
    line="$(crontab -l 2>/dev/null | grep -F "$WATCHDOG_SCRIPT" || true)"
  fi
  if [ -n "$line" ]; then
    return 0
  fi
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    return 0
  fi
  return 1
}

check_cron() {
  local cron_line="inactive"
  if command -v crontab >/dev/null 2>&1; then
    cron_line="$(crontab -l 2>/dev/null | grep -F "$WATCHDOG_SCRIPT" || true)"
  fi
  if [ -n "$cron_line" ]; then
    cat <<EOF
dogfood cron status
  watchdog_cron_line: active
  watchdog_cron_entry: $cron_line
EOF
  else
    cat <<EOF
dogfood cron status
  watchdog_cron_line: inactive
EOF
  fi
}

validate_batch() {
  python3 "$REPO/local_harness/validate_dogfood_batch_artifacts.py" \
    --queue "$QUEUE" \
    --state "$STATE" \
    --runs-dir "$WORK/runs" \
    --stage-log "$WORK/stage.log"
}

bundle_batch() {
  local out_dir="${1:-$WORK/reviews/latest_acceptance_review_bundle}"
  python3 "$REPO/local_harness/render_dogfood_acceptance_review_bundle.py" \
    --queue "$QUEUE" \
    --state "$STATE" \
    --runs-dir "$WORK/runs" \
    --stage-log "$WORK/stage.log" \
    --out-dir "$out_dir"
}

archive_current() {
  local batch_name="$1"
  local batch_dir="$BATCH_ROOT/$batch_name"
  mkdir -p "$batch_dir"
  cp -a "$QUEUE" "$batch_dir/roadmap_queue.tsv" 2>/dev/null || true
  cp -a "$STATE" "$batch_dir/state.tsv" 2>/dev/null || true
  [ -f "$WORK/stage.log" ] && cp -a "$WORK/stage.log" "$batch_dir/stage.log"
  [ -f "$WORK/watchdog.log" ] && cp -a "$WORK/watchdog.log" "$batch_dir/watchdog.log"
  [ -f "$WORK/watchdog.status.log" ] && cp -a "$WORK/watchdog.status.log" "$batch_dir/watchdog.status.log"
  [ -f "$WORK/active_stage.lease" ] && cp -a "$WORK/active_stage.lease" "$batch_dir/active_stage.lease"
  printf '%s\n' "$batch_dir"
}

prepare_from_tsv() {
  local queue_file="$1"
  local batch_name="$2"
  local allow_cron="${3:-}"
  local batch_dir="$BATCH_ROOT/$batch_name"

  if [ ! -f "$queue_file" ]; then
    printf 'missing queue file: %s\n' "$queue_file" >&2
    exit 1
  fi

  if [ "${allow_cron}" != "--allow-cron-active" ] && cron_active; then
    printf 'cron appears active; refuse prepare without --allow-cron-active\n' >&2
    exit 1
  fi

  mkdir -p "$batch_dir"
  archive_current "$batch_name" >/dev/null

  if ! awk -F '\t' '
    BEGIN { ok = 1 }
    /^#/ { next }
    NF == 0 { next }
    NF < 3 { ok = 0 }
    END { exit ok ? 0 : 1 }
  ' "$queue_file"; then
    printf 'queue file must contain comment lines or tab-separated rows with at least 3 fields\n' >&2
    exit 1
  fi

  cp -a "$queue_file" "$QUEUE"
  : > "$STATE"
  printf 'prepared batch: %s\n' "$batch_dir"
  printf 'queue replaced: %s\n' "$QUEUE"
  printf 'state reset: %s\n' "$STATE"
}

main() {
  ensure_repo
  case "${1:-}" in
    status)
      status_report
      ;;
    validate)
      validate_batch
      ;;
    bundle)
      shift
      if [ "${#}" -gt 1 ]; then
        usage >&2
        exit 1
      fi
      bundle_batch "${1:-}"
      ;;
    prepare-from-tsv)
      shift
      if [ "${#}" -lt 2 ] || [ "${#}" -gt 3 ]; then
        usage >&2
        exit 1
      fi
      prepare_from_tsv "$@"
      ;;
    archive-current)
      shift
      if [ "${#}" -ne 1 ]; then
        usage >&2
        exit 1
      fi
      archive_current "$1"
      ;;
    check-cron)
      check_cron
      ;;
    print-disable-cron-command)
      printf '%s\n' "crontab -l | grep -v 'scripts/zth_dogfood_watchdog.sh' | crontab -"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
