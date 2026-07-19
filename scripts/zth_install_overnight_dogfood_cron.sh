#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ZTH_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
TAG="ZTH_OVERNIGHT_DOGFOOD_20260718"
CRON_LINE="*/5 * * * * /bin/bash -lc 'cd \"$REPO\" && exec \"$REPO/scripts/zth_overnight_dogfood_controller.sh\" --tick' # $TAG"
tmp="$(mktemp)"
if crontab -l 2>/dev/null | grep -vF "$TAG" > "$tmp"; then :; else : > "$tmp"; fi
printf '%s\n' "$CRON_LINE" >> "$tmp"
crontab "$tmp"
rm -f "$tmp"
printf '%s\n' "$CRON_LINE"
printf '%s\n' "remove with: $REPO/scripts/zth_uninstall_overnight_dogfood_cron.sh"
