#!/usr/bin/env bash
set -euo pipefail

TAG="ZTH_LONG_DURATION_DOGFOOD"

usage() {
  cat <<'EOF'
Usage:
  scripts/zth_uninstall_long_duration_cron.sh

Remove only cron lines tagged for the long-duration dogfood tick.
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

  local tmp_cron
  tmp_cron="$(mktemp)"
  if crontab -l 2>/dev/null > "$tmp_cron"; then
    :
  else
    : > "$tmp_cron"
  fi

  python3 - "$tmp_cron" "$TAG" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
tag = sys.argv[2]
lines = path.read_text(encoding="utf-8").splitlines()
kept = [line for line in lines if tag not in line]
path.write_text(("\n".join(kept) + ("\n" if kept else "")), encoding="utf-8")
PY

  crontab "$tmp_cron"

  printf '%s\n' "remaining tagged cron lines:"
  crontab -l 2>/dev/null | grep -F "$TAG" || true

  rm -f "$tmp_cron"
}

main "$@"
