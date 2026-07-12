#!/usr/bin/env bash
set -euo pipefail

PROMPT_PATCH="${1:?Usage: $0 PROMPT_PATCH [MODEL] [BASE_URL]}"
MODEL="${2:-qwen3-coder-30b-a3b}"
BASE="${3:-http://127.0.0.1:12345/v1}"
FIXTURES="${FIXTURES:-local_harness/logic_probes.example.json}"

if [[ ! -f "$PROMPT_PATCH" ]]; then
    echo "ERROR: Prompt patch not found: $PROMPT_PATCH" >&2
    exit 1
fi

if [[ ! -f "$FIXTURES" ]]; then
    echo "ERROR: Fixtures not found: $FIXTURES" >&2
    exit 1
fi

PATCH_NAME="$(basename "$PROMPT_PATCH")"
PATCH_NAME="${PATCH_NAME%.*}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

RUN="${RUN:-.work/model_auditions/logic_probe_runs/${MODEL}-${PATCH_NAME}-${TIMESTAMP}}"
RAW_DIR="$RUN/raw/$MODEL"

export BASE MODEL RUN RAW_DIR FIXTURES
export SYSTEM_PROMPT="$(cat "$PROMPT_PATCH")"

mkdir -p "$RAW_DIR"

echo "Model:        $MODEL"
echo "Endpoint:     $BASE"
echo "Prompt patch: $PROMPT_PATCH"
echo "Fixtures:     $FIXTURES"
echo "Run:          $RUN"
echo

python3 local_harness/logic_probe.py validate \
    --fixtures "$FIXTURES"

python3 - <<'PY'
import json
import os
import time
import urllib.request
from pathlib import Path

base = os.environ["BASE"].rstrip("/")
model = os.environ["MODEL"]
system_prompt = os.environ["SYSTEM_PROMPT"]
run_dir = Path(os.environ["RUN"])
raw_dir = Path(os.environ["RAW_DIR"])
fixtures_path = Path(os.environ["FIXTURES"])

raw_dir.mkdir(parents=True, exist_ok=True)
fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))

for probe in fixtures["probes"]:
    probe_id = probe["id"]
    destination = raw_dir / f"{probe_id}.json"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": probe["prompt"],
            },
        ],
        "temperature": 0.1,
        "top_p": 0.8,
        "max_tokens": 512,
    }

    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.monotonic()

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))

        elapsed = round(time.monotonic() - started, 3)
        choice = result["choices"][0]
        timings = result.get("timings", {})

        record = {
            "model_id": model,
            "probe_id": probe_id,
            "response_text": choice["message"]["content"],
            "finish_reason": choice.get("finish_reason"),
            "elapsed_seconds": elapsed,
            "usage": result.get("usage", {}),
            "timings": timings,
        }

        speed = timings.get("predicted_per_second", "unknown")
        print(
            f"PASS {probe_id}: "
            f"{speed} generation t/s; "
            f"{elapsed}s elapsed"
        )

    except Exception as exc:
        record = {
            "model_id": model,
            "probe_id": probe_id,
            "response_text": "",
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(f"ERROR {probe_id}: {exc}")

    destination.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

print(f"\nRaw evidence written to: {raw_dir}")
PY

python3 local_harness/logic_probe.py score \
    --fixtures "$FIXTURES" \
    --responses "$RUN/raw" \
    --out-dir "$RUN"

echo
cat "$RUN/LOGIC_PROBE_SUMMARY.md"

echo
echo "Completed run:"
echo "$RUN"
