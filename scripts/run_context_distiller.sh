#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ "${1:-}" = "--manifest" ] || [ "${1:-}" = "--plan-only" ]; then
  exec python3 "${PACKAGE_ROOT}/local_harness/context_distiller_manifest.py" "$@"
fi

if [ $# -ge 3 ]; then
  exec python3 "${PACKAGE_ROOT}/local_harness/context_distiller_manifest.py" "$@"
fi

echo "Usage: ${0##*/} --manifest MANIFEST [--plan-only] | <SOURCE_ID> <SOURCE_FILE> <SHORT_TITLE>"
exit 1
