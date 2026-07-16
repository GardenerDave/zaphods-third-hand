#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ZTH_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"

usage() {
  cat <<'EOF'
Usage:
  scripts/zth_prompt_patch_candidate.sh RUN_DIR CANDIDATE_CASE_ID [OUT_DIR]

This wrapper is operator-only. It exports a supervised live prompt patch A/B
candidate draft, reviews it deterministically, and prints the resulting paths
and reviewability status. It does not import fixtures or promote patches.
EOF
}

main() {
  local run_dir="${1:-}"
  local candidate_case_id="${2:-}"
  local out_dir="${3:-}"
  local run_base review_rc review_path candidate_path reviewable harness_result

  if [ "${run_dir}" = "" ] || [ "${candidate_case_id}" = "" ]; then
    usage >&2
    exit 1
  fi
  if [ "$#" -gt 3 ]; then
    usage >&2
    exit 1
  fi

  if [ "${out_dir}" = "" ]; then
    run_base="$(basename "$run_dir")"
    out_dir="$REPO/.work/prompt_patch_ab_candidates/$run_base"
  fi

  mkdir -p "$out_dir"
  candidate_path="$out_dir/prompt_patch_ab_fixture_candidate.json"
  review_path="$out_dir/prompt_patch_ab_fixture_candidate_review.json"

  python3 "$REPO/local_harness/export_prompt_patch_ab_fixture_candidate.py" \
    --run-dir "$run_dir" \
    --case-id "$candidate_case_id" \
    --out "$candidate_path"

  set +e
  python3 "$REPO/local_harness/review_prompt_patch_ab_fixture_candidate.py" \
    --candidate "$candidate_path" \
    --out "$review_path"
  review_rc="$?"
  set -e

  if [ -f "$review_path" ]; then
    reviewable="$(python3 - <<'PY' "$review_path"
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(str(bool(payload.get("reviewable"))).lower())
PY
)"
    harness_result="$(python3 - <<'PY' "$review_path"
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
results = payload.get("harness_result", {}).get("results", [])
print(results[0].get("result", "") if results else "")
PY
)"
    cat <<EOF
candidate_path: $candidate_path
review_path: $review_path
candidate_case_id: $candidate_case_id
reviewable: ${reviewable:-unknown}
harness_result: ${harness_result:-unknown}
manual_next_step: Review the candidate and review report. If accepted, manually copy candidate_case into the tracked fixture pack and commit only tracked fixture/test/doc changes.
EOF
  else
    cat <<EOF
candidate_path: $candidate_path
review_path: $review_path
candidate_case_id: $candidate_case_id
reviewable: unknown
harness_result: unknown
manual_next_step: Review the candidate and review report. If accepted, manually copy candidate_case into the tracked fixture pack and commit only tracked fixture/test/doc changes.
EOF
  fi

  exit "$review_rc"
}

main "$@"
