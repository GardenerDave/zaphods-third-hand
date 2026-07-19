#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ZTH_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
exec "$REPO/scripts/zth_overnight_dogfood_controller.sh" --status
