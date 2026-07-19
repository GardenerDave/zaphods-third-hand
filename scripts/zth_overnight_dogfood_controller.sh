#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ZTH_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
WORK="$REPO/.work/dogfood/overnight"
QUEUE="$REPO/.work/dogfood/roadmap_queue.tsv"
STATE="$WORK/state.tsv"
LOCK="$WORK/controller.lock"
LOG_DIR="$WORK/logs"
MANIFEST_DIR="$WORK/manifests"
RUNS_DIR="$WORK/runs"
STATUS_FILE="$WORK/status.json"
DEADLINE_DEFAULT="2026-07-19T08:00:00-04:00"
MAX_STAGES_PER_INVOCATION=3
MAX_RUNTIME_SECONDS=720
MAX_MODEL_ATTEMPTS=3
RUN_ID="$(date +%Y%m%d_%H%M%S)"
MODE="${1:---tick}"

usage() {
  cat <<'EOF'
Usage:
  scripts/zth_overnight_dogfood_controller.sh --tick
  scripts/zth_overnight_dogfood_controller.sh --dry-run
  scripts/zth_overnight_dogfood_controller.sh --status

The controller advances bounded dogfood stages, records evidence, and stops
starting new work after the configured deadline.
EOF
}

load_env() {
  if [ -f "$REPO/.env.local" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO/.env.local"
    set +a
  fi
  : "${ZTH_JARVIS_BASE_URL:?missing ZTH_JARVIS_BASE_URL}"
  : "${ZTH_PUBLIC_HOST_ALIAS:=JARVIS_LOCAL}"
  : "${ZTH_MODEL_ID:=Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf}"
}

now_epoch() { date +%s; }
iso_now() { date -Is; }

deadline_epoch() {
  python3 - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo
print(int(datetime(2026, 7, 19, 8, 0, tzinfo=ZoneInfo("America/New_York")).timestamp()))
PY
}

ensure_dirs() {
  mkdir -p "$WORK" "$LOG_DIR" "$MANIFEST_DIR" "$RUNS_DIR"
  touch "$STATE"
}

stage_status() {
  awk -F '\t' '
    NF >= 4 { last[$2]=$3 "\t" $4 }
    END {
      for (k in last) print k "\t" last[k]
    }
  ' "$STATE"
}

next_stage() {
  python3 - "$QUEUE" "$STATE" <<'PY'
import csv, sys
from pathlib import Path

queue = Path(sys.argv[1])
state = Path(sys.argv[2])
done = set()
if state.exists():
    for row in csv.reader(state.open(encoding="utf-8"), delimiter="\t"):
        if len(row) >= 2:
            done.add(row[1])
for row in csv.reader(queue.open(encoding="utf-8"), delimiter="\t"):
    if not row or row[0].startswith("#") or len(row) < 3:
        continue
    if row[1] not in done:
        print("\t".join(row[:3]))
        break
PY
}

self_generated_stage() {
  printf '%s\t%s\t%s\n' \
    "overnight-status-evidence-manifest" \
    "Create overnight status and evidence manifest." \
    "Summarize the overnight controller evidence, queue exhaustion state, live-run constraints, and next supervised action using only repository-local evidence."
}

write_state() {
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" "$6" "$7" >> "$STATE"
}

stage_dir_for() {
  printf '%s/%s-%s' "$RUNS_DIR" "$RUN_ID" "$1"
}

packet_for_stage() {
  local slug="$1" title="$2" desc="$3" dir="$4"
  cat > "$dir/stage_packet.md" <<EOF
# ZTH Overnight Dogfood Packet

Run ID: $RUN_ID
Slug: $slug
Title: $title

## Objective

$desc

## Authority Boundary

- Inspect repository evidence only.
- Do not expand authority.
- Do not push, merge, deploy, or modify secrets.
- Preserve all failed evidence.

## Allowed Targets

- Existing repository files only.
- Stage-local evidence under .work/dogfood/overnight/.

## Held Targets

- Anything requiring broader authority.

## Implementation Constraints

- Keep local-model input compact.
- Preserve raw output and repair attempts.
- Stop starting new work after the deadline.
- Process at most three stages per invocation.

## Verification Contract

- Review the raw output structure.
- Verify any changed files against the packet allowlist.
- Run the narrowest relevant local checks.

## Stop Conditions

- Deadline reached.
- Malformed model output after three repair attempts.
- Verification failure.
- Scope expansion.

Return strict JSON with keys: verdict, review_state, changed_paths, verification, notes.
EOF
}

call_model() {
  python3 - "$ZTH_JARVIS_BASE_URL" "$ZTH_MODEL_ID" "$1" "$2" <<'PY'
import json, sys, urllib.request
from pathlib import Path
base_url, model, packet_path, out_path = sys.argv[1:5]
packet = Path(packet_path).read_text(encoding="utf-8")
payload = {"model": model, "messages": [{"role":"system","content":"Return valid JSON only."},{"role":"user","content":packet}], "temperature": 0.1, "max_tokens": 1600}
req = urllib.request.Request(base_url.rstrip("/") + "/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req, timeout=1200) as resp:
    data = json.loads(resp.read().decode())
Path(out_path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(out_path)
PY
}

content_from_raw() {
  python3 - "$1" "$2" <<'PY'
import json, sys
from pathlib import Path
raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
content = raw["choices"][0]["message"]["content"]
Path(sys.argv[2]).write_text(content, encoding="utf-8")
json.loads(content)
PY
}

repair_content() {
  local raw="$1"
  local packet="$2"
  local attempt="$3"
  local repair_prompt="$4"
  python3 - "$ZTH_JARVIS_BASE_URL" "$ZTH_MODEL_ID" "$repair_prompt" "$raw" <<'PY'
import json, sys, urllib.request
from pathlib import Path
base_url, model, repair_prompt, raw_path = sys.argv[1:5]
packet = Path(repair_prompt).read_text(encoding="utf-8")
raw = Path(raw_path).read_text(encoding="utf-8")
payload = {"model": model, "messages": [{"role":"system","content":"Return valid JSON only."},{"role":"user","content":"Repair the prior output. Keep the same evidence and only output corrected JSON.\n\nPACKET:\n" + packet[:4500] + "\n\nRAW:\n" + raw[:3500]}], "temperature": 0.0, "max_tokens": 1200}
req = urllib.request.Request(base_url.rstrip("/") + "/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req, timeout=1200) as resp:
    data = json.loads(resp.read().decode())
print(json.dumps(data, indent=2))
PY
}

status_cmd() {
  python3 - "$STATE" "$STATUS_FILE" "$QUEUE" "$DEADLINE_DEFAULT" <<'PY'
import csv, json, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
state = Path(sys.argv[1])
out = Path(sys.argv[2])
queue = Path(sys.argv[3])
deadline = datetime.fromisoformat(sys.argv[4]).astimezone(ZoneInfo("America/New_York"))
rows = []
if state.exists():
    rows = [r for r in csv.reader(state.open(encoding="utf-8"), delimiter="\t") if len(r) >= 4]
completed = [r for r in rows if r[2] == "completed"]
payload = {
    "deadline_local": deadline.isoformat(),
    "queue_path": str(queue),
    "state_path": str(state),
    "completed_count": len(completed),
    "latest_stage": completed[-1][1] if completed else None,
    "working_tree": "clean",
}
out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2))
PY
}

run_stage() {
  local slug="$1" title="$2" desc="$3" deadline="$4" dry_run="$5"
  local dir raw repaired content attempt verdict review_state
  dir="$(stage_dir_for "$slug")"
  if [ "$dry_run" = "1" ]; then
    printf '%s\t%s\t%s\n' "$slug" "$title" "dry-run"
    return 0
  fi
  mkdir -p "$dir"
  packet_for_stage "$slug" "$title" "$desc" "$dir"
  write_state "$RUN_ID" "$slug" "started" "$dir" "$deadline" "$ZTH_PUBLIC_HOST_ALIAS" "review"
  attempt=1
  while [ "$attempt" -le "$MAX_MODEL_ATTEMPTS" ]; do
    raw="$dir/model_output.raw.${attempt}.json"
    repaired="$dir/model_output.repaired.${attempt}.json"
    if ! call_model "$dir/stage_packet.md" "$raw" >"$dir/model_call.${attempt}.log" 2>&1; then
      printf '%s\n' "model call failed" > "$dir/model_call.${attempt}.error"
      attempt=$((attempt + 1))
      continue
    fi
    if content_from_raw "$raw" "$dir/model_content.${attempt}.json"; then
      verdict="completed"
      review_state="ready_for_review"
      cp "$dir/model_content.${attempt}.json" "$dir/model_content.json"
      cp "$raw" "$dir/model_output.raw.json"
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$RUN_ID" "$slug" "$verdict" "$dir" "$review_state" "$(git rev-parse HEAD)" "$(date -Is)" >> "$STATE"
      return 0
    fi
    repaired="$dir/model_output.repaired.${attempt}.json"
    if repair_content "$raw" "$dir/stage_packet.md" "$attempt" "$dir/stage_packet.md" > "$repaired"; then
      :
    fi
    attempt=$((attempt + 1))
  done
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$RUN_ID" "$slug" "blocked" "$dir" "review" "$(git rev-parse HEAD)" "$(date -Is)" >> "$STATE"
  return 1
}

main() {
  case "$MODE" in
    --status)
      ensure_dirs
      status_cmd
      return 0
      ;;
    --dry-run|--tick)
      :
      ;;
    *)
      usage >&2
      return 1
      ;;
  esac

  if [ "$MODE" != "--dry-run" ]; then
    load_env
  fi
  ensure_dirs
  exec 9>"$LOCK"
  flock -n 9 || { echo "overnight controller already running"; return 0; }
  local start now deadline count stage_line slug title desc dry
  start="$(now_epoch)"
  deadline="$(deadline_epoch)"
  if [ "$MODE" = "--tick" ] && [ "$start" -ge "$deadline" ]; then
    echo "deadline reached before new work"
    status_cmd >/dev/null
    return 0
  fi
  dry=0
  [ "$MODE" = "--dry-run" ] && dry=1
  count=0
  while [ "$count" -lt "$MAX_STAGES_PER_INVOCATION" ]; do
    now="$(now_epoch)"
    [ "$now" -lt "$deadline" ] || break
    stage_line="$(next_stage)"
    if [ -z "$stage_line" ]; then
      stage_line="$(self_generated_stage)"
    fi
    [ -n "$stage_line" ] || break
    slug="$(printf '%s' "$stage_line" | cut -f2)"
    title="$(printf '%s' "$stage_line" | cut -f3)"
    desc="$(printf '%s' "$stage_line" | cut -f3-)"
    run_stage "$slug" "$title" "$desc" "$deadline" "$dry"
    count=$((count + 1))
  done
  status_cmd >/dev/null
}

main "$@"
