#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ZTH_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
WORK="$REPO/.work/long_duration_dogfood"
CONTROL_DIR="$WORK/control"
TAG="ZTH_LONG_DURATION_DOGFOOD"
CADENCE_MINUTES="${ZTH_LONG_DURATION_DOGFOOD_CADENCE_MINUTES:-20}"
MAX_DURATION_HOURS="${ZTH_LONG_DURATION_DOGFOOD_MAX_DURATION_HOURS:-8}"

usage() {
  cat <<'EOF'
Usage:
  scripts/zth_install_long_duration_cron.sh

Install a tagged user crontab entry for the long-duration dogfood tick.
EOF
}

main() {
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "${1:-}" = "help" ]; then
    usage
    exit 0
  fi
  if [ "$#" -gt 0 ]; then
    usage >&2
    exit 1
  fi

  mkdir -p "$CONTROL_DIR" "$WORK/runs"

  python3 - "$CONTROL_DIR/window.json" "$CADENCE_MINUTES" "$MAX_DURATION_HOURS" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
cadence_minutes = int(sys.argv[2])
max_duration_hours = int(sys.argv[3])
installed_at = int(datetime.now(tz=timezone.utc).timestamp())
expires_at = installed_at + max_duration_hours * 3600
payload = {
    "window_schema": "long_duration_dogfood_window_v1",
    "source": "cron_install",
    "installed_at_epoch": installed_at,
    "installed_at_utc": datetime.fromtimestamp(installed_at, tz=timezone.utc).isoformat(),
    "expires_at_epoch": expires_at,
    "expires_at_utc": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
    "cadence_minutes": cadence_minutes,
    "max_duration_hours": max_duration_hours,
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

  local cron_line
  cron_line="*/${CADENCE_MINUTES} * * * * cd \"$REPO\" && \"$REPO/scripts/zth_long_duration_dogfood_tick.sh\" --once # $TAG"

  local tmp_cron
  tmp_cron="$(mktemp)"
  if crontab -l 2>/dev/null | grep -v "$TAG" > "$tmp_cron"; then
    :
  else
    : > "$tmp_cron"
  fi
  printf '%s\n' "$cron_line" >> "$tmp_cron"
  crontab "$tmp_cron"
  rm -f "$tmp_cron"

  printf '%s\n' "installed cron line:"
  printf '%s\n' "$cron_line"
  printf '%s\n' "uninstall command:"
  printf '%s\n' "$REPO/scripts/zth_uninstall_long_duration_cron.sh"
}

main "$@"
