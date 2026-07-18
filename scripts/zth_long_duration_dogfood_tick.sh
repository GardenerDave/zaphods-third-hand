#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ZTH_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
WORK="$REPO/.work/long_duration_dogfood"
CONTROL_DIR="$WORK/control"
RUNS_DIR="$WORK/runs"
LOCK_FILE="$WORK/tick.lock"
DEFAULT_CADENCE_MINUTES=20
DEFAULT_MAX_DURATION_HOURS=8
CONTROL_FILE="$CONTROL_DIR/window.json"
RUN_ID=""
RUN_DIR=""

usage() {
  cat <<'EOF'
Usage:
  scripts/zth_long_duration_dogfood_tick.sh [--once]

Run one bounded supervised dogfood tick. The script is safe for cron and does
not mutate tracked files, commit, push, queue-write, or grant authority.
EOF
}

now_epoch() {
  date +%s
}

iso_now() {
  date -Is
}

ensure_control_window() {
  if [ -f "$CONTROL_FILE" ]; then
    return 0
  fi

  local installed_at expires_at
  installed_at="$(now_epoch)"
  expires_at="$((installed_at + DEFAULT_MAX_DURATION_HOURS * 3600))"
  python3 - "$CONTROL_FILE" "$installed_at" "$expires_at" "$DEFAULT_CADENCE_MINUTES" "$DEFAULT_MAX_DURATION_HOURS" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
installed_at = int(sys.argv[2])
expires_at = int(sys.argv[3])
cadence_minutes = int(sys.argv[4])
max_duration_hours = int(sys.argv[5])

payload = {
    "window_schema": "long_duration_dogfood_window_v1",
    "source": "manual_bootstrap",
    "installed_at_epoch": installed_at,
    "installed_at_utc": datetime.fromtimestamp(installed_at, tz=timezone.utc).isoformat(),
    "expires_at_epoch": expires_at,
    "expires_at_utc": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
    "cadence_minutes": cadence_minutes,
    "max_duration_hours": max_duration_hours,
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

read_window() {
  python3 - "$CONTROL_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print(json.dumps({
        "window_schema": "long_duration_dogfood_window_v1",
        "source": "missing_control",
        "installed_at_epoch": None,
        "installed_at_utc": None,
        "expires_at_epoch": None,
        "expires_at_utc": None,
        "cadence_minutes": 20,
        "max_duration_hours": 8,
    }, indent=2, sort_keys=True))
    raise SystemExit(0)

payload = json.loads(path.read_text(encoding="utf-8"))
print(json.dumps(payload, indent=2, sort_keys=True))
PY
}

check_tracked_clean() {
  local tracked_dirty
  tracked_dirty="$(git -C "$REPO" status --short --untracked-files=no || true)"
  if [ -n "$tracked_dirty" ]; then
    printf '%s\n' "tracked modifications present; refusing to start tick" >&2
    printf '%s\n' "$tracked_dirty" >&2
    return 1
  fi
}

start_run() {
  RUN_ID="$(date +%Y%m%d_%H%M%S)"
  RUN_DIR="$RUNS_DIR/$RUN_ID"
  mkdir -p "$RUN_DIR"
  exec >"$RUN_DIR/tick.log" 2>&1
}

record_file() {
  local path="$1"
  shift
  "$@" > "$path"
}

run_command() {
  local name="$1"
  shift
  local stdout="$RUN_DIR/${name}.stdout.txt"
  local stderr="$RUN_DIR/${name}.stderr.txt"
  local exitcode="$RUN_DIR/${name}.exitcode"
  set +e
  "$@" >"$stdout" 2>"$stderr"
  local rc="$?"
  set -e
  printf '%s\n' "$rc" > "$exitcode"
  return 0
}

write_summary() {
  local classification="$1"
  local next_task_category="$2"
  local next_task_title="$3"
  local next_prompt="$4"
  local window_json="$5"
  local branch="$6"
  local head_commit="$7"
  python3 - "$RUN_DIR/tick_summary.json" "$classification" "$next_task_category" "$next_task_title" "$next_prompt" "$window_json" "$branch" "$head_commit" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
classification = sys.argv[2]
next_task_category = sys.argv[3]
next_task_title = sys.argv[4]
next_prompt = sys.argv[5]
window = json.loads(sys.argv[6])
branch = sys.argv[7]
head_commit = sys.argv[8]

def read_status(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

payload = {
    "summary_schema": "long_duration_dogfood_tick_v1",
    "summary_status": classification,
    "next_task_category": next_task_category,
    "next_task_title": next_task_title,
    "implementation_prompt": next_prompt,
    "branch": branch,
    "head_commit": head_commit,
    "run_dir": str(summary_path.parent),
    "window": window,
    "git_status_short": read_status(summary_path.parent / "git_status_short.txt").splitlines(),
    "git_log_oneline_20": read_status(summary_path.parent / "git_log_oneline_20.txt").splitlines(),
    "roadmap_snippets": read_status(summary_path.parent / "roadmap_snippets.txt").splitlines(),
    "safe_checks": {
        "git_diff_check": {
            "exit_code": int((summary_path.parent / "git_diff_check.exitcode").read_text(encoding="utf-8").strip())
            if (summary_path.parent / "git_diff_check.exitcode").exists()
            else None
        },
        "queue_handoff_validator_tests": {
            "exit_code": int((summary_path.parent / "pytest_queue_handoff.exitcode").read_text(encoding="utf-8").strip())
            if (summary_path.parent / "pytest_queue_handoff.exitcode").exists()
            else None
        },
        "front_door_tests": {
            "exit_code": int((summary_path.parent / "pytest_front_door.exitcode").read_text(encoding="utf-8").strip())
            if (summary_path.parent / "pytest_front_door.exitcode").exists()
            else None
        },
    },
}
summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
PY
}

main() {
  local once=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --once)
        once=1
        shift
        ;;
      -h|--help|help)
        usage
        exit 0
        ;;
      *)
        usage >&2
        exit 1
        ;;
    esac
  done

  if [ "$once" -ne 1 ]; then
    once=1
  fi

  check_tracked_clean
  mkdir -p "$WORK" "$CONTROL_DIR" "$RUNS_DIR"
  ensure_control_window

  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    printf '%s\n' "another long-duration dogfood tick is already running; exiting cleanly"
    exit 0
  fi

  start_run

  local window_json window_status branch head_commit
  window_json="$(read_window)"
  printf '%s\n' "$window_json" > "$RUN_DIR/window.json"
  window_status="$(python3 - <<'PY' "$RUN_DIR/window.json"
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
now = int(__import__("time").time())
expires = payload.get("expires_at_epoch")
if expires is None:
    print("missing_window")
elif now > int(expires):
    print("expired")
else:
    print("active")
PY
)"

  printf 'run_id=%s\n' "$RUN_ID"
  printf 'run_dir=%s\n' "$RUN_DIR"
  branch="$(git -C "$REPO" branch --show-current)"
  head_commit="$(git -C "$REPO" rev-parse HEAD)"
  printf 'branch=%s\n' "$branch"
  printf 'head=%s\n' "$head_commit"
  printf 'window_status=%s\n' "$window_status"

  record_file "$RUN_DIR/git_status_short.txt" git -C "$REPO" status --short --untracked-files=no
  record_file "$RUN_DIR/git_log_oneline_20.txt" git -C "$REPO" log --oneline -20
  record_file "$RUN_DIR/roadmap_snippets.txt" bash -lc "cd '$REPO' && rg -n 'future work remains|queue-handoff review|ready_for_review|blocked_needs_review|tests_or_fixtures|code_or_validator|docs_only' docs/ROADMAP.md docs/ORCHESTRATION_BOUNDARY.md docs/QUEUE_HANDOFF_REVIEW.md docs/REVIEW_TERMINOLOGY.md || true"

  local classification="blocked_needs_review"
  local next_task_category="blocked_needs_review"
  local next_task_title="Long-duration tick could not determine a safe next step."
  local next_prompt="Review the long-duration dogfood outputs manually; no implementation recommendation was generated."

  if [ "$window_status" = "active" ]; then
    run_command git_diff_check git -C "$REPO" diff --check
    run_command pytest_queue_handoff python3 -m pytest tests/test_validate_queue_handoff_review.py tests/test_queue_handoff_review_fixtures.py
    run_command pytest_front_door python3 -m pytest tests/test_review_front_door_chain.py tests/test_score_front_door_chain.py tests/test_validate_front_door_chain.py

    local diff_rc queue_rc front_rc
    diff_rc="$(cat "$RUN_DIR/git_diff_check.exitcode")"
    queue_rc="$(cat "$RUN_DIR/pytest_queue_handoff.exitcode")"
    front_rc="$(cat "$RUN_DIR/pytest_front_door.exitcode")"

    if [ "$diff_rc" -eq 0 ] && [ "$queue_rc" -eq 0 ] && [ "$front_rc" -eq 0 ]; then
      if [ ! -f "$REPO/tests/test_long_duration_dogfood_scripts.py" ]; then
        classification="tests_or_fixtures"
        next_task_category="tests_or_fixtures"
        next_task_title="Add bounded tests for the long-duration dogfood tick control window and cron tag handling."
        next_prompt=$'Add deterministic tests for scripts/zth_long_duration_dogfood_tick.sh, scripts/zth_install_long_duration_cron.sh, and scripts/zth_uninstall_long_duration_cron.sh. Cover lock contention, expired control-window skipping, cron tagging, and clean uninstall behavior. Preserve the authority boundary: no queue writing, no router automation, no unattended execution, no repo mutation without review.'
      elif [ ! -f "$REPO/local_harness/validate_queue_approval_path.py" ] || [ ! -f "$REPO/tests/test_validate_queue_approval_path.py" ] || [ ! -f "$REPO/tests/test_queue_approval_path_fixtures.py" ]; then
        classification="code_or_validator"
        next_task_category="code_or_validator"
        next_task_title="Add queue approval path validator design scaffold."
        next_prompt=$'Add a review-artifact-only validator scaffold for a future queue approval path. It must not write queues, insert queues, run queues, automate handoff, mutate repositories, train, promote, deploy, or grant downstream-use authority. Start with schema/validator/test fixtures only if the existing queue-handoff review artifacts provide enough evidence; otherwise produce a blocked review note explaining what design information is missing.'
      elif [ ! -f "$REPO/docs/reports/model_auditions/QUEUE_APPROVAL_PATH_CALIBRATION_SYNTHESIS_2026-07-18.md" ]; then
        classification="tests_or_fixtures"
        next_task_category="tests_or_fixtures"
        next_task_title="Add queue approval path calibration synthesis."
        next_prompt=$'Add a queue approval path calibration synthesis report after the validator, pass fixtures, blocked fixtures, and regression tests. Record what the queue_approval_path_v1 validator proves, what remains unimplemented, and the authority boundary. Do not add queue writing, queue insertion, queue running, automatic handoff, router automation, repo mutation, training capture, promotion, deployment, or downstream-use authority.'
      elif [ ! -f "$REPO/local_harness/review_queue_approval_path.py" ] || [ ! -f "$REPO/tests/test_review_queue_approval_path.py" ] || [ ! -f "$REPO/docs/reports/model_auditions/QUEUE_APPROVAL_REVIEW_COMMAND_2026-07-18.md" ]; then
        classification="code_or_validator"
        next_task_category="code_or_validator"
        next_task_title="Add read-only queue approval review command."
        next_prompt=$'Add a read-only queue approval review command that wraps queue_approval_path_v1 validation and emits a review/report artifact only. It must not write queues, insert queues, run queues, automate handoff, mutate repositories, import fixtures, train, promote, deploy, or grant downstream-use authority. Follow the existing front-door/queue-handoff review command pattern if present. If the existing command pattern is insufficient, produce a blocked review note explaining what design information is missing.'
      else
        classification="tests_or_fixtures"
        next_task_category="tests_or_fixtures"
        next_task_title="Add queue approval review command calibration synthesis."
        next_prompt=$'Add a queue approval review command calibration synthesis report after the read-only command, direct tests, smoke output, and regression slices. Record what queue_approval_path_review_v1 proves, what remains unimplemented, output-path safety behavior, exit-status behavior, and the authority boundary. Do not add queue writing, queue insertion, queue running, automatic handoff, router automation, repo mutation, fixture import, training capture, promotion, deployment, or downstream-use authority.'
      fi
    elif [ "$diff_rc" -ne 0 ]; then
      classification="blocked_needs_review"
      next_task_category="code_or_validator"
      next_task_title="Fix tracked diff-check failures before extending the long-duration dogfood loop."
      next_prompt=$'Fix the tracked diff-check failure(s) reported by scripts/zth_long_duration_dogfood_tick.sh. Keep the fix bounded, reviewed, and non-authoritative. Do not add queue writing, router automation, unattended execution, repo mutation without review, training capture, promotion, deployment, or downstream-use authority.'
    else
      classification="blocked_needs_review"
      next_task_category="code_or_validator"
      next_task_title="Repair the failing validator or review-chain tests before the next loop tick."
      next_prompt=$'Repair the failing validator or review-chain test output reported by scripts/zth_long_duration_dogfood_tick.sh. Keep the change bounded to the failing validator, fixture, or test, and preserve the authority boundary: no queue writing, no router automation, no unattended execution, no repo mutation without review, no training capture, no promotion, no deployment, and no downstream-use grant.'
    fi
  else
    next_task_category="blocked_needs_review"
    next_task_title="The long-duration control window expired before the tick could do useful work."
    next_prompt=$'Refresh the long-duration control window and review the expired tick evidence before any further implementation. Keep the loop supervised and non-authoritative.'
  fi

  local summary_path="$RUN_DIR/tick_summary.json"
  write_summary "$classification" "$next_task_category" "$next_task_title" "$next_prompt" "$window_json" "$branch" "$head_commit" > "$RUN_DIR/tick_summary.stdout.json"
  printf '%s\n' "$next_prompt" > "$RUN_DIR/implementation_prompt.md"
  printf '%s\n' "$next_task_title" > "$RUN_DIR/next_task_title.txt"
  printf '%s\n' "$classification" > "$RUN_DIR/classification.txt"
  printf '%s\n' "$next_task_category" > "$RUN_DIR/next_task_category.txt"

  if [ -f "$summary_path" ]; then
    cat "$summary_path"
  fi

  if [ "$classification" = "blocked_needs_review" ]; then
    exit 1
  fi
}

main "$@"
