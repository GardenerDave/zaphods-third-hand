#!/usr/bin/env bash
set -euo pipefail
TAG="ZTH_OVERNIGHT_DOGFOOD_20260718"
tmp="$(mktemp)"
if crontab -l 2>/dev/null > "$tmp"; then :; else : > "$tmp"; fi
python3 - "$tmp" "$TAG" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1]); tag = sys.argv[2]
lines = [line for line in path.read_text(encoding="utf-8").splitlines() if tag not in line]
path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
PY
crontab "$tmp"
rm -f "$tmp"
printf '%s\n' "removed cron lines tagged $TAG"
