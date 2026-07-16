#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ZTH_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
WORK="$REPO/.work/dogfood"
LOCK="$WORK/watchdog.lock"
LEASE="$WORK/active_stage.lease"
LOG="$WORK/watchdog.log"
STAGE_LOG="$WORK/stage.log"
SESSION="${ZTH_DOGFOOD_SESSION:-zth-dogfood-run}"

mkdir -p "$WORK"
cd "$REPO"

redact_ips() {
  sed -E \
    -e 's#http://[0-9]{1,3}(\.[0-9]{1,3}){3}(:[0-9]+)?#http://<IP_REDACTED>#g' \
    -e 's#[0-9]{1,3}(\.[0-9]{1,3}){3}#<IP_REDACTED>#g'
}

{
  echo "---- $(date -Is) watchdog tick ----"

  exec 9>"$LOCK"
  if ! flock -n 9; then
    echo "watchdog already running; exit"
    exit 0
  fi

  if [ -f "$REPO/.env.local" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO/.env.local"
    set +a
  fi

  : "${ZTH_JARVIS_BASE_URL:?missing ZTH_JARVIS_BASE_URL}"
  : "${ZTH_PUBLIC_HOST_ALIAS:=JARVIS_LOCAL}"
  : "${ZTH_MODEL_ID:=Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf}"

  if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "active tmux session exists: $SESSION"
    exit 0
  fi

  if [ -f "$LEASE" ]; then
    now="$(date +%s)"
    lease_time="$(stat -c %Y "$LEASE")"
    age="$((now - lease_time))"

    if [ "$age" -lt 900 ]; then
      echo "recent active lease exists age=${age}s; exit"
      exit 0
    fi

    echo "stale lease found age=${age}s; removing"
    rm -f "$LEASE"
  fi

  if ! curl -fsS "$ZTH_JARVIS_BASE_URL/v1/models" >/dev/null; then
    echo "model endpoint unavailable: $ZTH_PUBLIC_HOST_ALIAS"
    exit 0
  fi

  q_repo="$(printf '%q' "$REPO")"
  q_lease="$(printf '%q' "$LEASE")"
  q_stage_log="$(printf '%q' "$STAGE_LOG")"
  q_model_id="$(printf '%q' "$ZTH_MODEL_ID")"

  echo "starting dogfood runner in tmux session: $SESSION"

  tmux new-session -d -s "$SESSION" "bash -lc '
    set -o pipefail
    cd $q_repo
    {
      echo \"---- runner wrapper start \$(date -Is) ----\"

      if [ -f .env.local ]; then
        set -a
        source .env.local
        set +a
      fi

      export ZTH_MODEL_ID=$q_model_id

      touch $q_lease

      bash scripts/zth_run_next_dogfood_stage.sh
      status=\$?

      echo \"---- runner wrapper exit status=\$status \$(date -Is) ----\"

      rm -f $q_lease
      exit \$status
    } 2>&1 | tee -a $q_stage_log
  '"

  echo "started: $SESSION"
} 2>&1 | redact_ips >> "$LOG"
